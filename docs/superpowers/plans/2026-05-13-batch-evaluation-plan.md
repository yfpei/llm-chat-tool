# Batch Evaluation (Step 5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional step 5 evaluation to batch tasks — classification metrics (confusion matrix, per-class P/R/F1, micro/macro avg) and LLM subjective scoring — both embeddable in batch flow and usable standalone.

**Architecture:** New `eval_config_json` column on `batch_tasks`, independent `/api/eval` route group, `eval_service.py` with sklearn for classification and async LLM for scoring, `EvalPanel.vue` as reusable component embedded in `BatchPanel.vue` step 5 and standalone `/eval` page.

**Tech Stack:** FastAPI, scikit-learn, openpyxl, Vue 3 + Naive UI, TypeScript

---

## File Map

**Create (backend):**
- `backend/app/routers/eval.py` — `/api/eval` endpoints
- `backend/app/services/eval_service.py` — classification metrics + LLM scoring logic

**Create (frontend):**
- `frontend/src/components/EvalPanel.vue` — reusable evaluation component
- `frontend/src/views/EvalPage.vue` — standalone `/eval` page
- `frontend/src/api/eval.ts` — eval API client

**Modify (backend):**
- `backend/app/models.py` — add `eval_config_json` to BatchTask
- `backend/app/schemas.py` — add eval Pydantic schemas
- `backend/app/main.py` — register eval router
- `backend/requirements.txt` — add scikit-learn

**Modify (frontend):**
- `frontend/src/types/index.ts` — add eval TypeScript types
- `frontend/src/components/BatchPanel.vue` — step 3 eval config panel + step 5
- `frontend/src/router/index.ts` — add `/eval` route

---

### Task 1: Add scikit-learn dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add scikit-learn to requirements.txt**

```bash
echo "scikit-learn>=1.3.0,<2.0.0" >> backend/requirements.txt
```

- [ ] **Step 2: Install the dependency**

```bash
cd backend && pip install scikit-learn>=1.3.0
```

- [ ] **Step 3: Commit**

```
git add backend/requirements.txt
git commit -m "deps: add scikit-learn for classification evaluation"
```

---

### Task 2: Add eval_config_json to BatchTask model

**Files:**
- Modify: `backend/app/models.py:99-109`

- [ ] **Step 1: Add the eval_config_json column**

In `backend/app/models.py`, add `eval_config_json` after `config_json` in the `BatchTask` class:

```python
class BatchTask(Base):
    __tablename__ = "batch_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), default="未命名任务")
    file_id = Column(String(36), nullable=False)
    filename = Column(String(500), nullable=False)
    columns = Column(Text, nullable=False)
    headers = Column(Text, nullable=False)
    total_rows = Column(Integer, default=0)
    status = Column(String(20), default="uploaded")
    config_json = Column(Text, nullable=True)
    eval_config_json = Column(Text, nullable=True)  # <-- new
    progress_completed = Column(Integer, default=0)
    progress_total = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="batch_tasks")
```

- [ ] **Step 2: Add migration in database.py**

In `backend/app/database.py`, find the `init_db` function and add the new column migration:

```python
# Add eval_config_json column (migration)
try:
    async with engine.connect() as conn:
        await conn.execute(text("ALTER TABLE batch_tasks ADD COLUMN eval_config_json TEXT"))
        await conn.commit()
except Exception:
    pass  # column already exists
```

*(Place this after the existing `check_column` pattern used for other migrations.)*

- [ ] **Step 3: Commit**

```
git add backend/app/models.py backend/app/database.py
git commit -m "feat: add eval_config_json column to batch_tasks"
```

---

### Task 3: Add eval Pydantic schemas

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Add eval schemas at the end of schemas.py**

```python
# --- Eval Schemas ---

class MappingRule(BaseModel):
    model_output: str
    label_value: str


class ClassificationEvalConfig(BaseModel):
    label_column: str
    predict_column: str
    mappings: list[MappingRule] = []


class LLMScoringEvalConfig(BaseModel):
    api_key_id: int
    prompt: str
    score_column: str
    output_column_name: str = "评分"
    concurrency: int = 3


class EvalConfig(BaseModel):
    enabled: bool = False
    method: str = "classification"  # "classification" | "llm_scoring" | "both"

    classification: ClassificationEvalConfig | None = None
    llm_scoring: LLMScoringEvalConfig | None = None


class ClassificationEvalRequest(BaseModel):
    task_id: str
    config: ClassificationEvalConfig


class LLMScoringEvalRequest(BaseModel):
    task_id: str
    config: LLMScoringEvalConfig


class PerClassMetric(BaseModel):
    class_name: str
    precision: float
    recall: float
    f1: float


class AvgMetric(BaseModel):
    precision: float
    recall: float
    f1: float


class ClassificationEvalResponse(BaseModel):
    accuracy: float
    total_samples: int
    num_classes: int
    confusion_matrix: list[list[int]]
    labels: list[str]
    per_class: list[PerClassMetric]
    micro_avg: AvgMetric
    macro_avg: AvgMetric
    skipped_count: int = 0
```

- [ ] **Step 2: Add eval_config_json to BatchTaskUpdate**

Find the existing `BatchTaskUpdate` class in `schemas.py` and add `eval_config_json`:

```python
class BatchTaskUpdate(BaseModel):
    title: Optional[str] = None
    config_json: Optional[str] = None
    eval_config_json: Optional[str] = None  # <-- new
    status: Optional[str] = None
    progress_completed: Optional[int] = None
    progress_total: Optional[int] = None
```

- [ ] **Step 3: Commit**

```
git add backend/app/schemas.py
git commit -m "feat: add eval Pydantic schemas"
```

---

### Task 4: Implement evaluation service — classification

**Files:**
- Create: `backend/app/services/eval_service.py`

- [ ] **Step 1: Create eval_service.py with classification evaluation logic**

