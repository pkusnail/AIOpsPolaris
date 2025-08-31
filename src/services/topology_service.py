"""
拓扑查询服务
查询Neo4j中的服务依赖关系和上下游拓扑
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from config.settings import settings


class TopologyService:
    """服务拓扑查询服务"""
    
    def __init__(self):
        self.driver = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_driver()
        
    def _initialize_driver(self):
        """初始化Neo4j驱动"""
        try:
            neo4j_config = settings.get_neo4j_config()
            self.driver = GraphDatabase.driver(
                neo4j_config["uri"],
                auth=neo4j_config["auth"],
                max_connection_lifetime=neo4j_config["max_connection_lifetime"],
                max_connection_pool_size=neo4j_config["max_connection_pool_size"],
                connection_acquisition_timeout=neo4j_config["connection_acquisition_timeout"]
            )
            self.logger.info("Neo4j拓扑服务初始化成功")
            
        except Exception as e:
            self.logger.error(f"Neo4j拓扑服务初始化失败: {e}")
            
    async def get_service_topology(self, service_names: List[str]) -> Dict[str, Any]:
        """获取服务的完整拓扑关系"""
        if not self.driver or not service_names:
            return {"services": [], "relationships": []}
            
        try:
            with self.driver.session() as session:
                # 查询指定服务及其直接相关的上下游服务
                query = """
                MATCH (s:Service)
                WHERE s.name IN $service_names OR s.service_id IN $service_names
                
                OPTIONAL MATCH (s)-[r1]->(target:Service)
                OPTIONAL MATCH (source:Service)-[r2]->(s)
                
                RETURN 
                    s.name as service_name,
                    s.service_id as service_id,
                    s.host as host,
                    s.datacenter as datacenter,
                    s.status as status,
                    
                    collect(DISTINCT {
                        from_service: s.name,
                        to_service: target.name,
                        relation: type(r1),
                        relation_data: properties(r1)
                    }) as outgoing_relations,
                    
                    collect(DISTINCT {
                        from_service: source.name, 
                        to_service: s.name,
                        relation: type(r2),
                        relation_data: properties(r2)
                    }) as incoming_relations
                """
                
                result = session.run(query, service_names=service_names)
                
                services = []
                all_relationships = []
                
                for record in result:
                    # 服务信息
                    service_info = {
                        "name": record["service_name"],
                        "service_id": record["service_id"],
                        "host": record["host"],
                        "datacenter": record["datacenter"], 
                        "status": record["status"]
                    }
                    services.append(service_info)
                    
                    # 出向关系
                    outgoing = record["outgoing_relations"]
                    for rel in outgoing:
                        if (rel and rel.get("to_service") and rel.get("from_service") and 
                            rel.get("to_service") not in [None, "null", ""] and 
                            rel.get("from_service") not in [None, "null", ""]):
                            all_relationships.append(rel)
                            
                    # 入向关系  
                    incoming = record["incoming_relations"]
                    for rel in incoming:
                        if (rel and rel.get("from_service") and rel.get("to_service") and
                            rel.get("from_service") not in [None, "null", ""] and 
                            rel.get("to_service") not in [None, "null", ""]):
                            all_relationships.append(rel)
                
                # 去重关系
                unique_relationships = []
                seen = set()
                for rel in all_relationships:
                    key = (rel["from_service"], rel["to_service"], rel["relation"])
                    if key not in seen:
                        unique_relationships.append(rel)
                        seen.add(key)
                
                self.logger.info(f"拓扑查询完成: 找到{len(services)}个服务, {len(unique_relationships)}个关系")
                
                return {
                    "services": services,
                    "relationships": unique_relationships,
                    "query_services": service_names
                }
                
        except Exception as e:
            self.logger.error(f"拓扑查询失败: {e}")
            return {"services": [], "relationships": [], "error": str(e)}
            
    async def get_upstream_services(self, service_name: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """获取上游服务（依赖的服务）"""
        if not self.driver:
            return []
            
        try:
            with self.driver.session() as session:
                # 查找上游依赖，限制深度避免过度查询
                query = """
                MATCH path = (upstream:Service)-[:ROUTES_TO|:CONNECTS_TO*1..{}]->(s:Service)
                WHERE s.name = $service_name OR s.service_id = $service_name
                
                RETURN DISTINCT
                    upstream.name as upstream_name,
                    upstream.service_id as upstream_id,
                    upstream.host as upstream_host,
                    length(path) as distance,
                    [rel IN relationships(path) | type(rel)] as relation_chain
                    
                ORDER BY distance ASC
                LIMIT 20
                """.format(max_depth)
                
                result = session.run(query, service_name=service_name)
                
                upstream_services = []
                for record in result:
                    upstream_services.append({
                        "name": record["upstream_name"],
                        "service_id": record["upstream_id"], 
                        "host": record["upstream_host"],
                        "distance": record["distance"],
                        "relation_chain": record["relation_chain"]
                    })
                
                return upstream_services
                
        except Exception as e:
            self.logger.error(f"上游服务查询失败: {e}")
            return []
            
    async def get_downstream_services(self, service_name: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """获取下游服务（被依赖的服务）"""
        if not self.driver:
            return []
            
        try:
            with self.driver.session() as session:
                # 查找下游服务
                query = """
                MATCH path = (s:Service)-[:ROUTES_TO|:CONNECTS_TO*1..{}]->(downstream:Service)
                WHERE s.name = $service_name OR s.service_id = $service_name
                
                RETURN DISTINCT
                    downstream.name as downstream_name,
                    downstream.service_id as downstream_id,
                    downstream.host as downstream_host,
                    length(path) as distance,
                    [rel IN relationships(path) | type(rel)] as relation_chain
                    
                ORDER BY distance ASC  
                LIMIT 20
                """.format(max_depth)
                
                result = session.run(query, service_name=service_name)
                
                downstream_services = []
                for record in result:
                    downstream_services.append({
                        "name": record["downstream_name"],
                        "service_id": record["downstream_id"],
                        "host": record["downstream_host"],
                        "distance": record["distance"],
                        "relation_chain": record["relation_chain"]
                    })
                
                return downstream_services
                
        except Exception as e:
            self.logger.error(f"下游服务查询失败: {e}")
            return []
            
    async def find_critical_path(self, from_service: str, to_service: str) -> List[Dict[str, Any]]:
        """查找两个服务间的关键路径"""
        if not self.driver:
            return []
            
        try:
            with self.driver.session() as session:
                # 查找两个服务间的最短路径
                query = """
                MATCH path = shortestPath((from:Service)-[:ROUTES_TO|:CONNECTS_TO*1..5]->(to:Service))
                WHERE (from.name = $from_service OR from.service_id = $from_service)
                  AND (to.name = $to_service OR to.service_id = $to_service)
                  
                RETURN 
                    [node IN nodes(path) | {name: node.name, host: node.host}] as path_nodes,
                    [rel IN relationships(path) | {type: type(rel), properties: properties(rel)}] as path_relations,
                    length(path) as path_length
                    
                ORDER BY path_length ASC
                LIMIT 5
                """
                
                result = session.run(query, from_service=from_service, to_service=to_service)
                
                paths = []
                for record in result:
                    paths.append({
                        "nodes": record["path_nodes"],
                        "relations": record["path_relations"],
                        "length": record["path_length"]
                    })
                
                return paths
                
        except Exception as e:
            self.logger.error(f"关键路径查询失败: {e}")
            return []
            
    async def get_host_services(self, host_name: str) -> List[Dict[str, Any]]:
        """获取指定主机上的所有服务"""
        if not self.driver:
            return []
            
        try:
            with self.driver.session() as session:
                query = """
                MATCH (s:Service)
                WHERE s.host = $host_name
                
                RETURN 
                    s.name as service_name,
                    s.service_id as service_id,
                    s.status as status,
                    s.datacenter as datacenter
                    
                ORDER BY s.name ASC
                """
                
                result = session.run(query, host_name=host_name)
                
                services = []
                for record in result:
                    services.append({
                        "name": record["service_name"],
                        "service_id": record["service_id"],
                        "status": record["status"],
                        "datacenter": record["datacenter"]
                    })
                
                return services
                
        except Exception as e:
            self.logger.error(f"主机服务查询失败: {e}")
            return []
            
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j拓扑服务连接已关闭")


# 全局拓扑服务实例
topology_service = TopologyService()