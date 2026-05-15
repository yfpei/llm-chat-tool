import json
import os
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.deps import get_current_user
from app.models import MySQLExportTask, User
from app.schemas import (
    MySQLExportRequest,
    MySQLExportTaskCreate,
    MySQLExportTaskResponse,
    MySQLExportTaskUpdate,
    MySQLPreviewRequest,
)
from app.services import mysql_service
from app.utils.crypto import decrypt, encrypt

router = APIRouter(prefix="/api/mysql-export", tags=["mysql-export"])

UPLOAD_DIR = os.environ.get(
    "UPLOAD_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads"),
)


def _task_to_response(task: MySQLExportTask) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "mysql_host": task.mysql_host,
        "mysql_port": task.mysql_port,
        "mysql_username": task.mysql_username,
        "database_name": task.database_name,
        "table_name": task.table_name,
        "where_clause": task.where_clause,
        "custom_sql": task.custom_sql,
        "output_columns": task.output_columns,
        "status": task.status,
        "total_rows": task.total_rows,
        "exported_count": task.exported_count,
        "file_id": task.file_id,
        "config_json": task.config_json,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def _get_password(task: MySQLExportTask) -> str | None:
    if task.mysql_password:
        try:
            return decrypt(task.mysql_password)
        except Exception:
            return task.mysql_password
    return None


def _verify_ownership(task: MySQLExportTask | None, current_user: User):
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")


@router.post("/tasks", response_model=MySQLExportTaskResponse)
async def create_task(data: MySQLExportTaskCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = MySQLExportTask(
        title=data.title,
        mysql_host=data.mysql_host,
        mysql_port=data.mysql_port,
        mysql_username=data.mysql_username,
        mysql_password=encrypt(data.mysql_password) if data.mysql_password else None,
        status="created",
        user_id=current_user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _task_to_response(task)


@router.get("/tasks", response_model=list[MySQLExportTaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(MySQLExportTask)
        .where(MySQLExportTask.user_id == current_user.id)
        .order_by(MySQLExportTask.created_at.desc())
    )
    tasks = result.scalars().all()
    return [_task_to_response(t) for t in tasks]


@router.get("/tasks/{task_id}", response_model=MySQLExportTaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(MySQLExportTask, task_id)
    _verify_ownership(task, current_user)
    return _task_to_response(task)


@router.put("/tasks/{task_id}", response_model=MySQLExportTaskResponse)
async def update_task(task_id: str, data: MySQLExportTaskUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(MySQLExportTask, task_id)
    _verify_ownership(task, current_user)

    update_data = data.model_dump(exclude_unset=True)
    if "mysql_password" in update_data:
        if update_data["mysql_password"]:
            update_data["mysql_password"] = encrypt(update_data["mysql_password"])
        else:
            update_data["mysql_password"] = None

    for key, value in update_data.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)
    return _task_to_response(task)


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(MySQLExportTask, task_id)
    _verify_ownership(task, current_user)
    if task.file_id:
        for suffix in (".xlsx",):
            p = os.path.join(mysql_service.UPLOAD_DIR, f"{task.file_id}{suffix}")
            if os.path.exists(p):
                os.remove(p)
    await db.delete(task)
    await db.commit()
    return {"ok": True}


@router.post("/tasks/{task_id}/test-connection")
async def test_connection(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(MySQLExportTask, task_id)
    _verify_ownership(task, current_user)
    try:
        result = mysql_service.test_connection(task.mysql_host, task.mysql_port, task.mysql_username, _get_password(task))
        return {"ok": True, "info": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")


@router.get("/tasks/{task_id}/databases")
async def list_databases(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(MySQLExportTask, task_id)
    _verify_ownership(task, current_user)
    try:
        databases = mysql_service.list_databases(task.mysql_host, task.mysql_port, task.mysql_username, _get_password(task))
        return {"databases": databases}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取数据库列表失败: {str(e)}")


@router.get("/tasks/{task_id}/tables")
async def list_tables(task_id: str, database: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(MySQLExportTask, task_id)
    _verify_ownership(task, current_user)
    try:
        tables = mysql_service.list_tables(task.mysql_host, task.mysql_port, task.mysql_username, _get_password(task), database)
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取表列表失败: {str(e)}")


@router.get("/tasks/{task_id}/columns")
async def get_columns(task_id: str, database: str, table: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(MySQLExportTask, task_id)
    _verify_ownership(task, current_user)
    try:
        fields = mysql_service.get_columns(task.mysql_host, task.mysql_port, task.mysql_username, _get_password(task), database, table)
        return {"fields": fields}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取列信息失败: {str(e)}")


@router.post("/tasks/{task_id}/preview")
async def preview_query(task_id: str, data: MySQLPreviewRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(MySQLExportTask, task_id)
    _verify_ownership(task, current_user)

    db_name = data.database_name or task.database_name
    if not db_name:
        raise HTTPException(status_code=400, detail="请先选择数据库")

    try:
        result = mysql_service.preview_query(
            host=task.mysql_host,
            port=task.mysql_port,
            username=task.mysql_username,
            password=_get_password(task),
            database=db_name,
            table=data.table_name or task.table_name or "",
            where_clause=data.where_clause or task.where_clause or "",
            custom_sql=data.custom_sql or task.custom_sql or "",
            output_columns=data.output_columns,
            page=data.page,
            page_size=data.page_size,
            top_n=data.top_n,
        )
        task.total_rows = result["total"]
        await db.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"查询失败: {str(e)}")


@router.post("/tasks/{task_id}/export")
async def export_excel(task_id: str, data: MySQLExportRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = await db.get(MySQLExportTask, task_id)
    _verify_ownership(task, current_user)

    db_name = data.database_name or task.database_name
    if not db_name:
        raise HTTPException(status_code=400, detail="请先选择数据库")

    task.status = "running"
    await db.commit()

    async def event_generator():
        try:
            gen = mysql_service.export_to_excel(
                host=task.mysql_host,
                port=task.mysql_port,
                username=task.mysql_username,
                password=_get_password(task),
                database=db_name,
                table=data.table_name or task.table_name or "",
                where_clause=data.where_clause or task.where_clause or "",
                custom_sql=data.custom_sql or task.custom_sql or "",
                output_columns=data.output_columns,
                top_n=data.top_n,
            )
            for event in gen:
                if event["type"] == "progress":
                    task.exported_count = event["completed"]
                    task.total_rows = event["total"]
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
    task = await db.get(MySQLExportTask, task_id)
    _verify_ownership(task, current_user)
    if not task.file_id:
        raise HTTPException(status_code=400, detail="尚未导出文件")

    file_path = os.path.join(UPLOAD_DIR, f"{task.file_id}.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    safe_title = re.sub(r'[<>:"/\\|?*]', '_', task.title)
    filename = f"{safe_title}.xlsx"
    return FileResponse(path=file_path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/files/{file_id}/download")
def download_file(file_id: str):
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    filename = f"export_{file_id[:8]}.xlsx"
    return FileResponse(path=file_path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
