#!/usr/bin/env bash
# ============================================================
#  导出镜像脚本 — 在构建机器上运行
#  Usage: bash export.sh
#  生成 llm-chat-tool.tar 供离线部署使用
# ============================================================
set -euo pipefail

IMAGE_NAME="llm-chat-tool"
IMAGE_TAG="latest"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 如果镜像不存在，先构建
if ! docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" &>/dev/null; then
    echo "🔨 镜像不存在，先构建..."
    docker compose build
fi

OUTPUT="${SCRIPT_DIR}/llm-chat-tool.tar.gz"

echo "📦 导出镜像: ${IMAGE_NAME}:${IMAGE_TAG} -> ${OUTPUT}"
docker save "${IMAGE_NAME}:${IMAGE_TAG}" | gzip > "${OUTPUT}"

SIZE=$(du -h "${OUTPUT}" | cut -f1)
echo "✅ 导出完成: ${OUTPUT} (${SIZE})"
echo ""
echo "将以下文件复制到目标机器同目录:"
echo "  - deploy.sh"
echo "  - llm-chat-tool.tar.gz"
echo ""
echo "然后在目标机器上运行: bash deploy.sh"
