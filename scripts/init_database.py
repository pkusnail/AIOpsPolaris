#!/usr/bin/env python3
"""
数据库初始化脚本
创建数据库表结构并导入样本数据
"""

import asyncio
import sys
import os
import json
import logging
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from src.models.database import init_database, Base, engine
from src.services.database_service import DatabaseService
from src.services.vector_service import VectorService  
from src.services.graph_service import GraphService
from src.services.embedding_service import EmbeddingService
from src.services.ner_service import NERService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_mysql_database():
    """初始化MySQL数据库"""
    try:
        logger.info("Initializing MySQL database...")
        await init_database()
        logger.info("MySQL database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize MySQL database: {e}")
        return False


async def init_vector_database():
    """初始化向量数据库"""
    try:
        logger.info("Initializing vector database (Weaviate)...")
        vector_service = VectorService()
        await vector_service.create_schema()
        logger.info("Vector database initialized successfully")
        return vector_service
    except Exception as e:
        logger.error(f"Failed to initialize vector database: {e}")
        return None


async def init_graph_database():
    """初始化图数据库"""
    try:
        logger.info("Initializing graph database (Neo4j)...")
        graph_service = GraphService()
        
        # 验证连接
        if not await graph_service.verify_connection():
            raise Exception("Cannot connect to Neo4j")
        
        # 初始化约束和索引
        await graph_service.initialize_constraints()
        logger.info("Graph database initialized successfully")
        return graph_service
    except Exception as e:
        logger.error(f"Failed to initialize graph database: {e}")
        return None


