# AIOps Polaris POC测试流程

## 概述

本文档提供了完整的POC测试流程，确保系统各个组件正常工作并能提供预期的功能。

## 前置条件

1. **系统要求**
   - Docker & Docker Compose
   - Python 3.8+
   - 至少8GB内存
   - 至少10GB可用磁盘空间

2. **端口检查**
   确保以下端口未被占用：
   - 3306 (MySQL)
   - 7474, 7687 (Neo4j)
   - 8080 (Weaviate) 
   - 6379 (Redis)
   - 8888 (API服务)
   - 7860 (Gradio界面)

## 测试流程

### 第一阶段：基础服务启动测试

1. **启动所有服务**
   ```bash
   ./scripts/start_services.sh
   ```

2. **验证基础服务**
   - MySQL: `docker-compose ps mysql`
   - Neo4j: 访问 http://localhost:7474 (用户名: neo4j, 密码: aiops123)
   - Weaviate: `curl http://localhost:8080/v1/schema`
   - Redis: `docker exec -it aiopspolaris_redis_1 redis-cli ping`

3. **验证API服务**
   ```bash
   curl http://localhost:8888/health
   ```
   预期响应：
   ```json
   {
     "status": "healthy",
     "components": {
       "weaviate": {"status": "healthy"},
       "neo4j": {"status": "healthy"},
       "embedding": {"status": "healthy"}
     }
   }
   ```

4. **验证Gradio界面**
   访问 http://localhost:7860，应看到多标签页界面

### 第二阶段：数据初始化测试

1. **检查样本数据**
   ```bash
   ls -la data/
   ls -la data/wiki/ data/gitlab/ data/jira/ data/logs/
   ```

2. **验证数据加载**
   检查日志中的数据加载信息：
   ```bash
   tail -f logs/api.log | grep "documents\|entities\|relationships"
   ```

3. **验证数据库内容**
   ```bash
   # MySQL
   docker exec -it aiopspolaris_mysql_1 mysql -u root -paiops123 -D aiops -e "SELECT COUNT(*) FROM knowledge_documents;"
   
   # Neo4j (通过浏览器查询)
   MATCH (n) RETURN labels(n), count(n)
   
   # Weaviate
   curl http://localhost:8080/v1/objects?class=KnowledgeDocument&limit=5
   ```

### 第三阶段：API功能测试

1. **搜索功能测试**
   ```bash
   curl -X POST http://localhost:8888/search \
     -H "Content-Type: application/json" \
     -d '{"query": "kubernetes deployment", "limit": 5}'
   ```

2. **知识提取测试**
   ```bash
   curl -X POST "http://localhost:8888/knowledge/extract?source=test" \
     -H "Content-Type: application/json" \
     -d '"Kubernetes deployment failed due to insufficient memory resources"'
   ```

3. **聊天功能测试**
   ```bash
   curl -X POST http://localhost:8888/chat \
     -H "Content-Type: application/json" \
     -d '{
       "message": "How to troubleshoot Kubernetes pod failures?",
       "user_id": "test_user",
       "temperature": 0.7,
       "max_tokens": 500
     }'
   ```

### 第四阶段：Gradio界面测试

1. **聊天界面测试**
   - 输入问题："What are the common causes of service outages?"
   - 验证响应包含相关搜索结果和Agent处理流程
   - 检查"显示详细信息"功能

2. **知识搜索测试**
   - 搜索"database performance"
   - 验证返回向量搜索和图谱搜索结果
   - 测试不同搜索类型：hybrid, vector, graph

3. **知识提取测试**
   - 输入文本："The API gateway returned 503 errors due to Redis connection timeout"
   - 验证提取的实体和关系
   - 检查置信度分数

4. **系统状态测试**
   - 查看系统统计信息
   - 验证各组件健康状态
   - 检查Agent状态

### 第五阶段：端到端工作流测试

1. **问题诊断场景**
   用户输入："Our microservice is experiencing high latency, how to troubleshoot?"
   
   预期工作流：
   - Planner分析问题类型
   - Knowledge Agent搜索相关文档
   - Reasoning Agent分析可能原因
   - Executor Agent提供具体解决步骤

2. **多轮对话测试**
   - 继续问："What specific metrics should I check?"
   - 验证系统能记住上下文
   - 检查会话保持功能

3. **多用户测试**
   - 使用不同用户ID进行并发聊天
   - 验证会话隔离

### 第六阶段：性能和稳定性测试

1. **并发测试**
   ```bash
   # 使用ab或其他工具进行简单的并发测试
   ab -n 50 -c 5 -T "application/json" -p test_chat.json http://localhost:8888/chat
   ```

2. **长时间运行测试**
   - 让系统运行1小时
   - 监控内存和CPU使用情况
   - 检查日志是否有错误

## 常见问题排查

### 服务启动失败
1. 检查端口占用：`lsof -i :端口号`
2. 查看Docker日志：`docker-compose logs 服务名`
3. 检查磁盘空间：`df -h`

### 数据库连接失败
1. 确认服务启动顺序
2. 检查连接字符串配置
3. 验证网络连通性

### API响应错误
1. 查看API日志：`tail -f logs/api.log`
2. 检查依赖服务状态
3. 验证请求格式

### Gradio界面异常
1. 检查浏览器控制台错误
2. 查看Gradio日志：`tail -f logs/gradio.log`
3. 验证API连接

## 测试报告模板

```markdown
# POC测试报告

## 测试环境
- 操作系统：
- Docker版本：
- 测试时间：

## 测试结果
- [ ] 基础服务启动正常
- [ ] 数据初始化成功
- [ ] API功能正常
- [ ] Gradio界面可用
- [ ] 端到端工作流正常
- [ ] 性能满足预期

## 问题记录
1. 问题描述：
   解决方案：

## 性能数据
- 响应时间：
- 内存使用：
- CPU使用：

## 建议改进
1. 
2. 
```

## 下一步优化

基于测试结果，可以考虑以下优化：
1. 增加更多样本数据
2. 优化搜索算法
3. 改进Agent决策逻辑
4. 增加监控和告警
5. 性能调优