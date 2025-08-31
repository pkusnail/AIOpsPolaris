"""
简化的Pipeline运行脚本
避免复杂的导入依赖问题
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


async def setup_rag_collections():
    """建立RAG Collections"""
    print("🔧 建立RAG Collections...")
    try:
        import weaviate
        
        client = weaviate.Client(url="http://localhost:8080")
        
        # 删除现有collections
        existing_collections = ["EmbeddingCollection", "FullTextCollection"]
        for collection_name in existing_collections:
            try:
                client.schema.delete_class(collection_name)
                print(f"   删除现有collection: {collection_name}")
            except:
                pass
        
        # 创建EmbeddingCollection
        embedding_schema = {
            "class": "EmbeddingCollection",
            "description": "存储向量嵌入的集合，支持语义搜索",
            "vectorizer": "none",
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "文档内容"
                },
                {
                    "name": "source_type",
                    "dataType": ["string"],
                    "description": "数据源类型"
                },
                {
                    "name": "service_name",
                    "dataType": ["string"],
                    "description": "服务名称"
                },
                {
                    "name": "hostname",
                    "dataType": ["string"],
                    "description": "主机名"
                },
                {
                    "name": "timestamp",
                    "dataType": ["string"],
                    "description": "时间戳"
                },
                {
                    "name": "log_file",
                    "dataType": ["string"],
                    "description": "日志文件名"
                },
                {
                    "name": "line_number",
                    "dataType": ["int"],
                    "description": "行号"
                },
                {
                    "name": "keywords",
                    "dataType": ["string[]"],
                    "description": "关键词"
                }
            ]
        }
        
        client.schema.create_class(embedding_schema)
        print("✅ EmbeddingCollection创建完成")
        
        # 创建FullTextCollection
        fulltext_schema = {
            "class": "FullTextCollection",
            "description": "存储全文索引的集合，支持BM25搜索",
            "vectorizer": "none",
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "文档内容",
                    "indexFilterable": True,
                    "indexSearchable": True
                },
                {
                    "name": "source_type",
                    "dataType": ["string"],
                    "description": "数据源类型",
                    "indexFilterable": True
                },
                {
                    "name": "service_name",
                    "dataType": ["string"],
                    "description": "服务名称",
                    "indexFilterable": True
                },
                {
                    "name": "hostname",
                    "dataType": ["string"],
                    "description": "主机名",
                    "indexFilterable": True
                },
                {
                    "name": "timestamp",
                    "dataType": ["string"],
                    "description": "时间戳",
                    "indexFilterable": True
                },
                {
                    "name": "log_file",
                    "dataType": ["string"],
                    "description": "日志文件名",
                    "indexFilterable": True
                },
                {
                    "name": "line_number",
                    "dataType": ["int"],
                    "description": "行号",
                    "indexFilterable": True
                },
                {
                    "name": "keywords",
                    "dataType": ["string[]"],
                    "description": "关键词",
                    "indexFilterable": True
                }
            ]
        }
        
        client.schema.create_class(fulltext_schema)
        print("✅ FullTextCollection创建完成")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG Collections创建失败: {e}")
        return False


async def process_log_files():
    """处理日志文件"""
    print("\n📋 处理日志文件...")
    try:
        import weaviate
        import re
        from sentence_transformers import SentenceTransformer
        
        client = weaviate.Client(url="http://localhost:8080")
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        logs_dir = Path("./data/logs/")
        if not logs_dir.exists():
            print("❌ 日志目录不存在")
            return False
        
        # 日志解析模式
        log_pattern = re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\s+'
            r'\[(?P<level>\w+)\]\s+'
            r'(?P<service>[\w-]+):\s+'
            r'(?P<message>.*)'
        )
        
        processed_count = 0
        
        for log_file in logs_dir.glob("*.log"):
            print(f"   处理文件: {log_file.name}")
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                if line.strip() and not line.startswith('#'):
                    match = log_pattern.match(line.strip())
                    
                    if match:
                        groups = match.groupdict()
                        content = f"[{groups['level']}] {groups['service']}: {groups['message']}"
                        
                        # 提取关键词
                        keywords = []
                        if 'CPU' in groups['message']:
                            keywords.append('CPU')
                        if 'error' in groups['message'].lower():
                            keywords.append('error')
                        if 'timeout' in groups['message'].lower():
                            keywords.append('timeout')
                        if groups['service']:
                            keywords.append(groups['service'])
                        
                        # 生成向量
                        vector = model.encode(content).tolist()
                        
                        # 数据对象
                        data_obj = {
                            "content": content,
                            "source_type": "logs",
                            "service_name": groups['service'],
                            "hostname": "unknown",
                            "timestamp": groups['timestamp'],
                            "log_file": log_file.name,
                            "line_number": line_num,
                            "keywords": keywords
                        }
                        
                        # 添加到EmbeddingCollection
                        client.data_object.create(
                            data_object=data_obj,
                            class_name="EmbeddingCollection",
                            vector=vector
                        )
                        
                        # 添加到FullTextCollection
                        client.data_object.create(
                            data_object=data_obj,
                            class_name="FullTextCollection"
                        )
                        
                        processed_count += 1
        
        print(f"✅ 处理完成: {processed_count} 条日志记录")
        return processed_count > 0
        
    except Exception as e:
        print(f"❌ 日志文件处理失败: {e}")
        return False


async def process_knowledge_files():
    """处理知识文件"""
    print("\n📚 处理知识文件...")
    try:
        import weaviate
        from sentence_transformers import SentenceTransformer
        
        client = weaviate.Client(url="http://localhost:8080")
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        processed_count = 0
        
        # 处理Wiki数据
        wiki_file = Path("./data/wiki/sample_wiki.json")
        if wiki_file.exists():
            with open(wiki_file, 'r', encoding='utf-8') as f:
                wiki_data = json.load(f)
            
            print(f"   处理Wiki数据: {len(wiki_data)} 个文档")
            
            for doc in wiki_data:
                content = f"{doc.get('title', '')}: {doc.get('content', '')}"
                
                if len(content) > 50:  # 只处理有意义的内容
                    # 生成向量
                    vector = model.encode(content).tolist()
                    
                    # 提取关键词
                    keywords = []
                    content_lower = content.lower()
                    if 'service' in content_lower:
                        keywords.append('service')
                    if 'kubernetes' in content_lower:
                        keywords.append('kubernetes')
                    if 'cpu' in content_lower:
                        keywords.append('cpu')
                    if 'memory' in content_lower:
                        keywords.append('memory')
                    
                    data_obj = {
                        "content": content,
                        "source_type": "wiki",
                        "service_name": "documentation",
                        "hostname": "wiki",
                        "timestamp": datetime.now().isoformat() + "Z",
                        "log_file": "wiki",
                        "line_number": 0,
                        "keywords": keywords
                    }
                    
                    # 添加到collections
                    client.data_object.create(
                        data_object=data_obj,
                        class_name="EmbeddingCollection",
                        vector=vector
                    )
                    
                    client.data_object.create(
                        data_object=data_obj,
                        class_name="FullTextCollection"
                    )
                    
                    processed_count += 1
        
        # 处理GitLab数据
        gitlab_file = Path("./data/gitlab/sample_gitlab.json")
        if gitlab_file.exists():
            with open(gitlab_file, 'r', encoding='utf-8') as f:
                gitlab_data = json.load(f)
            
            print(f"   处理GitLab数据: {len(gitlab_data)} 个项目")
            
            for project in gitlab_data:
                content = f"Project: {project.get('name', '')}, Description: {project.get('description', '')}"
                
                if len(content) > 50:
                    vector = model.encode(content).tolist()
                    
                    keywords = ['gitlab', 'project']
                    if project.get('name'):
                        keywords.append(project['name'])
                    
                    data_obj = {
                        "content": content,
                        "source_type": "gitlab",
                        "service_name": project.get('name', 'unknown'),
                        "hostname": "gitlab",
                        "timestamp": datetime.now().isoformat() + "Z",
                        "log_file": "gitlab",
                        "line_number": 0,
                        "keywords": keywords
                    }
                    
                    client.data_object.create(
                        data_object=data_obj,
                        class_name="EmbeddingCollection",
                        vector=vector
                    )
                    
                    client.data_object.create(
                        data_object=data_obj,
                        class_name="FullTextCollection"
                    )
                    
                    processed_count += 1
        
        # 处理Jira数据
        jira_file = Path("./data/jira/sample_jira.json")
        if jira_file.exists():
            with open(jira_file, 'r', encoding='utf-8') as f:
                jira_data = json.load(f)
            
            print(f"   处理Jira数据: {len(jira_data)} 个工单")
            
            for issue in jira_data:
                content = f"Issue: {issue.get('summary', '')}, Description: {issue.get('description', '')}"
                
                if len(content) > 50:
                    vector = model.encode(content).tolist()
                    
                    keywords = ['jira', 'issue']
                    if issue.get('summary'):
                        keywords.append('bug' if 'bug' in issue['summary'].lower() else 'task')
                    
                    data_obj = {
                        "content": content,
                        "source_type": "jira",
                        "service_name": issue.get('project', 'unknown'),
                        "hostname": "jira",
                        "timestamp": datetime.now().isoformat() + "Z",
                        "log_file": "jira",
                        "line_number": 0,
                        "keywords": keywords
                    }
                    
                    client.data_object.create(
                        data_object=data_obj,
                        class_name="EmbeddingCollection",
                        vector=vector
                    )
                    
                    client.data_object.create(
                        data_object=data_obj,
                        class_name="FullTextCollection"
                    )
                    
                    processed_count += 1
        
        print(f"✅ 知识文件处理完成: {processed_count} 条记录")
        return processed_count > 0
        
    except Exception as e:
        print(f"❌ 知识文件处理失败: {e}")
        return False


async def setup_knowledge_graph():
    """建立知识图谱"""
    print("\n🕸️ 建立知识图谱...")
    try:
        from neo4j import GraphDatabase
        
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "aiops123")
        )
        
        # 创建基础实体
        with driver.session() as session:
            # 创建服务节点
            services = ["service-a", "service-b", "service-c", "database", "redis"]
            
            for service in services:
                session.run(
                    "MERGE (s:Service {name: $name})",
                    name=service
                )
            
            # 创建主机节点
            hosts = ["host-1", "host-2", "d1"]
            
            for host in hosts:
                session.run(
                    "MERGE (h:Host {name: $name})",
                    name=host
                )
            
            # 创建问题节点
            issues = [
                {"name": "CPU overload", "type": "performance", "service": "service-b"},
                {"name": "Memory leak", "type": "memory", "service": "service-a"},
                {"name": "Disk IO bottleneck", "type": "disk", "service": "database"}
            ]
            
            for issue in issues:
                session.run(
                    """
                    MERGE (i:Issue {name: $name, type: $type})
                    MERGE (s:Service {name: $service})
                    MERGE (i)-[:AFFECTS]->(s)
                    """,
                    name=issue["name"],
                    type=issue["type"],
                    service=issue["service"]
                )
            
            # 创建依赖关系
            dependencies = [
                ("service-a", "database"),
                ("service-b", "database"),
                ("service-b", "redis"),
                ("service-c", "service-a")
            ]
            
            for from_service, to_service in dependencies:
                session.run(
                    """
                    MERGE (from:Service {name: $from_service})
                    MERGE (to:Service {name: $to_service})
                    MERGE (from)-[:DEPENDS_ON]->(to)
                    """,
                    from_service=from_service,
                    to_service=to_service
                )
            
            # 创建部署关系
            deployments = [
                ("service-a", "host-1"),
                ("service-b", "host-2"),
                ("database", "d1"),
                ("redis", "host-1")
            ]
            
            for service, host in deployments:
                session.run(
                    """
                    MERGE (s:Service {name: $service})
                    MERGE (h:Host {name: $host})
                    MERGE (s)-[:DEPLOYED_ON]->(h)
                    """,
                    service=service,
                    host=host
                )
        
        # 统计创建的节点和关系
        with driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            print(f"✅ 知识图谱创建完成:")
            print(f"   节点数: {node_count}")
            print(f"   关系数: {rel_count}")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ 知识图谱创建失败: {e}")
        return False


async def main():
    """主函数"""
    print("🚀 开始运行RAG Pipelines")
    print("=" * 50)
    
    success_count = 0
    total_steps = 4
    
    # 1. 建立RAG Collections
    if await setup_rag_collections():
        success_count += 1
    
    # 2. 处理日志文件
    if await process_log_files():
        success_count += 1
    
    # 3. 处理知识文件
    if await process_knowledge_files():
        success_count += 1
    
    # 4. 建立知识图谱
    if await setup_knowledge_graph():
        success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Pipeline运行结果: {success_count}/{total_steps} 步骤成功")
    
    if success_count == total_steps:
        print("🎉 所有Pipelines运行成功!")
        print("💡 现在可以运行agent测试验证RAG功能")
    elif success_count >= total_steps * 0.7:
        print("✅ 大部分步骤成功")
        print("💡 建议检查失败的步骤")
    else:
        print("⚠️ 多个步骤失败")
        print("💡 建议检查服务状态和数据完整性")


if __name__ == "__main__":
    asyncio.run(main())