async def load_sample_data():
    """加载样本数据"""
    try:
        logger.info("Loading sample data...")
        
        # 初始化服务
        db_service = DatabaseService()
        vector_service = VectorService()
        graph_service = GraphService()
        embedding_service = EmbeddingService()
        ner_service = NERService()
        
        # 数据目录
        data_dir = Path(__file__).parent.parent / "data"
        
        # 处理各种数据源
        total_docs = 0
        total_entities = 0
        total_relationships = 0
        
        # 1. 加载Wiki文档
        wiki_file = data_dir / "wiki" / "sample_wiki.json"
        if wiki_file.exists():
            logger.info("Processing wiki documents...")
            with open(wiki_file, 'r', encoding='utf-8') as f:
                wiki_docs = json.load(f)
            
            for doc in wiki_docs:
                # 保存到MySQL
                knowledge_doc = await db_service.save_knowledge_document(
                    title=doc["title"],
                    content=doc["content"],
                    source="wiki",
                    source_id=doc["id"],
                    category=doc.get("category"),
                    tags=doc.get("tags")
                )
                
                # 生成向量并保存到Weaviate
                try:
                    embedding = await embedding_service.encode_knowledge_document(
                        title=doc["title"],
                        content=doc["content"]
                    )
                    
                    weaviate_id = await vector_service.add_knowledge_document(
                        mysql_id=knowledge_doc.id,
                        title=doc["title"],
                        content=doc["content"],
                        source="wiki",
                        source_id=doc["id"],
                        category=doc.get("category"),
                        tags=doc.get("tags"),
                        vector=embedding
                    )
                    
                    # 更新MySQL中的embedding_id
                    knowledge_doc.embedding_id = weaviate_id
                except Exception as e:
                    logger.warning(f"Failed to create embedding for wiki doc {doc['id']}: {e}")
                
                # NER提取实体和关系
                try:
                    ner_result = await ner_service.extract_from_document(
                        title=doc["title"],
                        content=doc["content"],
                        source="wiki"
                    )
                    
                    # 保存实体
                    for entity in ner_result["entities"]:
                        try:
                            # 保存到MySQL
                            db_entity = await db_service.save_entity(
                                name=entity["text"],
                                entity_type=entity["label"],
                                description=f"从Wiki文档'{doc['title']}'中提取",
                                properties={
                                    "confidence": entity["confidence"],
                                    "start": entity["start"],
                                    "end": entity["end"]
                                }
                            )
                            
                            # 创建Neo4j节点
                            neo4j_id = await graph_service.create_entity(
                                name=entity["text"],
                                entity_type=entity["label"],
                                properties={
                                    "confidence": entity["confidence"],
                                    "source": "wiki"
                                },
                                mysql_id=db_entity.id
                            )
                            
                            # 更新MySQL中的neo4j_id
                            db_entity.neo4j_id = neo4j_id
                            total_entities += 1
                            
                        except Exception as e:
                            logger.warning(f"Failed to save entity {entity['text']}: {e}")
                    
                    # 保存关系
                    for relationship in ner_result["relationships"]:
                        try:
                            # 这里简化处理，实际应该查找对应的实体ID
                            source_text = relationship["source_text"]
                            target_text = relationship["target_text"]
                            rel_type = relationship["relationship_type"]
                            
                            # 在Neo4j中创建关系
                            rel_id = await graph_service.create_relationship(
                                source_name=source_text,
                                source_type="Entity",  # 简化处理
                                target_name=target_text,
                                target_type="Entity",
                                relationship_type=rel_type,
                                properties={
                                    "confidence": relationship["confidence"],
                                    "source": "wiki"
                                }
                            )
                            
                            if rel_id > 0:
                                total_relationships += 1
                            
                        except Exception as e:
                            logger.warning(f"Failed to save relationship: {e}")
                
                except Exception as e:
                    logger.warning(f"Failed to extract entities from wiki doc {doc['id']}: {e}")
                
                # 在Neo4j中创建文档节点
                try:
                    doc_neo4j_id = await graph_service.create_document_node(
                        mysql_id=knowledge_doc.id,
                        title=doc["title"],
                        content=doc["content"],
                        source="wiki",
                        category=doc.get("category"),
                        tags=doc.get("tags")
                    )
                except Exception as e:
                    logger.warning(f"Failed to create document node: {e}")
                
                total_docs += 1
                logger.info(f"Processed wiki document: {doc['title']}")
        
        # 2. 加载GitLab数据
        gitlab_file = data_dir / "gitlab" / "sample_gitlab.json"
        if gitlab_file.exists():
            logger.info("Processing GitLab data...")
            with open(gitlab_file, 'r', encoding='utf-8') as f:
                gitlab_docs = json.load(f)
            
            for doc in gitlab_docs:
                # 构造标题和内容
                title = f"GitLab MR: {doc['title']}"
                content = f"""
Merge Request: {doc['title']}
Description: {doc['description']}
Author: {doc['author']}
Branch: {doc['branch']} -> {doc['target_branch']}
Files Changed: {', '.join(doc['files_changed'])}
Changes: +{doc['changes']['additions']} -{doc['changes']['deletions']}
Labels: {', '.join(doc['labels'])}
Status: {doc['status']}
"""
                
                # 保存文档
                knowledge_doc = await db_service.save_knowledge_document(
                    title=title,
                    content=content,
                    source="gitlab",
                    source_id=doc["id"],
                    category="code_change",
                    tags=doc.get("labels")
                )
                
                # 生成向量
                try:
                    embedding = await embedding_service.encode_knowledge_document(title, content)
                    weaviate_id = await vector_service.add_knowledge_document(
                        mysql_id=knowledge_doc.id,
                        title=title,
                        content=content,
                        source="gitlab",
                        source_id=doc["id"],
                        category="code_change",
                        tags=doc.get("labels"),
                        vector=embedding
                    )
                    knowledge_doc.embedding_id = weaviate_id
                except Exception as e:
                    logger.warning(f"Failed to create embedding for gitlab doc {doc['id']}: {e}")
                
                total_docs += 1
                logger.info(f"Processed GitLab MR: {doc['title']}")
        
        # 3. 加载Jira数据
        jira_file = data_dir / "jira" / "sample_jira.json"
        if jira_file.exists():
            logger.info("Processing Jira data...")
            with open(jira_file, 'r', encoding='utf-8') as f:
                jira_docs = json.load(f)
            
            for doc in jira_docs:
                title = f"Jira {doc['type']}: {doc['title']}"
                content = f"""
Issue: {doc['key']} - {doc['title']}
Type: {doc['type']}
Priority: {doc['priority']}
Status: {doc['status']}
Description: {doc['description']}
Assignee: {doc['assignee']}
Reporter: {doc['reporter']}
Components: {', '.join(doc['components'])}
Labels: {', '.join(doc['labels'])}
Resolution: {doc.get('resolution', 'N/A')}
"""
                
                knowledge_doc = await db_service.save_knowledge_document(
                    title=title,
                    content=content,
                    source="jira",
                    source_id=doc["id"],
                    category=doc["type"].lower(),
                    tags=doc.get("labels")
                )
                
                try:
                    embedding = await embedding_service.encode_knowledge_document(title, content)
                    weaviate_id = await vector_service.add_knowledge_document(
                        mysql_id=knowledge_doc.id,
                        title=title,
                        content=content,
                        source="jira",
                        source_id=doc["id"],
                        category=doc["type"].lower(),
                        tags=doc.get("labels"),
                        vector=embedding
                    )
                    knowledge_doc.embedding_id = weaviate_id
                except Exception as e:
                    logger.warning(f"Failed to create embedding for jira doc {doc['id']}: {e}")
                
                total_docs += 1
                logger.info(f"Processed Jira issue: {doc['title']}")
        
        # 4. 处理日志文件
        logs_file = data_dir / "logs" / "sample_logs.txt"
        if logs_file.exists():
            logger.info("Processing log data...")
            with open(logs_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # 将日志作为一个整体文档处理
            title = "System Logs Sample"
            
            knowledge_doc = await db_service.save_knowledge_document(
                title=title,
                content=log_content,
                source="logs",
                source_id="logs_sample",
                category="system_logs",
                tags=["logs", "system", "monitoring"]
            )
            
            try:
                embedding = await embedding_service.encode_knowledge_document(title, log_content)
                weaviate_id = await vector_service.add_knowledge_document(
                    mysql_id=knowledge_doc.id,
                    title=title,
                    content=log_content,
                    source="logs",
                    source_id="logs_sample",
                    category="system_logs",
                    tags=["logs", "system", "monitoring"],
                    vector=embedding
                )
                knowledge_doc.embedding_id = weaviate_id
            except Exception as e:
                logger.warning(f"Failed to create embedding for logs: {e}")
            
            total_docs += 1
            logger.info("Processed system logs")
        
        # 关闭服务
        await graph_service.close()
        vector_service.close()
        embedding_service.close()
        ner_service.close()
        
        logger.info(f"""
Sample data loading completed:
- Total documents: {total_docs}
- Total entities: {total_entities}  
- Total relationships: {total_relationships}
""")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to load sample data: {e}")
        return False


async def main():
    """主函数"""
    logger.info("Starting AIOps database initialization...")
    
    try:
        # 1. 初始化MySQL
        if not await init_mysql_database():
            logger.error("MySQL initialization failed")
            return False
        
        # 2. 初始化Vector DB
        vector_service = await init_vector_database()
        if not vector_service:
            logger.error("Vector database initialization failed")
            return False
        vector_service.close()
        
        # 3. 初始化Graph DB  
        graph_service = await init_graph_database()
        if not graph_service:
            logger.error("Graph database initialization failed")
            return False
        await graph_service.close()
        
        # 4. 加载样本数据
        if not await load_sample_data():
            logger.error("Sample data loading failed")
            return False
        
        logger.info("🎉 Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    # 运行初始化
    success = asyncio.run(main())
    
    if success:
        print("\n✅ 数据库初始化成功！")
        print("现在可以启动API服务和Gradio界面了。")
        sys.exit(0)
    else:
        print("\n❌ 数据库初始化失败！")
        print("请检查数据库连接和配置。")
        sys.exit(1)