```python
import os
from collections import Counter

import openpyxl
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)

UPLOAD_DIR = os.environ.get(
    "UPLOAD_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads"),
)


def run_classification_eval(
    file_id: str,
    label_column: str,
    predict_column: str,
    mappings: list[dict],  # [{model_output, label_value}]
) -> dict:
    """Calculate classification metrics from the batch result file.

    Returns a dict matching ClassificationEvalResponse schema.
    """
    result_path = _find_result_file(file_id)
    if not result_path:
        raise FileNotFoundError(f"Result file not found for {file_id}")

    mapping_dict: dict[str, str] = {m["model_output"]: m["label_value"] for m in mappings}

    wb = openpyxl.load_workbook(result_path)
    ws = wb.active

    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    if label_column not in headers or predict_column not in headers:
        wb.close()
        missing = []
        if label_column not in headers:
            missing.append(label_column)
        if predict_column not in headers:
            missing.append(predict_column)
        raise ValueError(f"Columns not found: {', '.join(missing)}")

    label_idx = headers.index(label_column)
    predict_idx = headers.index(predict_column)

    y_true: list[str] = []
    y_pred: list[str] = []
    skipped = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        label_val = str(row[label_idx]).strip() if row[label_idx] is not None else ""
        raw_predict = str(row[predict_idx]).strip() if row[predict_idx] is not None else ""

        # Apply mapping
        mapped = mapping_dict.get(raw_predict, raw_predict)

        if not label_val or not mapped:
            skipped += 1
            continue

        y_true.append(label_val)
        y_pred.append(mapped)

    wb.close()

    if not y_true:
        raise ValueError("No valid data rows found after applying mapping")

    labels = sorted(set(y_true + y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_list: list[list[int]] = cm.tolist()

    accuracy = float(accuracy_score(y_true, y_pred))

    # Per-class metrics
    per_class: list[dict] = []
    for i, label in enumerate(labels):
        tp = cm[i][i]
        fp = sum(cm[j][i] for j in range(len(labels))) - tp
        fn = sum(cm[i][j] for j in range(len(labels))) - tp

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class.append({
            "class_name": label,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        })

    # Micro average
    micro_precision = float(precision_score(y_true, y_pred, average="micro", zero_division=0))
    micro_recall = float(recall_score(y_true, y_pred, average="micro", zero_division=0))
    micro_f1 = float(f1_score(y_true, y_pred, average="micro", zero_division=0))

    # Macro average
    macro_precision = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    macro_recall = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

    # Write result Excel
    _write_classification_excel(
        file_id, labels, cm_list, cm, accuracy,
        per_class, micro_precision, micro_recall, micro_f1,
        macro_precision, macro_recall, macro_f1,
    )

    return {
        "accuracy": round(accuracy, 4),
        "total_samples": len(y_true),
        "num_classes": len(labels),
        "confusion_matrix": cm_list,
        "labels": labels,
        "per_class": per_class,
        "micro_avg": {
            "precision": round(micro_precision, 4),
            "recall": round(micro_recall, 4),
            "f1": round(micro_f1, 4),
        },
        "macro_avg": {
            "precision": round(macro_precision, 4),
            "recall": round(macro_recall, 4),
            "f1": round(macro_f1, 4),
        },
        "skipped_count": skipped,
    }


def _find_result_file(file_id: str) -> str | None:
    """Find _result.xlsx file for a given file_id."""
    base = os.path.join(UPLOAD_DIR, file_id)
    result_path = base + "_result.xlsx"
    if os.path.exists(result_path):
        return result_path
    return None


def _write_classification_excel(
    file_id: str, labels: list[str], cm_list: list[list[int]], cm,
    accuracy: float, per_class: list[dict],
    micro_p: float, micro_r: float, micro_f1: float,
    macro_p: float, macro_r: float, macro_f1: float,
):
    """Write classification eval results to _eval_classification.xlsx."""
    out_path = os.path.join(UPLOAD_DIR, file_id + "_eval_classification.xlsx")
    wb = openpyxl.Workbook()

    # Sheet 1: Confusion Matrix
    ws1 = wb.active
    ws1.title = "混淆矩阵"
    ws1.cell(row=1, column=1, value="实际\\预测")
    for j, label in enumerate(labels, start=2):
        ws1.cell(row=1, column=j, value=label)
    # Add column sums header
    col_sum_col = len(labels) + 2
    ws1.cell(row=1, column=col_sum_col, value="合计")
    for i, label in enumerate(labels):
        ws1.cell(row=i + 2, column=1, value=label)
        row_sum = 0
        for j in range(len(labels)):
            ws1.cell(row=i + 2, column=j + 2, value=cm_list[i][j])
            row_sum += cm_list[i][j]
        ws1.cell(row=i + 2, column=col_sum_col, value=row_sum)
    # Row sums row
    row_sum_row = len(labels) + 2
    ws1.cell(row=row_sum_row, column=1, value="合计")
    total_all = 0
    for j in range(len(labels)):
        col_sum = sum(cm_list[i][j] for i in range(len(labels)))
        ws1.cell(row=row_sum_row, column=j + 2, value=col_sum)
        total_all += col_sum
    ws1.cell(row=row_sum_row, column=col_sum_col, value=total_all)

    # Sheet 2: Per-class metrics
    ws2 = wb.create_sheet("各分类指标")
    ws2.cell(row=1, column=1, value="分类")
    ws2.cell(row=1, column=2, value="Precision")
    ws2.cell(row=1, column=3, value="Recall")
    ws2.cell(row=1, column=4, value="F1 Score")
    for i, pc in enumerate(per_class, start=2):
        ws2.cell(row=i, column=1, value=pc["class_name"])
        ws2.cell(row=i, column=2, value=pc["precision"])
        ws2.cell(row=i, column=3, value=pc["recall"])
        ws2.cell(row=i, column=4, value=pc["f1"])

    # Sheet 3: Summary metrics
    ws3 = wb.create_sheet("汇总指标")
    ws3.cell(row=1, column=1, value="指标")
    ws3.cell(row=1, column=2, value="Precision")
    ws3.cell(row=1, column=3, value="Recall")
    ws3.cell(row=1, column=4, value="F1 Score")
    ws3.cell(row=2, column=1, value="Accuracy")
    ws3.cell(row=2, column=2, value=round(accuracy, 4))
    ws3.cell(row=3, column=1, value="Micro Avg")
    ws3.cell(row=3, column=2, value=round(micro_p, 4))
    ws3.cell(row=3, column=3, value=round(micro_r, 4))
    ws3.cell(row=3, column=4, value=round(micro_f1, 4))
    ws3.cell(row=4, column=1, value="Macro Avg")
    ws3.cell(row=4, column=2, value=round(macro_p, 4))
    ws3.cell(row=4, column=3, value=round(macro_r, 4))
    ws3.cell(row=4, column=4, value=round(macro_f1, 4))

    wb.save(out_path)
    wb.close()


def get_classification_eval_result(file_id: str) -> dict | None:
    """Get saved classification eval result, or None if not yet run."""
    result_path = _find_result_file(file_id)
    eval_path = os.path.join(UPLOAD_DIR, file_id + "_eval_classification.xlsx")
    if not result_path or not os.path.exists(eval_path):
        return None
    return {"has_result": True, "eval_file": f"{file_id}_eval_classification.xlsx"}


def get_classification_eval_file(file_id: str) -> str | None:
    path = os.path.join(UPLOAD_DIR, file_id + "_eval_classification.xlsx")
    return path if os.path.exists(path) else None
```

- [ ] **Step 2: Commit**

```
git add backend/app/services/eval_service.py
git commit -m "feat: add classification evaluation service"
```

---

### Task 5: Implement evaluation service — LLM scoring

**Files:**
- Modify: `backend/app/services/eval_service.py` — append LLM scoring functions

- [ ] **Step 1: Add LLM scoring async generator to eval_service.py**

Append the following to `backend/app/services/eval_service.py`:

