# Stage 1: Build frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Final image
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY backend/ ./

# Remove files that should not be in the image
RUN rm -f .env *.db && rm -rf uploads/*

# Copy built frontend static files
COPY --from=frontend-build /app/frontend/dist/ /app/static/

# Create data directory for volume mounts (db + uploads)
RUN mkdir -p /app/data

ENV STATIC_DIR=/app/static
ENV UPLOAD_DIR=/app/data/uploads
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/llm_chat.db

EXPOSE 8099

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099"]
