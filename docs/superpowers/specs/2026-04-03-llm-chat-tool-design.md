# LLM Chat Tool — 设计文档

## 概述

一个个人使用的 LLM 问答工具，支持 OpenAI 和 Anthropic 两种协议，提供前端问答页面，支持配置和切换 API Key，添加时验证连通性，聊天记录持久化保存。

## 技术栈

- **后端**：Python FastAPI + SQLite + SQLAlchemy
- **前端**：Vue 3 + Vite + Naive UI + TypeScript
- **通信**：REST API + SSE（流式输出）

## 整体架构

```
┌─────────────────────────────────────┐
│         Vue 3 前端 (Vite)            │
│  ┌──────────┐  ┌──────────────────┐ │
│  │ 会话列表  │  │   聊天窗口       │ │
│  │          │  │   (流式输出)     │ │
│  └──────────┘  └──────────────────┘ │
│         ┌──────────────┐            │
│         │  设置面板     │            │
│         │  (API Key管理)│            │
│         └──────────────┘            │
└──────────────┬──────────────────────┘
               │ HTTP / SSE
┌──────────────▼──────────────────────┐
│       FastAPI 后端                   │
│  ┌────────────┐  ┌───────────────┐  │
│  │ API Key 管理│  │ 聊天/会话管理  │  │
│  │ (验证+加密) │  │ (CRUD+流式)   │  │
│  └────────────┘  └───────────────┘  │
│  ┌────────────────────────────────┐  │
│  │     LLM 代理层                 │  │
│  │  ┌─────────┐  ┌────────────┐  │  │
│  │  │ OpenAI  │  │ Anthropic  │  │  │
│  │  │ 适配器   │  │  适配器     │  │  │
│  │  └─────────┘  └────────────┘  │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │   SQLite (聊天记录 + API Key)   │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

**核心模块：**

- **前端**：Vue 3 + Vite + Naive UI 组件库
- **后端**：FastAPI，分为三层 — API Key 管理、会话/聊天管理、LLM 代理层
- **LLM 代理层**：统一接口，内部适配 OpenAI 和 Anthropic 两种协议
- **存储**：SQLite，存 API Key（加密）和聊天记录
- **通信**：普通请求用 REST，流式回复用 SSE (Server-Sent Events)

## 数据模型

### API Key 配置表 (`api_keys`)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT | 用户自定义的配置名称，如"我的OpenAI" |
| provider | TEXT | "openai" 或 "anthropic" |
| base_url | TEXT | API 地址 |
| api_key | TEXT | 加密存储的密钥 |
| model | TEXT | 默认模型名，如 "gpt-4o"、"claude-sonnet-4-20250514" |
| max_context_tokens | INTEGER | 上下文 token 上限，默认 200000 |
| is_active | BOOLEAN | 当前是否选中使用 |
| is_valid | BOOLEAN | 上次验证是否通过 |
| created_at | DATETIME | 创建时间 |

### 会话表 (`conversations`)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | UUID |
| title | TEXT | 会话标题（可自动生成） |
| api_key_id | INTEGER FK | 关联的 API Key 配置 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 消息表 (`messages`)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| conversation_id | TEXT FK | 所属会话 |
| role | TEXT | "user" / "assistant" / "system" |
| content | TEXT | 消息内容 |
| created_at | DATETIME | 创建时间 |

### 设计要点

- 每个会话绑定一个 API Key 配置，但可以随时切换（切换后新消息用新配置）
- `is_active` 标记当前选中的配置，同一时间只有一个为 true
- API Key 使用 Fernet 对称加密存储，密钥从环境变量 `ENCRYPTION_KEY` 读取

## 记忆（上下文管理）

### 机制

- 每次用户发送消息时，后端从数据库取出当前会话的全部历史消息
- 按时间顺序组装成消息列表，计算总 token 数
- 如果总 token 数超过配置的上限（默认 200,000），从最早的消息开始丢弃，直到总量低于上限
- 保留 system 消息（如果有的话），只丢弃 user/assistant 消息

### Token 计算

- OpenAI：使用 `tiktoken` 库精确计算
- Anthropic：使用 `anthropic` SDK 自带的 token 计数，或退回到 `tiktoken` 近似估算

### 丢弃策略

```
历史消息: [msg1, msg2, msg3, ..., msg_n, 新消息]
                ↑ 从这里开始丢弃，直到总 token ≤ max_context_tokens
```

简单直接 — 超出就从最老的开始扔，不做摘要压缩。`max_context_tokens` 可在每个 API Key 配置中独立设置。

## 后端 API 设计

### API Key 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/keys` | 添加 API Key（自动验证连通性） |
| GET | `/api/keys` | 获取所有配置列表（不返回明文 key） |
| PUT | `/api/keys/{id}` | 更新配置 |
| DELETE | `/api/keys/{id}` | 删除配置 |
| POST | `/api/keys/{id}/verify` | 手动重新验证连通性 |
| POST | `/api/keys/{id}/activate` | 设为当前选中配置 |

### 验证连通性