```python
import asyncio
import re
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey
from app.services.key_service import get_decrypted_key
from app.services.llm import create_provider


async def run_llm_scoring(
    db: AsyncSession,
    file_id: str,
    api_key_id: int,
    score_column: str,
    prompt_template: str,
    output_column_name: str,
    concurrency: int = 3,
) -> AsyncGenerator[dict, None]:
    """SSE generator for LLM subjective scoring.

    Yields: progress, row_result, row_error, done, error
    """
    result_path = _find_result_file(file_id)
    if not result_path:
        yield {"type": "error", "message": "结果文件不存在，请先跑批"}
        return

    # Get API key
    api_key = await db.get(ApiKey, api_key_id)
    if not api_key:
        yield {"type": "error", "message": "API Key 不存在"}
        return
    plaintext_key = get_decrypted_key(api_key)

    wb = openpyxl.load_workbook(result_path)
    ws = wb.active
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]

    if score_column not in headers:
        yield {"type": "error", "message": f"列 '{score_column}' 不存在"}
        wb.close()
        return

    score_col_idx = headers.index(score_column)

    # Read all rows
    rows_data: list[tuple[int, dict[str, str]]] = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        row_dict: dict[str, str] = {}
        for ci, col_name in enumerate(headers):
            if ci < len(row) and row[ci] is not None:
                row_dict[col_name] = str(row[ci])
        if score_column in row_dict:
            rows_data.append((row_idx, row_dict))
    wb.close()

    total = len(rows_data)
    if total == 0:
        yield {"type": "error", "message": "无数据行"}
        return

    # Add score column header and save
    wb = openpyxl.load_workbook(result_path)
    ws = wb.active
    score_out_col = len(headers) + 1
    ws.cell(row=1, column=score_out_col, value=output_column_name)
    # Also write back to the _llm_scoring file
    scoring_path = os.path.join(UPLOAD_DIR, file_id + "_eval_llm_scoring.xlsx")
    wb.save(scoring_path)

    results: dict[int, str] = {}
    results_lock = asyncio.Lock()
    completed = 0
    completed_lock = asyncio.Lock()
    sem = asyncio.Semaphore(concurrency)

    use_native_thinking = api_key.enable_thinking

    async def process_one(row_idx: int, row_data: dict[str, str]):
        nonlocal completed
        prompt = prompt_template
        for col_name, cell_value in row_data.items():
            prompt = prompt.replace("{{" + col_name + "}}", str(cell_value))
        try:
            provider = create_provider(
                api_key.provider, api_key.base_url, plaintext_key,
                api_key.model, use_native_thinking,
            )
            messages = [{"role": "user", "content": prompt}]
            full = ""
            async for chunk in provider.chat_stream(messages):
                full += chunk
            score = full.strip()
            # Remove thinking if present
            score = re.sub(r'</?(?:think|unused\d+)[^>]*>.*?</(?:think|unused\d+)>', '', score, flags=re.DOTALL | re.IGNORECASE).strip()
            async with results_lock:
                results[row_idx] = score
            return (row_idx, score, None)
        except Exception as e:
            return (row_idx, "", str(e))

    async def limited_process(row_idx: int, row_data: dict[str, str]):
        async with sem:
            return await process_one(row_idx, row_data)

    tasks_list = [asyncio.create_task(limited_process(r, d)) for r, d in rows_data]
    pending = set(tasks_list)

    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            row_idx, score, error = t.result()
            async with completed_lock:
                completed += 1
            yield {"type": "progress", "completed": completed, "total": total}
            if error:
                yield {"type": "row_error", "row": row_idx, "error": error}
            else:
                yield {"type": "row_result", "row": row_idx, "score": score}

    # Write scores into the scoring Excel
    wb = openpyxl.load_workbook(scoring_path)
    ws = wb.active
    for row_idx, score in results.items():
        ws.cell(row=row_idx, column=score_out_col, value=score)
    wb.save(scoring_path)
    wb.close()

    # Calculate average
    numeric_scores = []
    for s in results.values():
        try:
            numeric_scores.append(float(s))
        except ValueError:
            pass
    avg_score = round(sum(numeric_scores) / len(numeric_scores), 2) if numeric_scores else 0

    yield {"type": "done", "total": total, "avg_score": avg_score}


def get_llm_scoring_file(file_id: str) -> str | None:
    path = os.path.join(UPLOAD_DIR, file_id + "_eval_llm_scoring.xlsx")
    return path if os.path.exists(path) else None
```

- [ ] **Step 2: Commit**

```
git add backend/app/services/eval_service.py
git commit -m "feat: add LLM scoring evaluation service"
```

---

### Task 6: Create eval router

**Files:**
- Create: `backend/app/routers/eval.py`

- [ ] **Step 1: Create eval.py router**

```python
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
```

- [ ] **Step 2: Commit**

```
git add backend/app/routers/eval.py
git commit -m "feat: add eval API router"
```

---

### Task 7: Register eval router in main.py

**Files:**
- Modify: `backend/app/main.py:10,47`

- [ ] **Step 1: Import and register eval router**

Change the import line:
```python
from app.routers import keys, conversations, chat, batch, batch_tasks, es_export, auth, users, eval
```

Add after the other router registrations:
```python
app.include_router(eval.router)
```

- [ ] **Step 2: Commit**

```
git add backend/app/main.py
git commit -m "feat: register eval router"
```

---

### Task 8: Add eval TypeScript types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add eval_config_json to BatchTask interface**

Find `BatchTask` in `types/index.ts` and add `eval_config_json`:

```typescript
export interface BatchTask {
  // ... existing fields ...
  config_json: string | null
  eval_config_json: string | null  // <-- new
  progress_completed: number
  // ...
}
```

- [ ] **Step 2: Add eval types after BatchEvent interface (~line 153)**

```typescript
// ── Eval Types ────────────────────────────────

export interface MappingRule {
  model_output: string
  label_value: string
}

export interface ClassificationEvalConfig {
  label_column: string
  predict_column: string
  mappings: MappingRule[]
}

export interface LLMScoringEvalConfig {
  api_key_id: number
  prompt: string
  score_column: string
  output_column_name: string
  concurrency: number
}

export interface EvalConfigData {
  enabled: boolean
  method: 'classification' | 'llm_scoring' | 'both'
  classification?: ClassificationEvalConfig | null
  llm_scoring?: LLMScoringEvalConfig | null
}

export interface PerClassMetric {
  class_name: string
  precision: number
  recall: number
  f1: number
}

export interface AvgMetric {
  precision: number
  recall: number
  f1: number
}

export interface ClassificationEvalResult {
  accuracy: number
  total_samples: number
  num_classes: number
  confusion_matrix: number[][]
  labels: string[]
  per_class: PerClassMetric[]
  micro_avg: AvgMetric
  macro_avg: AvgMetric
  skipped_count: number
}

export interface LLMScoringEvalEvent {
  type: 'progress' | 'row_result' | 'row_error' | 'done' | 'error'
  completed?: number
  total?: number
  row?: number
  score?: string
  error?: string
  avg_score?: number
  message?: string
}
```

- [ ] **Step 2: Commit**

```
git add frontend/src/types/index.ts
git commit -m "feat: add eval TypeScript types"
```

---

### Task 9: Create eval API client

**Files:**
- Create: `frontend/src/api/eval.ts`

- [ ] **Step 1: Create eval.ts API client**

