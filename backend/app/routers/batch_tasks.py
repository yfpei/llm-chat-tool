import json
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import BatchTask, User
from app.schemas import BatchTaskUpdate, BatchTaskResponse
from app.services import batch_service
from app.services.batch_service import UPLOAD_DIR

router = APIRouter(prefix="/api/batch-tasks", tags=["batch-tasks"])


def _resolve_file_path(file_id: str) -> str:
    result_path = os.path.join(UPLOAD_DIR, f"{file_id}_result.xlsx")
    if os.path.exists(result_path):
        return result_path
    return os.path.join(UPLOAD_DIR, f"{file_id}.xlsx")


def _verify_ownership(task: BatchTask | None, current_user: User):
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")


@router.get("", response_model=list[BatchTaskResponse])
async def list_batch_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BatchTask)
        .where(BatchTask.user_id == current_user.id)
        .order_by(BatchTask.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{task_id}", response_model=BatchTaskResponse)
async def get_batch_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    _verify_ownership(task, current_user)
    return task


@router.put("/{task_id}", response_model=BatchTaskResponse)
async def update_batch_task(
    task_id: str,
    data: BatchTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    _verify_ownership(task, current_user)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}/preview")
async def get_task_preview(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    _verify_ownership(task, current_user)
    file_path = _resolve_file_path(task.file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    info = batch_service.parse_upload(file_path)
    return {"columns": info["columns"], "headers": info["headers"], "total_rows": info["total_rows"], "preview": info["preview"]}


@router.get("/{task_id}/results")
async def get_task_results(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    _verify_ownership(task, current_user)
    file_path = _resolve_file_path(task.file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    import openpyxl
    wb = openpyxl.load_workbook(file_path, read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(c) if c is not None else "" for c in next(rows_iter, [])]

    input_col_indices: dict[str, int] = {}
    output_col_idx = len(headers) - 1
    parse_json_enabled = False
    if task.config_json:
        try:
            cfg = json.loads(task.config_json)
            input_cols = cfg.get("input_columns")
            if not input_cols:
                input_col = cfg.get("input_column", "")
                input_cols = [input_col] if input_col else []
            for col_name in input_cols:
                if col_name in headers:
                    input_col_indices[col_name] = headers.index(col_name)
            output_col = cfg.get("output_column_name", "")
            if output_col in headers:
                output_col_idx = headers.index(output_col)
            parse_json_enabled = cfg.get("parse_json", False)
        except (json.JSONDecodeError, ValueError):
            pass

    parsed_field_cols: list[tuple[int, str]] = []
    if parse_json_enabled and output_col_idx < len(headers):
        for i in range(output_col_idx + 1, len(headers)):
            parsed_field_cols.append((i, headers[i]))

    def build_input_label(row: tuple) -> str:
        parts = []
        for col_name, ci in input_col_indices.items():
            val = str(row[ci]) if ci < len(row) and row[ci] is not None else ""
            parts.append(f"{col_name}: {val}")
        return "; ".join(parts)

    results = []
    for row_idx, row in enumerate(rows_iter, start=2):
        input_val = build_input_label(row)
        output_val = str(row[output_col_idx]) if output_col_idx < len(row) and row[output_col_idx] is not None else ""
        item: dict = {
            "row": row_idx,
            "input": input_val,
            "output": output_val,
            "status": "success" if output_val else "error",
        }
        if parsed_field_cols:
            parsed: dict[str, str] = {}
            for ci, name in parsed_field_cols:
                val = row[ci] if ci < len(row) and row[ci] is not None else ""
                parsed[name] = str(val)
            if any(v for v in parsed.values()):
                item["parsed"] = parsed
        results.append(item)

    wb.close()
    return results


@router.delete("/{task_id}")
async def delete_batch_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    _verify_ownership(task, current_user)
    for suffix in (".xlsx", "_original.xlsx", "_result.xlsx"):
        p = os.path.join(UPLOAD_DIR, f"{task.file_id}{suffix}")
        if os.path.exists(p):
            os.remove(p)
    await db.delete(task)
    await db.commit()
    return {"message": "deleted"}
