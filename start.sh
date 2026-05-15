#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  启动服务
#  Usage: bash start.sh
# ============================================================

IMAGE_NAME="llm-chat-tool"
IMAGE_TAG="latest"
CONTAINER_NAME="llm-chat-tool"
PORT="${PORT:-8099}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${DATA_DIR:-${SCRIPT_DIR}/data}"
ENV_FILE="${DATA_DIR}/.env"

# ── 读取密钥 ─────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE" 2>/dev/null || true; set +a
fi

if [ -z "${ENCRYPTION_KEY:-}" ]; then
    echo "❌ 未找到 ENCRYPTION_KEY，请先运行 deploy.sh"
    exit 1
fi

# ── 检查镜像 ─────────────────────────────────────────
if ! docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" &>/dev/null; then
    echo "❌ 镜像 ${IMAGE_NAME}:${IMAGE_TAG} 不存在，请先运行 deploy.sh"
    exit 1
fi

# ── 停止旧容器（如有）────────────────────────────────
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker stop "${CONTAINER_NAME}" &>/dev/null || true
    docker rm "${CONTAINER_NAME}" &>/dev/null || true
fi

# ── 启动 ─────────────────────────────────────────────
mkdir -p "${DATA_DIR}"
echo "🚀 启动容器..."
docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -p "${PORT}:8099" \
    -v "${DATA_DIR}:/app/data" \
    -e "ENCRYPTION_KEY=${ENCRYPTION_KEY}" \
    "${IMAGE_NAME}:${IMAGE_TAG}"

# ── 等待就绪 ─────────────────────────────────────────
echo "⏳ 等待服务就绪..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${PORT}/api/health" &>/dev/null; then
        echo "✅ 服务已就绪: http://localhost:${PORT}"
        echo "   查看日志: docker logs -f ${CONTAINER_NAME}"
        exit 0
    fi
    sleep 1
done

echo "⚠️  容器已启动但健康检查超时，请查看日志: docker logs ${CONTAINER_NAME}"