```typescript
import { authFetch } from './client'
import type {
  ClassificationEvalConfig,
  ClassificationEvalResult,
  LLMScoringEvalConfig,
  LLMScoringEvalEvent,
} from '../types'

export async function runClassificationEval(
  taskId: string,
  config: ClassificationEvalConfig,
): Promise<ClassificationEvalResult> {
  const res = await authFetch(`/api/eval/${taskId}/run-classification`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId, config }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '客观评测失败')
  }
  return res.json()
}

export function runLLMScoringEval(
  taskId: string,
  config: LLMScoringEvalConfig,
  onProgress: (completed: number, total: number) => void,
  onRowResult: (row: number, score: string) => void,
  onRowError: (row: number, error: string) => void,
  onDone: (total: number, avgScore: number) => void,
  onError: (msg: string) => void,
): AbortController {
  const controller = new AbortController()

  authFetch(`/api/eval/${taskId}/run-llm-scoring`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId, config }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json()
        onError(err.detail || '请求失败')
        return
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let finished = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: LLMScoringEvalEvent = JSON.parse(line.slice(6))
              switch (event.type) {
                case 'progress':
                  onProgress(event.completed || 0, event.total || 0)
                  break
                case 'row_result':
                  onRowResult(event.row || 0, event.score || '')
                  break
                case 'row_error':
                  onRowError(event.row || 0, event.error || '未知错误')
                  break
                case 'done':
                  finished = true
                  onDone(event.total || 0, event.avg_score || 0)
                  break
                case 'error':
                  finished = true
                  onError(event.message || '评分失败')
                  break
              }
            } catch { /* skip malformed JSON */ }
          }
        }
      }
      if (!finished) {
        onError('服务器连接意外关闭')
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError('连接中断')
      }
    })

  return controller
}

export async function checkClassificationResult(taskId: string): Promise<boolean> {
  try {
    const res = await authFetch(`/api/eval/${taskId}/classification-result`)
    return res.ok
  } catch {
    return false
  }
}

export function classificationDownloadUrl(taskId: string): string {
  return `/api/eval/${taskId}/classification-download`
}

export function llmScoringDownloadUrl(taskId: string): string {
  return `/api/eval/${taskId}/llm-scoring-download`
}
```

- [ ] **Step 2: Commit**

```
git add frontend/src/api/eval.ts
git commit -m "feat: add eval API client"
```

---

### Task 10: Create EvalPanel reusable component

**Files:**
- Create: `frontend/src/components/EvalPanel.vue`

- [ ] **Step 1: Create EvalPanel.vue — template section**

```vue
<template>
  <div class="eval-panel">
    <div class="step-title">5. 评测</div>

    <!-- Only show if done OR this is standalone (no batch dependency) -->
    <div v-if="!hasResultFile && !classResult && !llmScoringDone">
      <p class="eval-hint">跑批完成后可进行评测</p>
    </div>

    <!-- Tab switcher -->
    <div class="eval-tabs" v-if="showTabs">
      <div
        v-for="tab in tabs"
        :key="tab.key"
        :class="['eval-tab', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >{{ tab.label }}</div>
    </div>

    <!-- Classification Tab -->
    <div v-if="activeTab === 'classification'" class="eval-tab-content">
      <!-- Config -->
      <div v-if="!classResult" class="eval-config">
        <div class="eval-config-grid">
          <div class="eval-config-item">
            <label>标签列（答案）</label>
            <n-select v-model:value="classConfig.label_column" :options="columnOptions" placeholder="选择标签列" />
          </div>
          <div class="eval-config-item">
            <label>模型结果列</label>
            <n-select v-model:value="classConfig.predict_column" :options="columnOptions" placeholder="选择结果列" />
          </div>
        </div>

        <div class="mapping-section">
          <div class="mapping-header">
            <label>值映射（模型输出 → 标签值）</label>
            <n-button text size="small" type="primary" @click="addMapping">+ 添加映射</n-button>
          </div>
          <div v-if="classConfig.mappings.length > 0" class="mapping-table">
            <div class="mapping-row head">
              <span>模型输出</span>
              <span>映射为 Label</span>
              <span></span>
            </div>
            <div v-for="(m, i) in classConfig.mappings" :key="i" class="mapping-row">
              <n-input v-model:value="m.model_output" size="small" placeholder="如：正面" />
              <n-input v-model:value="m.label_value" size="small" placeholder="如：1" />
              <n-button text size="tiny" type="error" @click="classConfig.mappings.splice(i, 1)">✕</n-button>
            </div>
          </div>
        </div>

        <n-button type="primary" :loading="classRunning" @click="runClassification" :disabled="!classConfig.label_column || !classConfig.predict_column">
          {{ classRunning ? '评测中...' : '开始客观评测' }}
        </n-button>
        <p v-if="classError" class="eval-error">{{ classError }}</p>
      </div>

      <!-- Results -->
      <div v-if="classResult">
        <div class="eval-summary">
          <div class="eval-summary-item">
            <span class="eval-summary-label">总体准确率 (Accuracy)</span>
            <span class="eval-summary-value">{{ classResult.accuracy.toFixed(4) }}</span>
          </div>
          <div class="eval-summary-item">
            <span class="eval-summary-label">总样本数</span>
            <span class="eval-summary-value">{{ classResult.total_samples }}</span>
          </div>
          <div class="eval-summary-item">
            <span class="eval-summary-label">分类数量</span>
            <span class="eval-summary-value">{{ classResult.num_classes }}</span>
          </div>
        </div>

        <h4>混淆矩阵</h4>
        <div class="cm-table-wrap">
          <table class="cm-table">
            <thead>
              <tr>
                <th class="cm-corner"><div class="cm-diag"><span class="cm-actual">实际值</span><span class="cm-predict">预测值</span></div></th>
                <th v-for="l in classResult.labels" :key="l" class="cm-col-h">{{ l }}</th>
                <th class="cm-col-sum">合计</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in classResult.confusion_matrix" :key="i">
                <td class="cm-row-h">{{ classResult.labels[i] }}</td>
                <td v-for="(val, j) in row" :key="j" :class="{ 'cm-diag-cell': i === j, 'cm-off-cell': i !== j }">{{ val }}</td>
                <td class="cm-row-sum">{{ row.reduce((a: number, b: number) => a + b, 0) }}</td>
              </tr>
              <tr class="cm-col-sum-row">
                <td>合计</td>
                <td v-for="j in classResult.labels.length" :key="j">
                  {{ classResult.confusion_matrix.reduce((s: number, r: number[]) => s + r[j - 1], 0) }}
                </td>
                <td>{{ classResult.total_samples }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h4>各分类指标</h4>
        <n-data-table
          :columns="perClassColumns"
          :data="classResult.per_class"
          :bordered="true"
          size="small"
        />

        <h4>汇总指标</h4>
        <n-data-table
          :columns="avgColumns"
          :data="avgRows"
          :bordered="true"
          size="small"
        />

        <div class="eval-actions">
          <n-button type="success" @click="downloadClassification">下载评测结果 Excel</n-button>
          <n-button @click="classResult = null" style="margin-left: 8px;">重新评测</n-button>
        </div>
      </div>
    </div>

    <!-- LLM Scoring Tab -->
    <div v-if="activeTab === 'llm_scoring'" class="eval-tab-content">
      <div v-if="!llmScoringDone" class="eval-config">
        <div class="eval-config-grid">
          <div class="eval-config-item">
            <label>评分模型（独立选择）</label>
            <n-select v-model:value="llmConfig.api_key_id" :options="keyOptions" placeholder="选择模型" />
          </div>
          <div class="eval-config-item">
            <label>评分列</label>
            <n-select v-model:value="llmConfig.score_column" :options="columnOptions" placeholder="选择要评分的列" />
          </div>
        </div>
        <div class="eval-config-grid">
          <div class="eval-config-item">
            <label>输出列名</label>
            <n-input v-model:value="llmConfig.output_column_name" placeholder="评分" />
          </div>
          <div class="eval-config-item">
            <label>并发数</label>
            <n-input-number v-model:value="llmConfig.concurrency" :min="1" :max="20" />
          </div>
        </div>
        <div class="eval-prompt">
          <label>评分 Prompt（可用 <code>{{"{{列名}}"}}</code> 引用列）</label>
          <n-input v-model:value="llmConfig.prompt" type="textarea" :rows="8" placeholder="请根据以下标准对回答进行评分..." />
        </div>
        <n-button type="primary" :loading="llmRunning" @click="runLLMScoring" :disabled="!llmConfig.api_key_id || !llmConfig.score_column || !llmConfig.prompt.trim()">
          {{ llmRunning ? '评分中...' : '开始主观评测' }}
        </n-button>
        <p v-if="llmError" class="eval-error">{{ llmError }}</p>
      </div>

      <!-- Progress -->
      <div v-if="llmRunning || llmScoringDone">
        <n-progress
          type="line"
          :percentage="llmProgress.total > 0 ? Math.round((llmProgress.completed / llmProgress.total) * 100) : 0"
          :indicator-text="`${llmProgress.completed} / ${llmProgress.total}`"
          :height="24"
        />
      </div>

      <!-- Results table -->
      <div v-if="llmScores.length > 0" class="table-scroll">
        <n-data-table
          :columns="llmScoreColumns"
          :data="llmScores"
          :bordered="true"
          :single-line="false"
          size="small"
          :max-height="400"
          virtual-scroll
        />
      </div>

      <div v-if="llmScoringDone" class="eval-actions">
        <p>
          <span>评分完成 · 平均分：<strong>{{ llmAvgScore }}</strong></span>
          <span style="margin-left: 12px; color: #666;">{{ llmScores.length }} 条</span>
        </p>
        <n-button type="success" @click="downloadLLMScoring">下载评分结果 Excel</n-button>
        <n-button @click="resetLLMScoring" style="margin-left: 8px;">重新评分</n-button>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Create EvalPanel.vue — script section**

Append after template:

```vue
<script setup lang="ts">
import { ref, reactive, computed, h, watch } from 'vue'
import {
  NButton, NSelect, NInput, NInputNumber, NDataTable, NProgress, NTag,
  useMessage,
} from 'naive-ui'
import { useChatStore } from '../stores/chat'
import * as evalApi from '../api/eval'
import { authFetch } from '../api/client'
import type {
  ClassificationEvalConfig,
  ClassificationEvalResult,
  LLMScoringEvalConfig,
  MappingRule,
} from '../types'

