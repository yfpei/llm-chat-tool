# LLM Chat Tool

A personal multi-turn LLM chat web application with a ChatGPT-like UI. Supports OpenAI-compatible and Anthropic Claude APIs with SSE streaming, API key management, conversation persistence, and batch Excel processing.

## Features

- **Multi-provider LLM chat** — OpenAI-compatible and Anthropic Claude APIs with SSE streaming
- **API key management** — Add, verify, update, and switch between multiple API keys (encrypted at rest)
- **Conversation management** — Create, rename, delete conversations with full message history
- **Context window management** — Automatic token-aware truncation to stay within model context limits
- **Thinking mode** — Support for extended thinking (Anthropic) and reasoning models
- **Batch processing** — Upload Excel/JSON/TXT files, configure prompts, and process rows in parallel with concurrency control
- **Data filtering** — Filter rows before processing with condition groups supporting `(A AND B) OR (C AND D)` logic, top-N limit, contains/equals/gt/lt operators, and preview/download filtered results
- **Prompt variable highlighting** — Inline `{{variable}}` color highlighting in the prompt editor with `/` slash-picker for quick column selection
- **Markdown rendering** — Assistant responses rendered with rich Markdown support
- **Docker support** — Single-command deployment with Docker Compose

## Screenshots

![Chat Interface](frontend/src/assets/hero.png)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI 0.115 + uvicorn |
| Database | SQLite + SQLAlchemy (async) + aiosqlite |
| Encryption | cryptography (Fernet) |
| LLM SDKs | openai 1.51, anthropic 0.34 |
| Streaming | SSE via sse-starlette |
| Frontend | Vue 3 + TypeScript + Vite |
| UI Library | Naive UI |
| State | Pinia |
| Markdown | markdown-it |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 22+
- An OpenAI or Anthropic API key

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
echo "ENCRYPTION_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" > .env

# Start the backend
uvicorn app.main:app --host 0.0.0.0 --port 8099 --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API requests to the backend at `http://localhost:8099`.

### 3. Docker (Alternative)

```bash
# Generate encryption key
ENCRYPTION_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')

# Start with Docker Compose
ENCRYPTION_KEY=$ENCRYPTION_KEY docker compose up -d
```

Access at `http://localhost:8099`.

## Usage

1. Open the app, click the **Settings** icon in the top bar
2. **Add an API key** — select provider type (OpenAI / Anthropic), enter your API key, base URL, and model name
3. The key is **automatically verified** on save — look for the ✅ indicator
4. **Create a new conversation** from the left sidebar
5. **Start chatting** — type a message and press Enter to send
6. Responses stream in real-time with Markdown rendering
7. Use **Shift+Enter** for line breaks in the input box
8. Toggle **Thinking mode** to enable extended reasoning (where supported)
9. For batch processing: upload a file, configure filters (optional), select input columns, write a prompt with `{{column}}` placeholders, and run
10. Type `/` in the prompt editor to quickly insert column variables from a dropdown

## Project Structure

```
model-web/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration (encryption key, DB URL)
│   │   ├── database.py          # SQLite connection & table init
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── keys.py          # API key CRUD + verification
│   │   │   ├── conversations.py # Conversation CRUD
│   │   │   ├── chat.py          # Chat endpoint (SSE streaming)
│   │   │   ├── batch.py         # Batch file upload + run
│   │   │   └── batch_tasks.py   # Batch task management
│   │   ├── services/
│   │   │   ├── key_service.py   # Key encryption & verification
│   │   │   ├── chat_service.py  # Chat logic & context management
│   │   │   ├── batch_service.py # Batch processing logic
│   │   │   └── llm/
│   │   │       ├── base.py      # Abstract LLM provider
│   │   │       ├── openai.py    # OpenAI-compatible adapter
│   │   │       └── anthropic.py # Anthropic adapter
│   │   └── utils/
│   │       ├── crypto.py        # Fernet encryption utilities
│   │       └── token_counter.py # Token counting utilities
│   ├── tests/                   # pytest test suite
│   ├── requirements.txt
│   └── .env                     # Environment variables (git-ignored)
├── frontend/
│   ├── src/
│   │   ├── App.vue              # Root component
│   │   ├── main.ts              # Vue app entry
│   │   ├── api/                 # API client modules
│   │   ├── components/          # Vue components
│   │   │   ├── ChatWindow.vue   # Main chat area
│   │   │   ├── MessageBubble.vue# Message display
│   │   │   ├── SessionList.vue  # Conversation sidebar
│   │   │   ├── InputBox.vue     # Message input
│   │   │   ├── SettingsPanel.vue# API key management
│   │   │   └── BatchPanel.vue   # Batch processing UI
│   │   ├── stores/              # Pinia stores
│   │   └── types/               # TypeScript definitions
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── Dockerfile
└── docs/
```

## API Endpoints

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |

### API Keys
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/keys` | Add key (auto-verifies connectivity) |
| GET | `/api/keys` | List all keys (keys masked) |
| PUT | `/api/keys/{id}` | Update key |
| DELETE | `/api/keys/{id}` | Delete key |
| POST | `/api/keys/{id}/verify` | Re-verify connectivity |
| POST | `/api/keys/{id}/activate` | Set as active key |

### Conversations
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations` | List conversations |
| GET | `/api/conversations/{id}` | Get conversation with messages |
| PUT | `/api/conversations/{id}` | Update conversation |
| DELETE | `/api/conversations/{id}` | Delete conversation |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat/{conversation_id}` | Send message, returns SSE stream |

### Batch
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/batch/upload` | Upload Excel/JSON/TXT file |
| POST | `/api/batch/run` | Start batch processing (SSE stream) |
| POST | `/api/batch/{id}/filter-preview` | Preview filtered rows count and data |
| POST | `/api/batch/{id}/filter-download` | Download filtered data as Excel |
| GET | `/api/batch/{id}/download` | Download batch results as Excel |

### Batch Tasks
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/batch-tasks` | List all batch tasks |
| GET | `/api/batch-tasks/{id}` | Get batch task detail |
| PUT | `/api/batch-tasks/{id}` | Update batch task |
| DELETE | `/api/batch-tasks/{id}` | Delete batch task and files |
| GET | `/api/batch-tasks/{id}/preview` | Get task file preview |
| GET | `/api/batch-tasks/{id}/results` | Get task results from Excel |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENCRYPTION_KEY` | Yes | — | Fernet key for encrypting API keys |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./llm_chat.db` | Database connection URL |
| `STATIC_DIR` | No | — | Path to static files (serves built frontend) |
| `UPLOAD_DIR` | No | `./uploads` | Directory for uploaded batch files |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated allowed origins |

## License

MIT
