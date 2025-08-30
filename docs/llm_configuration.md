# LLM配置指南

## 概述

AIOps Polaris支持多种LLM提供商，包括OpenAI、Claude、本地vLLM和演示模式。系统设计确保**不会因为缺少API密钥而破坏业务逻辑**。

## API密钥配置方法

### 1. OpenAI API密钥配置

#### 方法一：Docker Compose环境变量（推荐）
在 `docker-compose.yml` 中的 `api` 服务添加环境变量：

```yaml
api:
  environment:
    - DATABASE_URL=mysql+aiomysql://aiops_user:aiops_pass@mysql:3306/aiops
    - NEO4J_URI=bolt://neo4j:7687
    # ... 其他配置 ...
    - OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

#### 方法二：.env文件
在项目根目录创建 `.env` 文件：

```bash
# .env
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-claude-api-key-here
```

#### 方法三：系统环境变量
```bash
export OPENAI_API_KEY="sk-your-actual-openai-api-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-claude-api-key-here"
```

### 2. Claude API密钥配置

同样方式配置Anthropic API密钥：
```bash
ANTHROPIC_API_KEY=sk-ant-your-claude-api-key-here
```

## 提供商切换

在 `config/llm_config.yaml` 中修改 `provider` 字段：

```yaml
llm_config:
  # 可选项: "openai", "claude", "local_vllm", "demo"
  provider: "openai"  # 切换到OpenAI
```

### 支持的提供商：

1. **openai** - OpenAI GPT模型
2. **claude** - Anthropic Claude模型  
3. **local_vllm** - 本地vLLM服务
4. **demo** - 演示模式（无需API密钥）

## 自动回退机制

系统具有智能回退机制：

1. **配置优先级**：按配置文件中的 `provider` 设置
2. **自动回退**：如果配置的提供商不可用，自动切换到演示模式
3. **业务连续性**：确保聊天功能始终可用，不会因API密钥问题中断

## 配置示例

### OpenAI配置示例
```yaml
llm_config:
  provider: "openai"
  openai:
    api_key: "${OPENAI_API_KEY}"
    base_url: "https://api.openai.com/v1"
    model: "gpt-3.5-turbo"
    max_tokens: 4096
    temperature: 0.7
```

### Claude配置示例
```yaml
llm_config:
  provider: "claude"
  claude:
    api_key: "${ANTHROPIC_API_KEY}"
    base_url: "https://api.anthropic.com"
    model: "claude-3-haiku-20240307"
    max_tokens: 4096
    temperature: 0.7
```

### 本地vLLM配置示例
```yaml
llm_config:
  provider: "local_vllm"
  local_vllm:
    base_url: "http://vllm:8000/v1"
    model: "Qwen/Qwen2.5-1.5B-Instruct"
    max_tokens: 4096
    temperature: 0.7
```

### 演示模式配置示例
```yaml
llm_config:
  provider: "demo"
  demo:
    enabled: true
    default_response: "这是一个演示响应。完整的LLM功能正在开发中。"
```

## 验证配置

### 1. 检查当前LLM配置
```bash
curl http://localhost:8888/llm/info
```

### 2. 重新加载配置
```bash
curl -X POST http://localhost:8888/llm/reload
```

### 3. 测试聊天功能
```bash
curl -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

## 安全注意事项

1. **不要在代码中硬编码API密钥**
2. **使用环境变量管理敏感信息**
3. **不要将API密钥提交到版本控制**
4. **定期轮换API密钥**

## 故障排除

### 问题：OpenAI API调用失败
**解决方案**：
1. 检查环境变量是否正确设置
2. 验证API密钥有效性
3. 检查网络连接
4. 系统会自动回退到演示模式

### 问题：本地vLLM服务不可用
**解决方案**：
1. 检查vLLM容器状态：`docker-compose ps vllm`
2. 查看vLLM日志：`docker-compose logs vllm`
3. 系统会自动回退到演示模式

### 问题：所有LLM服务都不可用
**解决方案**：
系统会自动启用演示模式，确保基本聊天功能可用。

## API端点

- `GET /llm/info` - 查看当前LLM配置信息
- `POST /llm/reload` - 重新加载LLM配置
- `POST /chat` - 聊天接口（支持所有提供商）

## 总结

这个配置系统确保了：
1. ✅ **业务逻辑不被破坏** - 始终有可用的LLM服务
2. ✅ **灵活的提供商切换** - 支持多种LLM提供商
3. ✅ **安全的密钥管理** - 通过环境变量管理API密钥
4. ✅ **自动故障恢复** - 智能回退机制确保服务连续性