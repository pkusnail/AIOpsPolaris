# AIOps Polaris 变更日志

## 最新版本 - 2025-08-31

### 🎯 主要特性更新

#### 1. Multi-Agent智能分析系统
- **新增完整的多智能体协作框架**
  - Planner Agent: 分析问题并制定执行计划
  - Knowledge Agent: 实体识别、证据收集、拓扑分析
  - Reasoning Agent: 多维度根因推理
  - Executor Agent: 生成具体解决方案
  - Monitor Agent: 监控执行过程和结果验证

#### 2. 增强的流式RCA服务
- **新增文件**:
  - `src/api/enhanced_streaming_rca_service.py` - 完整多智能体流式服务
  - `src/api/streaming_rca_service.py` - 基础流式服务
  - `src/utils/multi_agent_task_manager.py` - 多智能体任务状态管理
  - `src/utils/task_manager.py` - 基础任务管理

#### 3. 实时状态追踪与交互控制
- **支持实时进度监控**: 长轮询机制，500ms更新间隔
- **用户中断控制**: 支持任务执行过程中的用户中断
- **详细状态展示**: 显示每个Agent的执行状态和进度

#### 4. 增强的证据展示系统
- **RAG搜索证据详细显示**:
  - 📄 真实日志文件名（如 incident_001_service_b_cpu_overload.log）
  - 📚 Wiki知识库文档
  - 🎫 JIRA工单记录
  - 💻 GitLab项目代码
- **Neo4j拓扑关系可视化**:
  - 服务依赖关系图
  - 跨数据中心连接信息
  - 超时和权重配置详情
- **完整数据源追踪**: 显示证据来源、服务名称、时间戳和内容预览

### 🛠️ 架构改进

#### API接口扩展
- `POST /chat/multi_agent` - 启动多智能体RCA分析
- `GET /chat/multi_agent_status/{task_id}` - 获取详细执行状态
- `POST /chat/interrupt/{task_id}` - 中断任务执行

#### 数据处理优化
- **智能数据源识别**: 根据source_type自动分类显示
- **混合搜索结果整合**: 向量搜索 + BM25全文搜索
- **实时状态同步**: 任务状态、Agent进度、中间结论

### 🐛 问题修复

#### 1. Unknown File显示问题
- **问题**: RAG搜索证据显示为 "unknown_file"
- **根因**: 前端UI期望旧格式的metadata结构
- **修复**: 更新UI逻辑，正确解析新的数据结构
- **结果**: 现在正确显示具体的日志文件名和数据源类型

#### 2. 数据源类型混淆
- **问题**: Wiki/JIRA/GitLab数据被错误显示为日志文件
- **修复**: 实现智能数据源识别和分类显示
- **结果**: 不同数据源有对应的图标和友好名称

#### 3. 索引状态检查
- **验证**: Weaviate索引健康状态正常
- **性能**: 搜索响应时间 <20ms，符合预期
- **结论**: 无需重建索引

### 📈 性能提升

#### 搜索性能优化
- **向量搜索**: 384维embedding，cosine相似度
- **BM25搜索**: 标准配置（k1=1.2, b=0.75）
- **混合搜索**: 加权重排序算法（α=0.6）

#### UI响应优化
- **长轮询机制**: 减少服务器负载
- **渐进式显示**: 实时更新Agent状态
- **智能缓存**: embedding结果本地缓存

### 📚 文档更新
- 新增多智能体架构设计文档
- 更新RAG搜索流程说明
- 添加API接口详细说明
- 创建系统交互流程图

### 🔧 技术栈
- **后端**: Python 3.9+, FastAPI, AsyncIO
- **AI/ML**: SentenceTransformers, OpenAI API
- **数据库**: Weaviate (向量数据库), Neo4j (知识图谱)
- **前端**: HTML5, JavaScript ES6+, 长轮询
- **架构**: 多智能体协作, 混合搜索, 流式处理

---

## 配置要求

### 环境依赖
```bash
python >= 3.9
weaviate >= 1.23.7
neo4j >= 4.x
sentence-transformers
openai
fastapi
uvicorn
```

### 性能建议
- **内存**: 至少 8GB RAM（用于向量索引）
- **存储**: SSD推荐（提升搜索性能）
- **网络**: 稳定的OpenAI API连接

---

## 下一步计划
- [ ] 添加更多Agent类型（如专门的日志分析Agent）
- [ ] 支持WebSocket实时通信
- [ ] 集成更多数据源（Prometheus、Elasticsearch）
- [ ] 添加Agent协作的可视化界面
- [ ] 实现分布式多智能体部署