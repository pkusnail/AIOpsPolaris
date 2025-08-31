# AIOps Polaris - 智能运维平台

![AIOps Polaris](https://img.shields.io/badge/AIOps-Polaris-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-green?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge)

AIOps Polaris 是一个基于知识图谱和语义搜索的智能运维平台，整合了多种数据存储和处理技术来提供全面的运维支持。

## ✨ 特性

- 🤖 **智能对话**: 基于大语言模型的智能运维助手
- 🕸️ **知识图谱**: Neo4j驱动的复杂关系建模
- 🔍 **语义搜索**: Weaviate向量数据库支持的语义检索
- 📊 **监控告警**: Prometheus + Grafana 完整监控方案
- 🏗️ **微服务架构**: Docker Compose 一键部署
- 📈 **可观测性**: 完整的监控指标和健康检查

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         AIOps Polaris                          │
├─────────────────────────────────────────────────────────────────┤
│  Frontend API                                                   │
│  ├── REST API (FastAPI)                                        │
│  ├── WebSocket (实时通信)                                        │
│  └── 会话管理 (多用户支持)                                        │
├─────────────────────────────────────────────────────────────────┤
│  Agent Layer (LangGraph)                                       │
│  ├── Planner Agent (任务规划)                                   │
│  ├── Executor Agent (任务执行)                                  │
│  ├── Knowledge Agent (知识查询)                                  │
│  └── Reasoning Agent (推理分析)                                  │
├─────────────────────────────────────────────────────────────────┤
│  Knowledge & Search Layer                                      │
│  ├── Vector DB (Weaviate) - 向量检索                            │
│  ├── Knowledge Graph (Neo4j) - 实体关系                         │
│  ├── Hybrid Search (向量+关键词)                                │
│  └── RAG Engine (检索增强生成)                                   │
├─────────────────────────────────────────────────────────────────┤
│  Data Processing Layer                                         │
│  ├── NER (命名实体识别)                                          │
│  ├── Relation Extraction (关系抽取)                             │
│  ├── Embedding Generation (向量化)                              │
│  └── Knowledge Graph Construction                              │
├─────────────────────────────────────────────────────────────────┤
│  Data Sources                                                  │
│  ├── Wiki文档 (运维知识库)                                       │
│  ├── GitLab (代码变更)                                          │
│  ├── Jira (事件工单)                                            │
│  └── Logs (系统日志)                                            │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure                                               │
│  ├── LLM Backend (vLLM + 开源模型)                              │
│  ├── MySQL (会话存储)                                           │
│  └── Docker Compose (容器编排)                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 🎯 系统交互流程

详细的系统架构图、时序图和交互流程请参考：[系统交互流程文档](docs/system-interaction-flow.md)

主要交互流程包括：
- **用户聊天交互**: Web UI → FastAPI → AIOps Graph → Multi-Agents → Services → Databases  
- **知识搜索流程**: 并行混合搜索（向量+图+全文）
- **健康检查机制**: 定期服务状态监测
- **错误处理链路**: 完善的异常捕获和恢复

## 核心功能

### 1. 🧠 智能RCA根因分析
- **多阶段推理**: NER实体识别 → 混合搜索 → 拓扑查询 → 智能推理 → 结果输出
- **服务拓扑分析**: 自动查询Neo4j获取服务依赖关系 (DEPENDS_ON/CALLS/ROUTES_TO)
- **证据驱动推理**: 基于真实日志数据进行根因分析，无占位符或模拟数据
- **详细结果展示**: 显示关键证据详情、服务拓扑关系、推理过程、解决方案
- **完整日志记录**: 全程记录分析过程到 `./logs/` 目录，便于审查和调试
- **个性化解决方案**: 根据故障类型和服务特征提供定制化修复建议

### 2. **🔬 AIOps根因分析实验环境**
- **完整的微服务故障模拟**: 5种服务类型，2个数据中心的真实架构
- **10个精心设计的故障场景**: 涵盖CPU过载、磁盘IO、内存泄漏、网络分区等
- **AI训练数据集**: 结构化的incident数据 + 时序日志 + RCA分析模式
- **LLM训练Pipeline**: 专门为根因分析设计的Prompt模板和训练方法
- 📚 **详细文档**: [实验环境设置 - 实验一](docs/experiment_setup_1.md)

### 3. 知识图谱构建
- 自动从多源数据抽取实体和关系
- 构建运维领域专业知识图谱
- 支持图查询和推理分析

### 4. 🌐 知识图谱拓扑分析
- **服务依赖关系**: 自动查询和可视化服务间的DEPENDS_ON/CALLS/ROUTES_TO关系
- **多服务联合查询**: 支持跨服务的依赖关系分析和故障传播路径追踪  
- **拓扑数据验证**: 过滤Neo4j查询中的空值关系，确保拓扑数据准确性
- **上下游影响分析**: 分析故障服务对上下游服务的潜在影响

### 5. 🔍 高级RAG分析系统
- **混合搜索引擎**: 向量搜索 + BM25全文搜索 + 智能重排序 (α=0.6向量, 0.4 BM25)
- **双Collection架构**: EmbeddingCollection(向量搜索) + FullTextCollection(全文搜索)
- **多源数据集成**: 日志文件、Wiki文档、GitLab项目、Jira工单统一索引
- **实体识别(NER)**: 中英文服务名、组件、故障类型自动识别
- **数据质量过滤**: 自动过滤unknown/None数据，确保分析结果真实性
- **完整证据追踪**: 显示证据来源（日志文件、行号、时间戳、置信度）
- 📚 **详细文档**: [最新更新记录](docs/RECENT_UPDATES.md)

### 6. 智能对话系统
- 基于LangGraph的多轮对话
- 支持多用户并发会话
- 上下文感知和记忆能力
- 任务规划和执行

### 7. 实时数据处理
- 日志流式处理和分析
- 异常模式识别
- 自动告警和通知
- 趋势分析和预测

## 技术栈

### 核心框架
- **Agent框架**: LangGraph
- **Web框架**: FastAPI
- **LLM服务**: vLLM + 开源模型 (Qwen, ChatGLM等)

### 数据存储
- **关系数据库**: MySQL (会话管理)
- **向量数据库**: Weaviate (语义搜索)
- **图数据库**: Neo4j (知识图谱)

### AI/ML组件
- **NLP**: spaCy/transformers (NER)
- **Embeddings**: sentence-transformers
- **检索**: RAG + 混合搜索

### 基础设施
- **容器化**: Docker & Docker Compose
- **监控**: Prometheus + Grafana
- **日志**: ELK Stack

## 快速开始

### 前置要求
- Docker & Docker Compose (推荐最新版本)
- Python 3.11+
- 至少16GB内存 (GPU模型推理需要更多内存)
- 至少20GB可用磁盘空间
- **GPU环境 (用于vLLM模型推理)**:
  - NVIDIA GPU (推荐RTX 3090或更高)
  - CUDA 12.2+ 驱动
  - NVIDIA Container Toolkit
  - 至少12GB GPU显存 (用于Qwen2.5-7B模型)

### 一键启动

**重要：在启动前，请先配置.env文件！**

```bash
# 1. 首先配置API密钥（重要！）
echo "OPENAI_API_KEY=sk-your-openai-api-key-here" > .env

# 2. 然后启动系统
./scripts/start_services.sh
```

我们提供了完全自动化的启动脚本，只需两个命令即可启动整个系统。

这个脚本会自动：
1. ✅ 检查所有依赖工具（Docker、Python等）
2. ✅ 检查端口占用情况
3. ✅ 启动所有基础服务（MySQL、Neo4j、Weaviate、Redis）
4. ✅ 等待服务就绪并进行健康检查
5. ✅ 创建Python虚拟环境并安装依赖
6. ✅ 自动初始化数据库结构
7. ✅ 加载样本数据并构建知识图谱
8. ✅ 启动API服务和Gradio界面
9. ✅ 显示所有访问地址和连接信息

### RAG Pipeline配置和测试

完成基础启动后，需要建立RAG数据索引：

#### 🔧 建立RAG数据索引
```bash
# 激活虚拟环境
source venv/bin/activate

# 运行pipeline建立索引（一键完成所有indexing）
python run_pipelines.py

# 或者分别运行各个pipeline
python -m src.services.log_pipeline
python -m src.services.knowledge_pipeline
python -m src.services.knowledge_graph_pipeline
```

#### 🧪 RAG功能测试
```bash
# 基础功能测试
python test_rag_simple.py          # 测试RAG基础连接和功能
python test_agent_simple.py        # 测试Agent-RAG集成

# 完整集成测试
python test_complete_rca.py        # 端到端RCA流程测试
python test_api_rca.py             # API接口RCA功能测试
```

#### 📊 预期测试结果
- **RAG数据状态**: 234条向量索引 + 27个知识图谱节点
- **搜索功能**: 支持语义搜索、全文搜索、混合搜索
- **Agent能力**: 症状识别、根因推理、解决方案生成
- **RCA场景**: 支持CPU过载、数据库连接、磁盘IO等故障分析

### 系统访问和使用方法

启动成功后，您可以通过以下方式与系统交互：

#### 🖥️ Web界面 (推荐)
```bash
# 在浏览器中打开
open web_ui.html
# 或直接访问文件路径
file:///{ your local path to project }/AIOpsPolaris/web_ui.html
```

#### 💻 命令行工具
```bash
# 启动命令行聊天界面
python chat_cli.py
```

#### 🌐 系统访问地址

| 服务 | 地址 | 用途 | 状态 |
|------|------|------|------|
| 🤖 **HTML聊天界面** | file://web_ui.html | 主要聊天界面 | ✅ 可用 |
| 💻 **CLI聊天工具** | python chat_cli.py | 命令行交互 | ✅ 可用 |
| 📚 **API文档** | http://localhost:8888/docs | REST API文档 | ✅ 可用 |
| ❤️ **健康检查** | http://localhost:8888/health | 系统状态 | ✅ 可用 |
| 🕸️ **Neo4j浏览器** | http://localhost:7474 | 知识图谱可视化 | ✅ 可用 |

#### 📚 详细文档

| 文档 | 描述 | 链接 |
|------|------|------|
| 🏗️ **系统设计文档** | 架构设计、数据库设计、Agent设计 | [system-design.md](docs/system-design.md) |
| 🎯 **系统交互流程** | 架构图、时序图、API交互流程 | [system-interaction-flow.md](docs/system-interaction-flow.md) |
| 🔬 **实验环境设置** | AIOps根因分析实验环境完整文档 | [experiment_setup_1.md](docs/experiment_setup_1.md) |
| 🖥️ **Web UI使用指南** | Web界面详细使用说明 | [web-ui-guide.md](docs/web-ui-guide.md) |
| 📖 **API参考文档** | 完整的API接口文档 | [api-reference.md](docs/api-reference.md) |
| 🔍 **RAG Pipeline架构** | RAG系统完整架构和实现详解 | [rag_pipeline_architecture.md](docs/rag_pipeline_architecture.md) |
| 🤖 **Agent RAG集成验证** | Agent与RAG集成的验证方法和测试结果 | [agent_rag_validation.md](docs/agent_rag_validation.md) |

#### 🧪 快速测试示例

**1. 使用命令行工具聊天:**
```bash
python chat_cli.py
# 然后输入: 服务器CPU使用率过高怎么办？
```

**2. 使用Web界面:**
- 在浏览器中打开 `web_ui.html`
- 输入问题: "数据库连接超时如何排查？"
- 点击发送

**3. 直接API调用:**
```bash
curl -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "微服务监控最佳实践", "user_id": "test_user"}'
```

### 数据库连接信息

| 数据库 | 连接地址 | 用户名/密码 |
|--------|----------|------------|
| MySQL | localhost:3306 | aiops / aiops_pass |
| Neo4j | localhost:7687 | neo4j / aiops123 |
| Weaviate | http://localhost:8080 | - |
| Redis | localhost:6379 | - |

### 手动安装（高级用户）

如果您需要自定义安装过程，可以按以下步骤手动安装：

1. **克隆项目**
```bash
git clone <repository-url>
cd AIOpsPolaris
```

2. **配置环境变量（重要）**

创建 `.env` 文件配置LLM API密钥：

```bash
# 创建.env文件
echo "OPENAI_API_KEY=sk-your-openai-api-key-here" > .env
echo "ANTHROPIC_API_KEY=sk-ant-your-claude-api-key-here" >> .env
```

或者手动创建 `.env` 文件：
```env
# OpenAI API密钥 (必需，用于智能对话功能)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Claude API密钥 (可选)
ANTHROPIC_API_KEY=sk-ant-your-claude-api-key-here
```

**注意**: 
- 如果没有配置API密钥，系统会自动使用演示模式
- 演示模式提供基本功能，但无法使用完整的AI对话能力

3. **启动基础服务**
```bash
docker-compose up -d mysql neo4j weaviate redis
```

3. **创建虚拟环境**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或者
venv\Scripts\activate     # Windows
```

4. **安装Python依赖**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

5. **初始化数据库**
```bash
python scripts/init_database.py
```

6. **启动API服务**
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8888 --reload
```

7. **启动Gradio界面**
```bash
python gradio_app.py
```

### 停止服务

使用以下命令停止所有服务：

```bash
./scripts/stop_services.sh
```

该脚本会：
- 优雅地停止所有Python服务
- 停止所有Docker容器
- 清理PID文件
- 可选择性清理日志文件

### 快速测试验证

#### 1. 系统健康检查
```bash
curl http://localhost:8888/health
```
预期响应包含所有组件的健康状态。

#### 2. Gradio界面测试
访问 http://localhost:7860，尝试以下测试：

- **聊天测试**: 输入 "Kubernetes pod一直重启，如何排查？"
- **搜索测试**: 在知识搜索标签页搜索 "database performance"  
- **知识提取**: 在知识提取标签页输入 "API服务返回503错误，Redis连接超时"

#### 3. API接口测试

**智能故障诊断**:
```bash
curl -X POST "http://localhost:8888/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "生产环境CPU使用率突然飙升到90%，用户反馈页面加载很慢",
    "user_id": "test_user",
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

**知识搜索**:
```bash
curl -X POST "http://localhost:8888/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "数据库连接池配置优化",
    "search_type": "hybrid",
    "limit": 10
  }'
