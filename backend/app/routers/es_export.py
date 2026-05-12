import json
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.deps import get_current_user
from app.models import EsExportTask, User
from app.schemas import (
    EsExportRequest,
    EsExportTaskCreate,
    EsExportTaskResponse,
    EsExportTaskUpdate,
    EsPreviewRequest,
)
from app.services import es_service
from app.utils.crypto import decrypt, encrypt

router = APIRouter(prefix="/api/es-export", tags=["es-export"])

UPLOAD_DIR = os.environ.get(
    "UPLOAD_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads"),
)


def _task_to_response(task: EsExportTask) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "es_host": task.es_host,
        "es_username": task.es_username,
        "index_name": task.index_name,
        "query_dsl": task.query_dsl,
        "output_fields": task.output_fields,
        "status": task.status,
        "total_hits": task.total_hits,
        "exported_count": task.exported_count,
        "file_id": task.file_id,
        "config_json": task.config_json,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def _get_password(task: EsExportTask) -> str | None:
    if task.es_password:
        try:
            return decrypt(task.es_password)
        except Exception:
            return task.es_password
    return None


def _verify_ownership(task: EsExportTask | None, current_user: User):
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")


@router.post("/tasks", response_model=EsExportTaskResponse)
async def create_task(data: EsExportTaskCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = EsExportTask(
        title=data.title,
        es_host=data.es_host,
        es_username=data.es_username,
        es_password=encrypt(data.es_password) if data.es_password else None,
        status="created",
        user_id=current_user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _task_to_response(task)


@router.get("/tasks", response_model=list[EsExportTaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(EsExportTask)
        .where(EsExportTask.user_id == current_user.id)
        .order_by(EsExportTask.created_at.desc())
    )
    tasks = result.scalars().all()
    return [_task_to_response(t) for t in tasks]


@router.get("/tasks/{task_id}", response_model=EsExportTaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(EsExportTask, task_id)
    _verify_ownership(task, current_user)
    return _task_to_response(task)


@router.put("/tasks/{task_id}", response_model=EsExportTaskResponse)
async def update_task(task_id: str, data: EsExportTaskUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(EsExportTask, task_id)
    _verify_ownership(task, current_user)

    update_data = data.model_dump(exclude_unset=True)
    if "es_password" in update_data and update_data["es_password"]:
        update_data["es_password"] = encrypt(update_data["es_password"])

    for key, value in update_data.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)
    return _task_to_response(task)


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(EsExportTask, task_id)
    _verify_ownership(task, current_user)
    # Clean up exported files
    if task.file_id:
        for suffix in (".xlsx",):
            p = os.path.join(es_service.UPLOAD_DIR, f"{task.file_id}{suffix}")
            if os.path.exists(p):
                os.remove(p)
    await db.delete(task)
    await db.commit()
    return {"ok": True}


@router.post("/tasks/{task_id}/test-connection")
async def test_connection(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(EsExportTask, task_id)
    _verify_ownership(task, current_user)
    try:
        result = es_service.test_connection(task.es_host, task.es_username, _get_password(task))
        return {"ok": True, "info": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")


@router.get("/tasks/{task_id}/indices")
async def list_indices(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(EsExportTask, task_id)
    _verify_ownership(task, current_user)
    try:
        indices = es_service.list_indices(task.es_host, task.es_username, _get_password(task))
        return {"indices": indices}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取索引失败: {str(e)}")


@router.get("/tasks/{task_id}/mapping")
async def get_mapping(task_id: str, index: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(EsExportTask, task_id)
    _verify_ownership(task, current_user)
    try:
        fields = es_service.get_mapping(task.es_host, task.es_username, _get_password(task), index)
        return {"fields": fields}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取映射失败: {str(e)}")


@router.post("/tasks/{task_id}/preview")
async def preview_query(task_id: str, data: EsPreviewRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(EsExportTask, task_id)
    _verify_ownership(task, current_user)
    if not task.index_name:
        raise HTTPException(status_code=400, detail="请先选择索引")

    try:
        result = es_service.preview_query(
            host=task.es_host,
            username=task.es_username,
            password=_get_password(task),
            index_name=task.index_name,
            query_dsl=data.query_dsl,
            output_fields=data.output_fields,
            page=data.page,
            page_size=data.page_size,
            top_n=data.top_n,
        )
        task.total_hits = result["total"]
        await db.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"查询失败: {str(e)}")


@router.post("/tasks/{task_id}/export")
async def export_excel(task_id: str, data: EsExportRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(EsExportTask, task_id)
    _verify_ownership(task, current_user)
    if not task.index_name:
        raise HTTPException(status_code=400, detail="请先选择索引")

    task.status = "running"
    await db.commit()

    async def event_generator():
        try:
            gen = es_service.export_to_excel(
                host=task.es_host,
                username=task.es_username,
                password=_get_password(task),
                index_name=task.index_name,
                query_dsl=data.query_dsl,
                output_fields=data.output_fields,
                top_n=data.top_n,
            )
            for event in gen:
                if event["type"] == "progress":
                    task.exported_count = event["completed"]
                    task.total_hits = event["total"]
                    await db.commit()
                    yield {"event": "progress", "data": json.dumps(event)}
                elif event["type"] == "done":
                    task.status = "completed"
                    task.exported_count = event["count"]
                    task.file_id = event["file_id"]
                    await db.commit()
                    yield {"event": "done", "data": json.dumps(event)}
                elif event["type"] == "error":
                    task.status = "failed"
                    await db.commit()
                    yield {"event": "error", "data": json.dumps(event)}
        except Exception as e:
            task.status = "failed"
            await db.commit()
            yield {"event": "error", "data": json.dumps({"type": "error", "content": str(e)})}

    return EventSourceResponse(event_generator())


@router.get("/tasks/{task_id}/download")
async def download_excel(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(EsExportTask, task_id)
    _verify_ownership(task, current_user)
    if not task.file_id:
        raise HTTPException(status_code=400, detail="尚未导出文件")

    file_path = os.path.join(UPLOAD_DIR, f"{task.file_id}.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    filename = f"{task.title}.xlsx"
    return FileResponse(path=file_path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/files/{file_id}/download")
def download_file(file_id: str):
    """Serve an exported Excel file directly by file_id, no DB lookup needed."""
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    filename = f"export_{file_id[:8]}.xlsx"
    return FileResponse(path=file_path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
