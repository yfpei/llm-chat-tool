#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  停止服务
#  Usage: bash stop.sh
# ============================================================

CONTAINER_NAME="llm-chat-tool"

if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "⚠️  容器 ${CONTAINER_NAME} 未运行"
    exit 0
fi

echo "🛑 停止容器: ${CONTAINER_NAME}"
docker stop "${CONTAINER_NAME}" && echo "✅ 已停止"
