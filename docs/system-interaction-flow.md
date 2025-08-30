# AIOps Polaris 系统交互流程文档

## 系统概览

AIOps Polaris 是一个基于 RAG + 混合搜索 + 多Agent架构的智能运维助手系统，采用微服务架构设计，支持多种交互方式。

## 系统架构图

```mermaid
graph TB
    subgraph "前端层 Frontend Layer"
        WebUI[Web UI<br/>web_ui.html]
        CLI[CLI Interface<br/>chat_cli.py]
    end
    
    subgraph "API网关层 API Gateway"
        FastAPI[FastAPI Server<br/>:8888]
    end
    
    subgraph "业务逻辑层 Business Logic"
        AIOpsGraph[AIOps Graph<br/>多Agent协调器]
        
        subgraph "Agents"
            Planner[Planner Agent<br/>查询分析和规划]
            Knowledge[Knowledge Agent<br/>知识检索]
            Reasoning[Reasoning Agent<br/>推理分析]
            Executor[Executor Agent<br/>执行操作]
        end
    end
    
    subgraph "服务层 Service Layer"
        SearchSvc[Search Service<br/>混合搜索]
        DatabaseSvc[Database Service<br/>数据库操作]
        VectorSvc[Vector Service<br/>向量搜索]
        GraphSvc[Graph Service<br/>图数据库]
        EmbeddingSvc[Embedding Service<br/>文本嵌入]
        NERSvc[NER Service<br/>实体识别]
    end
    
    subgraph "数据存储层 Data Storage"
        MySQL[(MySQL<br/>会话/消息)]
        Neo4j[(Neo4j<br/>知识图谱)]
        Weaviate[(Weaviate<br/>向量数据库)]
        Redis[(Redis<br/>缓存)]
    end
    
    WebUI --> FastAPI
    CLI --> FastAPI
    FastAPI --> AIOpsGraph
    AIOpsGraph --> Planner
    AIOpsGraph --> Knowledge
    AIOpsGraph --> Reasoning
    AIOpsGraph --> Executor
    
    Planner --> SearchSvc
    Knowledge --> SearchSvc
    Reasoning --> SearchSvc
    Executor --> DatabaseSvc
    
    SearchSvc --> VectorSvc
    SearchSvc --> GraphSvc
    SearchSvc --> DatabaseSvc
    
    DatabaseSvc --> MySQL
    VectorSvc --> Weaviate
    GraphSvc --> Neo4j
    SearchSvc --> Redis
    EmbeddingSvc --> Redis
```

## Web UI 交互时序图

### 1. 用户聊天交互流程

```mermaid
sequenceDiagram
    participant User as DevOps用户
    participant WebUI as Web UI
    participant API as FastAPI Server
    participant Graph as AIOps Graph
    participant Agents as Multi-Agents
    participant Services as Services
    participant DB as Databases
    
    User->>WebUI: 输入运维问题
    WebUI->>WebUI: 验证输入，显示加载状态
    
    WebUI->>API: POST /chat
    Note over WebUI,API: {message, user_id, temperature}
    
    API->>API: 创建/获取用户会话
    API->>DB: 查询/创建 UserSession
    DB-->>API: 返回会话信息
    
    API->>Graph: process_user_message_simple()
    
    loop Multi-Agent 处理流程
        Graph->>Agents: 调用 Planner Agent
        Agents->>Services: 分析查询，制定计划
        Services-->>Agents: 返回分析结果
        
        Graph->>Agents: 调用 Knowledge Agent
        Agents->>Services: 搜索相关知识
        Services->>DB: 查询向量/图/关系数据
        DB-->>Services: 返回匹配结果
        Services-->>Agents: 返回知识信息
        
        Graph->>Agents: 调用 Reasoning Agent  
        Agents->>Services: 推理分析问题
        Services-->>Agents: 返回推理结果
        
        Graph->>Agents: 调用 Executor Agent
        Agents->>Services: 生成执行方案
        Services-->>Agents: 返回执行建议
    end
    
    Graph-->>API: 返回处理结果
    API->>DB: 保存消息记录
    DB-->>API: 确认保存
    
    API-->>WebUI: 返回响应结果
    Note over API,WebUI: {response, session_id, processing_time}
    
    WebUI->>WebUI: 显示AI回复，更新状态
    WebUI-->>User: 展示运维建议
```

### 2. 系统健康检查流程

```mermaid
sequenceDiagram
    participant User as DevOps用户
    participant WebUI as Web UI
    participant API as FastAPI Server
    participant Services as Services
    participant DB as Databases
    
    User->>WebUI: 点击"系统状态"按钮
    WebUI->>API: GET /health
    
    par 并行检查各服务
        API->>Services: 检查 Weaviate 连接
        Services->>DB: 连接测试
        DB-->>Services: 返回状态
        Services-->>API: Weaviate状态
    and
        API->>Services: 检查 Neo4j 连接  
        Services->>DB: 连接测试
        DB-->>Services: 返回状态
        Services-->>API: Neo4j状态
    and
        API->>Services: 检查 Embedding 服务
        Services-->>API: 模型状态
    end
    
    API-->>WebUI: 返回健康状态
    Note over API,WebUI: {status, components, timestamp}
    
    WebUI->>WebUI: 格式化显示状态信息
    WebUI-->>User: 显示系统健康状况
```

### 3. 知识搜索流程

