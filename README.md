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
- Docker & Docker Compose
- Python 3.9+
- NVIDIA GPU (可选，用于LLM加速)

### 安装部署

1. **克隆项目**
```bash
git clone <repository-url>
cd AIOpsPolaris
```

2. **启动基础服务**
```bash
docker-compose up -d mysql neo4j weaviate redis
```

3. **安装Python依赖**
```bash
pip install -r requirements.txt
```

4. **初始化数据库**
```bash
python scripts/init_database.py
```

5. **导入样本数据**
```bash
python scripts/load_sample_data.py
```

6. **启动应用**
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 使用示例

#### 智能故障诊断
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "生产环境CPU使用率突然飙升到90%，用户反馈页面加载很慢",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

#### 知识图谱查询
```bash
curl -X GET "http://localhost:8000/knowledge/entities/kubernetes"
```

#### 混合搜索
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "数据库连接池配置优化",
    "search_type": "hybrid",
    "limit": 10
  }'
```

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

### 会话管理
- `POST /chat` - 发送消息到智能助手
- `GET /sessions/{user_id}` - 获取用户会话列表
- `DELETE /sessions/{session_id}` - 删除会话

### 知识图谱
- `GET /knowledge/entities` - 获取实体列表
- `GET /knowledge/relations` - 获取关系列表
- `POST /knowledge/query` - 图查询

### 搜索服务
- `POST /search` - 混合搜索
- `POST /search/vector` - 向量搜索
- `POST /search/graph` - 图搜索

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
