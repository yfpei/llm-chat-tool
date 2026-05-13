import json
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.deps import get_current_user
from app.models import BatchTask, User
from app.schemas import ClassificationEvalRequest, LLMScoringEvalRequest
from app.services import eval_service

router = APIRouter(prefix="/api/eval", tags=["eval"])


@router.post("/{task_id}/run-classification")
async def run_classification_eval(
    task_id: str,
    body: ClassificationEvalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # Save eval config to task
    existing = {}
    if task.eval_config_json:
        try:
            existing = json.loads(task.eval_config_json)
        except Exception:
            pass
    existing["enabled"] = True
    existing["method"] = "classification"
    existing["classification"] = body.config.model_dump()
    task.eval_config_json = json.dumps(existing, ensure_ascii=False)
    await db.commit()

    try:
        result = eval_service.run_classification_eval(
            task.file_id,
            body.config.label_column,
            body.config.predict_column,
            [m.model_dump() for m in body.config.mappings],
        )
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="结果文件不存在，请先跑批")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评测失败: {str(e)}")


@router.post("/{task_id}/run-llm-scoring")
async def run_llm_scoring_eval(
    task_id: str,
    body: LLMScoringEvalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # Save eval config to task
    existing = {}
    if task.eval_config_json:
        try:
            existing = json.loads(task.eval_config_json)
        except Exception:
            pass
    existing["enabled"] = True
    existing["method"] = "llm_scoring"
    existing["llm_scoring"] = body.config.model_dump()
    task.eval_config_json = json.dumps(existing, ensure_ascii=False)
    await db.commit()

    async def event_stream():
        async for event in eval_service.run_llm_scoring(
            db, task.file_id, body.config.api_key_id,
            body.config.score_column, body.config.prompt,
            body.config.output_column_name, body.config.concurrency,
            input_columns=body.config.input_columns,
        ):
            t = event.get("type", "error")
            if t == "error":
                yield f"event: error\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                return
            yield f"event: {t}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    return EventSourceResponse(event_stream())


@router.get("/{task_id}/classification-result")
async def get_classification_result(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    result = eval_service.get_classification_eval_file(task.file_id)
    if not result:
        raise HTTPException(status_code=404, detail="评测结果不存在，请先执行客观评测")
    return {"has_result": True}


@router.get("/{task_id}/classification-download")
async def download_classification(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    file_path = eval_service.get_classification_eval_file(task.file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="评测结果文件不存在")
    filename = f"{task.title or 'eval'}_评测结果.xlsx"
    return FileResponse(file_path, filename=filename,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/{task_id}/llm-scoring-download")
async def download_llm_scoring(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    file_path = eval_service.get_llm_scoring_file(task.file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="评分结果文件不存在")
    filename = f"{task.title or 'scoring'}_评分结果.xlsx"
    return FileResponse(file_path, filename=filename,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