interface LLMScoreRow {
  row: number
  score: string
  status: 'success' | 'error'
  error?: string
}

const props = defineProps<{
  taskId: string
  columns: string[]
  fileId: string
  standalone?: boolean
  savedEvalConfig?: string | null
}>()

const emit = defineEmits<{
  (e: 'eval-config-saved', config: Record<string, any>): void
}>()

const store = useChatStore()
const message = useMessage()

const activeTab = ref<'classification' | 'llm_scoring'>('classification')
const showTabs = ref(true)

const tabs = [
  { key: 'classification' as const, label: '客观评测' },
  { key: 'llm_scoring' as const, label: '主观评测' },
]

const columnOptions = computed(() => props.columns.map((c) => ({ label: c, value: c })))
const keyOptions = computed(() =>
  store.apiKeys
    .filter((k) => k.is_valid || k.is_active)
    .map((k) => ({ label: `${k.name} (${k.model})`, value: k.id })),
)

// ── Classification state ──
const classRunning = ref(false)
const classError = ref('')
const classResult = ref<ClassificationEvalResult | null>(null)
const classConfig = reactive<ClassificationEvalConfig>({
  label_column: '',
  predict_column: '',
  mappings: [],
})

// ── LLM scoring state ──
const llmRunning = ref(false)
const llmError = ref('')
const llmScoringDone = ref(false)
const llmAvgScore = ref(0)
const llmScores = ref<LLMScoreRow[]>([])
const llmProgress = reactive({ completed: 0, total: 0 })
const llmConfig = reactive<LLMScoringEvalConfig>({
  api_key_id: 0,
  prompt: '',
  score_column: '',
  output_column_name: '评分',
  concurrency: 3,
})
let llmAbortController: AbortController | null = null

const hasResultFile = ref(false)

// ── Methods ──

function addMapping() {
  classConfig.mappings.push({ model_output: '', label_value: '' })
}

async function runClassification() {
  classRunning.value = true
  classError.value = ''
  try {
    classResult.value = await evalApi.runClassificationEval(props.taskId, classConfig)
    message.success('客观评测完成')
  } catch (e: any) {
    classError.value = e.message || '评测失败'
  } finally {
    classRunning.value = false
  }
}

function runLLMScoring() {
  llmError.value = ''
  llmRunning.value = true
  llmScoringDone.value = false
  llmScores.value = []
  llmProgress.completed = 0
  llmProgress.total = 0
  llmAvgScore.value = 0

  llmAbortController = evalApi.runLLMScoringEval(
    props.taskId,
    { ...llmConfig },
    (completed, total) => {
      llmProgress.completed = completed
      llmProgress.total = total
    },
    (row, score) => {
      llmScores.value.push({ row, score, status: 'success' })
    },
    (row, error) => {
      llmScores.value.push({ row, score: '', status: 'error', error })
    },
    (total, avgScore) => {
      llmRunning.value = false
      llmScoringDone.value = true
      llmAvgScore.value = avgScore
    },
    (msg) => {
      llmError.value = msg
      llmRunning.value = false
    },
  )
}

function resetLLMScoring() {
  llmScoringDone.value = false
  llmScores.value = []
  llmProgress.completed = 0
  llmProgress.total = 0
  llmAvgScore.value = 0
}

async function downloadClassification() {
  const url = evalApi.classificationDownloadUrl(props.taskId)
  const resp = await authFetch(url)
  if (!resp.ok) { message.warning('下载失败'); return }
  const blob = await resp.blob()
  const objUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objUrl
  a.download = `评测结果.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(objUrl)
}

async function downloadLLMScoring() {
  const url = evalApi.llmScoringDownloadUrl(props.taskId)
  const resp = await authFetch(url)
  if (!resp.ok) { message.warning('下载失败'); return }
  const blob = await resp.blob()
  const objUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objUrl
  a.download = `评分结果.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(objUrl)
}

// ── Table columns ──

const perClassColumns = [
  { title: '分类', key: 'class_name' },
  { title: 'Precision', key: 'precision' },
  { title: 'Recall', key: 'recall' },
  { title: 'F1 Score', key: 'f1' },
]

const avgColumns = [
  { title: '类型', key: 'type' },
  { title: 'Precision', key: 'precision' },
  { title: 'Recall', key: 'recall' },
  { title: 'F1 Score', key: 'f1' },
]

const avgRows = computed(() => {
  if (!classResult.value) return []
  return [
    { type: 'Micro Avg', ...classResult.value.micro_avg },
    { type: 'Macro Avg', ...classResult.value.macro_avg },
  ]
})

const llmScoreColumns = [
  { title: '#', key: 'row', width: 50 },
  { title: '评分', key: 'score', width: 100,
    render(row: LLMScoreRow) {
      if (row.status === 'error') return h('span', { style: { color: '#ef4444' } }, row.error || '错误')
      return row.score
    }
  },
  {
    title: '状态', key: 'status', width: 70,
    render(row: LLMScoreRow) {
      return h(NTag, { type: row.status === 'success' ? 'success' : 'error', size: 'small', bordered: false }, () =>
        row.status === 'success' ? '完成' : '失败',
      )
    },
  },
]

