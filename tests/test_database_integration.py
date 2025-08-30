#!/usr/bin/env python3
"""
数据库集成测试脚本
测试MySQL, Neo4j, Weaviate, Redis连接和基本操作
"""

import asyncio
import aiohttp
import asyncio
import json
import time
from typing import Dict, Any, List

# 数据库连接配置
DATABASES = {
    "mysql": {
        "host": "localhost",
        "port": 3306,
        "database": "aiops",
        "user": "aiops_user",
        "password": "aiops_pass"
    },
    "neo4j": {
        "uri": "bolt://localhost:7687",
        "user": "neo4j", 
        "password": "aiops123"
    },
    "weaviate": {
        "url": "http://localhost:8080"
    },
    "redis": {
        "host": "localhost",
        "port": 6379,
        "password": "aiops123",
        "db": 0
    }
}

async def test_mysql_connection() -> Dict[str, Any]:
    """测试MySQL连接"""
    try:
        import aiomysql
        
        conn = await aiomysql.connect(
            host=DATABASES["mysql"]["host"],
            port=DATABASES["mysql"]["port"],
            user=DATABASES["mysql"]["user"],
            password=DATABASES["mysql"]["password"],
            db=DATABASES["mysql"]["database"]
        )
        
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT VERSION()")
            version = await cursor.fetchone()
            
            # 测试表创建
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_connection (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    test_data VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入测试数据
            await cursor.execute(
                "INSERT INTO test_connection (test_data) VALUES (%s)",
                ("database_test_" + str(int(time.time())),)
            )
            await conn.commit()
            
            # 查询测试数据
            await cursor.execute("SELECT COUNT(*) FROM test_connection")
            count = await cursor.fetchone()
            
        await conn.ensure_closed()
        
        return {
            "status": "success",
            "version": version[0],
            "test_records": count[0]
        }
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def test_neo4j_connection() -> Dict[str, Any]:
    """测试Neo4j连接"""
    try:
        from neo4j import AsyncGraphDatabase
        
        driver = AsyncGraphDatabase.driver(
            DATABASES["neo4j"]["uri"],
            auth=(DATABASES["neo4j"]["user"], DATABASES["neo4j"]["password"])
        )
        
        async with driver.session() as session:
            # 测试连接
            result = await session.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version")
            info = await result.single()
            
            # 创建测试节点
            test_time = int(time.time())
            await session.run("""
                CREATE (t:TestNode {
                    name: $name,
                    created_at: datetime()
                })
            """, name=f"test_node_{test_time}")
            
            # 查询测试节点数量
            result = await session.run("MATCH (t:TestNode) RETURN COUNT(t) as count")
            count = await result.single()
            
        await driver.close()
        
        return {
            "status": "success",
            "version": info["version"],
            "test_nodes": count["count"]
        }
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def test_weaviate_connection() -> Dict[str, Any]:
    """测试Weaviate连接"""
    try:
        import httpx
        
        # 使用REST API直接测试Weaviate
        base_url = DATABASES["weaviate"]["url"]
        
        async with httpx.AsyncClient() as client:
            # 测试健康检查
            health_response = await client.get(f"{base_url}/v1/.well-known/ready")
            if health_response.status_code != 200:
                return {"status": "error", "details": f"Health check failed: {health_response.status_code}"}
            
            # 获取schema
            schema_response = await client.get(f"{base_url}/v1/schema")
            if schema_response.status_code == 200:
                schema = schema_response.json()
                classes = [cls["class"] for cls in schema.get("classes", [])]
            else:
                classes = []
            
            # 测试数据插入
            test_time = int(time.time())
            class_name = "TestDocument"
            
            # 确保类存在
            if class_name not in classes:
                class_definition = {
                    "class": class_name,
                    "description": "Test document class",
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "Document content"
                        },
                        {
                            "name": "timestamp",
                            "dataType": ["number"],
                            "description": "Creation timestamp"
                        }
                    ]
                }
                
                create_response = await client.post(f"{base_url}/v1/schema", json=class_definition)
                if create_response.status_code not in [200, 422]:  # 422 可能表示类已存在
                    return {"status": "error", "details": f"Failed to create class: {create_response.status_code}"}
            
            # 插入测试对象
            test_object = {
                "class": class_name,
                "properties": {
                    "content": f"Test document content {test_time}",
                    "timestamp": test_time
                }
            }
            
            insert_response = await client.post(f"{base_url}/v1/objects", json=test_object)
            insert_success = insert_response.status_code in [200, 201]
            
            # 查询对象数量
            query = {
                "query": f"{{ Aggregate {{ {class_name} {{ meta {{ count }} }} }} }}"
            }
            
            try:
                query_response = await client.post(f"{base_url}/v1/graphql", json=query)
                if query_response.status_code == 200:
                    data = query_response.json()
                    count = data.get("data", {}).get("Aggregate", {}).get(class_name, [{}])[0].get("meta", {}).get("count", 0)
                else:
                    count = 0
            except:
                count = 0
            
            return {
                "status": "success",
                "classes": classes + ([class_name] if class_name not in classes else []),
                "test_documents": count,
                "insert_success": insert_success
            }
            
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def test_redis_connection() -> Dict[str, Any]:
    """测试Redis连接"""
    try:
        import redis.asyncio as redis
        
        r = redis.Redis(
            host=DATABASES["redis"]["host"],
            port=DATABASES["redis"]["port"],
            password=DATABASES["redis"]["password"],
            db=DATABASES["redis"]["db"]
        )
        
        # 测试连接
        await r.ping()
        
        # 获取Redis信息
        info = await r.info()
        
        # 测试数据操作
        test_key = f"test_key_{int(time.time())}"
        await r.set(test_key, "test_value")
        value = await r.get(test_key)
        
        # 获取所有测试键数量
        keys = await r.keys("test_key_*")
        
        await r.close()
        
        return {
            "status": "success",
            "version": info["redis_version"],
            "test_value": value.decode() if value else None,
            "test_keys_count": len(keys)
        }
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def main():
    """主测试函数"""
    print("🗄️  AIOps Polaris 数据库集成测试")
    print("=" * 50)
    
    # 数据库测试映射
    tests = {
        "MySQL": test_mysql_connection,
        "Neo4j": test_neo4j_connection, 
        "Weaviate": test_weaviate_connection,
        "Redis": test_redis_connection
    }
    
    results = {}
    
    for db_name, test_func in tests.items():
        print(f"\n🔍 测试 {db_name} 连接...")
        try:
            result = await test_func()
            results[db_name] = result
            
            if result["status"] == "success":
                print(f"   ✅ {db_name}: 连接成功")
                if "version" in result:
                    print(f"      版本: {result['version']}")
                for key, value in result.items():
                    if key not in ["status", "version"]:
                        print(f"      {key}: {value}")
            else:
                print(f"   ❌ {db_name}: 连接失败")
                print(f"      错误: {result['details']}")
        except Exception as e:
            print(f"   ❌ {db_name}: 测试异常 - {str(e)}")
            results[db_name] = {"status": "error", "details": str(e)}
    
    # 总结
    print(f"\n📊 测试总结:")
    successful = sum(1 for r in results.values() if r["status"] == "success")
    total = len(results)
    print(f"   成功: {successful}/{total}")
    
    if successful == total:
        print("   🎉 所有数据库测试通过！")
    else:
        print("   ⚠️  部分数据库连接失败，请检查服务状态")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())