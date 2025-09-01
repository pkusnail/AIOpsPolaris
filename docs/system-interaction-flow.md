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
        RCAChatSvc[RCA Chat Service<br/>根因分析]
        ImprovedRAGSvc[Improved RAG Service<br/>混合搜索+重排序]
        TopologySvc[Topology Service<br/>服务拓扑查询]
        SearchSvc[Search Service<br/>混合搜索]
        DatabaseSvc[Database Service<br/>数据库操作]
        VectorSvc[Vector Service<br/>向量搜索]
        GraphSvc[Graph Service<br/>图数据库]
        EmbeddingSvc[Embedding Service<br/>文本嵌入]
        NERSvc[NER Extractor<br/>实体识别]
    end
    
    subgraph "数据存储层 Data Storage"
        MySQL[(MySQL<br/>会话/消息)]
        Neo4j[(Neo4j<br/>知识图谱)]
        Weaviate[(Weaviate<br/>向量数据库)]
        Redis[(Redis<br/>缓存)]
    end
    
    WebUI --> FastAPI
    CLI --> FastAPI
    FastAPI --> RCAChatSvc
    RCAChatSvc --> NERSvc
    RCAChatSvc --> ImprovedRAGSvc
    RCAChatSvc --> TopologySvc
    RCAChatSvc --> AIOpsGraph
    AIOpsGraph --> Planner
    AIOpsGraph --> Knowledge
    AIOpsGraph --> Reasoning
    AIOpsGraph --> Executor
    
    Planner --> SearchSvc
    Knowledge --> SearchSvc
    Reasoning --> SearchSvc
    Executor --> DatabaseSvc
    
    ImprovedRAGSvc --> VectorSvc
    ImprovedRAGSvc --> DatabaseSvc
    TopologySvc --> GraphSvc
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

### 1. RCA根因分析聊天流程 (新版)

```mermaid
sequenceDiagram
    participant User as DevOps用户
    participant WebUI as Web UI
    participant API as FastAPI Server
    participant RCASvc as RCA Chat Service
    participant NER as NER Extractor
    participant RAG as Improved RAG Service
    participant Topo as Topology Service
    participant Graph as AIOps Graph
    participant DB as Databases
    
    User->>WebUI: 输入故障症状或问题
    Note over User,WebUI: "service-b CPU使用率过高，响应超时"
    WebUI->>WebUI: 验证输入，显示加载状态
    
    WebUI->>API: POST /chat
    Note over WebUI,API: {message, user_id, temperature}
    
    API->>API: 创建/获取用户会话
    API->>RCASvc: process_rca_query()
    
    RCASvc->>NER: extract_entities(query)
    Note over NER: 识别服务名称(service-b, CPU等)
    NER-->>RCASvc: {services: ["service-b"], metrics: ["CPU"]}
    
    par 并行数据检索
        RCASvc->>RAG: hybrid_search(query)
        Note over RAG: 向量搜索+BM25+重排序
        par 混合搜索
            RAG->>DB: 向量相似搜索 (Weaviate)
            DB-->>RAG: 相似文档
        and
            RAG->>DB: BM25全文搜索 (Weaviate FullTextCollection)
            DB-->>RAG: 匹配文档
        end
        RAG->>RAG: 重排序合并结果 (α=0.6)
        RAG-->>RCASvc: 证据数据集合
    and
        RCASvc->>Topo: get_service_topology(["service-b"])
        Topo->>DB: 查询Neo4j服务依赖关系
        DB-->>Topo: 服务拓扑数据
        Topo-->>RCASvc: 过滤后的拓扑关系
    end
    
    RCASvc->>Graph: perform_rca_analysis()
    Note over RCASvc,Graph: 传入查询、证据、实体、拓扑
    
    Graph->>Graph: Multi-Agent推理流程
    Note over Graph: 基于真实证据进行分析
    Graph-->>RCASvc: RCA分析结果
    
    RCASvc->>RCASvc: 格式化结果+证据链
    Note over RCASvc: 包含日志文件、时间戳、拓扑关系
    RCASvc-->>API: 完整RCA响应
    
    API->>DB: 保存分析记录和日志
    DB-->>API: 确认保存
    
    API-->>WebUI: 返回RCA结果
    Note over API,WebUI: {response, evidence_files, topology, confidence}
    
    WebUI->>WebUI: 显示根因分析+证据链
    WebUI-->>User: 展示详细分析结果
```

### 2. 传统聊天交互流程 (兼容模式)

```mermaid
sequenceDiagram
    participant User as DevOps用户
    participant WebUI as Web UI
    participant API as FastAPI Server
    participant Graph as AIOps Graph
    participant Agents as Multi-Agents
    participant Services as Services
    participant DB as Databases
    
    User->>WebUI: 输入一般运维问题
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

### 3. 系统健康检查流程

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

### 4. 知识搜索流程 (混合搜索升级版)

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
    
    API->>ImprovedRAGSvc: hybrid_search()
    Note over API,ImprovedRAGSvc: 使用改进的混合搜索引擎
    
    par 并行混合搜索
        ImprovedRAGSvc->>VectorSvc: 向量相似搜索
        VectorSvc->>DB: 查询 Weaviate (384维向量)
        DB-->>VectorSvc: 返回相似向量
        VectorSvc-->>ImprovedRAGSvc: 向量搜索结果
    and
        ImprovedRAGSvc->>DB: BM25全文搜索 (Weaviate FullTextCollection)
        DB-->>ImprovedRAGSvc: 返回文档匹配
    and
        ImprovedRAGSvc->>GraphSvc: 图数据库搜索
        GraphSvc->>DB: 查询 Neo4j
        DB-->>GraphSvc: 返回图节点/关系
        GraphSvc-->>ImprovedRAGSvc: 图搜索结果
    end
    
    ImprovedRAGSvc->>ImprovedRAGSvc: 重排序算法 (α=0.6向量+0.4BM25)
    ImprovedRAGSvc->>ImprovedRAGSvc: 过滤无效数据 (None/unknown)
    ImprovedRAGSvc-->>API: 返回重排序后的混合搜索结果
    
    API-->>WebUI: 返回搜索结果
    Note over API,WebUI: {documents: [...], total, search_type}
    
    WebUI->>WebUI: 格式化显示搜索结果
    WebUI-->>User: 展示相关文档和来源
```

