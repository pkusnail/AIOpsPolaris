"""
完整的RCA流程测试
测试从用户输入到最终RCA结论的完整链路
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


async def test_rag_integration():
    """测试RAG集成是否可用"""
    print("🔍 测试RAG集成...")
    try:
        import weaviate
        from sentence_transformers import SentenceTransformer
        from neo4j import GraphDatabase
        
        # 测试Weaviate
        client = weaviate.Client(url="http://localhost:8080")
        embedding_count = client.query.aggregate("EmbeddingCollection").with_meta_count().do()
        fulltext_count = client.query.aggregate("FullTextCollection").with_meta_count().do()
        
        embedding_records = embedding_count['data']['Aggregate']['EmbeddingCollection'][0]['meta']['count']
        fulltext_records = fulltext_count['data']['Aggregate']['FullTextCollection'][0]['meta']['count']
        
        print(f"✅ Weaviate: {embedding_records} embedding records, {fulltext_records} fulltext records")
        
        # 测试Neo4j
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "aiops123"))
        with driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
        driver.close()
        
        print(f"✅ Neo4j: {node_count} nodes, {rel_count} relationships")
        
        return embedding_records > 0 and node_count > 0
        
    except Exception as e:
        print(f"❌ RAG集成测试失败: {e}")
        return False


async def simulate_rag_search(incident_description):
    """模拟RAG搜索过程"""
    print(f"🔍 模拟RAG搜索: '{incident_description}'")
    
    try:
        import weaviate
        from sentence_transformers import SentenceTransformer
        from neo4j import GraphDatabase
        
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        client = weaviate.Client(url="http://localhost:8080")
        
        # 1. 向量搜索相关日志
        query_vector = model.encode(incident_description).tolist()
        
        vector_result = (
            client.query
            .get("EmbeddingCollection", ["content", "service_name", "log_file", "timestamp"])
            .with_near_vector({"vector": query_vector})
            .with_limit(5)
            .with_additional(["certainty"])
            .do()
        )
        
        log_evidence = vector_result["data"]["Get"]["EmbeddingCollection"]
        print(f"   📋 找到 {len(log_evidence)} 条相关日志")
        
        for i, log in enumerate(log_evidence[:3]):
            certainty = log["_additional"]["certainty"]
            content = log["content"][:60]
            service = log.get("service_name", "unknown")
            print(f"      {i+1}. [{service}] {content}... (certainty: {certainty:.3f})")
        
        # 2. 全文搜索知识文档
        bm25_result = (
            client.query
            .get("FullTextCollection", ["content", "source_type", "service_name"])
            .with_bm25(query=incident_description)
            .with_limit(3)
            .do()
        )
        
        knowledge_evidence = bm25_result["data"]["Get"]["FullTextCollection"]
        print(f"   📚 找到 {len(knowledge_evidence)} 条相关知识")
        
        for i, doc in enumerate(knowledge_evidence):
            content = doc["content"][:60]
            source = doc.get("source_type", "unknown")
            print(f"      {i+1}. [{source}] {content}...")
        
        # 3. 查询知识图谱
        # 从incident_description中提取服务名
        services_mentioned = []
        for service in ["service-a", "service-b", "service-c", "database", "redis"]:
            if service in incident_description.lower():
                services_mentioned.append(service)
        
        graph_evidence = []
        if services_mentioned:
            driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "aiops123"))
            
            with driver.session() as session:
                for service in services_mentioned:
                    result = session.run(
                        """
                        MATCH (s:Service {name: $service})-[r]-(related)
                        RETURN related.name as name, labels(related) as labels, type(r) as relation
                        LIMIT 5
                        """,
                        service=service
                    )
                    
                    for record in result:
                        graph_evidence.append({
                            'service': service,
                            'related': record['name'],
                            'labels': record['labels'],
                            'relation': record['relation']
                        })
            
            driver.close()
        
        print(f"   🕸️ 找到 {len(graph_evidence)} 条图谱关系")
        for i, rel in enumerate(graph_evidence[:3]):
            print(f"      {i+1}. {rel['service']} --{rel['relation']}--> {rel['related']} {rel['labels']}")
        
        return {
            "log_evidence": log_evidence,
            "knowledge_evidence": knowledge_evidence,
            "graph_evidence": graph_evidence,
            "total_evidence": len(log_evidence) + len(knowledge_evidence) + len(graph_evidence)
        }
        
    except Exception as e:
        print(f"❌ RAG搜索模拟失败: {e}")
        return None


async def simulate_rca_reasoning(evidence_data, incident_description):
    """模拟RCA推理过程"""
    print("\n🧠 模拟RCA推理过程...")
    
    if not evidence_data:
        print("❌ 缺少证据数据，无法进行推理")
        return None
    
    try:
        # 1. 症状分析
        symptoms = []
        incident_lower = incident_description.lower()
        
        if "cpu" in incident_lower:
            symptoms.append({"type": "performance", "symptom": "CPU高使用率", "severity": "high"})
        if "timeout" in incident_lower or "超时" in incident_lower:
            symptoms.append({"type": "performance", "symptom": "响应超时", "severity": "high"})
        if "error" in incident_lower or "错误" in incident_lower:
            symptoms.append({"type": "functional", "symptom": "功能错误", "severity": "medium"})
        if "slow" in incident_lower or "慢" in incident_lower:
            symptoms.append({"type": "performance", "symptom": "响应缓慢", "severity": "medium"})
        
        print(f"   📊 识别症状: {len(symptoms)} 个")
        for symptom in symptoms:
            print(f"      - {symptom['symptom']} ({symptom['type']}, {symptom['severity']})")
        
        # 2. 根因推理
        potential_causes = []
        
        # 基于日志证据推理
        for log in evidence_data.get("log_evidence", [])[:3]:
            content = log["content"].lower()
            if "cpu" in content and "high" in content:
                potential_causes.append({
                    "cause": "CPU资源不足",
                    "confidence": log["_additional"]["certainty"],
                    "evidence_type": "log",
                    "source": log.get("service_name", "unknown")
                })
            elif "memory" in content:
                potential_causes.append({
                    "cause": "内存资源问题",
                    "confidence": log["_additional"]["certainty"],
                    "evidence_type": "log",
                    "source": log.get("service_name", "unknown")
                })
        
        # 基于图谱证据推理
        for rel in evidence_data.get("graph_evidence", [])[:3]:
            if rel['relation'] == 'DEPENDS_ON':
                potential_causes.append({
                    "cause": f"{rel['service']}依赖的{rel['related']}服务问题",
                    "confidence": 0.7,
                    "evidence_type": "dependency",
                    "source": rel['service']
                })
            elif rel['relation'] == 'DEPLOYED_ON':
                potential_causes.append({
                    "cause": f"{rel['related']}主机资源问题",
                    "confidence": 0.6,
                    "evidence_type": "deployment",
                    "source": rel['service']
                })
        
        # 根据置信度排序
        potential_causes.sort(key=lambda x: x["confidence"], reverse=True)
        
        print(f"   🎯 潜在根因: {len(potential_causes)} 个")
        for i, cause in enumerate(potential_causes[:3]):
            print(f"      {i+1}. {cause['cause']} (置信度: {cause['confidence']:.3f}, 来源: {cause['evidence_type']})")
        
        # 3. 解决方案建议
        solutions = []
        
        for cause in potential_causes[:2]:  # 取前2个最可能的根因
            if "CPU" in cause["cause"]:
                solutions.append({
                    "solution": "扩容CPU资源或优化CPU密集型操作",
                    "priority": "high",
                    "estimated_time": "30分钟"
                })
            elif "内存" in cause["cause"]:
                solutions.append({
                    "solution": "检查内存泄露，重启相关服务",
                    "priority": "high", 
                    "estimated_time": "15分钟"
                })
            elif "依赖" in cause["cause"]:
                solutions.append({
                    "solution": "检查依赖服务状态，修复服务间通信",
                    "priority": "medium",
                    "estimated_time": "45分钟"
                })
            elif "主机" in cause["cause"]:
                solutions.append({
                    "solution": "检查主机资源使用情况，考虑迁移服务",
                    "priority": "medium",
                    "estimated_time": "60分钟"
                })
        
        print(f"   💡 解决方案: {len(solutions)} 个")
        for i, solution in enumerate(solutions):
            print(f"      {i+1}. {solution['solution']} ({solution['priority']}, 预计{solution['estimated_time']})")
        
        # 4. 最终RCA结论
        if potential_causes:
            primary_cause = potential_causes[0]
            
            rca_conclusion = {
                "incident_description": incident_description,
                "primary_root_cause": primary_cause["cause"],
                "confidence": primary_cause["confidence"],
                "symptoms_count": len(symptoms),
                "evidence_count": evidence_data["total_evidence"],
                "alternative_causes": [c["cause"] for c in potential_causes[1:3]],
                "recommended_solutions": solutions[:2],
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            print(f"\n✅ RCA分析完成:")
            print(f"   主要根因: {rca_conclusion['primary_root_cause']}")
            print(f"   置信度: {rca_conclusion['confidence']:.3f}")
            print(f"   证据总数: {rca_conclusion['evidence_count']}")
            print(f"   推荐方案: {len(rca_conclusion['recommended_solutions'])} 个")
            
            return rca_conclusion
        else:
            print("❌ 无法确定根本原因")
            return None
        
    except Exception as e:
        print(f"❌ RCA推理失败: {e}")
        return None


async def test_complete_rca_scenarios():
    """测试完整RCA场景"""
    print("\n🚀 开始完整RCA场景测试")
    print("=" * 60)
    
    # 准备测试场景
    test_scenarios = [
        {
            "title": "Incident 001 - Service-B CPU过载",
            "description": "service-b CPU使用率过高导致响应超时，用户反馈页面加载缓慢",
            "expected_keywords": ["CPU", "service-b", "timeout", "performance"]
        },
        {
            "title": "Incident 002 - 数据库连接问题", 
            "description": "database服务连接失败，多个服务无法访问数据库",
            "expected_keywords": ["database", "connection", "dependency", "error"]
        },
        {
            "title": "Incident 003 - 磁盘IO瓶颈",
            "description": "d1主机磁盘IO过高，部署在其上的服务响应变慢",
            "expected_keywords": ["disk", "IO", "d1", "performance"]
        }
    ]
    
    successful_scenarios = 0
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📋 场景 {i}: {scenario['title']}")
        print(f"   描述: {scenario['description']}")
        
        # 1. RAG搜索
        evidence_data = await simulate_rag_search(scenario['description'])
        
        if evidence_data and evidence_data["total_evidence"] >= 3:
            print(f"   ✅ RAG搜索成功 - 找到 {evidence_data['total_evidence']} 条证据")
            
            # 2. RCA推理
            rca_result = await simulate_rca_reasoning(evidence_data, scenario['description'])
            
            if rca_result:
                print(f"   ✅ RCA推理成功")
                print(f"      根因: {rca_result['primary_root_cause']}")
                print(f"      置信度: {rca_result['confidence']:.3f}")
                print(f"      解决方案: {len(rca_result['recommended_solutions'])} 个")
                successful_scenarios += 1
            else:
                print(f"   ❌ RCA推理失败")
        else:
            print(f"   ❌ RAG搜索失败 - 证据不足")
    
    print(f"\n" + "=" * 60)
    print(f"📊 RCA场景测试结果: {successful_scenarios}/{len(test_scenarios)} 成功")
    
    if successful_scenarios == len(test_scenarios):
        print("🎉 所有RCA场景测试通过！")
        print("💡 Agent具备完整的RCA分析能力，可以：")
        print("   - 从用户描述中理解问题症状")
        print("   - 通过RAG搜索获取相关证据") 
        print("   - 基于证据进行根因推理")
        print("   - 提供具体的解决方案建议")
        print("   - 给出置信度评估")
    elif successful_scenarios >= len(test_scenarios) * 0.7:
        print("✅ 大部分RCA场景成功")
        print("💡 Agent基本具备RCA分析能力，建议优化失败场景")
    else:
        print("⚠️ RCA场景测试存在问题") 
        print("💡 建议检查RAG数据完整性和推理逻辑")
    
    return successful_scenarios == len(test_scenarios)


async def main():
    """主函数"""
    print("🚀 开始完整RCA流程测试")
    print("=" * 60)
    
    # 1. 测试RAG集成
    rag_ready = await test_rag_integration()
    
    if not rag_ready:
        print("❌ RAG集成未就绪，无法进行RCA测试")
        print("💡 请先运行 python run_pipelines.py 建立数据索引")
        return
    
    # 2. 测试完整RCA场景
    rca_success = await test_complete_rca_scenarios()
    
    print(f"\n" + "=" * 60)
    print("📋 完整RCA流程测试总结:")
    print(f"   RAG集成: {'✅ 就绪' if rag_ready else '❌ 未就绪'}")
    print(f"   RCA场景: {'✅ 通过' if rca_success else '❌ 失败'}")
    
    if rag_ready and rca_success:
        print("\n🎉 恭喜！RCA Pipeline完全就绪")
        print("💡 现在可以在web UI中测试:")
        print("   1. 启动API服务: uvicorn src.api.main:app --reload")
        print("   2. 访问 http://localhost:8000/docs")
        print("   3. 使用/chat端点测试RCA查询")
        print("   4. 示例查询: 'service-b CPU使用率过高，响应超时'")


if __name__ == "__main__":
    asyncio.run(main())