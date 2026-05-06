# LLM Chat Tool

一个类 ChatGPT 界面的个人 LLM 多轮对话 Web 应用。支持 OpenAI 兼容 API 和 Anthropic Claude API，具备 SSE 流式输出、API Key 管理、会话持久化和 Excel 批量处理功能。

[English](README.md)

## 功能特性

- **多提供商 LLM 对话** — 支持 OpenAI 兼容和 Anthropic Claude API，SSE 流式输出
- **API Key 管理** — 添加、验证、更新、切换多个 API Key（加密存储）
- **会话管理** — 创建、重命名、删除会话，完整消息历史记录
- **上下文窗口管理** — 自动 Token 感知截断，确保不超出模型上下文限制
- **思考模式** — 支持扩展思考（Anthropic）和推理模型
- **批量处理** — 上传 Excel/JSON/TXT 文件，配置提示词，并发处理多行数据
- **数据筛选** — 支持条件组模型 `(A AND B) OR (C AND D)`、前 N 行限制、包含/等于/大于/小于操作符，可预览和下载筛选结果
- **变量高亮** — Prompt 编辑器中 `{{变量}}` 内联彩色高亮，输入 `/` 快速选择列变量
- **Markdown 渲染** — 助手回复支持丰富的 Markdown 格式渲染
- **Docker 部署** — 使用 Docker Compose 一键部署

## 界面截图

![聊天界面](frontend/src/assets/hero.png)

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.115 + uvicorn |
| 数据库 | SQLite + SQLAlchemy（异步）+ aiosqlite |
| 加密 | cryptography（Fernet） |
| LLM SDK | openai 1.51, anthropic 0.34 |
| 流式传输 | SSE（sse-starlette） |
| 前端框架 | Vue 3 + TypeScript + Vite |
| UI 组件库 | Naive UI |
| 状态管理 | Pinia |
| Markdown | markdown-it |

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 22+
- OpenAI 或 Anthropic API Key

### 1. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 创建 .env 文件
echo "ENCRYPTION_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" > .env

# 启动后端
uvicorn app.main:app --host 0.0.0.0 --port 8099 --reload
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 `http://localhost:5173`，API 请求自动代理到后端 `http://localhost:8099`。

### 3. Docker 部署（可选）

```bash
# 生成加密密钥
ENCRYPTION_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')

# 使用 Docker Compose 启动
ENCRYPTION_KEY=$ENCRYPTION_KEY docker compose up -d
```

访问 `http://localhost:8099`。

## 使用说明

1. 打开应用，点击顶栏的**设置图标**
2. **添加 API Key** — 选择提供商类型（OpenAI / Anthropic），输入 API Key、Base URL 和模型名称
3. 保存时**自动验证连通性** — 验证通过显示 ✅
4. 从左侧边栏**创建新会话**
5. **开始对话** — 输入消息后按 Enter 发送
6. 回复内容实时流式展示，支持 Markdown 渲染
7. 使用 **Shift+Enter** 在输入框中换行
8. 开启**思考模式**以启用扩展推理（部分模型支持）
9. 批量处理：上传文件，配置筛选条件（可选），选择输入列，编写含 `{{列名}}` 占位符的 Prompt，点击开始跑批
10. 在 Prompt 编辑器中输入 `/` 可快速弹出列变量下拉菜单

## 项目结构

```
model-web/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置（加密密钥、数据库 URL）
│   │   ├── database.py          # SQLite 连接和表初始化
│   │   ├── models.py            # SQLAlchemy 数据模型
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── routers/
│   │   │   ├── keys.py          # API Key 增删改查和验证
│   │   │   ├── conversations.py # 会话增删改查
│   │   │   ├── chat.py          # 聊天接口（SSE 流式）
│   │   │   ├── batch.py         # 批量文件上传和执行
│   │   │   └── batch_tasks.py   # 批量任务管理
│   │   ├── services/
│   │   │   ├── key_service.py   # Key 加密和验证逻辑
│   │   │   ├── chat_service.py  # 聊天逻辑和上下文管理
│   │   │   ├── batch_service.py # 批量处理逻辑
│   │   │   └── llm/
│   │   │       ├── base.py      # LLM 抽象基类
│   │   │       ├── openai.py    # OpenAI 兼容适配器
│   │   │       └── anthropic.py # Anthropic 适配器
│   │   └── utils/
│   │       ├── crypto.py        # Fernet 加密工具
│   │       └── token_counter.py # Token 计数工具
│   ├── tests/                   # pytest 测试
│   ├── requirements.txt
│   └── .env                     # 环境变量（git 忽略）
├── frontend/
│   ├── src/
│   │   ├── App.vue              # 根组件
│   │   ├── main.ts              # Vue 入口
│   │   ├── api/                 # API 调用封装
│   │   ├── components/          # Vue 组件
│   │   │   ├── ChatWindow.vue   # 聊天主窗口
│   │   │   ├── MessageBubble.vue# 消息气泡
│   │   │   ├── SessionList.vue  # 会话列表
│   │   │   ├── InputBox.vue     # 输入框
│   │   │   ├── SettingsPanel.vue# 设置面板
│   │   │   └── BatchPanel.vue   # 批量处理面板
│   │   ├── stores/              # Pinia 状态管理
│   │   └── types/               # TypeScript 类型定义
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── Dockerfile
└── docs/
```

## API 接口

### 健康检查
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |

### API Key 管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/keys` | 添加 Key（自动验证连通性） |
| GET | `/api/keys` | 获取所有配置（不返回明文 key） |
| PUT | `/api/keys/{id}` | 更新配置 |
| DELETE | `/api/keys/{id}` | 删除配置 |
| POST | `/api/keys/{id}/verify` | 重新验证连通性 |
| POST | `/api/keys/{id}/activate` | 设为当前使用 |

### 会话管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/conversations` | 创建会话 |
| GET | `/api/conversations` | 获取会话列表 |
| GET | `/api/conversations/{id}` | 获取会话详情（含消息） |
| PUT | `/api/conversations/{id}` | 更新会话 |
| DELETE | `/api/conversations/{id}` | 删除会话 |

### 聊天
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/{conversation_id}` | 发送消息，返回 SSE 流 |

### 批量处理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/batch/upload` | 上传 Excel/JSON/TXT 文件 |
| POST | `/api/batch/run` | 启动批量处理（SSE 流） |
| POST | `/api/batch/{id}/filter-preview` | 预览筛选结果 |
| POST | `/api/batch/{id}/filter-download` | 下载筛选结果 Excel |
| GET | `/api/batch/{id}/download` | 下载批量处理结果 Excel |

### 批量任务管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/batch-tasks` | 获取所有批量任务 |
| GET | `/api/batch-tasks/{id}` | 获取任务详情 |
| PUT | `/api/batch-tasks/{id}` | 更新任务 |
| DELETE | `/api/batch-tasks/{id}` | 删除任务及文件 |
| GET | `/api/batch-tasks/{id}/preview` | 获取任务文件预览 |
| GET | `/api/batch-tasks/{id}/results` | 获取任务结果 |

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `ENCRYPTION_KEY` | 是 | — | Fernet 密钥，用于加密 API Key |
| `DATABASE_URL` | 否 | `sqlite+aiosqlite:///./llm_chat.db` | 数据库连接地址 |
| `STATIC_DIR` | 否 | — | 静态文件目录（部署构建后的前端） |
| `UPLOAD_DIR` | 否 | `./uploads` | 批量处理文件上传目录 |
| `CORS_ORIGINS` | 否 | `http://localhost:5173` | 允许的跨域来源（逗号分隔） |

## 许可证

MIT
