# AIOps Polaris 工具集

本目录包含用于维护、调试和管理AIOps Polaris系统的实用工具。

## 🛠️ 可用工具

### 📊 数据质量检查
```bash
python tools/check_data_quality.py
```
- **用途**: 检查Weaviate数据库中的数据质量问题
- **功能**: 
  - 识别unknown_file、None值、空字段等问题
  - 统计不同数据源的数量和分布
  - 验证数据完整性

### 💬 命令行聊天界面  
```bash
python tools/chat_cli.py
```
- **用途**: 命令行界面与AIOps系统交互
- **功能**:
  - 直接测试RCA分析功能
  - 查看系统健康状态
  - 支持多种命令：/health, /stats, /quit

### 📈 知识图谱更新
```bash
python tools/update_knowledge_graph.py
```
- **用途**: 更新和维护Neo4j知识图谱
- **功能**:
  - 批量添加服务依赖关系
  - 更新拓扑结构
  - 验证图谱完整性

### 🔧 CPU隔离重启
```bash
./tools/restart_with_cpu_isolation.sh
```
- **用途**: 在CPU隔离环境中重启服务
- **功能**:
  - Docker容器CPU隔离配置
  - 性能优化启动
  - 资源管理

## 🚀 使用前提

1. **确保系统正在运行**:
   ```bash
   # 启动基础服务
   docker-compose up -d
   
   # 启动API服务
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

2. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   export NEO4J_PASSWORD="your-neo4j-password"
   ```

## 📝 使用说明

### 数据质量检查示例
```bash
cd /path/to/AIOpsPolaris
python tools/check_data_quality.py

# 输出示例:
# 🔍 检查Weaviate数据质量...
# ✅ EmbeddingCollection: 1,234 documents
# ❌ 发现 15 个 unknown_file 问题
# ✅ FullTextCollection: 1,189 documents
```

### CLI聊天示例
```bash
python tools/chat_cli.py

# 交互示例:
# 🤖 AIOps Polaris 智能运维助手
# > service-b出现CPU异常，需要分析根因
# 📊 分析中...
# 🎯 发现根因: 内存泄漏导致CPU使用率异常
```

## ⚠️ 注意事项

- 所有工具都需要在项目根目录下运行
- 确保相关服务(Weaviate, Neo4j, Redis)正常运行
- 工具会自动添加项目路径到Python path
- 日志和输出会显示在终端中

## 🔄 维护

工具脚本会随着主项目一起更新。如果遇到导入错误或路径问题：

1. 检查项目结构是否正确
2. 确认所有依赖已安装
3. 验证环境变量配置
4. 查看error log获取详细信息