# AIOps Polaris 部署状态文档

## 系统当前状态 ✅ 

**最后更新**: 2025-08-30

### 🚀 部署完成情况

| 组件 | 状态 | 端口 | 访问地址 | 说明 |
|------|------|------|----------|------|
| **MySQL数据库** | ✅ 运行中 | 3306 | localhost:3306 | aiops/aiops_pass |
| **Neo4j图数据库** | ✅ 运行中 | 7474/7687 | http://localhost:7474 | neo4j/aiops123 |
| **Weaviate向量库** | ✅ 运行中 | 8080 | http://localhost:8080 | 无密码 |
| **Redis缓存** | ✅ 运行中 | 6379 | localhost:6379 | 密码: aiops123 |
| **Prometheus监控** | ✅ 运行中 | 9090 | http://localhost:9090 | 无密码 |
| **Grafana仪表盘** | ✅ 运行中 | 3000 | http://localhost:3000 | admin/aiops123 |
| **API服务** | ✅ 运行中 | 8888 | http://localhost:8888 | REST API |
| **vLLM服务** | ⚠️ 可选 | 8000 | http://localhost:8000 | 本地LLM |

### 🤖 AI 功能状态

| 功能 | 状态 | 配置 | 说明 |
|------|------|------|------|
| **OpenAI集成** | ✅ 正常 | 通过.env配置 | 主要LLM提供商 |
| **Claude集成** | ⚠️ 可选 | 需要API密钥 | 备选LLM提供商 |
| **本地vLLM** | ⚠️ 可选 | Docker容器 | 离线LLM方案 |
| **智能对话** | ✅ 正常 | OpenAI API | 支持技术问答 |
| **错误处理** | ✅ 正常 | 直接报错 | 无回退模式 |

### 📊 监控与指标

| 监控项 | 状态 | 配置位置 | 说明 |
|--------|------|----------|------|
| **Prometheus指标收集** | ✅ 正常 | /metrics端点 | text/plain格式 |
| **Grafana可视化** | ✅ 正常 | 预配置仪表盘 | 自动数据源 |
| **健康检查** | ✅ 正常 | /health端点 | 所有组件状态 |
| **系统统计** | ✅ 正常 | /stats端点 | CPU/内存/磁盘 |

### 🔧 配置管理

#### 环境变量配置 (.env)
```env
OPENAI_API_KEY=sk-proj-...  # OpenAI API密钥
ANTHROPIC_API_KEY=sk-ant-...  # Claude API密钥 (可选)
```

#### LLM配置 (config/llm_config.yaml)
```yaml
llm_config:
  provider: "openai"  # 当前使用OpenAI
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-3.5-turbo"
    max_tokens: 4096
    temperature: 0.7
```

### 🏗️ Docker容器资源限制

所有容器都限制为1个CPU核心：

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
```

### 🔗 API端点总览

| 分类 | 端点 | 方法 | 说明 |
|------|------|------|------|
| **基础** | `/` | GET | API信息 |
| **健康检查** | `/health` | GET | 系统健康状态 |
| **统计** | `/stats` | GET | 系统资源统计 |
| **监控** | `/metrics` | GET | Prometheus指标 |
| **智能对话** | `/chat` | POST | AI聊天接口 |
| **LLM管理** | `/llm/info` | GET | LLM配置信息 |
| **LLM管理** | `/llm/reload` | POST | 重载LLM配置 |
| **会话管理** | `/sessions/{user_id}` | GET | 用户会话列表 |
| **会话管理** | `/sessions/{session_id}/messages` | GET | 会话消息历史 |
| **会话管理** | `/sessions/{session_id}` | DELETE | 删除会话 |
| **知识图谱** | `/knowledge/entities` | GET | 图谱实体 |
| **知识图谱** | `/knowledge/extract` | POST | 知识抽取 |

### 🔄 最近重要变更

#### 2025-08-30 主要更新
1. **统一API入口**: 合并 `main.py` 和 `main_simple.py` 为单一入口点
2. **LLM适配器**: 实现多提供商支持 (OpenAI/Claude/vLLM/Demo)
3. **配置管理**: 通过.env文件管理API密钥
4. **错误处理**: 移除回退机制，直接报告真实错误
5. **监控集成**: 修复Prometheus指标格式问题
6. **资源限制**: 所有Docker容器限制为1个CPU

### 🚦 快速启动

1. **配置API密钥**:
   ```bash
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```

2. **启动系统**:
   ```bash
   docker-compose up -d
   ```

3. **验证部署**:
   ```bash
   curl http://localhost:8888/health
   ```

4. **测试AI功能**:
   ```bash
   curl -X POST http://localhost:8888/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "系统状态如何？"}'
   ```

### 📝 未来待办事项

- [ ] 实现会话管理的具体逻辑
- [ ] 完善知识图谱功能
- [ ] 添加用户认证机制
- [ ] 实现向量搜索功能
- [ ] 完善NER和关系抽取
- [ ] 添加批处理API接口

### 🔍 故障排除

**常见问题**:

1. **OpenAI API错误**: 检查.env文件中的API密钥是否正确
2. **容器启动失败**: 确保端口未被占用
3. **监控数据缺失**: 重启API服务重新注册指标
4. **Neo4j连接问题**: 等待健康检查通过后再访问

**健康检查命令**:
```bash
# 检查所有容器状态
docker-compose ps

# 检查API健康状态
curl http://localhost:8888/health

# 查看容器日志
docker-compose logs api
```