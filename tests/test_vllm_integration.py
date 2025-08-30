#!/usr/bin/env python3
"""
vLLM服务集成测试脚本
测试vLLM OpenAI兼容API接口
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List

# vLLM服务配置
VLLM_CONFIG = {
    "base_url": "http://localhost:8000/v1",
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "timeout": 60
}

async def test_vllm_health(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """测试vLLM健康状态"""
    try:
        async with session.get(f"http://localhost:8000/health") as response:
            if response.status == 200:
                return {"status": "healthy", "details": "Service is running"}
            else:
                return {"status": "unhealthy", "details": f"HTTP {response.status}"}
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def test_vllm_models(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """测试vLLM模型列表接口"""
    try:
        async with session.get(f"{VLLM_CONFIG['base_url']}/models") as response:
            if response.status == 200:
                data = await response.json()
                models = [model["id"] for model in data.get("data", [])]
                return {
                    "status": "success",
                    "models": models,
                    "model_count": len(models)
                }
            else:
                return {"status": "error", "details": f"HTTP {response.status}"}
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def test_vllm_completions(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """测试vLLM文本生成接口"""
    try:
        # 测试提示词
        prompts = [
            {
                "name": "简单问答",
                "prompt": "你好，请介绍一下你自己。",
                "max_tokens": 100
            },
            {
                "name": "AIOps场景",
                "prompt": "作为一个AIOps专家，请解释什么是异常检测？",
                "max_tokens": 200
            },
            {
                "name": "中文推理",
                "prompt": "如果一个系统的CPU使用率突然从20%升高到90%，可能的原因有哪些？",
                "max_tokens": 150
            }
        ]
        
        results = []
        
        for test_case in prompts:
            print(f"      测试: {test_case['name']}")
            
            payload = {
                "model": VLLM_CONFIG["model"],
                "prompt": test_case["prompt"],
                "max_tokens": test_case["max_tokens"],
                "temperature": 0.7,
                "stop": ["Human:", "\n\n"]
            }
            
            start_time = time.time()
            
            timeout = aiohttp.ClientTimeout(total=VLLM_CONFIG["timeout"])
            async with session.post(
                f"{VLLM_CONFIG['base_url']}/completions",
                json=payload,
                timeout=timeout
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    response_time = time.time() - start_time
                    
                    choice = data["choices"][0]
                    result = {
                        "test_name": test_case["name"],
                        "status": "success",
                        "response_time": round(response_time, 2),
                        "generated_text": choice["text"].strip(),
                        "finish_reason": choice["finish_reason"],
                        "tokens_used": data["usage"]["total_tokens"]
                    }
                    results.append(result)
                    print(f"        ✅ 成功 ({response_time:.2f}s, {data['usage']['total_tokens']} tokens)")
                    
                else:
                    error_text = await response.text()
                    result = {
                        "test_name": test_case["name"],
                        "status": "error",
                        "details": f"HTTP {response.status}: {error_text}"
                    }
                    results.append(result)
                    print(f"        ❌ 失败: HTTP {response.status}")
        
        return {
            "status": "success" if all(r["status"] == "success" for r in results) else "partial",
            "test_results": results,
            "successful_tests": sum(1 for r in results if r["status"] == "success"),
            "total_tests": len(results)
        }
        
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def test_vllm_chat_completions(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """测试vLLM聊天接口"""
    try:
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的AIOps助手，擅长系统运维和故障诊断。"
            },
            {
                "role": "user",
                "content": "我的服务器内存使用率达到95%，应该怎么处理？"
            }
        ]
        
        payload = {
            "model": VLLM_CONFIG["model"],
            "messages": messages,
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        start_time = time.time()
        
        timeout = aiohttp.ClientTimeout(total=VLLM_CONFIG["timeout"])
        async with session.post(
            f"{VLLM_CONFIG['base_url']}/chat/completions",
            json=payload,
            timeout=timeout
        ) as response:
            
            if response.status == 200:
                data = await response.json()
                response_time = time.time() - start_time
                
                choice = data["choices"][0]
                return {
                    "status": "success",
                    "response_time": round(response_time, 2),
                    "message_content": choice["message"]["content"].strip(),
                    "finish_reason": choice["finish_reason"],
                    "tokens_used": data["usage"]["total_tokens"]
                }
            else:
                error_text = await response.text()
                return {
                    "status": "error", 
                    "details": f"HTTP {response.status}: {error_text}"
                }
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def test_vllm_streaming(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """测试vLLM流式响应"""
    try:
        payload = {
            "model": VLLM_CONFIG["model"],
            "prompt": "请简单介绍一下机器学习在运维中的应用",
            "max_tokens": 150,
            "stream": True,
            "temperature": 0.7
        }
        
        start_time = time.time()
        chunks_received = 0
        total_content = ""
        
        timeout = aiohttp.ClientTimeout(total=VLLM_CONFIG["timeout"])
        async with session.post(
            f"{VLLM_CONFIG['base_url']}/completions",
            json=payload,
            timeout=timeout
        ) as response:
            
            if response.status == 200:
                async for chunk in response.content:
                    if chunk:
                        chunk_text = chunk.decode('utf-8').strip()
                        if chunk_text.startswith('data: '):
                            data_text = chunk_text[6:]  # Remove 'data: ' prefix
                            if data_text != '[DONE]':
                                try:
                                    chunk_data = json.loads(data_text)
                                    if chunk_data["choices"][0]["text"]:
                                        total_content += chunk_data["choices"][0]["text"]
                                        chunks_received += 1
                                except json.JSONDecodeError:
                                    continue
                
                response_time = time.time() - start_time
                
                return {
                    "status": "success",
                    "response_time": round(response_time, 2),
                    "chunks_received": chunks_received,
                    "total_content_length": len(total_content),
                    "sample_content": total_content[:100] + "..." if len(total_content) > 100 else total_content
                }
            else:
                return {"status": "error", "details": f"HTTP {response.status}"}
                
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def main():
    """主测试函数"""
    print("🤖 AIOps Polaris vLLM服务集成测试")
    print("=" * 50)
    
    timeout = aiohttp.ClientTimeout(total=120)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        # 1. 测试服务健康状态
        print("\n1️⃣  测试vLLM服务健康状态...")
        health_result = await test_vllm_health(session)
        if health_result["status"] == "healthy":
            print(f"   ✅ vLLM服务正常运行")
        else:
            print(f"   ❌ vLLM服务异常: {health_result['details']}")
            print("   请确保vLLM服务已启动并完成模型加载")
            return
        
        # 2. 测试模型列表
        print("\n2️⃣  测试模型列表接口...")
        models_result = await test_vllm_models(session)
        if models_result["status"] == "success":
            print(f"   ✅ 找到 {models_result['model_count']} 个模型")
            for model in models_result["models"]:
                print(f"      - {model}")
        else:
            print(f"   ❌ 模型列表获取失败: {models_result['details']}")
        
        # 3. 测试文本生成
        print("\n3️⃣  测试文本生成接口...")
        completions_result = await test_vllm_completions(session)
        if completions_result["status"] in ["success", "partial"]:
            print(f"   ✅ 完成 {completions_result['successful_tests']}/{completions_result['total_tests']} 个测试")
            for test in completions_result["test_results"]:
                if test["status"] == "success":
                    print(f"      📝 {test['test_name']}: {test['generated_text'][:50]}...")
        else:
            print(f"   ❌ 文本生成测试失败: {completions_result['details']}")
        
        # 4. 测试聊天接口
        print("\n4️⃣  测试聊天接口...")
        chat_result = await test_vllm_chat_completions(session)
        if chat_result["status"] == "success":
            print(f"   ✅ 聊天接口测试成功 ({chat_result['response_time']}s)")
            print(f"      💬 回复: {chat_result['message_content'][:100]}...")
        else:
            print(f"   ❌ 聊天接口测试失败: {chat_result['details']}")
        
        # 5. 测试流式响应
        print("\n5️⃣  测试流式响应...")
        streaming_result = await test_vllm_streaming(session)
        if streaming_result["status"] == "success":
            print(f"   ✅ 流式响应测试成功")
            print(f"      📊 接收 {streaming_result['chunks_received']} 个数据块")
            print(f"      📝 示例内容: {streaming_result['sample_content']}")
        else:
            print(f"   ❌ 流式响应测试失败: {streaming_result['details']}")
    
    print("\n🎯 vLLM测试完成！")
    print("\n📋 GPU使用情况:")
    
    # 显示GPU状态
    try:
        import subprocess
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            gpu_info = result.stdout.strip().split(', ')
            print(f"   GPU: {gpu_info[0]}")
            print(f"   显存使用: {gpu_info[1]}MB / {gpu_info[2]}MB")
            print(f"   GPU利用率: {gpu_info[3]}%")
        else:
            print("   无法获取GPU信息")
    except Exception as e:
        print(f"   GPU信息获取失败: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())