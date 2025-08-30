"""
LLM适配器服务
支持多种LLM提供商：OpenAI、Claude、本地vLLM等
"""

import os
import asyncio
import logging
import yaml
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime
import aiohttp
import json

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """LLM提供商抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """生成响应"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = self._get_api_key()
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        
    def _get_api_key(self) -> str:
        """获取API密钥"""
        api_key = self.config.get("api_key", "")
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            return os.getenv(env_var, "")
        return api_key
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """生成OpenAI响应"""
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config.get("model", "gpt-3.5-turbo"),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
            "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7))
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"].strip()
                    else:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error {response.status}: {error_text}")
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise
    
    def get_provider_name(self) -> str:
        return "openai"


class ClaudeProvider(LLMProvider):
    """Claude API提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = self._get_api_key()
        self.base_url = config.get("base_url", "https://api.anthropic.com")
        
    def _get_api_key(self) -> str:
        """获取API密钥"""
        api_key = self.config.get("api_key", "")
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            return os.getenv(env_var, "")
        return api_key
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """生成Claude响应"""
        if not self.api_key:
            raise ValueError("Claude API key not configured")
            
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": self.config.get("model", "claude-3-haiku-20240307"),
            "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7))
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/messages",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["content"][0]["text"].strip()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Claude API error {response.status}: {error_text}")
        except Exception as e:
            logger.error(f"Claude API request failed: {e}")
            raise
    
    def get_provider_name(self) -> str:
        return "claude"


class LocalVLLMProvider(LLMProvider):
    """本地vLLM提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://vllm:8000/v1")
        
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """生成本地vLLM响应"""
        headers = {"Content-Type": "application/json"}
        
        data = {
            "model": self.config.get("model", "Qwen/Qwen2.5-1.5B-Instruct"),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
            "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"].strip()
                    else:
                        error_text = await response.text()
                        raise Exception(f"vLLM API error {response.status}: {error_text}")
        except Exception as e:
            logger.error(f"vLLM API request failed: {e}")
            raise
    
    def get_provider_name(self) -> str:
        return "local_vllm"


class DemoProvider(LLMProvider):
    """演示提供商 - 返回简单固定回复"""
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """生成演示响应"""
        # 根据提示内容生成不同的回复
        prompt_lower = prompt.lower()
        
        if "健康" in prompt or "状态" in prompt or "health" in prompt_lower:
            return "系统状态良好。所有核心服务正在正常运行，包括数据库、缓存和监控系统。"
        elif "错误" in prompt or "故障" in prompt or "error" in prompt_lower:
            return "我正在分析系统日志和监控指标。目前没有发现重大错误或故障。如需详细诊断，请提供更多信息。"
        elif "性能" in prompt or "优化" in prompt or "performance" in prompt_lower:
            return "系统性能监控显示正常。CPU使用率和内存占用在合理范围内。如需性能优化建议，请查看监控仪表盘。"
        elif "hello" in prompt_lower or "你好" in prompt:
            return "你好！我是AIOps Polaris智能运维助手。我可以帮助您监控系统状态、分析日志、诊断问题。请告诉我您需要什么帮助。"
        else:
            default_msg = self.config.get("default_response", "这是一个演示响应。")
            return f"收到查询: {prompt[:50]}{'...' if len(prompt) > 50 else ''}。{default_msg}"
    
    def get_provider_name(self) -> str:
        return "demo"


class LLMAdapter:
    """LLM适配器主类"""
    
    def __init__(self, config_path: str = "/app/config/llm_config.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.provider: Optional[LLMProvider] = None
        self.load_config()
        
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            # 尝试多个可能的路径
            possible_paths = [
                self.config_path,
                "./config/llm_config.yaml",
                "../config/llm_config.yaml",
                "/home/alejandroseaah/AIOpsPolaris/config/llm_config.yaml"
            ]
            
            config_data = None
            for path in possible_paths:
                try:
                    if os.path.exists(path):
                        with open(path, 'r', encoding='utf-8') as f:
                            config_data = yaml.safe_load(f)
                            logger.info(f"Loaded LLM config from: {path}")
                            break
                except Exception as e:
                    logger.warning(f"Failed to load config from {path}: {e}")
                    continue
            
            if not config_data:
                logger.warning("No config file found, using default demo configuration")
                config_data = {
                    "llm_config": {
                        "provider": "demo",
                        "demo": {"enabled": True}
                    }
                }
            
            self.config = config_data.get("llm_config", {})
            self._initialize_provider()
            
        except Exception as e:
            logger.error(f"Error loading LLM config: {e}")
            # 使用默认演示配置
            self.config = {"provider": "demo", "demo": {"enabled": True}}
            self._initialize_provider()
    
    def _initialize_provider(self) -> None:
        """初始化LLM提供商"""
        provider_name = self.config.get("provider", "demo")
        
        try:
            if provider_name == "openai":
                self.provider = OpenAIProvider(self.config.get("openai", {}))
            elif provider_name == "claude":
                self.provider = ClaudeProvider(self.config.get("claude", {}))
            elif provider_name == "local_vllm":
                self.provider = LocalVLLMProvider(self.config.get("local_vllm", {}))
            else:  # 默认使用demo
                self.provider = DemoProvider(self.config.get("demo", {}))
            
            logger.info(f"Initialized LLM provider: {provider_name}")
            
        except Exception as e:
            logger.error(f"Error initializing provider {provider_name}: {e}")
            logger.info("Falling back to demo provider")
            self.provider = DemoProvider({})
    
    async def generate_response(
        self, 
        prompt: str, 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """生成响应"""
        if not self.provider:
            raise RuntimeError("No LLM provider initialized")
        
        try:
            # 添加重试逻辑
            max_retries = self.config.get("general", {}).get("max_retries", 3)
            retry_delay = self.config.get("general", {}).get("retry_delay", 1)
            
            for attempt in range(max_retries):
                try:
                    response = await self.provider.generate_response(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        **kwargs
                    )
                    return response
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"LLM request failed (attempt {attempt + 1}), retrying: {e}")
                        await asyncio.sleep(retry_delay)
                    else:
                        raise
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # 直接抛出错误，不回退到演示模式
            raise
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取当前提供商信息"""
        if not self.provider:
            return {"error": "No provider initialized"}
        
        return {
            "provider": self.provider.get_provider_name(),
            "config": self.config.get(self.provider.get_provider_name(), {}),
            "status": "active"
        }
    
    def reload_config(self) -> None:
        """重新加载配置"""
        logger.info("Reloading LLM configuration")
        self.load_config()


# 全局LLM适配器实例
_llm_adapter: Optional[LLMAdapter] = None


def get_llm_adapter() -> LLMAdapter:
    """获取LLM适配器实例（单例模式）"""
    global _llm_adapter
    if _llm_adapter is None:
        _llm_adapter = LLMAdapter()
    return _llm_adapter


async def test_llm_adapter():
    """测试LLM适配器"""
    adapter = get_llm_adapter()
    
    test_prompts = [
        "Hello, how are you?",
        "系统状态如何？",
        "检查系统健康状态",
        "有什么性能优化建议？"
    ]
    
    print(f"LLM Provider Info: {adapter.get_provider_info()}")
    
    for prompt in test_prompts:
        try:
            response = await adapter.generate_response(prompt)
            print(f"Prompt: {prompt}")
            print(f"Response: {response}")
            print("-" * 50)
        except Exception as e:
            print(f"Error with prompt '{prompt}': {e}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_llm_adapter())