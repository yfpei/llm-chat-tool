import os
import re
import asyncio
from typing import AsyncGenerator

import openpyxl
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey
from app.services.key_service import get_decrypted_key
from app.services.llm import create_provider

UPLOAD_DIR = os.environ.get(
    "UPLOAD_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads"),
)


def _find_result_file(file_id: str) -> str | None:
    """Find _result.xlsx file for a given file_id."""
    base = os.path.join(UPLOAD_DIR, file_id)
    result_path = base + "_result.xlsx"
    if os.path.exists(result_path):
        return result_path
    return None


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
        file_id, labels, cm_list, accuracy,
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


def _write_classification_excel(
    file_id: str, labels: list[str], cm_list: list[list[int]],
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
    col_sum_col = len(labels) + 2
    ws1.cell(row=1, column=col_sum_col, value="合计")
    for i, label in enumerate(labels):
        ws1.cell(row=i + 2, column=1, value=label)
        row_sum = 0
        for j in range(len(labels)):
            ws1.cell(row=i + 2, column=j + 2, value=cm_list[i][j])
            row_sum += cm_list[i][j]
        ws1.cell(row=i + 2, column=col_sum_col, value=row_sum)
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


def get_classification_eval_file(file_id: str) -> str | None:
    path = os.path.join(UPLOAD_DIR, file_id + "_eval_classification.xlsx")
    return path if os.path.exists(path) else None


async def run_llm_scoring(
    db: AsyncSession,
    file_id: str,
    api_key_id: int,
    score_column: str,
    prompt_template: str,
    output_column_name: str,
    concurrency: int = 3,
    input_columns: list[str] | None = None,
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

    if input_columns:
        missing = [c for c in input_columns if c not in headers]
        if missing:
            yield {"type": "error", "message": f"列 {missing} 不存在"}
            wb.close()
            return

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

    # Set up scoring output file
    scoring_path = os.path.join(UPLOAD_DIR, file_id + "_eval_llm_scoring.xlsx")
    wb = openpyxl.load_workbook(result_path)
    ws = wb.active
    score_out_col = len(headers) + 1
    ws.cell(row=1, column=score_out_col, value=output_column_name)
    wb.save(scoring_path)
    wb.close()

    results: dict[int, str] = {}
    results_lock = asyncio.Lock()
    completed = 0
    completed_lock = asyncio.Lock()
    sem = asyncio.Semaphore(concurrency)

    use_native_thinking = api_key.enable_thinking

    async def process_one(row_idx: int, row_data: dict[str, str]):
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
            score = re.sub(
                r'</?(?:think|unused\d+)[^>]*>.*?</(?:think|unused\d+)>',
                '', score, flags=re.DOTALL | re.IGNORECASE
            ).strip()
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

    # Write scores to Excel
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