```

**知识提取**:
```bash
curl -X POST "http://localhost:8888/knowledge/extract?source=test" \
  -H "Content-Type: application/json" \
  -d '"Kubernetes deployment failed due to insufficient memory resources"'
```

#### 4. 完整POC测试流程

详细的测试流程请参考：[POC测试文档](docs/poc_testing.md)

### 使用场景演示

#### 场景1: 服务故障排查
1. **用户问题**: "我们的微服务响应时间很慢，怎么排查？"
2. **系统响应**: 
   - Planner分析问题类型
   - Knowledge Agent搜索相关排查文档
   - Reasoning Agent分析可能原因
   - Executor Agent提供具体操作步骤

#### 场景2: 知识库查询
1. **搜索查询**: "Redis性能优化"
2. **系统响应**:
   - 向量搜索匹配语义相似内容
   - 关键词搜索精确匹配
   - 图谱查询关联实体和关系
   - 综合排序返回最相关结果

## 数据源配置

### 1. 🔬 实验数据 (`data/`)

#### RCA训练数据 (`data/rca/`)
用于AIOps根因分析训练的结构化incident数据：
```json
{
  "incident_id": "INC-2025-001",
  "title": "Service B CPU Overload Causing Chain Latency",
  "root_cause": {"primary": "CPU overload due to inefficient algorithm"},
  "analysis_steps": ["症状识别", "影响范围", "根因定位"],
  "impact_metrics": {"requests_affected": 45000}
}
```

#### 故障日志 (`data/logs/`)
时序故障日志，包含故障前后1小时的完整日志：
```
2025-08-20T14:31:45.456Z [ERROR] service-b: CPU usage: 95%, GC time: 25%
2025-08-20T14:35:07.234Z [CRITICAL] service-b: OutOfMemoryError in processing pool
```

#### 架构知识库 (`data/wiki/`)
包含系统架构文档和Neo4j知识图谱：
```cypher
CREATE (a:Service {name: 'service-a', type: 'api-gateway'})
CREATE (b:Service {name: 'service-b', type: 'business-logic'})
CREATE (a)-[:CALLS {timeout_ms: 5000}]->(b)
```

### 2. Wiki文档 (`data/wiki/`)
存储运维知识文档，支持Markdown和JSON格式
```json
{
  "id": "wiki_001",
  "title": "故障排查指南",
  "content": "...",
  "category": "运维文档",
  "tags": ["troubleshooting", "guide"]
}
```

### 3. GitLab数据 (`data/gitlab/`)
包含代码变更信息，用于关联代码变更与故障
```json
{
  "id": "mr_001",
  "title": "修复内存泄露问题",
  "files_changed": ["src/auth/token_manager.py"],
  "labels": ["bug", "performance"]
}
```

### 4. Jira工单 (`data/jira/`)
事件和故障工单信息
```json
{
  "id": "AIOPS-001",
  "title": "CPU使用率异常",
  "type": "故障",
  "priority": "高",
  "components": ["web-server"]
}
```

## API文档

完整的API文档请访问：http://localhost:8888/docs

### 📋 核心API端点

| 端点 | 方法 | 描述 | 状态 |
|------|------|------|------|
| `/chat` | POST | 🤖 智能运维对话 | ✅ |
| `/search` | POST | 🔍 混合知识搜索 | ✅ |
| `/health` | GET | ❤️ 系统健康检查 | ✅ |
| `/stats` | GET | 📊 系统统计信息 | ✅ |

### 📞 会话管理 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/sessions/{user_id}` | GET | 获取用户会话列表 |
| `/sessions/{session_id}/messages` | GET | 获取会话消息历史 |
| `/sessions/{session_id}` | DELETE | 删除/停用会话 |