// ── Load saved eval config ──
watch(() => props.savedEvalConfig, (json) => {
  if (!json) return
  try {
    const cfg = JSON.parse(json)
    if (cfg.enabled) {
      if (cfg.classification) {
        classConfig.label_column = cfg.classification.label_column || ''
        classConfig.predict_column = cfg.classification.predict_column || ''
        classConfig.mappings = cfg.classification.mappings || []
      }
      if (cfg.llm_scoring) {
        llmConfig.api_key_id = cfg.llm_scoring.api_key_id || 0
        llmConfig.prompt = cfg.llm_scoring.prompt || ''
        llmConfig.score_column = cfg.llm_scoring.score_column || ''
        llmConfig.output_column_name = cfg.llm_scoring.output_column_name || '评分'
        llmConfig.concurrency = cfg.llm_scoring.concurrency || 3
      }
      if (cfg.method) {
        if (cfg.method === 'both') activeTab.value = 'classification'
        else activeTab.value = cfg.method
      }
    }
  } catch { /* ignore */ }
}, { immediate: true })

// ── Check existing results ──
watch(() => props.taskId, async (tid) => {
  if (!tid) return
  const has = await evalApi.checkClassificationResult(tid)
  hasResultFile.value = has
}, { immediate: true })
</script>
```

- [ ] **Step 3: Create EvalPanel.vue — style section**

Append after script:

```vue
<style scoped>
.eval-panel {
  padding-bottom: 16px;
}

.step-title {
  font-size: 16px;
  font-weight: 600;
  color: #4b4b60;
  margin-bottom: 12px;
}

.eval-hint {
  color: #999;
  font-size: 13px;
  margin: 8px 0;
}

.eval-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.eval-tab {
  padding: 6px 14px;
  background: #f0f0f4;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.eval-tab.active {
  background: #6366f1;
  color: #fff;
}

.eval-tab-content {
  /* spacing handled by children */
}

.eval-config {
  border: 1px solid #e0e0e6;
  border-radius: 8px;
  padding: 16px;
}

.eval-config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.eval-config-item label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.mapping-section {
  margin-bottom: 12px;
}

.mapping-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.mapping-header label {
  font-size: 12px;
  color: #666;
}

.mapping-table {
  border: 1px solid #e0e0e6;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 4px;
}

.mapping-row {
  display: grid;
  grid-template-columns: 1fr 1fr 36px;
  gap: 8px;
  padding: 4px 8px;
  align-items: center;
}

.mapping-row.head {
  background: #f8f8fa;
  font-size: 11px;
  color: #666;
  padding: 6px 8px;
}

.eval-prompt {
  margin-bottom: 12px;
}

.eval-prompt label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.eval-prompt label code {
  font-size: 11px;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
  padding: 1px 4px;
  border-radius: 3px;
}

.eval-error {
  margin-top: 8px;
  color: #ef4444;
  font-size: 13px;
}

.eval-summary {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.eval-summary-item {
  padding: 8px 14px;
  background: #f0f4ff;
  border-radius: 6px;
  border-left: 3px solid #6366f1;
}

.eval-summary-item:nth-child(2) {
  background: #f4fcf0;
  border-left-color: #22c55e;
}

.eval-summary-item:nth-child(3) {
  background: #fff8f0;
  border-left-color: #f59e0b;
}

.eval-summary-label {
  display: block;
  font-size: 11px;
  color: #666;
}

.eval-summary-value {
  font-size: 18px;
  font-weight: 700;
  color: #6366f1;
}

.eval-summary-item:nth-child(2) .eval-summary-value {
  color: #22c55e;
}

.eval-summary-item:nth-child(3) .eval-summary-value {
  color: #f59e0b;
}

h4 {
  font-size: 14px;
  margin: 0 0 8px 0;
  color: #4b4b60;
}

/* Confusion Matrix */
.cm-table-wrap {
  border: 1px solid #e0e0e6;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 14px;
}

.cm-table {
  width: auto;
  min-width: 200px;
  border-collapse: collapse;
  font-size: 13px;
}

.cm-table th, .cm-table td {
  padding: 8px 12px;
  text-align: center;
  border-bottom: 1px solid #f0f0f4;
}

.cm-corner {
  border-bottom: 2px solid #d0d0d6 !important;
  border-right: 2px solid #d0d0d6 !important;
  width: 60px;
}

.cm-diag {
  position: relative;
  height: 32px;
}

.cm-actual {
  position: absolute;
  bottom: 0;
  left: 0;
  font-size: 10px;
  color: #666;
}

.cm-predict {
  position: absolute;
  top: 0;
  right: 0;
  font-size: 10px;
  color: #6366f1;
}

.cm-col-h {
  border-bottom: 2px solid #d0d0d6 !important;
  font-size: 12px;
  background: #f8f8fa;
}

.cm-col-sum {
  border-bottom: 2px solid #d0d0d6 !important;
  border-left: 2px solid #d0d0d6 !important;
  font-size: 11px;
  color: #666;
}

.cm-row-h {
  border-right: 2px solid #d0d0d6 !important;
  font-size: 12px;
  background: #fafafc;
  text-align: left !important;
}

.cm-diag-cell {
  font-weight: 700;
  color: #22c55e;
  background: #f6fff0;
}

.cm-off-cell {
  color: #ef4444;
}

.cm-row-sum {
  border-left: 2px solid #d0d0d6 !important;
  font-weight: 600;
  background: #fafafc;
}

.cm-col-sum-row {
  background: #f8f8fa;
  border-top: 2px solid #d0d0d6;
}

.cm-col-sum-row td {
  font-weight: 600;
}

.eval-actions {
  margin-top: 14px;
}

.table-scroll {
  max-height: 400px;
  overflow-y: auto;
  margin: 12px 0;
}
</style>
```

- [ ] **Step 4: Commit**

```
git add frontend/src/components/EvalPanel.vue
git commit -m "feat: add EvalPanel reusable evaluation component"
```

---

### Task 11: Create EvalPage standalone view and add /eval route

**Files:**
- Create: `frontend/src/views/EvalPage.vue`
- Modify: `frontend/src/router/index.ts:53-54`

- [ ] **Step 1: Create EvalPage.vue**

```vue
<template>
  <div class="eval-page">
    <div class="eval-page-header">
      <h2>评测</h2>
    </div>
    <div class="eval-page-body">
      <!-- Upload area -->
      <div v-if="!uploadResult" class="upload-area">
        <n-upload
          :max="1"
          accept=".xlsx,.xls,.json,.txt"
          @change="handleUpload"
          :show-file-list="false"
        >
          <n-button :loading="uploading" size="large">
            {{ uploading ? '解析中...' : '选择文件' }}
          </n-button>
        </n-upload>
        <span class="upload-hint">直接上传文件进行评测，无需跑批</span>
        <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>
      </div>

      <!-- Eval panel -->
      <EvalPanel
        v-if="uploadResult"
        :task-id="taskId"
        :columns="uploadResult.columns"
        :file-id="uploadResult.file_id"
        :standalone="true"
      />

      <!-- Select existing batch task result -->
      <div v-if="batchTasks.length > 0" class="existing-tasks">
        <h3>或选择已有跑批结果评测</h3>
        <div v-for="t in batchTasks.filter(t => t.status === 'completed')" :key="t.id" class="task-item">
          <span>{{ t.title }} ({{ t.filename }})</span>
          <n-button size="small" @click="selectBatchTask(t.id)">评测</n-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NUpload, useMessage } from 'naive-ui'
