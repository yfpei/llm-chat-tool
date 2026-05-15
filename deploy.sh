#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  部署脚本 — 加载镜像、初始化配置（仅需运行一次）
#  Usage: bash deploy.sh [IMAGE_TAR]
# ============================================================

IMAGE_NAME="llm-chat-tool"
IMAGE_TAG="latest"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${DATA_DIR:-${SCRIPT_DIR}/data}"

# ── 0. 检查 docker ──────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "❌ 未找到 docker，请先安装 Docker。"
    echo "   离线安装参考: https://docs.docker.com/engine/install/"
    exit 1
fi

# ── 1. 加载镜像 ─────────────────────────────────────────
IMAGE_TAR=""
if [ $# -ge 1 ]; then
    IMAGE_TAR="$1"
else
    for ext in ".tar" ".tar.gz" ".tgz"; do
        if [ -f "${SCRIPT_DIR}/llm-chat-tool${ext}" ]; then
            IMAGE_TAR="${SCRIPT_DIR}/llm-chat-tool${ext}"
            break
        fi
    done
fi

if [ -n "$IMAGE_TAR" ] && [ -f "$IMAGE_TAR" ]; then
    echo "📦 加载镜像: $IMAGE_TAR"
    docker load -i "$IMAGE_TAR"
    echo "✅ 镜像加载完成"
elif docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" &>/dev/null; then
    echo "📦 使用已有镜像 (跳过 load)"
else
    echo "❌ 未找到镜像文件，且镜像 ${IMAGE_NAME}:${IMAGE_TAG} 不存在。"
    echo "   自动查找: llm-chat-tool.tar / .tar.gz / .tgz"
    echo "   也可指定路径: bash deploy.sh /path/to/llm-chat-tool.tar.gz"
    echo "   请先从构建机器导出镜像: docker save llm-chat-tool:latest | gzip > llm-chat-tool.tar.gz"
    exit 1
fi

# ── 2. 准备数据目录 ─────────────────────────────────────
mkdir -p "${DATA_DIR}"

# ── 3. 处理密钥 ─────────────────────────────────────────
ENV_FILE="${DATA_DIR}/.env"
if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE" 2>/dev/null || true; set +a
fi

if [ -n "${ENCRYPTION_KEY:-}" ]; then
    KEY_LEN=$(printf '%s' "${ENCRYPTION_KEY}" | wc -c)
    if [ "${KEY_LEN}" -ne 44 ] || echo "${ENCRYPTION_KEY}" | grep -q '[^A-Za-z0-9_\-=]'; then
        echo "⚠️  密钥格式不正确 (需44字符 url-safe base64)，将重新生成"
        sed -i '/^ENCRYPTION_KEY=/d' "$ENV_FILE" 2>/dev/null || true
        unset ENCRYPTION_KEY
    fi
fi

if [ -z "${ENCRYPTION_KEY:-}" ]; then
    ENCRYPTION_KEY=$(openssl rand -base64 32 2>/dev/null | tr '+/' '-_' | tr -d '\n' || \
                     dd if=/dev/urandom bs=32 count=1 2>/dev/null | base64 | tr '+/' '-_' | tr -d '\n')
    echo "# 自动生成的加密密钥 (请妥善保管)" >> "$ENV_FILE"
    echo "ENCRYPTION_KEY=${ENCRYPTION_KEY}" >> "$ENV_FILE"
    echo "🔑 已生成随机 ENCRYPTION_KEY 并保存到 ${ENV_FILE}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  部署准备完成"
echo "  数据目录: ${DATA_DIR}/"
echo "  启动服务: bash start.sh"
echo "  停止服务: bash stop.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