- OpenAI 协议：调用 `GET /v1/models` 接口，能返回模型列表即为通
- Anthropic 协议：调用 `POST /v1/messages`，发一条极短消息（如 "hi"，max_tokens=1），能正常响应即为通
- 添加 Key 时自动验证，验证失败仍可保存但标记 `is_valid=false`

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/conversations` | 创建新会话 |
| GET | `/api/conversations` | 获取会话列表 |
| GET | `/api/conversations/{id}` | 获取会话详情+消息 |
| DELETE | `/api/conversations/{id}` | 删除会话 |
| PUT | `/api/conversations/{id}` | 更新会话（改标题、切换 Key） |

### 聊天

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/{conversation_id}` | 发送消息，返回 SSE 流 |

### SSE 流数据格式

```
event: message
data: {"type": "chunk", "content": "你"}

event: message
data: {"type": "chunk", "content": "好"}

event: message
data: {"type": "done", "content": ""}

event: message
data: {"type": "error", "content": "错误信息"}
```

### LLM 代理层

- 定义统一的 `LLMProvider` 基类，包含 `chat_stream(messages)` 方法
- `OpenAIProvider` 和 `AnthropicProvider` 分别实现
- 根据 `api_key` 配置的 `provider` 字段选择对应的适配器
- 两个适配器都使用各自的官方 SDK（`openai`、`anthropic`）

## 前端页面设计

### 整体布局

```
┌──────────────────────────────────────────────┐
│  ⚙️ 设置按钮                    当前模型: gpt-4o │
├────────────┬─────────────────────────────────┤
│            │                                 │
│  + 新会话   │    欢迎使用 LLM Chat             │
│            │                                 │
│  会话1      │    user: 你好                   │
│  会话2      │    assistant: 你好！有什么...     │
│  会话3      │                                 │
│            │                                 │
│            │                                 │
│            ├─────────────────────────────────┤
│            │  [输入框...              ] [发送] │
└────────────┴─────────────────────────────────┘
```

### 三个核心区域

**1. 左侧栏 — 会话管理**
- 新建会话按钮
- 会话列表，按更新时间倒序
- 右键或 hover 显示删除、重命名
- 当前选中会话高亮

**2. 右侧主区域 — 聊天窗口**
- 消息气泡列表，区分用户/助手样式
- 助手回复支持 Markdown 渲染
- 流式输出时显示打字光标动画
- 底部输入框 + 发送按钮，支持 Enter 发送、Shift+Enter 换行

**3. 设置面板 — 弹窗/抽屉**
- API Key 列表，显示名称、协议类型、验证状态（✅/❌）
- 添加 Key 表单：名称、协议类型（下拉选）、Base URL、API Key、模型名、最大上下文 Token
- 协议类型切换时自动填充默认 Base URL（OpenAI: `https://api.openai.com/v1`，Anthropic: `https://api.anthropic.com`）
- 保存时自动验证，显示验证中 loading 状态
- 验证通过显示 ✅，失败显示 ❌ 和错误原因，但仍可保存
- 点击某个 Key 可设为当前激活

## 项目结构

```
llm-chat/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置（加密密钥等）
│   │   ├── database.py          # SQLite 连接与表初始化
│   │   ├── models.py            # SQLAlchemy 模型
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── routers/
│   │   │   ├── keys.py          # API Key 管理路由
│   │   │   ├── conversations.py # 会话管理路由
│   │   │   └── chat.py          # 聊天路由（SSE）
│   │   ├── services/
│   │   │   ├── key_service.py   # API Key 业务逻辑（加密/验证）
│   │   │   ├── chat_service.py  # 聊天业务逻辑（上下文管理）
│   │   │   └── llm/
│   │   │       ├── base.py      # LLMProvider 基类
│   │   │       ├── openai.py    # OpenAI 适配器
│   │   │       └── anthropic.py # Anthropic 适配器
│   │   └── utils/
│   │       ├── crypto.py        # Fernet 加密工具
│   │       └── token_counter.py # Token 计数工具
│   ├── requirements.txt
│   └── .env                     # 加密密钥等环境变量
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── api/                 # 后端 API 调用封装
│   │   │   ├── keys.ts
│   │   │   ├── conversations.ts
│   │   │   └── chat.ts
│   │   ├── components/
│   │   │   ├── ChatWindow.vue   # 聊天主窗口
│   │   │   ├── MessageBubble.vue# 消息气泡
│   │   │   ├── SessionList.vue  # 左侧会话列表
│   │   │   ├── InputBox.vue     # 输入框
│   │   │   └── SettingsPanel.vue# 设置面板
│   │   ├── stores/
│   │   │   └── chat.ts          # Pinia 状态管理
│   │   └── types/
│   │       └── index.ts         # TypeScript 类型定义
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 错误处理

- **API Key 验证失败**：返回具体错误（网络不通、认证失败、URL 格式错误），前端展示错误原因
- **LLM 调用失败**：SSE 流中发送 error 事件，前端显示错误消息气泡
- **流式中断**：前端检测 SSE 连接断开，显示"回复中断"提示
- **数据库错误**：返回 500 + 错误信息，前端显示通用错误提示

## 启动方式

- 后端：`uvicorn app.main:app --reload --port 8099`
- 前端：`npm run dev`（开发时 Vite 代理到后端 8099 端口）