## API 接口详细说明

### 核心 API 端点

| 端点 | 方法 | 描述 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| `/chat` | POST | RCA根因分析对话 | `{message, user_id, session_id?, temperature?, max_tokens?}` | `{success, response, session_id, processing_time, evidence_files, topology_data, confidence_score}` |
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

## RCA多阶段分析流程

```mermaid
graph TB
    subgraph "RCA分析流程 (新版)"
        Start([故障症状输入]) --> NER[NER实体识别]
        NER --> |提取服务名/指标| Parallel{并行检索}
        
        Parallel --> HybridSearch[混合搜索]
        Parallel --> TopoQuery[拓扑查询]
        
        HybridSearch --> |向量+BM25+重排序| Evidence[证据收集]
        TopoQuery --> |Neo4j服务依赖| Topology[拓扑关系]
        
        Evidence --> Analysis[Agent推理分析]
        Topology --> Analysis
        
        Analysis --> Filter[结果过滤]
        Filter --> |去除None/unknown| Response[格式化响应]
        Response --> End([返回根因分析])
    end
    
    subgraph "证据来源 Evidence Sources"
        HybridSearch --> Vector[向量搜索<br/>Weaviate 384d]
        HybridSearch --> BM25[全文搜索<br/>Weaviate BM25]
        TopoQuery --> Neo4j[图数据库<br/>Neo4j Topology]
    end
    
    subgraph "输出组件 Output Components"
        Response --> EvidenceChain[证据链<br/>日志文件+时间戳]
        Response --> TopologyViz[拓扑可视化<br/>服务依赖关系]
        Response --> ConfidenceScore[置信度评分<br/>0.0-1.0]
    end
```

## 传统Multi-Agent协作流程 (兼容模式)

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

### 1. RCA输入数据流 (新版)
1. **故障症状输入** → Web UI JavaScript
2. **API请求** → FastAPI `/chat` 路由
3. **实体识别** → NER Extractor 提取服务名和指标
4. **并行检索** → Improved RAG Service + Topology Service
5. **证据整合** → RCA Chat Service 汇总分析
6. **AI推理** → AIOps Graph 多Agent协调
7. **数据访问** → Weaviate + Neo4j + MySQL 并行查询

### 2. RCA输出数据流 (新版)
1. **多源数据** → 向量搜索 + BM25搜索 + 拓扑查询
2. **重排序融合** → 混合搜索结果权重合并 (α=0.6)
3. **数据过滤** → 去除None/unknown/低质量数据
4. **Agent分析** → 基于真实证据的推理分析
5. **结果封装** → 包含证据链、拓扑关系、置信度
6. **API响应** → 结构化JSON返回
7. **前端渲染** → 详细分析结果 + 证据展示

### 3. 传统数据流 (兼容模式)
1. **用户输入** → Web UI JavaScript
2. **API请求** → FastAPI 路由处理
3. **业务逻辑** → AIOps Graph 多Agent协调
4. **数据访问** → 各Service层调用数据库
5. **数据库结果** → Service层封装
6. **Agent处理** → 业务逻辑合成
7. **API响应** → JSON格式返回
8. **前端渲染** → 用户界面展示

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
2. **连接池**: 数据库连接池管理 (MySQL + Neo4j + Weaviate)
3. **异步处理**: 全异步I/O操作 (asyncio.gather并行调用)
4. **并行搜索**: 混合搜索并行执行 (向量+BM25+拓扑同时查询)
5. **资源管理**: 服务生命周期管理
6. **数据过滤**: 早期过滤无效数据 (None/unknown值)
7. **向量优化**: 统一使用384维sentence-transformers模型
8. **重排序算法**: 加权融合多源搜索结果 (α=0.6 vector + 0.4 BM25)
9. **日志优化**: 分级日志记录 (./logs/rca_analysis.log + rca_detailed.log)

## 监控和日志

### RCA专用日志系统
- **RCA分析日志**: ./logs/rca_analysis.log (分析过程和结果)
- **RCA详细日志**: ./logs/rca_detailed.log (详细调试信息)
- **证据链追踪**: 记录所有证据来源文件和时间戳
- **置信度记录**: 每个分析步骤的置信度评分

### 系统监控
- **结构化日志**: 使用structlog记录关键操作
- **性能指标**: 处理时间、Token使用量、搜索命中率统计
- **健康检查**: 定期服务状态检测 (Weaviate + Neo4j + MySQL)
- **错误追踪**: 完整的错误堆栈信息
- **数据质量监控**: 检测和过滤None/unknown数据
- **向量一致性**: 监控向量维度和模型版本一致性

---

此文档详细描述了 AIOps Polaris 系统的完整交互流程，可作为开发和运维参考文档。