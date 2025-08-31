#!/usr/bin/env python3
"""
检查Weaviate数据库中的数据质量
找出unknown、None、空值等问题数据
"""

import sys
from pathlib import Path
# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

import asyncio
import weaviate
import json
from config.settings import settings

async def check_data_quality():
    """检查数据质量问题"""
    
    client = weaviate.Client(
        url=settings.weaviate.url,
        timeout_config=(5, 15)
    )
    
    try:
        print("=== 检查EmbeddingCollection数据 ===")
        
        # 查询所有数据
        result = client.query.get("EmbeddingCollection", [
            "content", "service_name", "source_type", "log_file", "timestamp"
        ]).with_additional(["id"]).with_limit(100).do()
        
        embedding_data = result.get("data", {}).get("Get", {}).get("EmbeddingCollection", [])
        
        print(f"总共找到 {len(embedding_data)} 条EmbeddingCollection记录")
        
        # 分析数据质量问题
        unknown_services = []
        empty_content = []
        none_values = []
        
        for i, item in enumerate(embedding_data):
            # 检查unknown服务名
            if item.get("service_name") == "unknown":
                unknown_services.append((i, item))
            
            # 检查空内容
            if not item.get("content") or item.get("content").strip() == "":
                empty_content.append((i, item))
                
            # 检查None值
            for key, value in item.items():
                if value is None:
                    none_values.append((i, key, item))
        
        print(f"\n=== 数据质量问题统计 ===")
        print(f"unknown服务名: {len(unknown_services)} 条")
        print(f"空内容: {len(empty_content)} 条") 
        print(f"None值: {len(none_values)} 条")
        
        # 显示问题详情
        if unknown_services:
            print(f"\n=== Unknown服务名详情 (前5条) ===")
            for i, (idx, item) in enumerate(unknown_services[:5]):
                print(f"{i+1}. 索引{idx}:")
                print(f"   内容: {item.get('content', '')[:100]}...")
                print(f"   服务名: {item.get('service_name')}")
                print(f"   源类型: {item.get('source_type')}")
                print(f"   日志文件: {item.get('log_file')}")
        
        if empty_content:
            print(f"\n=== 空内容详情 (前5条) ===")
            for i, (idx, item) in enumerate(empty_content[:5]):
                print(f"{i+1}. 索引{idx}:")
                print(f"   内容: '{item.get('content')}'")
                print(f"   服务名: {item.get('service_name')}")
        
        if none_values:
            print(f"\n=== None值详情 (前5条) ===")
            for i, (idx, key, item) in enumerate(none_values[:5]):
                print(f"{i+1}. 索引{idx}, 字段{key}:")
                print(f"   完整记录: {json.dumps(item, indent=2, ensure_ascii=False)}")
        
        print(f"\n=== 检查FullTextCollection数据 ===")
        
        # 查询FullTextCollection
        result_ft = client.query.get("FullTextCollection", [
            "content", "service_name", "source_type", "log_file", "timestamp"  
        ]).with_additional(["id"]).with_limit(100).do()
        
        fulltext_data = result_ft.get("data", {}).get("Get", {}).get("FullTextCollection", [])
        print(f"总共找到 {len(fulltext_data)} 条FullTextCollection记录")
        
        # 显示一些示例数据
        print(f"\n=== 正常数据示例 (前3条) ===")
        for i, item in enumerate(embedding_data[:3]):
            if item.get("service_name") != "unknown":
                print(f"{i+1}. 服务: {item.get('service_name')}")
                print(f"   内容: {item.get('content', '')[:80]}...")
                print(f"   日志文件: {item.get('log_file')}")
                print()
        
        # 检查特定服务的数据
        print(f"\n=== 检查service-b相关数据 ===")
        service_b_query = client.query.get("EmbeddingCollection", [
            "content", "service_name", "source_type", "log_file", "timestamp"
        ]).with_where({
            "path": ["service_name"],
            "operator": "Equal", 
            "valueString": "service-b"
        }).with_limit(10).do()
        
        service_b_data = service_b_query.get("data", {}).get("Get", {}).get("EmbeddingCollection", [])
        print(f"找到 {len(service_b_data)} 条service-b相关记录")
        
        for i, item in enumerate(service_b_data[:5]):
            print(f"{i+1}. {item.get('content', '')[:60]}...")
            
    except Exception as e:
        print(f"检查数据质量时出错: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_data_quality())