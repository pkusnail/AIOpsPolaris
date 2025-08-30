# AIOps Polaris API 参考文档

## 📖 概述

AIOps Polaris 提供了完整的 RESTful API，支持智能运维对话、知识搜索、会话管理等功能。所有API端点都通过 FastAPI 提供，支持自动化的API文档和交互式测试。

**基础URL**: `http://localhost:8888`

**API文档**: http://localhost:8888/docs (Swagger UI)

**响应格式**: 所有API返回标准JSON格式

## 🔐 认证

当前版本为POC演示，暂不需要认证。生产环境需要添加JWT或API Key认证。

## 📊 标准响应格式

### 成功响应
```json
{
  "success": true,
  "data": {},
  "message": "操作成功"
}
```

### 错误响应
```json
{
  "error": true,
  "status_code": 400,
  "message": "错误描述",
  "timestamp": "2024-08-30T10:30:00Z"
}
```

## 🤖 智能对话 API

### POST `/chat` - 智能运维对话

与AIOps助手进行智能对话，获得运维建议。

**请求参数**:
```json
{
  "message": "string",         // 必须: 用户输入的问题
  "user_id": "string",         // 必须: 用户ID
  "session_id": "string",      // 可选: 会话ID，不提供时自动创建
  "temperature": 0.7,          // 可选: 生成温度 (0.0-1.0)
  "max_tokens": 1000          // 可选: 最大Token数
}
```

**响应示例**:
```json
{
  "success": true,
  "response": "基于您描述的CPU使用率过高问题，我建议您按以下步骤排查：\n1. 使用top命令查看占用CPU最高的进程\n2. 检查系统负载average\n3. 查看最近的代码部署情况...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_id": "msg_20240830_103000",
  "tokens_used": 156,
  "processing_time": 2.34,
  "agent_messages": [
    {
      "type": "planner",
      "content": "问题分析：CPU高负载排查",
      "timestamp": "2024-08-30T10:30:00Z"
    },
    {
      "type": "knowledge",
      "content": "找到5个相关知识文档",
      "timestamp": "2024-08-30T10:30:01Z"
    },
    {
      "type": "reasoning", 
      "content": "根因分析：可能的CPU消耗原因",
      "timestamp": "2024-08-30T10:30:02Z"
    },
    {
      "type": "answer",
      "content": "最终回复内容",
      "timestamp": "2024-08-30T10:30:02Z"
    }
  ],
  "suggestions": [
    "查看执行详情",
    "获取相关文档", 
    "查询历史案例"
  ]
}
```

**错误码**:
- `400`: 请求参数错误
- `500`: 服务器内部错误
- `503`: 服务不可用

---

## 🔍 搜索 API

### POST `/search` - 混合知识搜索

执行向量+关键词+图的混合搜索，返回最相关的知识文档。

**请求参数**:
```json
{
  "query": "string",           // 必须: 搜索查询
  "search_type": "hybrid",     // 可选: 搜索类型 [hybrid|vector|keyword|graph]
  "source": "string",          // 可选: 数据源过滤
  "category": "string",        // 可选: 分类过滤
  "limit": 10,                 // 可选: 返回结果数量
  "threshold": 0.7             // 可选: 相似度阈值
}
```

**响应示例**:
```json
{
  "documents": [
    {
      "id": "doc_001",
      "title": "CPU性能优化指南",
      "content": "CPU使用率过高时的排查和优化方法...",
      "source": "wiki",
      "category": "性能优化",
      "tags": ["CPU", "性能", "优化"],
      "score": 0.95,
      "created_at": "2024-08-20T10:00:00Z"
    }
  ],
  "total": 1,
  "search_type": "hybrid",
  "processing_time": 0.45,
  "search_metadata": {
    "vector_results": 3,
    "keyword_results": 2, 
    "graph_results": 1
  }
}
```

### GET `/search/suggestions` - 获取搜索建议

基于输入的部分查询，提供搜索建议。

**参数**:
- `query` (string): 部分输入的查询
- `limit` (int): 建议数量，默认5

**响应示例**:
```json
{
  "suggestions": [
    "CPU使用率过高排查",
    "CPU性能优化方法",
    "CPU监控最佳实践"
  ]
}
```

