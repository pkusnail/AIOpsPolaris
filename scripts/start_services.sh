#!/bin/bash

# AIOps Polaris 服务启动脚本

set -e

echo "🚀 启动 AIOps Polaris 服务..."

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Docker和Docker Compose
echo -e "${YELLOW}检查依赖...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    exit 1
fi

# 检查端口是否被占用
check_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}警告: 端口 $port 已被占用 ($service)${NC}"
        echo "请停止占用端口的服务或修改配置"
        return 1
    fi
    return 0
}

echo "检查端口占用情况..."
check_port 3306 "MySQL" || true
check_port 7474 "Neo4j HTTP" || true
check_port 7687 "Neo4j Bolt" || true
check_port 8080 "Weaviate" || true
check_port 6379 "Redis" || true
check_port 8888 "API服务" || true
check_port 7860 "Gradio界面" || true

# 创建必要的目录
echo -e "${YELLOW}创建必要的目录...${NC}"
mkdir -p cache/embeddings
mkdir -p logs

# 启动基础服务
echo -e "${GREEN}启动基础服务 (MySQL, Neo4j, Weaviate, Redis)...${NC}"
docker-compose up -d mysql neo4j weaviate redis

# 等待服务启动
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 30

# 检查服务健康状态
echo -e "${YELLOW}检查服务状态...${NC}"

check_service() {
    local service=$1
    local port=$2
    local max_attempts=12
    local attempt=1
    
    echo "检查 $service 服务..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps $service | grep -q "Up"; then
            echo -e "${GREEN}✅ $service 服务正常${NC}"
            return 0
        fi
        
        echo "等待 $service 启动... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service 服务启动超时${NC}"
    docker-compose logs $service
    return 1
}

# 检查各个服务
check_service mysql 3306
check_service neo4j 7474
check_service weaviate 8080
check_service redis 6379

# 初始化数据库
echo -e "${GREEN}初始化数据库...${NC}"
cd "$(dirname "$0")/.."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: Python3 未安装${NC}"
    exit 1
fi

# 安装Python依赖（如果需要）
if [ ! -f "venv/bin/activate" ]; then
    echo -e "${YELLOW}创建Python虚拟环境...${NC}"
    python3 -m venv venv
fi

echo -e "${YELLOW}激活虚拟环境并安装依赖...${NC}"
source venv/bin/activate

# 检查是否需要安装依赖
if [ ! -f "venv/.deps_installed" ]; then
    echo -e "${YELLOW}安装Python依赖...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 下载spaCy模型（如果需要）
    python -m spacy download en_core_web_sm || echo "警告: 无法下载spaCy英文模型，将使用基础模型"
    
    touch venv/.deps_installed
fi

# 运行数据库初始化脚本
echo -e "${GREEN}运行数据库初始化...${NC}"
python scripts/init_database.py

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 数据库初始化失败${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 数据库初始化完成${NC}"

# 启动API服务
echo -e "${GREEN}启动API服务...${NC}"
nohup python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8888 --reload > logs/api.log 2>&1 &
API_PID=$!

# 等待API服务启动
echo -e "${YELLOW}等待API服务启动...${NC}"
sleep 10

# 检查API服务健康状态
for i in {1..12}; do
    if curl -s http://localhost:8888/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API服务启动成功${NC}"
        break
    fi
    
    if [ $i -eq 12 ]; then
        echo -e "${RED}❌ API服务启动失败${NC}"
        kill $API_PID 2>/dev/null || true
        exit 1
    fi
    
    echo "等待API服务响应... ($i/12)"
    sleep 5
done

# 启动Gradio界面
echo -e "${GREEN}启动Gradio前端界面...${NC}"
nohup python gradio_app.py > logs/gradio.log 2>&1 &
GRADIO_PID=$!

# 等待Gradio启动
echo -e "${YELLOW}等待Gradio界面启动...${NC}"
sleep 8

# 检查Gradio服务
for i in {1..6}; do
    if curl -s http://localhost:7860 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Gradio界面启动成功${NC}"
        break
    fi
    
    if [ $i -eq 6 ]; then
        echo -e "${RED}❌ Gradio界面启动失败${NC}"
        kill $GRADIO_PID 2>/dev/null || true
        kill $API_PID 2>/dev/null || true
        exit 1
    fi
    
    echo "等待Gradio界面响应... ($i/6)"
    sleep 5
done

# 保存进程ID
echo $API_PID > .api.pid
echo $GRADIO_PID > .gradio.pid

# 显示服务信息
echo ""
echo -e "${GREEN}🎉 AIOps Polaris 启动成功！${NC}"
echo ""
echo "服务访问地址:"
echo "  📱 Gradio界面:    http://localhost:7860"
echo "  🔧 API文档:       http://localhost:8888/docs"
echo "  ❤️  健康检查:      http://localhost:8888/health"
echo "  📊 Neo4j浏览器:   http://localhost:7474"
echo "  📈 Prometheus:    http://localhost:9090"
echo ""
echo "数据库连接信息:"
echo "  🗄️  MySQL:        localhost:3306 (aiops/aiops_pass)"  
echo "  🕸️  Neo4j:        localhost:7687 (neo4j/aiops123)"
echo "  🔍 Weaviate:     http://localhost:8080"
echo "  🚀 Redis:        localhost:6379"
echo ""
echo "日志文件:"
echo "  📋 API日志:       logs/api.log"
echo "  🖥️  Gradio日志:    logs/gradio.log"
echo ""
echo "停止服务: ./scripts/stop_services.sh"
echo ""

# 等待用户输入
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"

# 捕获中断信号
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务...${NC}"
    
    # 停止Python服务
    kill $GRADIO_PID 2>/dev/null || true
    kill $API_PID 2>/dev/null || true
    
    # 停止Docker服务
    docker-compose down
    
    # 清理PID文件
    rm -f .api.pid .gradio.pid
    
    echo -e "${GREEN}✅ 所有服务已停止${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 保持脚本运行
while true; do
    # 检查服务是否还在运行
    if ! kill -0 $API_PID 2>/dev/null; then
        echo -e "${RED}❌ API服务意外停止${NC}"
        break
    fi
    
    if ! kill -0 $GRADIO_PID 2>/dev/null; then
        echo -e "${RED}❌ Gradio服务意外停止${NC}"
        break
    fi
    
    sleep 5
done

cleanup