import { useBatchStore } from '../stores/batch'
import * as batchApi from '../api/batch'
import EvalPanel from '../components/EvalPanel.vue'
import type { UploadResponse } from '../types'

const batchStore = useBatchStore()
const message = useMessage()
const uploading = ref(false)
const uploadError = ref('')
const uploadResult = ref<UploadResponse | null>(null)
const taskId = ref('')
const batchTasks = ref<any[]>([])

async function handleUpload(opts: { file: any; fileList: any[] }) {
  uploadError.value = ''
  uploading.value = true
  try {
    const rawFile = opts.file.file as File
    const result = await batchApi.uploadExcel(rawFile)
    uploadResult.value = result
    taskId.value = result.task_id
    await batchStore.loadBatchTasks()
    batchTasks.value = batchStore.batchTasks
  } catch (e: any) {
    uploadError.value = e.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function selectBatchTask(id: string) {
  await batchStore.selectBatchTask(id)
  if (batchStore.uploadResult) {
    uploadResult.value = batchStore.uploadResult
    taskId.value = id
  }
}
</script>

<style scoped>
.eval-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
  overflow: hidden;
}

.eval-page-header {
  padding: 0 24px;
  height: 52px;
  display: flex;
  align-items: center;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0,0,0,0.06);
  flex-shrink: 0;
}

.eval-page-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #4b4b60;
  margin: 0;
}

.eval-page-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
  width: 100%;
}

.upload-area {
  text-align: center;
  padding: 40px;
}

.upload-hint {
  display: block;
  margin-top: 12px;
  font-size: 13px;
  color: #999;
}

.upload-error {
  margin-top: 12px;
  color: #ef4444;
  font-size: 13px;
}

.existing-tasks {
  margin-top: 32px;
  border-top: 1px solid #e0e0e6;
  padding-top: 24px;
}

.existing-tasks h3 {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid #e0e0e6;
  border-radius: 6px;
  margin-bottom: 8px;
  font-size: 13px;
}
</style>
```

- [ ] **Step 2: Add /eval route**

In `frontend/src/router/index.ts`, add after the `/batch` route:

```typescript
{
  path: '/eval',
  name: 'eval',
  component: () => import('../views/EvalPage.vue'),
  meta: { requiresAuth: true },
},
```

- [ ] **Step 3: Commit**

```
git add frontend/src/views/EvalPage.vue frontend/src/router/index.ts
git commit -m "feat: add standalone eval page and /eval route"
```

---

### Task 12: Integrate EvalPanel into BatchPanel.vue — Step 3 eval config

**Files:**
- Modify: `frontend/src/components/BatchPanel.vue`

- [ ] **Step 1: Add eval config collapsible panel in Step 3 template (after the "开始跑批" button ~line 226)**

Insert this after the `<n-button v-if="running" @click="stopBatch" ...>` line:

```vue
<!-- Eval pre-config (collapsible, Step 3) -->
<div class="eval-pre-config" v-if="uploadResult">
  <div class="eval-pre-header" @click="showEvalPreConfig = !showEvalPreConfig">
    <span :class="['eval-pre-arrow', { open: showEvalPreConfig }]">▶</span>
    <span class="eval-pre-title">评测配置（可选，跑批完成后自动执行）</span>
    <span v-if="!evalPreConfig.enabled" class="eval-pre-status off">未启用</span>
    <span v-else class="eval-pre-status on">✓ 已启用</span>
  </div>
  <div v-if="showEvalPreConfig" class="eval-pre-body">
    <div class="eval-pre-tabs">
      <div
        v-for="tab in evalPreTabs"
        :key="tab.key"
        :class="['eval-pre-tab', { active: evalPreActiveTab === tab.key }]"
        @click="evalPreActiveTab = tab.key"
      >{{ tab.label }}</div>
    </div>

    <!-- Classification pre-config -->
    <div v-if="evalPreActiveTab === 'classification'" class="eval-pre-tab-content">
      <div class="eval-pre-grid">
        <div class="eval-pre-item">
          <label>标签列（答案）</label>
          <n-select v-model:value="evalPreClassConfig.label_column" :options="columnOptions" size="small" />
        </div>
        <div class="eval-pre-item">
          <label>模型结果列</label>
          <n-select v-model:value="evalPreClassConfig.predict_column" :options="columnOptions" size="small" />
        </div>
      </div>
      <div class="eval-pre-mappings">
        <div class="eval-pre-mappings-header">
          <span>值映射</span>
          <n-button text size="tiny" type="primary" @click="addEvalPreMapping">+ 添加映射</n-button>
        </div>
        <div v-if="evalPreClassConfig.mappings.length > 0" class="eval-pre-mapping-table">
          <div v-for="(m, i) in evalPreClassConfig.mappings" :key="i" class="eval-pre-mapping-row">
            <n-input v-model:value="m.model_output" size="tiny" placeholder="模型输出" />
            <span class="eval-pre-mapping-arrow">→</span>
            <n-input v-model:value="m.label_value" size="tiny" placeholder="Label" />
            <n-button text size="tiny" type="error" @click="evalPreClassConfig.mappings.splice(i, 1)">✕</n-button>
          </div>
        </div>
      </div>
    </div>

    <!-- LLM scoring pre-config -->
    <div v-if="evalPreActiveTab === 'llm_scoring'" class="eval-pre-tab-content">
      <div class="eval-pre-grid">
        <div class="eval-pre-item">
          <label>评分模型</label>
          <n-select v-model:value="evalPreLLMConfig.api_key_id" :options="keyOptions" size="small" />
        </div>
        <div class="eval-pre-item">
          <label>评分列</label>
          <n-select v-model:value="evalPreLLMConfig.score_column" :options="columnOptions" size="small" />
        </div>
      </div>
      <div class="eval-pre-item">
        <label>评分 Prompt</label>
        <n-input v-model:value="evalPreLLMConfig.prompt" type="textarea" :rows="4" size="small" placeholder="请根据以下标准评分..." />
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Commit**

```
git add frontend/src/components/BatchPanel.vue
git commit -m "feat: add eval pre-config panel in Step 3"
```

---

### Task 13: Integrate EvalPanel into BatchPanel.vue — Step 5

**Files:**
- Modify: `frontend/src/components/BatchPanel.vue`

- [ ] **Step 1: Add Step 5 after Step 4 in template (after the download area ~line 262)**

```vue
<!-- Step 5: Evaluation -->
<div class="step" v-if="done && uploadResult">
  <EvalPanel
    :task-id="batchStore.currentTask!.id"
    :columns="uploadResult.columns"
    :file-id="uploadResult.file_id"
    :saved-eval-config="batchStore.currentTask?.eval_config_json"
  />
</div>
```

- [ ] **Step 2: Add EvalPanel import in script section (~line 277)**

```typescript
import EvalPanel from './EvalPanel.vue'
```

- [ ] **Step 3: Add eval pre-config reactive state in script section (~line 402)**

After the `filter` reactive:

