# AIOps Polaris API 文档

## 概述

AIOps Polaris API 是一个基于 FastAPI 的智能运维平台RESTful接口，提供系统监控、健康检查、智能对话等功能。

## 基础信息

- **基础URL**: `http://localhost:8888`
- **API版本**: v1.0.0
- **响应格式**: JSON
- **认证方式**: 暂无（开发版本）
- **LLM支持**: OpenAI, Claude, 本地vLLM, 演示模式

## API端点

### 1. 根端点

#### GET /

获取API基本信息。

**响应示例:**
```json
{
  "message": "AIOps Polaris API - 智能运维平台",
  "version": "1.0.0",
  "timestamp": "2025-08-30T06:15:00.000000",
  "endpoints": {
    "docs": "/docs",
    "health": "/health",
    "metrics": "/metrics", 
    "stats": "/stats",
    "chat": "/chat",
    "llm_info": "/llm/info",
    "llm_reload": "/llm/reload"
  }
}
```

### 2. 健康检查

#### GET /health

检查系统健康状态。

**响应示例:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-30T05:20:57.739078",
  "version": "1.0.0-simple",
  "components": {
    "database": {
      "status": "healthy",
      "type": "mysql"
    },
    "embedding": {
      "status": "healthy",
      "type": "service"
    },
    "aiops_graph": {
      "status": "healthy",
      "type": "graph"
    },
    "metrics": {
      "status": "healthy",
      "type": "monitoring"
    }
  }
}
```

**状态码:**
- `200`: 系统正常或部分降级
- `503`: 系统不可用

**响应字段:**
- `status`: 系统状态 (`healthy`, `degraded`, `unhealthy`)
- `timestamp`: 检查时间
- `version`: API版本
- `components`: 各组件状态详情

### 3. 系统统计

#### GET /stats

获取系统统计信息。

**响应示例:**
```json
{
  "system": {
    "cpu_usage": 9.7,
    "memory_usage": 30.5,
    "memory_total": 67359948800,
    "memory_available": 46848724992,
    "disk_usage": 75.80,
    "disk_total": 1866744266752,
    "disk_free": 356747620352
  },
  "services": {
    "database": "active",
    "embedding": "active",
    "aiops_graph": "active"
  },
  "version": "1.0.0-simple",
  "timestamp": "2025-08-30T05:21:07.965158"
}
```

**响应字段:**
- `system`: 系统资源使用情况
  - `cpu_usage`: CPU使用率(%)
  - `memory_usage`: 内存使用率(%)
  - `memory_total`: 总内存(字节)
  - `memory_available`: 可用内存(字节)
  - `disk_usage`: 磁盘使用率(%)
  - `disk_total`: 总磁盘空间(字节)
  - `disk_free`: 可用磁盘空间(字节)
- `services`: 服务状态
- `version`: API版本
- `timestamp`: 统计时间

### 4. 智能对话

#### POST /chat

与AIOps智能助手对话。

**请求体:**
```json
{
  "message": "Hello, AIOps!",
  "session_id": "test-session"
}
```

**请求参数:**
- `message` (string, required): 用户消息
- `session_id` (string, optional): 会话ID，用于保持上下文

**响应示例:**
```json
{
  "response": "收到查询: Hello, AIOps!。这是一个简化的响应，完整功能正在开发中。",
  "timestamp": "2025-08-30T05:21:37.778059",
  "session_id": "test-session"
}
```

**响应字段:**
- `response`: AI助手回复
- `timestamp`: 响应时间
- `session_id`: 会话ID

### 5. LLM 管理

#### GET /llm/info

获取当前LLM配置信息。

**响应示例:**
```json
{
  "llm_info": {
    "provider": "openai",
    "config": {
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "https://api.openai.com/v1",
      "model": "gpt-3.5-turbo",
      "max_tokens": 4096,
      "temperature": 0.7
    },
    "status": "active"
  },
  "timestamp": "2025-08-30T06:15:00.000000"
}
```

#### POST /llm/reload

重新加载LLM配置。

**响应示例:**
```json
{
  "message": "LLM configuration reloaded successfully",
  "new_config": {
    "provider": "openai",
    "config": {...},
    "status": "active"
  },
  "timestamp": "2025-08-30T06:15:00.000000"
}
```

### 6. 会话管理

#### GET /sessions/{user_id}

获取用户的会话列表。

**路径参数:**
- `user_id`: 用户ID

**响应示例:**
```json
{
  "user_id": "test_user",
  "sessions": [],
  "timestamp": "2025-08-30T06:15:00.000000"
}
```

#### GET /sessions/{session_id}/messages

获取会话的消息历史。

**路径参数:**
- `session_id`: 会话ID

**响应示例:**
```json
{
  "session_id": "session_123",
  "messages": [],
  "timestamp": "2025-08-30T06:15:00.000000"
}
```

#### DELETE /sessions/{session_id}

删除会话。

**路径参数:**
- `session_id`: 会话ID

**响应示例:**
```json
{
  "message": "Session session_123 deleted successfully",
  "timestamp": "2025-08-30T06:15:00.000000"
}
```

### 7. 知识图谱

#### GET /knowledge/entities

获取知识图谱实体。

**响应示例:**
```json
{
  "entities": [],
  "timestamp": "2025-08-30T06:15:00.000000"
}
```

#### POST /knowledge/extract

从文本中提取知识。

**请求体:**
```json
{
  "text": "要分析的文本内容"
}
```

**响应示例:**
```json
{
  "extracted_entities": [],
  "extracted_relations": [],
  "timestamp": "2025-08-30T06:15:00.000000"
}
```

### 8. 监控指标

#### GET /metrics

获取Prometheus格式的监控指标。

**响应格式**: `text/plain`

**响应示例:**
```
# HELP aiops_http_requests_total Total HTTP requests
# TYPE aiops_http_requests_total counter
aiops_http_requests_total{endpoint="/health",method="GET",status_code="200"} 2.0
aiops_http_requests_total{endpoint="/metrics",method="GET",status_code="200"} 5.0
aiops_http_requests_total{endpoint="/stats",method="GET",status_code="200"} 1.0