```mermaid
sequenceDiagram
    participant User as DevOps用户
    participant WebUI as Web UI
    participant API as FastAPI Server
    participant SearchSvc as Search Service
    participant VectorSvc as Vector Service
    participant GraphSvc as Graph Service
    participant DB as Databases
    
    User->>WebUI: 点击"搜索知识库"
    WebUI->>WebUI: 弹出输入框
    User->>WebUI: 输入搜索关键词
    
    WebUI->>API: POST /search
    Note over WebUI,API: {query, search_type: "hybrid", limit: 5}
    
    API->>SearchSvc: hybrid_search()
    
    par 并行混合搜索
        SearchSvc->>VectorSvc: 向量相似搜索
        VectorSvc->>DB: 查询 Weaviate
        DB-->>VectorSvc: 返回相似向量
        VectorSvc-->>SearchSvc: 向量搜索结果
    and
        SearchSvc->>GraphSvc: 图数据库搜索
        GraphSvc->>DB: 查询 Neo4j
        DB-->>GraphSvc: 返回图节点/关系
        GraphSvc-->>SearchSvc: 图搜索结果
    and
        SearchSvc->>DB: MySQL全文搜索
        DB-->>SearchSvc: 返回文档匹配
    end
    
    SearchSvc->>SearchSvc: 合并排序搜索结果
    SearchSvc-->>API: 返回混合搜索结果
    
    API-->>WebUI: 返回搜索结果
    Note over API,WebUI: {documents: [...], total, search_type}
    
    WebUI->>WebUI: 格式化显示搜索结果
    WebUI-->>User: 展示相关文档和来源
```

## API 接口详细说明

### 核心 API 端点

| 端点 | 方法 | 描述 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| `/chat` | POST | 智能运维对话 | `{message, user_id, session_id?, temperature?, max_tokens?}` | `{success, response, session_id, processing_time, agent_messages, suggestions}` |
| `/search` | POST | 混合知识搜索 | `{query, search_type, source?, category?, limit?, threshold?}` | `{documents: [...], total, search_type, processing_time}` |
| `/health` | GET | 系统健康检查 | - | `{status, timestamp, version, components: {...}}` |
| `/stats` | GET | 系统统计信息 | - | `{vector_stats, graph_stats, database_stats, api_info}` |

### 会话管理 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/sessions/{user_id}` | GET | 获取用户会话列表 |
| `/sessions/{session_id}/messages` | GET | 获取会话消息历史 |  
| `/sessions/{session_id}` | DELETE | 删除/停用会话 |

### 知识管理 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/knowledge/entities` | GET | 获取知识实体列表 |
| `/knowledge/extract` | POST | 从文本提取知识 |
| `/search/suggestions` | GET | 获取搜索建议 |

## Web UI 前端实现细节

### 核心 JavaScript 函数

```javascript
// API 请求封装 - 处理CORS
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            mode: 'cors',
            credentials: 'omit',
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                ...options.headers
            }
        });
        return response;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// 聊天消息发送
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    addMessage(message, true);
    updateStatus('正在处理您的请求...', 'loading');

    try {
        const response = await apiRequest(`${API_BASE_URL}/chat`, {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                user_id: userId,
                temperature: 0.7
            })
        });

        const result = await response.json();
        
        if (response.ok) {
            addMessage(result.response);
            updateStatus(`处理完成 (${result.processing_time?.toFixed(2)}s)`, 'success');
        } else {
            addMessage(`错误: ${result.message}`, false);
            updateStatus('处理失败', 'error');
        }
    } catch (error) {
        addMessage(`连接错误: ${error.message}`, false);
        updateStatus('连接失败', 'error');
    }
}
```

### 状态管理

- **用户ID生成**: `userId = 'web_user_' + Date.now()`  
- **会话状态**: 自动创建和管理会话
- **错误处理**: 完善的错误捕获和用户提示
- **加载状态**: 请求期间的视觉反馈

## 多Agent 协作流程

```mermaid
graph LR
    subgraph "AIOps Graph 处理流程"
        Start([用户输入]) --> Planner[Planner Agent]
        Planner --> |分析查询| PlanResult{制定计划}
        PlanResult --> Knowledge[Knowledge Agent]
        Knowledge --> |搜索知识| KnowResult{获取信息}
        KnowResult --> Reasoning[Reasoning Agent]
        Reasoning --> |推理分析| ReasonResult{分析结果}
        ReasonResult --> Executor[Executor Agent]
        Executor --> |生成建议| Final[最终回复]
        Final --> End([返回用户])
    end
    
    subgraph "并行服务调用"
        Knowledge --> VectorSearch[向量搜索]
        Knowledge --> GraphSearch[图搜索]  
        Knowledge --> FullTextSearch[全文搜索]
    end
```

## 数据流转说明

### 1. 输入数据流
1. **用户输入** → Web UI JavaScript
2. **API请求** → FastAPI 路由处理
3. **业务逻辑** → AIOps Graph 多Agent协调
4. **数据访问** → 各Service层调用数据库

### 2. 输出数据流
1. **数据库结果** → Service层封装
2. **Agent处理** → 业务逻辑合成
3. **API响应** → JSON格式返回
4. **前端渲染** → 用户界面展示

## 错误处理机制

### API层错误处理
- HTTP状态码标准化
- 统一错误响应格式
- 异常捕获和日志记录

### 前端错误处理  
- 网络错误重试机制
- 用户友好错误提示
- 降级处理方案

### 服务层错误处理
- 数据库连接失败恢复
- 外部服务调用超时
- 数据验证和清理

## 性能优化策略

1. **缓存机制**: Redis缓存嵌入向量和搜索结果
2. **连接池**: 数据库连接池管理
3. **异步处理**: 全异步I/O操作
4. **并行搜索**: 混合搜索并行执行
5. **资源管理**: 服务生命周期管理

## 监控和日志

- **结构化日志**: 使用structlog记录关键操作
- **性能指标**: 处理时间、Token使用量统计
- **健康检查**: 定期服务状态检测
- **错误追踪**: 完整的错误堆栈信息

---

此文档详细描述了 AIOps Polaris 系统的完整交互流程，可作为开发和运维参考文档。