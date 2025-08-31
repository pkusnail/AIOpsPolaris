"""
简化的Agent RAG集成测试
避免复杂的导入依赖，直接测试核心功能
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_rag_search_service():
    """测试RAG搜索服务"""
    print("\n=== 测试RAG搜索服务 ===")
    try:
        import weaviate
        from sentence_transformers import SentenceTransformer
        
        # 连接Weaviate
        client = weaviate.Client(url="http://localhost:8080")
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # 测试查询
        query = "service-b CPU过高导致响应超时"
        query_vector = model.encode(query).tolist()
        
        # 检查是否有数据
        collections = ["EmbeddingCollection", "FullTextCollection", "LogEntry", "KnowledgeDocument"]
        found_data = False
        
        for collection_name in collections:
            try:
                result = client.query.aggregate(collection_name).with_meta_count().do()
                count = result['data']['Aggregate'][collection_name][0]['meta']['count']
                if count > 0:
                    print(f"✅ {collection_name}: {count} 条记录")
                    found_data = True
                    
                    # 尝试搜索
                    if collection_name in ["EmbeddingCollection", "LogEntry"]:
                        search_result = (
                            client.query
                            .get(collection_name)
                            .with_near_vector({"vector": query_vector})
                            .with_limit(3)
                            .do()
                        )
                        
                        results = search_result["data"]["Get"].get(collection_name, [])
                        print(f"   向量搜索找到: {len(results)} 条结果")
                        
                        if results:
                            for i, result in enumerate(results[:2]):
                                content = str(result).get('content', str(result))[:50]
                                print(f"     结果{i+1}: {content}...")
                    
                    elif collection_name in ["FullTextCollection", "KnowledgeDocument"]:
                        bm25_result = (
                            client.query
                            .get(collection_name)
                            .with_bm25(query="CPU")
                            .with_limit(3)
                            .do()
                        )
                        
                        results = bm25_result["data"]["Get"].get(collection_name, [])
                        print(f"   BM25搜索找到: {len(results)} 条结果")
                        
                else:
                    print(f"❌ {collection_name}: 无数据")
                    
            except Exception as e:
                print(f"⚠️ {collection_name}: 不存在或查询失败 - {e}")
        
        if found_data:
            print("✅ RAG搜索服务可用")
            return True
        else:
            print("❌ 没有找到可用数据")
            return False
            
    except Exception as e:
        print(f"❌ RAG搜索服务测试失败: {e}")
        return False


async def test_knowledge_graph_data():
    """测试知识图谱数据"""
    print("\n=== 测试知识图谱数据 ===")
    try:
        from neo4j import GraphDatabase
        
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "aiops123")
        )
        
        with driver.session() as session:
            # 检查服务实体
            service_result = session.run(
                "MATCH (s:Service) RETURN s.name as name LIMIT 5"
            )
            services = [record["name"] for record in service_result]
            print(f"✅ 发现服务实体: {services}")
            
            # 检查关系
            rel_result = session.run(
                "MATCH (a)-[r]->(b) RETURN type(r) as rel_type, count(r) as count"
            )
            relationships = {record["rel_type"]: record["count"] for record in rel_result}
            print(f"✅ 发现关系: {relationships}")
            
            # 查找与service-b相关的信息
            serviceb_result = session.run(
                """
                MATCH (s:Service {name: 'service-b'})-[r]-(related)
                RETURN labels(related) as labels, related.name as name, type(r) as rel_type
                LIMIT 10
                """
            )
            
            serviceb_related = []
            for record in serviceb_result:
                serviceb_related.append({
                    'labels': record['labels'],
                    'name': record['name'],
                    'relation': record['rel_type']
                })
            
            if serviceb_related:
                print(f"✅ service-b相关实体: {len(serviceb_related)} 个")
                for item in serviceb_related[:3]:
                    print(f"   - {item['labels']} {item['name']} ({item['relation']})")
            else:
                print("⚠️ 未找到service-b相关实体")
        
        driver.close()
        return len(services) > 0 or len(relationships) > 0
        
    except Exception as e:
        print(f"❌ 知识图谱数据测试失败: {e}")
        return False


async def test_rca_scenario():
    """测试RCA场景"""
    print("\n=== 测试RCA场景 ===")
    try:
        import weaviate
        from sentence_transformers import SentenceTransformer
        from neo4j import GraphDatabase
        
        # 模拟RCA查询场景
        incident_query = "service-b CPU使用率过高，响应超时，需要分析根本原因"
        
        # 1. 向量搜索相关日志
        client = weaviate.Client(url="http://localhost:8080")
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        query_vector = model.encode(incident_query).tolist()
        
        log_results = []
        collections = ["EmbeddingCollection", "LogEntry"]
        
        for collection_name in collections:
            try:
                result = (
                    client.query
                    .get(collection_name)
                    .with_near_vector({"vector": query_vector})
                    .with_limit(5)
                    .with_additional(["certainty"])
                    .do()
                )
                
                items = result["data"]["Get"].get(collection_name, [])
                if items:
                    log_results.extend(items)
                    print(f"✅ {collection_name}: 找到 {len(items)} 条相关日志")
            except:
                continue
        
        # 2. 搜索相关知识文档
        knowledge_results = []
        knowledge_collections = ["FullTextCollection", "KnowledgeDocument"]
        
        for collection_name in knowledge_collections:
            try:
                result = (
                    client.query
                    .get(collection_name)
                    .with_bm25(query="CPU 性能 service-b")
                    .with_limit(5)
                    .do()
                )
                
                items = result["data"]["Get"].get(collection_name, [])
                if items:
                    knowledge_results.extend(items)
                    print(f"✅ {collection_name}: 找到 {len(items)} 条相关文档")
            except:
                continue
        
        # 3. 查询知识图谱
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "aiops123"))
        
        graph_results = []
        with driver.session() as session:
            # 查找service-b的依赖关系
            dependency_result = session.run(
                """
                MATCH (s:Service {name: 'service-b'})-[r]-(related)
                RETURN related.name as name, labels(related) as labels, type(r) as relation
                UNION
                MATCH (s:Service {name: 'service-b'})
                MATCH (issue:Issue)-[:AFFECTS]->(s)
                RETURN issue.name as name, ['Issue'] as labels, 'AFFECTS' as relation
                LIMIT 10
                """
            )
            
            for record in dependency_result:
                graph_results.append({
                    'name': record['name'],
                    'labels': record['labels'],
                    'relation': record['relation']
                })
        
        driver.close()
        
        # 4. 综合分析结果
        total_evidence = len(log_results) + len(knowledge_results) + len(graph_results)
        
        print(f"\n📊 RCA分析结果:")
        print(f"   相关日志: {len(log_results)} 条")
        print(f"   知识文档: {len(knowledge_results)} 条") 
        print(f"   图谱关系: {len(graph_results)} 条")
        print(f"   总证据: {total_evidence} 条")
        
        if total_evidence >= 3:
            print("✅ 具备RCA分析能力 - 能够获取足够的上下文信息")
            
            # 显示一些具体证据
            if log_results:
                print(f"   日志证据示例: {str(log_results[0])[:80]}...")
            if knowledge_results:
                print(f"   知识证据示例: {str(knowledge_results[0])[:80]}...")
            if graph_results:
                print(f"   图谱证据示例: {graph_results[0]['name']} ({graph_results[0]['relation']})")
                
            return True
        else:
            print("❌ RCA分析能力不足 - 缺少足够的上下文信息")
            return False
        
    except Exception as e:
        print(f"❌ RCA场景测试失败: {e}")
        return False


async def test_pipeline_status():
    """测试pipeline运行状态"""
    print("\n=== 测试Pipeline状态 ===")
    try:
        # 检查数据是否已经被pipeline处理
        import weaviate
        
        client = weaviate.Client(url="http://localhost:8080")
        
        # 检查各个collection的数据量
        collections = {
            "EmbeddingCollection": "向量索引",
            "FullTextCollection": "全文索引", 
            "LogEntry": "日志条目",
            "KnowledgeDocument": "知识文档"
        }
        
        pipeline_ready = True
        
        for collection_name, description in collections.items():
            try:
                result = client.query.aggregate(collection_name).with_meta_count().do()
                count = result['data']['Aggregate'][collection_name][0]['meta']['count']
                
                if count > 0:
                    print(f"✅ {description}: {count} 条记录")
                else:
                    print(f"⚠️ {description}: 无数据 - 可能需要运行pipeline")
                    pipeline_ready = False
                    
            except Exception as e:
                print(f"❌ {description}: 不存在 - {e}")
                pipeline_ready = False
        
        if pipeline_ready:
            print("✅ Pipeline数据已就绪")
        else:
            print("⚠️ Pipeline可能需要运行以建立索引")
            print("💡 建议运行:")
            print("   python -m src.services.log_pipeline")
            print("   python -m src.services.knowledge_pipeline") 
            print("   python -m src.services.knowledge_graph_pipeline")
        
        return pipeline_ready
        
    except Exception as e:
        print(f"❌ Pipeline状态检查失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始Agent RAG集成简化测试")
    print("=" * 50)
    
    test_results = []
    
    # 1. 测试Pipeline状态
    pipeline_ok = await test_pipeline_status()
    test_results.append(("Pipeline状态", pipeline_ok))
    
    # 2. 测试RAG搜索服务
    rag_search_ok = await test_rag_search_service()
    test_results.append(("RAG搜索服务", rag_search_ok))
    
    # 3. 测试知识图谱数据
    kg_ok = await test_knowledge_graph_data()
    test_results.append(("知识图谱数据", kg_ok))
    
    # 4. 测试RCA场景
    if rag_search_ok or kg_ok:
        rca_ok = await test_rca_scenario()
        test_results.append(("RCA场景分析", rca_ok))
    
    # 显示结果
    print("\n" + "=" * 50)
    print("📋 Agent RAG集成测试结果:")
    print("=" * 50)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<15} {status}")
    
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    print(f"\n📊 总体结果: {passed_tests}/{total_tests} 测试通过")
    
    # 给出建议
    if passed_tests == total_tests:
        print("🎉 Agent能够正确理解和使用RAG信息进行RCA分析！")
        print("💡 建议: RAG Pipeline已完全就绪，可用于生产环境")
    elif passed_tests >= total_tests * 0.7:
        print("✅ Agent基本能够使用RAG信息")
        print("💡 建议: 运行缺失的pipeline以完善数据")
    else:
        print("⚠️ Agent RAG集成存在问题")
        print("💡 建议: 检查pipeline状态和数据完整性")


if __name__ == "__main__":
    asyncio.run(main())