# HELP aiops_active_sessions Number of active user sessions
# TYPE aiops_active_sessions gauge
aiops_active_sessions 0.0

# HELP aiops_system_info_info System information
# TYPE aiops_system_info_info gauge
aiops_system_info_info{python_version="3.9+",service_name="aiops-polaris",version="1.0.0"} 1.0
```

**可用指标:**
- `aiops_http_requests_total`: HTTP请求总数
- `aiops_http_request_duration_seconds`: HTTP请求耗时
- `aiops_active_sessions`: 活跃会话数
- `aiops_messages_total`: 消息处理总数
- `aiops_database_connections`: 数据库连接数
- `aiops_system_info_info`: 系统信息

## 错误处理

### 错误响应格式

```json
{
  "detail": "错误描述"
}
```

### 常见错误码

- `400`: 请求参数错误
- `404`: 资源不存在  
- `422`: 请求体验证失败
- `500`: 内部服务器错误
- `503`: 服务不可用

## 使用示例

### cURL 示例

```bash
# 健康检查
curl http://localhost:8888/health

# 系统统计
curl http://localhost:8888/stats

# 智能对话
curl -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "系统状态如何?", "session_id": "demo-001"}'

# 获取监控指标
curl http://localhost:8888/metrics
```

### Python 示例

```python
import requests

# 基础URL
base_url = "http://localhost:8888"

# 健康检查
health = requests.get(f"{base_url}/health")
print(health.json())

# 智能对话
chat_data = {
    "message": "请检查系统状态",
    "session_id": "python-client-001"
}
chat_response = requests.post(f"{base_url}/chat", json=chat_data)
print(chat_response.json())
```

### JavaScript 示例

```javascript
// 健康检查
fetch('http://localhost:8888/health')
  .then(response => response.json())
  .then(data => console.log(data));

// 智能对话
fetch('http://localhost:8888/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: '系统运行正常吗?',
    session_id: 'js-client-001'
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

## API 限制

- 无认证要求（开发版本）
- 无请求频率限制
- 最大请求体大小：1MB
- 超时时间：30秒

## 开发环境

- **交互式文档**: http://localhost:8888/docs (Swagger UI)
- **替代文档**: http://localhost:8888/redoc (ReDoc)

## 监控和可观测性

- **Prometheus监控**: http://localhost:9090
- **Grafana仪表盘**: http://localhost:3000
- **健康检查**: http://localhost:8888/health
- **系统指标**: http://localhost:8888/metrics

## 版本说明

当前版本为简化演示版本，完整功能包括：

**已实现功能：**
- ✅ RESTful API接口
- ✅ 健康检查和系统统计
- ✅ Prometheus监控指标
- ✅ 基础智能对话
- ✅ 交互式API文档

**待实现功能：**
- ⏳ 完整的知识图谱查询
- ⏳ 高级语义搜索
- ⏳ 用户认证和权限管理
- ⏳ 完整的LLM集成
- ⏳ 更多智能运维功能

## 支持

如有问题或建议，请通过以下方式联系：

- 查看系统日志: `docker-compose logs api`
- 检查服务状态: `docker-compose ps`
- 健康检查: `curl http://localhost:8888/health`