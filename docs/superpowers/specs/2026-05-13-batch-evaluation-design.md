# 批量跑批 - 第五步评测功能设计

## 概述

在跑批任务 4 步工作流（上传 → 筛选 → 配置 → 进度/结果）完成后，增加可选的第 5 步评测。支持两种独立评测方式：客观分类指标评测和 LLM 主观评分。同时支持不跑批、直接上传文件进行纯评测。

## 评测触发场景

1. **预配置自动评测**：Step 3 配置评测参数 → 跑批完成后自动执行
2. **完成后手动评测**：跑批完成后到 Step 5 手动配置并执行
3. **纯评测模式**：上传文件后直接评测（`/eval` 路由），不跑批

## 数据模型

### 修改 `batch_tasks` 表

新增字段 `eval_config_json` (TEXT, nullable)：

```json
{
  "enabled": true,
  "method": "classification",  // "classification" | "llm_scoring" | "both"

  "classification": {
    "label_column": "label",
    "predict_column": "AI结果",
    "mappings": [
      { "model_output": "正面", "label_value": "1" },
      { "model_output": "负面", "label_value": "0" }
    ]
  },

  "llm_scoring": {
    "api_key_id": 2,
    "prompt": "请对以下回答评分（1-10）：\n问题：{{input}}\n回答：{{AI结果}}\n\n评分：",
    "score_column": "AI结果",
    "output_column_name": "评分",
    "concurrency": 3
  }
}
```

评测结果保存为文件，不新建结果表：
- `{file_id}_eval_classification.xlsx` — 分类评测结果
- `{file_id}_eval_llm_scoring.xlsx` — LLM 评分结果

任务重新打开时通过检测文件存在性恢复评测状态。

## API 设计

新增 `/api/eval` 路由组：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/eval/{task_id}/run-classification` | 执行分类指标评测（同步） |
| POST | `/api/eval/{task_id}/run-llm-scoring` | 执行 LLM 主观评分（SSE 流） |
| GET | `/api/eval/{task_id}/classification-result` | 获取分类评测结果 JSON |
| GET | `/api/eval/{task_id}/classification-download` | 下载分类评测 Excel |
| GET | `/api/eval/{task_id}/llm-scoring-download` | 下载 LLM 评分 Excel |

### 分类评测响应 JSON

```json
{
  "accuracy": 0.765,
  "total_samples": 200,
  "num_classes": 3,
  "confusion_matrix": [[62, 8, 10], [7, 42, 11], [3, 8, 49]],
  "labels": ["正面 (1)", "中性 (2)", "负面 (0)"],
  "per_class": [
    { "class": "正面 (1)", "precision": 0.892, "recall": 0.775, "f1": 0.829 },
    { "class": "中性 (2)", "precision": 0.750, "recall": 0.700, "f1": 0.724 },
    { "class": "负面 (0)", "precision": 0.817, "recall": 0.817, "f1": 0.817 }
  ],
  "micro_avg": { "precision": 0.765, "recall": 0.765, "f1": 0.765 },
  "macro_avg": { "precision": 0.820, "recall": 0.764, "f1": 0.790 }
}
```

### LLM 评分 SSE 事件

```
event: progress    → data: {"completed": 45, "total": 200}
event: row_result  → data: {"row": 1, "score": "8"}
event: row_error   → data: {"row": 3, "error": "API error"}
event: done        → data: {"total": 200, "avg_score": 6.8, "elapsed_seconds": 45}
event: error       → data: {"message": "..."}
```

## 后端文件

- `backend/app/routers/eval.py` — 新路由
- `backend/app/services/eval_service.py` — 核心逻辑
  - `run_classification_eval()` — 读取结果 xlsx → 映射 → sklearn metrics → 写文件
  - `run_llm_scoring()` — 异步生成器，并发调用 LLM → 写文件
- `backend/app/models.py` — `BatchTask` 加 `eval_config_json`
- `backend/app/schemas.py` — 新增 EvalConfig, MappingRule, ClassificationEvalResponse 等
- `backend/app/main.py` — 注册 `eval.router`

## 前端文件

### 新建
- `frontend/src/components/EvalPanel.vue` — 独立可复用评测组件
  - 包含客观评测 Tab 和主观评测 Tab
  - Props: `taskId`, `columns`, `fileId`
  - 可嵌入 BatchPanel 或 /eval 页面
- `frontend/src/views/EvalPage.vue` — 纯评测独立页面
- `frontend/src/api/eval.ts` — 评测 API 客户端

### 修改
- `frontend/src/components/BatchPanel.vue`
  - Step 3 底部：折叠面板嵌入评测预设配置
  - 新增 Step 5：嵌入 `<EvalPanel />`，跑批完成后显示
- `frontend/src/types/index.ts` — 新增 EvalConfig, MappingRule 等 TS 类型
- `frontend/src/router/index.ts` — 新增 `/eval` 路由

## 客观评测 UI 展示

- 概览区：总体 Accuracy、总样本数、分类数量
- 混淆矩阵表格：带行列合计，对角线绿色/非对角线红色
- 各分类指标表：Precision、Recall、F1 Score（无 Support、无每分类 Accuracy）
- 汇总指标表：Micro Avg / Macro Avg（Precision、Recall、F1）
- 下载评测结果 Excel 按钮

## 主观评测 UI 展示

- 配置区：评分模型（独立选择）、评分列、评分 Prompt（支持 `{{变量}}`）、输出列名、并发数
- 进度条 + 流式结果表（原内容 / AI结果 / 评分）
- 完成：平均分 + 下载评分结果 Excel

## 下载 Excel 结构

### 分类评测下载
- Sheet "混淆矩阵"：带行列合计的混淆矩阵
- Sheet "各分类指标"：Precision、Recall、F1
- Sheet "汇总指标"：Micro/Macro Avg + Accuracy

### LLM 评分下载
- 原始跑批结果 + 末尾追加"评分"列

## 错误处理

- 映射未匹配：跳过该行，不计入统计，返回 `skipped_count`
- LLM 某行评分失败：标记 error，继续后续行
- 结果文件不存在：返回 404，前端提示
- 评测运行时阻止重复触发

## 外部依赖

- scikit-learn（分类指标计算），新增到 `requirements.txt`
