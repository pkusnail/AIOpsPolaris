# AIOps Polaris 测试说明

## 🧪 测试概览

AIOps Polaris 提供完整的测试套件，覆盖所有核心组件的集成测试。

### 测试脚本
- `test_all_services.py` - 综合测试脚本（推荐使用）
- `test_database_integration.py` - 数据库集成测试 
- `test_monitoring_integration.py` - 监控系统集成测试
- `test_vllm_integration.py` - vLLM服务集成测试

## 🚀 快速开始

### 前置要求
- Docker和Docker Compose已安装
- NVIDIA GPU驱动（用于vLLM服务）
- Python 3.11+ 环境

### 运行全套测试
```bash
# 1. 启动所有服务
docker-compose up -d

# 2. 等待服务启动完成（特别是vLLM需要下载模型）
docker-compose ps

# 3. 运行综合测试
python tests/test_all_services.py
```

## 📋 详细测试说明

### 1️⃣ 数据库集成测试
```bash
python tests/test_database_integration.py
```

**测试内容:**
- MySQL连接和基本CRUD操作
- Neo4j图数据库连接和节点创建
- Weaviate向量数据库连接和文档操作
- Redis缓存连接和键值操作

**预期输出:**
```
🗄️  AIOps Polaris 数据库集成测试
==================================================

🔍 测试 MySQL 连接...
   ✅ MySQL: 连接成功
      版本: 8.0.x
      test_records: x

🔍 测试 Neo4j 连接...
   ✅ Neo4j: 连接成功
      版本: 5.15.0
      test_nodes: x

🔍 测试 Weaviate 连接...
   ✅ Weaviate: 连接成功
      classes: ['TestDocument', ...]
      test_documents: x

🔍 测试 Redis 连接...
   ✅ Redis: 连接成功
      版本: 7.2.x
      test_keys_count: x
```

### 2️⃣ 监控系统集成测试
```bash
python tests/test_monitoring_integration.py
```

**测试内容:**
- API, Prometheus, Grafana服务健康检查
- API流量模拟和指标生成
- Prometheus指标收集验证
- Grafana数据源连接测试

**预期输出:**
```
🔍 AIOps Polaris 监控系统集成测试
==================================================

1️⃣  测试服务健康状态...
   ✅ API: healthy
   ✅ PROMETHEUS: healthy  
   ✅ GRAFANA: healthy

2️⃣  生成API流量以创建指标数据...
   ✅ 成功发送 9 个请求

3️⃣  测试Prometheus指标收集...
   ✅ 找到 5/5 个关键指标

4️⃣  测试Prometheus查询API...
   ✅ 查询成功，状态: success

5️⃣  测试Grafana数据源...
   ✅ Grafana连接成功
```

### 3️⃣ vLLM服务集成测试
```bash
python tests/test_vllm_integration.py
```

**测试内容:**
- vLLM服务健康状态检查
- 模型列表接口测试
- 文本生成接口测试（多种场景）
- 聊天接口测试
- 流式响应测试

**预期输出:**
```
🤖 AIOps Polaris vLLM服务集成测试
==================================================

1️⃣  测试vLLM服务健康状态...
   ✅ vLLM服务正常运行

2️⃣  测试模型列表接口...
   ✅ 找到 1 个模型
      - Qwen/Qwen2.5-7B-Instruct

3️⃣  测试文本生成接口...
   ✅ 完成 3/3 个测试

4️⃣  测试聊天接口...
   ✅ 聊天接口测试成功

5️⃣  测试流式响应...
   ✅ 流式响应测试成功
```

## 🔧 服务访问地址

### 核心服务
- **API文档**: http://localhost:8888/docs
- **API健康检查**: http://localhost:8888/health
- **API指标**: http://localhost:8888/metrics

### 数据库服务
- **MySQL**: localhost:3306 (aiops_user/aiops_pass)
- **Neo4j浏览器**: http://localhost:7474 (neo4j/aiops123)
- **Weaviate**: http://localhost:8080
- **Redis**: localhost:6379 (密码: aiops123)

### AI服务
- **vLLM OpenAI API**: http://localhost:8000/v1
- **vLLM健康检查**: http://localhost:8000/health

### 监控服务
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/aiops123)

### 代理服务
- **Nginx反向代理**: http://localhost:80

## 🐛 故障排除

### GPU相关问题

1. **vLLM启动失败 - CUDA版本不匹配**
   ```bash
   # 检查CUDA版本
   nvidia-smi
   
   # 如果CUDA版本低于12.8，使用兼容版本
   # 已配置使用 vllm/vllm-openai:v0.4.2 镜像
   ```

2. **显存不足**
   ```bash
   # 检查GPU显存使用情况
   nvidia-smi
   
   # 调整vLLM内存使用率（docker-compose.yml）
   VLLM_GPU_MEMORY_UTILIZATION: "0.7"  # 降低到0.5或更低
   ```

### 数据库连接问题

1. **服务连接失败**
   ```bash
   # 检查所有服务状态
   docker-compose ps
   
   # 查看特定服务日志
   docker-compose logs mysql
   docker-compose logs neo4j
   docker-compose logs weaviate
   docker-compose logs redis
   ```

2. **健康检查失败**
   ```bash
   # 等待服务完全启动
   docker-compose up -d
   
   # 检查网络连接
   docker network ls
   docker network inspect aiopspolaris_aiops-network
   ```

### 监控系统问题

1. **Prometheus无法收集指标**
   ```bash
   # 检查API服务是否正常
   curl http://localhost:8888/health
   curl http://localhost:8888/metrics
   
   # 检查Prometheus配置
   curl http://localhost:9090/api/v1/targets
   ```

2. **Grafana无法连接数据源**
   ```bash
   # 检查Grafana日志
   docker-compose logs grafana
   
   # 手动测试Prometheus连接
   curl http://localhost:9090/api/v1/query?query=up
   ```

### 常用调试命令

```bash
# 重启所有服务
docker-compose down && docker-compose up -d

# 查看资源使用情况
docker stats

# 清理Docker资源（谨慎使用）
docker system prune -a

# 查看详细服务配置
docker-compose config

# 实时查看服务日志
docker-compose logs -f --tail=50 [service_name]
```

## 📊 性能基准

### GPU使用情况
- **模型**: Qwen/Qwen2.5-7B-Instruct
- **显存占用**: ~13-15GB（推理时）
- **推理速度**: ~20-50 tokens/s（取决于硬件）

### 数据库性能
- **MySQL**: 支持高并发连接，适合结构化数据
- **Neo4j**: 图查询性能优异，适合关系分析
- **Weaviate**: 向量搜索响应时间 <100ms
- **Redis**: 缓存命中率 >95%

## 🔄 持续集成

测试脚本支持在CI/CD环境中运行：

```bash
# 设置环境变量（可选）
export AIOPS_TEST_TIMEOUT=300
export AIOPS_SKIP_GPU_TESTS=true  # 在无GPU环境跳过vLLM测试

# 运行测试并生成报告
python tests/test_all_services.py

# 测试报告将保存在 tests/test_report.md
```