```typescript
// Eval pre-config in Step 3
const showEvalPreConfig = ref(false)
const evalPreActiveTab = ref<'classification' | 'llm_scoring'>('classification')
const evalPreTabs = [
  { key: 'classification' as const, label: '客观评测' },
  { key: 'llm_scoring' as const, label: '主观评测' },
]
const evalPreClassConfig = reactive({
  label_column: '',
  predict_column: '',
  mappings: [] as { model_output: string; label_value: string }[],
})
const evalPreLLMConfig = reactive({
  api_key_id: 0,
  prompt: '',
  score_column: '',
  output_column_name: '评分',
  concurrency: 3,
})
const evalPreConfig = computed(() => ({
  enabled: evalPreClassConfig.label_column !== '' || evalPreLLMConfig.api_key_id !== 0,
  method: (evalPreClassConfig.label_column !== '' && evalPreLLMConfig.api_key_id !== 0) ? 'both'
    : evalPreClassConfig.label_column !== '' ? 'classification'
    : evalPreLLMConfig.api_key_id !== 0 ? 'llm_scoring'
    : 'classification',
  classification: evalPreClassConfig.label_column ? { ...evalPreClassConfig } : null,
  llm_scoring: evalPreLLMConfig.api_key_id ? { ...evalPreLLMConfig } : null,
}))

function addEvalPreMapping() {
  evalPreClassConfig.mappings.push({ model_output: '', label_value: '' })
}
```

- [ ] **Step 4: Save eval pre-config to task alongside batch config**

In the `startBatch` function, before saving config, also save the eval config:

Add after the `await batchStore.saveBatchTaskConfig(myTaskId, ...)` call (~line 913):

```typescript
// Save eval pre-config
if (evalPreConfig.value.enabled) {
  await batchTasksApi.updateBatchTask(myTaskId, {
    eval_config_json: JSON.stringify(evalPreConfig.value),
  })
}
```

- [ ] **Step 5: Commit**

```
git add frontend/src/components/BatchPanel.vue
git commit -m "feat: integrate EvalPanel as Step 5 in batch workflow"
```

---

### Task 14: Backend tests and manual smoke test

**Files:**
- Create: `backend/tests/test_eval.py`

- [ ] **Step 1: Create basic eval service test**

```python
import pytest
from unittest.mock import patch, MagicMock
import openpyxl
import os
import tempfile

from app.services.eval_service import run_classification_eval, _write_classification_excel


class TestClassificationEval:
    def test_basic_metrics(self):
        """Test classification metrics with simple data."""
        # Create a temporary result Excel
        tmpdir = tempfile.mkdtemp()
        file_id = "test_eval_001"
        result_path = os.path.join(tmpdir, file_id + "_result.xlsx")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.cell(row=1, column=1, value="input")
        ws.cell(row=1, column=2, value="label")
        ws.cell(row=1, column=3, value="AI结果")
        # 10 rows: 6 correct, 4 wrong
        data = [
            ("q1", "1", "正面"),
            ("q2", "1", "正面"),
            ("q3", "1", "负面"),  # wrong
            ("q4", "1", "正面"),
            ("q5", "0", "负面"),
            ("q6", "0", "负面"),
            ("q7", "0", "正面"),   # wrong
            ("q8", "0", "负面"),
            ("q9", "1", "正面"),
            ("q10", "0", "负面"),
        ]
        for i, (inp, lbl, pred) in enumerate(data, start=2):
            ws.cell(row=i, column=1, value=inp)
            ws.cell(row=i, column=2, value=lbl)
            ws.cell(row=i, column=3, value=pred)
        wb.save(result_path)
        wb.close()

        # Patch UPLOAD_DIR to use tempdir
        with patch("app.services.eval_service.UPLOAD_DIR", tmpdir):
            result = run_classification_eval(
                file_id,
                label_column="label",
                predict_column="AI结果",
                mappings=[
                    {"model_output": "正面", "label_value": "1"},
                    {"model_output": "负面", "label_value": "0"},
                ],
            )

        assert result["total_samples"] == 10
        assert result["num_classes"] == 2
        assert result["accuracy"] == 0.8  # 8/10 correct after mapping
        assert len(result["per_class"]) == 2
        assert "micro_avg" in result
        assert "macro_avg" in result
        assert result["skipped_count"] == 0

        # Check eval file was created
        assert os.path.exists(os.path.join(tmpdir, file_id + "_eval_classification.xlsx"))

    def test_missing_columns(self):
        tmpdir = tempfile.mkdtemp()
        file_id = "test_eval_002"
        result_path = os.path.join(tmpdir, file_id + "_result.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.cell(row=1, column=1, value="col_a")
        wb.save(result_path)
        wb.close()

        with patch("app.services.eval_service.UPLOAD_DIR", tmpdir):
            with pytest.raises(ValueError, match="Columns not found"):
                run_classification_eval(
                    file_id,
                    label_column="label",
                    predict_column="AI结果",
                    mappings=[],
                )

    def test_no_result_file(self):
        with pytest.raises(FileNotFoundError):
            run_classification_eval(
                "nonexistent",
                label_column="label",
                predict_column="AI结果",
                mappings=[],
            )
```

- [ ] **Step 2: Run the tests**

```bash
cd backend && python -m pytest tests/test_eval.py -v
```
Expected: 3 tests pass

- [ ] **Step 3: Smoke test manually**

```bash
# Start backend
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Start frontend
cd frontend && npm run dev
```

Manual test steps:
1. Login, go to /batch, upload a test Excel with label and data columns
2. Configure Step 3 with a fast/small model, start batch
3. Wait for batch to complete → Step 5 should appear
4. Tab to "客观评测", select label/predict columns, add mapping, run
5. Verify confusion matrix, per-class metrics, Micro/Macro Avg display
6. Download classification result Excel, verify sheets
7. Tab to "主观评测", select scoring model and column, enter prompt, run
8. Verify progress bar, streaming results, average score, download
9. Create new batch with eval pre-config in Step 3 → verify auto-run after completion
10. Go to /eval, upload file directly, run evaluation

- [ ] **Step 4: Commit**

```
git add backend/tests/test_eval.py
git commit -m "test: add classification eval service tests"
```

---

## Plan Self-Review

**Spec coverage:**
- eval_config_json column on batch_tasks ✓ (Task 2)
- Classification eval API + service ✓ (Tasks 4, 6)
- LLM scoring SSE API + service ✓ (Tasks 5, 6)
- Confusion matrix with row/col sums ✓ (Task 4 — _write_classification_excel, Task 10 — EvalPanel template)
- Per-class P/R/F1, no per-class accuracy ✓ (Task 4)
- Micro/Macro avg ✓ (Task 4)
- Overall accuracy ✓ (Task 4)
- Mapping support ✓ (Task 4, Task 10)
- EvalPanel component ✓ (Task 10)
- Step 3 eval pre-config ✓ (Task 12)
- Step 5 integration ✓ (Task 13)
- Standalone /eval page ✓ (Task 11)
- Download Excel ✓ (Task 6, Task 10)
- Error handling ✓ (throughout service and component)
- Three trigger scenarios ✓ (Tasks 12-13 + Task 11)

**Placeholder scan:** Clean — no TBD, TODO, or vague steps.

**Type consistency:**
- `ClassificationEvalConfig` matches between Python schema (Task 3) and TypeScript type (Task 8)
- `LLMScoringEvalConfig` consistent across schemas, API client, and component
- `MappingRule.model_output` → `label_value` consistent across all references
- SSE event types (`progress`, `row_result`, `row_error`, `done`, `error`) match between service, router, API client, and component
