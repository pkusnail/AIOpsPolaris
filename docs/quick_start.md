# AIOps Polaris 快速开始指南

## 概述

AIOps Polaris 是一个基于知识图谱和语义搜索的智能运维平台，整合了多种数据存储和处理技术来提供全面的运维支持。

## 系统架构

### 核心组件
- **API服务**: FastAPI驱动的RESTful接口
- **MySQL**: 业务数据和会话管理
- **Neo4j**: 知识图谱存储
- **Weaviate**: 向量数据库用于语义搜索
- **Redis**: 缓存和会话存储
- **Prometheus + Grafana**: 监控和可视化
- **vLLM**: 大语言模型推理服务

## 前置要求

### 硬件要求
- CPU: 4核心或更多
- 内存: 16GB或更多 (推荐32GB用于完整功能)
- 存储: 50GB可用空间
- GPU: (可选) NVIDIA GPU用于vLLM模型推理

### 软件要求
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (用于测试脚本)
- Git

### GPU支持 (可选)
如果要使用GPU进行模型推理，需要安装：
```bash
# 安装 NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - \
   && curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

## 安装步骤

### 1. 克隆项目
```bash
git clone <repository-url>
cd AIOpsPolaris
```

### 2. 检查环境
```bash
# 检查Docker版本
docker --version
docker-compose --version

# 检查可用内存
free -h

# 检查GPU（如果有）
nvidia-smi
```

### 3. 启动服务
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 验证安装

等待所有服务启动完成（约5-10分钟，首次启动需要下载镜像）：

```bash
# 检查服务健康状态
python tests/test_database_integration.py

# 测试监控集成
python tests/test_monitoring_integration.py

# 运行完整测试套件
python tests/test_all_services.py
```

## 服务访问地址

### 核心服务
- **API文档**: http://localhost:8888/docs
- **API健康检查**: http://localhost:8888/health
- **API指标**: http://localhost:8888/metrics

### 数据存储
- **MySQL**: localhost:3306 (aiops_user/aiops_pass)
- **Neo4j**: http://localhost:7474 (neo4j/aiops123)
- **Weaviate**: http://localhost:8080
- **Redis**: localhost:6379 (密码: aiops123)

### 监控和模型
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/aiops123)
- **vLLM API**: http://localhost:8000 (如果启用GPU)

## 基本使用

### 1. 健康检查
```bash
curl http://localhost:8888/health
```

### 2. 查看系统统计
```bash
curl http://localhost:8888/stats
```

### 3. 基本聊天测试
```bash
curl -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, AIOps!",
    "session_id": "test-session"
  }'
```

### 4. 监控指标
```bash
curl http://localhost:8888/metrics
```

## 开发和测试

### 运行测试脚本
```bash
# 安装Python依赖（用于测试脚本）
pip install aiohttp asyncio aiomysql neo4j httpx redis

# 数据库连接测试
python tests/test_database_integration.py

# 监控系统测试
python tests/test_monitoring_integration.py

# vLLM服务测试（如果启用）
python tests/test_vllm_integration.py

# 完整集成测试
python tests/test_all_services.py
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs api
docker-compose logs mysql
docker-compose logs neo4j
docker-compose logs weaviate
docker-compose logs prometheus
docker-compose logs grafana
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart api

# 重新构建并启动
docker-compose up --build -d
```

## 常见问题

### 1. 内存不足
如果系统内存不足，可以调整以下配置：
- Neo4j内存设置 (docker-compose.yml中的NEO4J_dbms_memory_*)
- 关闭vLLM服务（注释docker-compose.yml中的vllm部分）

### 2. 端口冲突
如果遇到端口冲突，修改docker-compose.yml中的端口映射：
```yaml
ports:
  - "8889:8000"  # 将8888改为8889
```

### 3. 服务启动失败
```bash
# 查看具体错误
docker-compose logs [service-name]

# 重新构建镜像
docker-compose build --no-cache [service-name]

# 清理并重启
docker-compose down
docker system prune -f
docker-compose up -d
```

### 4. GPU相关问题
```bash
# 检查NVIDIA驱动
nvidia-smi

# 检查Docker GPU支持
docker run --rm --gpus all nvidia/cuda:11.2-base-ubuntu20.04 nvidia-smi

# 如果GPU不可用，修改docker-compose.yml禁用vLLM的GPU依赖
```

## 配置说明

### 环境变量
可以通过环境变量或修改docker-compose.yml来调整配置：

```bash
# API服务配置
export API_HOST=0.0.0.0
export API_PORT=8000

# 数据库配置
export MYSQL_ROOT_PASSWORD=aiops123
export NEO4J_PASSWORD=aiops123
export REDIS_PASSWORD=aiops123

# 模型配置
export VLLM_MODEL="Qwen/Qwen2.5-7B-Instruct"
export VLLM_MAX_MODEL_LEN=4096
```

### 数据目录
Docker volumes将数据存储在：
- MySQL: mysql_data
- Neo4j: neo4j_data, neo4j_logs
- Weaviate: weaviate_data
- Redis: redis_data
- Prometheus: prometheus_data
- Grafana: grafana_data

## 下一步

1. 查看完整的[系统设计文档](./system-design.md)
2. 了解[API文档](http://localhost:8888/docs)
3. 配置[Grafana仪表盘](http://localhost:3000)
4. 开发自定义的运维脚本和集成

## 支持

如遇问题，请检查：
1. 系统要求是否满足
2. Docker和Docker Compose版本
3. 端口占用情况
4. 系统日志和服务日志
5. 可用内存和磁盘空间

更多详细信息请参考项目文档或提交Issue。