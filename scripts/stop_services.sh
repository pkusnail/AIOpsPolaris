#!/bin/bash

# AIOps Polaris 服务停止脚本

set -e

echo "🛑 停止 AIOps Polaris 服务..."

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 进入项目目录
cd "$(dirname "$0")/.."

# 停止Python服务
echo -e "${YELLOW}停止Python服务...${NC}"

if [ -f ".api.pid" ]; then
    API_PID=$(cat .api.pid)
    if kill -0 $API_PID 2>/dev/null; then
        kill $API_PID
        echo -e "${GREEN}✅ API服务已停止${NC}"
    fi
    rm -f .api.pid
fi

if [ -f ".gradio.pid" ]; then
    GRADIO_PID=$(cat .gradio.pid)
    if kill -0 $GRADIO_PID 2>/dev/null; then
        kill $GRADIO_PID
        echo -e "${GREEN}✅ Gradio服务已停止${NC}"
    fi
    rm -f .gradio.pid
fi

# 停止可能残留的Python进程
pkill -f "uvicorn src.api.main:app" 2>/dev/null || true
pkill -f "gradio_app.py" 2>/dev/null || true

# 停止Docker服务
echo -e "${YELLOW}停止Docker服务...${NC}"
docker-compose down

echo -e "${GREEN}✅ 所有服务已停止${NC}"

# 清理日志（可选）
read -p "是否清理日志文件? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f logs/*.log
    echo -e "${GREEN}✅ 日志文件已清理${NC}"
fi

echo ""
echo "服务已全部停止。使用 ./scripts/start_services.sh 重新启动。"