### 🧠 知识管理 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/knowledge/entities` | GET | 获取知识实体列表 |
| `/knowledge/extract` | POST | 从文本提取知识 |
| `/search/suggestions` | GET | 获取搜索建议 |

### 🎯 系统监控 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/agent/status` | GET | 获取Agent状态 |

### 💡 API调用示例

**聊天对话**:
```bash
curl -X POST "http://localhost:8888/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "生产环境CPU使用率突然飙升，怎么排查？",
    "user_id": "devops_user",
    "temperature": 0.7
  }'
```

**知识搜索**:
```bash
curl -X POST "http://localhost:8888/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "数据库连接池优化",
    "search_type": "hybrid",
    "limit": 10
  }'
```

**系统状态**:
```bash
curl -X GET "http://localhost:8888/health"
```

## 开发指南

### 项目结构
```
AIOpsPolaris/
├── src/
│   ├── agents/          # LangGraph智能体
│   ├── api/            # FastAPI接口
│   ├── models/         # 数据模型
│   ├── services/       # 业务逻辑
│   └── utils/          # 工具函数
├── data/               # 样本数据
├── tests/              # 测试用例
├── config/             # 配置文件
├── docker/             # Docker相关
└── scripts/            # 脚本工具
```

### 添加新的Agent

1. 在`src/agents/`下创建新的Agent类
2. 继承BaseAgent并实现必要方法
3. 在graph配置中注册新的Agent
4. 添加相应的测试用例

### 扩展数据源

1. 在`src/services/`下添加新的数据源服务
2. 实现数据抽取和标准化逻辑
3. 更新知识图谱构建流程
4. 配置定时同步任务

## 监控和运维

### 健康检查
```bash
curl http://localhost:8000/health
```

### 性能监控
- Grafana Dashboard: http://localhost:3000
- Prometheus Metrics: http://localhost:9090

### 日志查看
```bash
docker-compose logs -f api-service
```

## 故障排查

### 常见问题

1. **LLM服务启动失败**
   - 检查GPU内存是否足够
   - 确认模型文件是否正确下载

2. **向量数据库连接失败**
   - 检查Weaviate服务状态
   - 确认网络配置是否正确

3. **知识图谱查询超时**
   - 检查Neo4j服务状态
   - 优化图查询语句

## 贡献指南

1. Fork项目仓库
2. 创建功能分支
3. 提交代码变更
4. 创建Pull Request
5. 代码审查和合并


---

**注意**: 这是一个演示项目，生产环境使用前请进行充分的安全性评估和性能测试。
