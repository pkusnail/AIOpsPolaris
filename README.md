# AIOps Polaris - 智能运维系统

## 项目概述

AIOps Polaris 是一个基于AI的智能运维系统，集成了RAG（检索增强生成）、混合搜索、知识图谱、向量数据库等先进技术，为运维团队提供智能化的故障诊断、根因分析和解决方案推荐。

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

### 1. 智能故障诊断
- 基于症状描述自动识别可能的故障原因
- 结合历史数据和知识图谱进行根因分析
- 提供个性化的解决方案推荐

### 2. 知识图谱构建
- 自动从多源数据抽取实体和关系
- 构建运维领域专业知识图谱
- 支持图查询和推理分析

### 3. 混合搜索引擎
- 向量相似性搜索（语义理解）
- 关键词精确匹配
- 图结构关系查询
- 多维度融合排序

### 4. 智能对话系统
- 基于LangGraph的多轮对话
- 支持多用户并发会话
- 上下文感知和记忆能力
- 任务规划和执行

### 5. 实时数据处理
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
- Python 3.8+
- 至少8GB内存
- 至少10GB可用磁盘空间
- NVIDIA GPU (可选，用于LLM加速)

### 一键启动

我们提供了完全自动化的启动脚本，只需一个命令即可启动整个系统：

```bash
./scripts/start_services.sh
```

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

### 系统访问和使用方法

启动成功后，您可以通过以下方式与系统交互：

#### 🖥️ Web界面 (推荐)
```bash
# 在浏览器中打开
open web_ui.html
# 或直接访问文件路径
file:///home/alejandroseaah/AIOpsPolaris/web_ui.html
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
| 🎯 **系统交互流程** | 架构图、时序图、API交互流程 | [system-interaction-flow.md](docs/system-interaction-flow.md) |
| 🖥️ **Web UI使用指南** | Web界面详细使用说明 | [web-ui-guide.md](docs/web-ui-guide.md) |
| 📖 **API参考文档** | 完整的API接口文档 | [api-reference.md](docs/api-reference.md) |

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

2. **启动基础服务**
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

### 1. Wiki文档 (`data/wiki/`)
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

### 2. GitLab数据 (`data/gitlab/`)
包含代码变更信息，用于关联代码变更与故障
```json
{
  "id": "mr_001",
  "title": "修复内存泄露问题",
  "files_changed": ["src/auth/token_manager.py"],
  "labels": ["bug", "performance"]
}
```

### 3. Jira工单 (`data/jira/`)
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

### 4. 系统日志 (`data/logs/`)
结构化的系统日志数据
```
2024-08-22 08:30:15 [ERROR] web-server-01: CPU usage 85%
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

## 许可证

MIT License

---

**注意**: 这是一个演示项目，生产环境使用前请进行充分的安全性评估和性能测试。