---

## ❤️ 系统监控 API

### GET `/health` - 健康检查

检查系统各组件的健康状况。

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-08-30T10:30:00Z",
  "version": "1.0.0",
  "components": {
    "weaviate": {
      "status": "healthy",
      "response_time": 45,
      "last_check": "2024-08-30T10:30:00Z"
    },
    "neo4j": {
      "status": "healthy", 
      "response_time": 23,
      "last_check": "2024-08-30T10:30:00Z"
    },
    "embedding": {
      "status": "healthy",
      "model_info": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "device": "cpu"
      }
    }
  }
}
```

### GET `/stats` - 系统统计信息

获取系统使用统计和性能指标。

**响应示例**:
```json
{
  "vector_stats": {
    "total_documents": 10,
    "total_vectors": 10,
    "last_updated": "2024-08-30T08:00:00Z"
  },
  "graph_stats": {
    "total_nodes": 25,
    "total_relationships": 18,
    "node_types": {
      "Person": 5,
      "Technology": 8,
      "Problem": 7,
      "Solution": 5
    }
  },
  "database_stats": {
    "total_sessions": 3,
    "total_messages": 12,
    "active_sessions": 1
  },
  "api_info": {
    "version": "1.0.0",
    "uptime": "2 hours",
    "environment": "development"
  }
}
```

### GET `/agent/status` - Agent状态

获取多Agent系统的运行状态。

**响应示例**:
```json
{
  "agents": {
    "planner": {
      "status": "active",
      "tools": ["analyze_query", "create_plan", "search_relevant_docs"],
      "last_execution": "2024-08-30T10:25:00Z"
    },
    "knowledge": {
      "status": "active",
      "tools": ["search_documents", "find_similar_cases", "get_entity_relationships"],
      "last_execution": "2024-08-30T10:25:01Z"
    },
    "reasoning": {
      "status": "active", 
      "tools": ["analyze_symptoms", "infer_root_causes", "evaluate_solutions"],
      "last_execution": "2024-08-30T10:25:02Z"
    },
    "executor": {
      "status": "active",
      "tools": ["parse_execution_plan", "execute_step", "verify_result"],
      "last_execution": "2024-08-30T10:25:03Z"
    }
  },
  "graph_state": "ready",
  "total_executions": 4
}
```

---

## 👥 会话管理 API

### GET `/sessions/{user_id}` - 获取用户会话列表

获取指定用户的所有会话。

**参数**:
- `user_id` (string): 用户ID
- `page` (int): 页码，默认1
- `page_size` (int): 每页大小，默认20

**响应示例**:
```json
{
  "sessions": [
    {
      "id": 1,
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2024-08-30T08:00:00Z",
      "updated_at": "2024-08-30T10:30:00Z",
      "is_active": true,
      "session_metadata": {
        "temperature": 0.7,
        "max_tokens": 1000
      }
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### GET `/sessions/{session_id}/messages` - 获取会话消息

获取指定会话的所有消息。

**参数**:
- `session_id` (string): 会话ID
- `page` (int): 页码，默认1
- `page_size` (int): 每页大小，默认50

**响应示例**:
```json
{
  "messages": [
    {
      "id": 1,
      "message": "服务器CPU使用率过高怎么办？",
      "response": "基于您的问题，我建议...",
      "message_type": "user",
      "created_at": "2024-08-30T10:30:00Z",
      "tokens_used": 156,
      "processing_time": 2.34,
      "message_metadata": {
        "agent_messages": [...]
      }
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

### DELETE `/sessions/{session_id}` - 删除会话

停用指定的会话。

**响应示例**:
```json
{
  "success": true,
  "message": "Session deleted successfully"
}
```

---

## 🧠 知识管理 API

### GET `/knowledge/entities` - 获取实体列表

获取知识图谱中的实体信息。

**参数**:
- `entity_type` (string): 实体类型过滤
- `limit` (int): 返回数量，默认100

**响应示例**:
```json
{
  "entities": [
    {
      "id": 1,
      "name": "CPU",
      "entity_type": "Technology",
      "description": "中央处理器",
      "properties": {
        "category": "硬件",
        "monitoring": "top, htop"
      },
      "created_at": "2024-08-30T08:00:00Z",
      "updated_at": "2024-08-30T08:00:00Z"
    }
  ],
  "total": 1
}
```

### POST `/knowledge/extract` - 知识提取

从文本中提取实体和关系信息。

**参数**:
- `text` (string): 要处理的文本
- `source` (string): 数据源标识，默认"manual"

**请求示例**:
```bash
curl -X POST "http://localhost:8888/knowledge/extract?source=manual" \
  -H "Content-Type: application/json" \
  -d '"Kubernetes deployment failed due to insufficient memory resources"'
```

**响应示例**:
```json
{
  "entities": [
    {
      "text": "Kubernetes",
      "label": "Technology",
      "confidence": 0.95
    },
    {
      "text": "deployment",
      "label": "Process", 
      "confidence": 0.89
    },
    {
      "text": "memory resources",
      "label": "Resource",
      "confidence": 0.92
    }
  ],
  "relationships": [
    {
      "source": "deployment",
      "target": "memory resources",
      "relation": "requires",
      "confidence": 0.87
    }
  ],
  "document_info": {
    "title": "Manual Input",
    "source": "manual",
    "processed_at": "2024-08-30T10:30:00Z"
  }
}
```

---

## 🔧 使用示例

### Python 客户端示例

```python
import requests
import json

class AIOpsClient:
    def __init__(self, base_url="http://localhost:8888"):
        self.base_url = base_url
        
    def chat(self, message, user_id, temperature=0.7):
        """发送聊天消息"""
        response = requests.post(
            f"{self.base_url}/chat",
            json={
                "message": message,
                "user_id": user_id,
                "temperature": temperature
            }
        )
        return response.json()
    
    def search(self, query, search_type="hybrid", limit=10):
        """搜索知识库"""
        response = requests.post(
            f"{self.base_url}/search",
            json={
                "query": query,
                "search_type": search_type,
                "limit": limit
            }
        )
        return response.json()
    
    def health_check(self):
        """健康检查"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()

# 使用示例
client = AIOpsClient()

# 聊天
result = client.chat(
    message="生产环境CPU使用率突然飙升，如何排查？",
    user_id="devops_user"
)
print(result["response"])

# 搜索
search_result = client.search("数据库性能优化")
for doc in search_result["documents"]:
    print(f"- {doc['title']}")

# 健康检查
health = client.health_check()
print(f"系统状态: {health['status']}")
```

### JavaScript 客户端示例

```javascript
class AIOpsClient {
    constructor(baseUrl = 'http://localhost:8888') {
        this.baseUrl = baseUrl;
    }

    async chat(message, userId, temperature = 0.7) {
        const response = await fetch(`${this.baseUrl}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                user_id: userId,
                temperature: temperature
            })
        });
        return await response.json();
    }

    async search(query, searchType = 'hybrid', limit = 10) {
        const response = await fetch(`${this.baseUrl}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                search_type: searchType,
                limit: limit
            })
        });
        return await response.json();
    }
}

// 使用示例
const client = new AIOpsClient();

// 聊天
client.chat('CPU使用率过高怎么办？', 'web_user')
    .then(result => {
        console.log(result.response);
    });

// 搜索
client.search('Redis性能优化')
    .then(result => {
        result.documents.forEach(doc => {
            console.log(`- ${doc.title}`);
        });
    });
```

---

## ⚡ 性能考虑

- **并发限制**: 当前支持中等并发，生产环境需要配置适当的工作进程数
- **响应时间**: 聊天API平均响应时间 2-5秒，搜索API平均 0.5-2秒
- **缓存策略**: 嵌入向量和常用查询结果会被缓存
- **超时设置**: API调用建议设置30秒超时

## 🚀 生产部署建议

1. **认证授权**: 添加JWT或API Key认证
2. **限流控制**: 实现基于用户的请求限流
3. **日志监控**: 配置详细的API访问日志
4. **错误处理**: 增强错误信息和恢复机制
5. **性能优化**: 配置连接池和缓存策略

---

这份API文档提供了AIOps Polaris所有API端点的详细说明，帮助开发者快速集成和使用系统功能。