import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.database import init_db
from app.routers import keys, conversations, chat, batch, batch_tasks, es_export, mysql_export, auth, users, eval

logging.basicConfig(level=logging.INFO)

STATIC_DIR = os.environ.get("STATIC_DIR", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="LLM Chat Tool", version="1.0.0", lifespan=lifespan)

cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
if cors_origins and cors_origins[0]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


app.include_router(keys.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(batch.router)
app.include_router(batch_tasks.router)
app.include_router(es_export.router)
app.include_router(mysql_export.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(eval.router)

if STATIC_DIR and os.path.isdir(STATIC_DIR):
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # SPA fallback: serve index.html for any non-file, non-API route
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return JSONResponse({"detail": "Not Found"}, status_code=404)
