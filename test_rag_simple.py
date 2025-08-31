"""
简化的RAG Pipeline测试
直接测试核心功能，避免复杂的导入依赖
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


async def test_weaviate_connection():
    """测试Weaviate连接"""
    print("\n=== 测试Weaviate连接 ===")
    try:
        import weaviate
        
        client = weaviate.Client(
            url="http://localhost:8080",
            timeout_config=(5, 60)
        )
        
        # 检查连接
        result = client.cluster.get_nodes_status()
        print("✅ Weaviate连接成功")
        print(f"   节点状态: {len(result)} 个节点")
        
        # 检查现有schema
        schema = client.schema.get()
        class_names = [cls['class'] for cls in schema.get('classes', [])]
        print(f"   现有Collections: {class_names}")
        
        return True
        
    except Exception as e:
        print(f"❌ Weaviate连接失败: {e}")
        return False


async def test_embedding_service():
    """测试嵌入服务"""
    print("\n=== 测试嵌入服务 ===")
    try:
        from sentence_transformers import SentenceTransformer
        
        # 加载模型
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # 测试编码
        test_texts = [
            "service-b CPU使用率过高",
            "数据库连接超时问题", 
            "Kubernetes Pod重启循环"
        ]
        
        embeddings = model.encode(test_texts)
        print(f"✅ 嵌入服务正常")
        print(f"   向量维度: {embeddings.shape[1]}")
        print(f"   测试文本数: {embeddings.shape[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 嵌入服务失败: {e}")
        return False


async def test_neo4j_connection():
    """测试Neo4j连接"""
    print("\n=== 测试Neo4j连接 ===")
    try:
        from neo4j import GraphDatabase
        
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "aiops123")
        )
        
        # 测试连接
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            assert record["test"] == 1
        
        print("✅ Neo4j连接成功")
        
        # 检查现有数据
        with driver.session() as session:
            node_count_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = node_count_result.single()["count"]
            
            rel_count_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_count_result.single()["count"]
        
        print(f"   现有节点: {node_count} 个")
        print(f"   现有关系: {rel_count} 个")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Neo4j连接失败: {e}")
        return False


async def test_data_availability():
    """测试数据可用性"""
    print("\n=== 测试数据可用性 ===")
    try:
        data_stats = {}
        
        # 检查各数据目录
        data_dirs = {
            'logs': './data/logs/',
            'wiki': './data/wiki/',
            'gitlab': './data/gitlab/',
            'jira': './data/jira/'
        }
        
        for name, path in data_dirs.items():
            dir_path = Path(path)
            if dir_path.exists():
                files = list(dir_path.glob("*.*"))
                data_stats[name] = len(files)
                print(f"✅ {name}: {len(files)} 个文件")
                
                # 显示文件列表
                for file in files[:3]:
                    print(f"   - {file.name}")
                if len(files) > 3:
                    print(f"   - ... 还有 {len(files) - 3} 个文件")
            else:
                data_stats[name] = 0
                print(f"❌ {name}: 目录不存在")
        
        total_files = sum(data_stats.values())
        print(f"\n📊 总数据文件: {total_files} 个")
        
        return total_files > 0
        
    except Exception as e:
        print(f"❌ 数据可用性检查失败: {e}")
        return False


async def test_basic_rag_workflow():
    """测试基本RAG工作流"""
    print("\n=== 测试基本RAG工作流 ===")
    try:
        import weaviate
        from sentence_transformers import SentenceTransformer
        
        # 1. 连接Weaviate
        client = weaviate.Client(url="http://localhost:8080")
        
        # 2. 创建简化schema
        try:
            client.schema.delete_class("TestCollection")
        except:
            pass
        
        test_schema = {
            "class": "TestCollection",
            "description": "测试Collection",
            "vectorizer": "none",
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "内容"
                },
                {
                    "name": "source_type",
                    "dataType": ["string"],
                    "description": "数据源类型"
                }
            ]
        }
        
        client.schema.create_class(test_schema)
        print("✅ 测试schema创建成功")
        
        # 3. 添加测试数据
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        test_docs = [
            "service-b CPU使用率达到95%，请求响应超时",
            "数据库连接池耗尽，MySQL响应缓慢",
            "Kubernetes Pod不断重启，镜像拉取失败",
            "Redis内存使用率过高，缓存命中率下降"
        ]
        
        for i, doc in enumerate(test_docs):
            vector = model.encode(doc).tolist()
            
            client.data_object.create(
                data_object={
                    "content": doc,
                    "source_type": "logs"
                },
                class_name="TestCollection",
                vector=vector
            )
        
        print(f"✅ 添加测试数据: {len(test_docs)} 条")
        
        # 4. 测试搜索
        query = "CPU性能问题"
        query_vector = model.encode(query).tolist()
        
        # 向量搜索
        vector_result = (
            client.query
            .get("TestCollection", ["content", "source_type"])
            .with_near_vector({"vector": query_vector, "certainty": 0.5})
            .with_limit(3)
            .with_additional(["certainty"])
            .do()
        )
        
        vector_results = vector_result["data"]["Get"]["TestCollection"]
        print(f"✅ 向量搜索: 找到 {len(vector_results)} 条结果")
        
        if vector_results:
            top_result = vector_results[0]
            certainty = top_result["_additional"]["certainty"]
            content = top_result["content"][:50]
            print(f"   最佳匹配: {certainty:.3f} - {content}...")
        
        # BM25搜索
        bm25_result = (
            client.query
            .get("TestCollection", ["content", "source_type"])
            .with_bm25(query=query)
            .with_limit(3)
            .with_additional(["score"])
            .do()
        )
        
        bm25_results = bm25_result["data"]["Get"]["TestCollection"]
        print(f"✅ BM25搜索: 找到 {len(bm25_results)} 条结果")
        
        # 混合搜索
        hybrid_result = (
            client.query
            .get("TestCollection", ["content", "source_type"])
            .with_hybrid(query=query, vector=query_vector, alpha=0.7)
            .with_limit(3)
            .with_additional(["score"])
            .do()
        )
        
        hybrid_results = hybrid_result["data"]["Get"]["TestCollection"]
        print(f"✅ 混合搜索: 找到 {len(hybrid_results)} 条结果")
        
        # 清理测试数据
        client.schema.delete_class("TestCollection")
        print("✅ 清理测试数据完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 基本RAG工作流测试失败: {e}")
        return False


async def test_log_parsing():
    """测试日志解析功能"""
    print("\n=== 测试日志解析 ===")
    try:
        # 读取示例日志
        log_file = Path("./data/logs/incident_001_service_b_cpu_overload.log")
        if not log_file.exists():
            print("❌ 示例日志文件不存在")
            return False
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:10]  # 只读前10行进行测试
        
        print(f"📄 读取日志文件: {log_file.name}")
        print(f"   总行数: {len(lines)}")
        
        # 简单的日志解析
        import re
        
        log_pattern = re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\s+'
            r'\[(?P<level>\w+)\]\s+'
            r'(?P<service>[\w-]+):\s+'
            r'(?P<message>.*)'
        )
        
        parsed_count = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#'):
                match = log_pattern.match(line.strip())
                if match:
                    parsed_count += 1
                    if i < 3:  # 显示前3个解析结果
                        groups = match.groupdict()
                        print(f"   解析行 {i+1}: {groups['service']} [{groups['level']}] {groups['message'][:40]}...")
        
        print(f"✅ 成功解析: {parsed_count}/{len([l for l in lines if l.strip() and not l.startswith('#')])} 行")
        
        return parsed_count > 0
        
    except Exception as e:
        print(f"❌ 日志解析测试失败: {e}")
        return False


async def test_knowledge_data():
    """测试知识数据"""
    print("\n=== 测试知识数据 ===")
    try:
        # 测试Wiki数据
        wiki_file = Path("./data/wiki/sample_wiki.json")
        if wiki_file.exists():
            with open(wiki_file, 'r', encoding='utf-8') as f:
                wiki_data = json.load(f)
            
            print(f"✅ Wiki数据: {len(wiki_data)} 个文档")
            for doc in wiki_data[:2]:
                print(f"   - {doc.get('title', '')[:50]}...")
        
        # 测试GitLab数据
        gitlab_file = Path("./data/gitlab/sample_gitlab.json")
        if gitlab_file.exists():
            with open(gitlab_file, 'r', encoding='utf-8') as f:
                gitlab_data = json.load(f)
            
            print(f"✅ GitLab数据: {len(gitlab_data)} 个项目")
        
        # 测试Jira数据
        jira_file = Path("./data/jira/sample_jira.json")
        if jira_file.exists():
            with open(jira_file, 'r', encoding='utf-8') as f:
                jira_data = json.load(f)
            
            print(f"✅ Jira数据: {len(jira_data)} 个工单")
        
        return True
        
    except Exception as e:
        print(f"❌ 知识数据测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始RAG Pipeline简化测试")
    print("=" * 50)
    
    test_results = []
    
    # 1. 测试数据可用性
    data_ok = await test_data_availability()
    test_results.append(("数据可用性", data_ok))
    
    # 2. 测试Weaviate连接
    weaviate_ok = await test_weaviate_connection()
    test_results.append(("Weaviate连接", weaviate_ok))
    
    # 3. 测试Neo4j连接  
    neo4j_ok = await test_neo4j_connection()
    test_results.append(("Neo4j连接", neo4j_ok))
    
    # 4. 测试嵌入服务
    embedding_ok = await test_embedding_service()
    test_results.append(("嵌入服务", embedding_ok))
    
    # 5. 测试日志解析
    log_parsing_ok = await test_log_parsing()
    test_results.append(("日志解析", log_parsing_ok))
    
    # 6. 测试知识数据
    knowledge_ok = await test_knowledge_data()
    test_results.append(("知识数据", knowledge_ok))
    
    # 7. 测试基本RAG工作流
    if weaviate_ok and embedding_ok:
        rag_workflow_ok = await test_basic_rag_workflow()
        test_results.append(("RAG工作流", rag_workflow_ok))
    
    # 显示结果
    print("\n" + "=" * 50)
    print("📋 测试结果总结:")
    print("=" * 50)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<15} {status}")
    
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    print(f"\n📊 总体结果: {passed_tests}/{total_tests} 测试通过")
    
    # 给出建议
    if passed_tests == total_tests:
        print("🎉 所有基础组件工作正常！")
        print("💡 建议: 现在可以运行完整的pipeline")
        print("   python -m src.services.log_pipeline")
        print("   python -m src.services.knowledge_pipeline")
    elif passed_tests >= total_tests * 0.7:
        print("✅ 大部分组件工作正常")
        print("💡 建议: 检查失败的组件并修复")
    else:
        print("⚠️ 多个组件存在问题")
        print("💡 建议: 检查Docker服务状态")
        print("   docker-compose ps")


if __name__ == "__main__":
    asyncio.run(main())