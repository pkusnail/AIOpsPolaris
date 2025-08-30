"""
知识图谱服务
基于Neo4j实现图数据库操作
"""

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import Neo4jError
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import json

from config.settings import settings

logger = logging.getLogger(__name__)


class GraphService:
    """知识图谱服务类"""
    
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_driver()
    
    def _initialize_driver(self):
        """初始化Neo4j驱动"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j.uri,
                auth=(settings.neo4j.user, settings.neo4j.password),
                max_connection_lifetime=settings.neo4j.max_connection_lifetime,
                max_connection_pool_size=settings.neo4j.max_connection_pool_size,
                connection_acquisition_timeout=settings.neo4j.connection_acquisition_timeout
            )
            self.logger.info(f"Connected to Neo4j at {settings.neo4j.uri}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def verify_connection(self) -> bool:
        """验证连接"""
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
                return True
        except Exception as e:
            self.logger.error(f"Connection verification failed: {e}")
            return False
    
    async def initialize_constraints(self):
        """初始化约束和索引"""
        constraints = [
            "CREATE CONSTRAINT entity_name_type IF NOT EXISTS FOR (e:Entity) REQUIRE (e.name, e.type) IS UNIQUE",
            "CREATE CONSTRAINT service_name IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT component_name IF NOT EXISTS FOR (c:Component) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT error_code IF NOT EXISTS FOR (e:Error) REQUIRE e.code IS UNIQUE",
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.mysql_id IS UNIQUE"
        ]
        
        indexes = [
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_created_at IF NOT EXISTS FOR (e:Entity) ON (e.created_at)",
            "CREATE INDEX relationship_type IF NOT EXISTS FOR ()-[r:RELATES_TO]-() ON (r.type)",
            "CREATE INDEX document_source IF NOT EXISTS FOR (d:Document) ON (d.source)"
        ]
        
        try:
            async with self.driver.session() as session:
                for constraint in constraints:
                    try:
                        await session.run(constraint)
                    except Neo4jError as e:
                        if "already exists" not in str(e):
                            self.logger.warning(f"Constraint creation warning: {e}")
                
                for index in indexes:
                    try:
                        await session.run(index)
                    except Neo4jError as e:
                        if "already exists" not in str(e):
                            self.logger.warning(f"Index creation warning: {e}")
            
            self.logger.info("Constraints and indexes initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize constraints: {e}")
            raise
    
    async def create_entity(
        self,
        name: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None,
        mysql_id: Optional[str] = None
    ) -> int:
        """创建实体节点"""
        try:
            entity_props = {
                "name": name,
                "type": entity_type,
                "created_at": datetime.utcnow().isoformat()
            }
            
            if mysql_id:
                entity_props["mysql_id"] = mysql_id
            
            if properties:
                entity_props.update(properties)
            
            query = """
            MERGE (e:Entity {name: $name, type: $type})
            ON CREATE SET e += $props, e.created_at = $created_at
            ON MATCH SET e += $props, e.updated_at = $updated_at
            RETURN id(e) as node_id
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, {
                    "name": name,
                    "type": entity_type,
                    "props": entity_props,
                    "created_at": entity_props["created_at"],
                    "updated_at": datetime.utcnow().isoformat()
                })
                
                record = await result.single()
                node_id = record["node_id"]
                
                self.logger.info(f"Created/updated entity: {name} ({entity_type}) with ID: {node_id}")
                return node_id
                
        except Exception as e:
            self.logger.error(f"Failed to create entity: {e}")
            raise
    
    async def create_relationship(
        self,
        source_name: str,
        source_type: str,
        target_name: str,
        target_type: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0
    ) -> int:
        """创建关系"""
        try:
            rel_props = {
                "type": relationship_type,
                "confidence": confidence,
                "created_at": datetime.utcnow().isoformat()
            }
            
            if properties:
                rel_props.update(properties)
            
            query = f"""
            MATCH (source:Entity {{name: $source_name, type: $source_type}})
            MATCH (target:Entity {{name: $target_name, type: $target_type}})
            MERGE (source)-[r:RELATES_TO]->(target)
            ON CREATE SET r += $props
            ON MATCH SET r += $props, r.updated_at = $updated_at
            RETURN id(r) as rel_id
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, {
                    "source_name": source_name,
                    "source_type": source_type,
                    "target_name": target_name,
                    "target_type": target_type,
                    "props": rel_props,
                    "updated_at": datetime.utcnow().isoformat()
                })
                
                record = await result.single()
                if record:
                    rel_id = record["rel_id"]
                    self.logger.info(f"Created/updated relationship: {source_name} -> {target_name} ({relationship_type})")
                    return rel_id
                else:
                    self.logger.warning(f"Failed to create relationship: entities not found")
                    return -1
                    
        except Exception as e:
            self.logger.error(f"Failed to create relationship: {e}")
            raise
    
    async def find_entities(
        self,
        entity_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """查找实体"""
        try:
            query_parts = ["MATCH (e:Entity)"]
            params = {"limit": limit}
            
            conditions = []
            if entity_type:
                conditions.append("e.type = $entity_type")
                params["entity_type"] = entity_type
            
            if properties:
                for key, value in properties.items():
                    param_name = f"prop_{key}"
                    conditions.append(f"e.{key} = ${param_name}")
                    params[param_name] = value
            
            if conditions:
                query_parts.append("WHERE " + " AND ".join(conditions))
            
            query_parts.append("RETURN e, id(e) as node_id LIMIT $limit")
            query = " ".join(query_parts)
            
            async with self.driver.session() as session:
                result = await session.run(query, params)
                
                entities = []
                async for record in result:
                    entity_data = dict(record["e"])
                    entity_data["node_id"] = record["node_id"]
                    entities.append(entity_data)
                
                return entities
                
        except Exception as e:
            self.logger.error(f"Failed to find entities: {e}")
            return []
    
    async def find_related_entities(
        self,
        entity_name: str,
        entity_type: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """查找相关实体"""
        try:
            if relationship_types:
                rel_filter = "|".join([f":{rt}" for rt in relationship_types])
                rel_pattern = f"[r{rel_filter}*1..{max_depth}]"
            else:
                rel_pattern = f"[*1..{max_depth}]"
            
            query = f"""
            MATCH (start:Entity {{name: $entity_name, type: $entity_type}})
            MATCH path = (start)-{rel_pattern}-(related:Entity)
            WHERE related <> start
            RETURN DISTINCT related, id(related) as node_id, length(path) as distance
            ORDER BY distance, related.name
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, {
                    "entity_name": entity_name,
                    "entity_type": entity_type
                })
                
                related_entities = []
                async for record in result:
                    entity_data = dict(record["related"])
                    entity_data["node_id"] = record["node_id"]
                    entity_data["distance"] = record["distance"]
                    related_entities.append(entity_data)
                
                return related_entities
                
        except Exception as e:
            self.logger.error(f"Failed to find related entities: {e}")
            return []
    
    async def find_shortest_path(
        self,
        source_name: str,
        source_type: str,
        target_name: str,
        target_type: str,
        max_length: int = 5
    ) -> Optional[Dict[str, Any]]:
        """查找两个实体间的最短路径"""
        try:
            query = """
            MATCH (source:Entity {name: $source_name, type: $source_type})
            MATCH (target:Entity {name: $target_name, type: $target_type})
            MATCH path = shortestPath((source)-[*1..{}]-(target))
            RETURN path, length(path) as path_length
            """.format(max_length)
            
            async with self.driver.session() as session:
                result = await session.run(query, {
                    "source_name": source_name,
                    "source_type": source_type,
                    "target_name": target_name,
                    "target_type": target_type
                })
                
                record = await result.single()
                if record:
                    path = record["path"]
                    path_length = record["path_length"]
                    
                    # 解析路径
                    nodes = []
                    relationships = []
                    
                    for i, node in enumerate(path.nodes):
                        node_data = dict(node)
                        node_data["node_id"] = node.id
                        nodes.append(node_data)
                    
                    for i, rel in enumerate(path.relationships):
                        rel_data = dict(rel)
                        rel_data["rel_id"] = rel.id
                        rel_data["start_node_id"] = rel.start_node.id
                        rel_data["end_node_id"] = rel.end_node.id
                        relationships.append(rel_data)
                    
                    return {
                        "nodes": nodes,
                        "relationships": relationships,
                        "path_length": path_length
                    }
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to find shortest path: {e}")
            return None
    
    async def execute_cypher(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """执行自定义Cypher查询"""
        try:
            async with self.driver.session() as session:
                result = await session.run(query, parameters or {})
                
                records = []
                async for record in result:
                    records.append(dict(record))
                
                return records
                
        except Exception as e:
            self.logger.error(f"Failed to execute Cypher query: {e}")
            raise
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """获取图数据库统计信息"""
        try:
            queries = {
                "node_count": "MATCH (n) RETURN count(n) as count",
                "relationship_count": "MATCH ()-[r]->() RETURN count(r) as count",
                "entity_types": """
                    MATCH (e:Entity) 
                    RETURN e.type as entity_type, count(e) as count 
                    ORDER BY count DESC
                """,
                "relationship_types": """
                    MATCH ()-[r:RELATES_TO]->() 
                    RETURN r.type as relationship_type, count(r) as count 
                    ORDER BY count DESC
                """
            }
            
            stats = {}
            
            async with self.driver.session() as session:
                # 获取节点和关系总数
                for key, query in queries.items():
                    result = await session.run(query)
                    
                    if key in ["node_count", "relationship_count"]:
                        record = await result.single()
                        stats[key] = record["count"] if record else 0
                    else:
                        records = []
                        async for record in result:
                            records.append(dict(record))
                        stats[key] = records
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get graph stats: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def create_document_node(
        self,
        mysql_id: str,
        title: str,
        content: str,
        source: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> int:
        """创建文档节点"""
        try:
            doc_props = {
                "mysql_id": mysql_id,
                "title": title,
                "content": content[:1000],  # 限制内容长度
                "source": source,
                "created_at": datetime.utcnow().isoformat()
            }
            
            if category:
                doc_props["category"] = category
            if tags:
                doc_props["tags"] = tags
            
            query = """
            MERGE (d:Document {mysql_id: $mysql_id})
            ON CREATE SET d += $props
            ON MATCH SET d += $props, d.updated_at = $updated_at
            RETURN id(d) as node_id
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, {
                    "mysql_id": mysql_id,
                    "props": doc_props,
                    "updated_at": datetime.utcnow().isoformat()
                })
                
                record = await result.single()
                node_id = record["node_id"]
                
                self.logger.info(f"Created/updated document node: {title} with ID: {node_id}")
                return node_id
                
        except Exception as e:
            self.logger.error(f"Failed to create document node: {e}")
            raise
    
    async def link_document_entities(
        self,
        doc_mysql_id: str,
        entity_names: List[str]
    ):
        """将文档与实体关联"""
        try:
            query = """
            MATCH (d:Document {mysql_id: $doc_id})
            UNWIND $entity_names as entity_name
            MATCH (e:Entity {name: entity_name})
            MERGE (d)-[r:MENTIONS]->(e)
            ON CREATE SET r.created_at = $created_at
            RETURN count(r) as linked_count
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, {
                    "doc_id": doc_mysql_id,
                    "entity_names": entity_names,
                    "created_at": datetime.utcnow().isoformat()
                })
                
                record = await result.single()
                linked_count = record["linked_count"] if record else 0
                
                self.logger.info(f"Linked document {doc_mysql_id} with {linked_count} entities")
                
        except Exception as e:
            self.logger.error(f"Failed to link document entities: {e}")
    
    async def close(self):
        """关闭连接"""
        if self.driver:
            await self.driver.close()
            self.logger.info("Neo4j driver closed")