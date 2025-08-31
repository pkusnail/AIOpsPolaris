"""
更新知识图谱，构建完整的实验环境拓扑
基于system_architecture.md构建真实的微服务架构
"""

import asyncio
import logging
from neo4j import GraphDatabase
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExperimentTopologyBuilder:
    """实验环境拓扑构建器"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "aiops123")
        )
    
    async def build_complete_topology(self):
        """构建完整的实验拓扑"""
        logger.info("开始构建完整的实验拓扑...")
        
        with self.driver.session() as session:
            # 1. 清理旧数据
            await self._clean_old_topology(session)
            
            # 2. 创建服务节点
            await self._create_services(session)
            
            # 3. 创建主机和数据中心节点
            await self._create_infrastructure(session)
            
            # 4. 创建数据库节点
            await self._create_databases(session)
            
            # 5. 建立服务依赖关系
            await self._create_dependencies(session)
            
            # 6. 建立部署关系
            await self._create_deployments(session)
            
            # 7. 建立问题和故障节点
            await self._create_issues(session)
            
            # 8. 创建调用链路
            await self._create_call_paths(session)
            
        logger.info("完整拓扑构建完成")
    
    async def _clean_old_topology(self, session):
        """清理旧的拓扑数据"""
        logger.info("清理旧的拓扑数据...")
        
        # 删除实验相关的节点和关系，保留文档
        cleanup_queries = [
            "MATCH (n:TestNode) DETACH DELETE n",
            "MATCH (n:Service) DETACH DELETE n", 
            "MATCH (n:Host) DETACH DELETE n",
            "MATCH (n:DataCenter) DETACH DELETE n",
            "MATCH (n:Database) DETACH DELETE n",
            "MATCH (n:Issue) DETACH DELETE n",
            "MATCH (n:CallPath) DETACH DELETE n"
        ]
        
        for query in cleanup_queries:
            session.run(query)
    
    async def _create_services(self, session):
        """创建服务节点"""
        logger.info("创建服务节点...")
        
        services = [
            {
                "name": "service-a",
                "type": "api-gateway", 
                "technology": "Spring Boot",
                "port": 8080,
                "dc": "DC-East",
                "description": "API Gateway - 系统入口点，负责请求路由和负载均衡"
            },
            {
                "name": "service-b", 
                "type": "business-logic",
                "technology": "Spring Boot",
                "port": 8081,
                "dc": "DC-East",
                "description": "Primary Business Logic - 主要业务逻辑处理"
            },
            {
                "name": "service-c",
                "type": "business-logic", 
                "technology": "Node.js",
                "port": 8082,
                "dc": "DC-East",
                "description": "Secondary Business Logic - 备选业务逻辑处理"
            },
            {
                "name": "service-d1",
                "type": "data-processing",
                "technology": "Java MyBatis", 
                "port": 8083,
                "dc": "DC-East",
                "description": "Data Processing Instance 1"
            },
            {
                "name": "service-d2",
                "type": "data-processing",
                "technology": "Java MyBatis",
                "port": 8083,
                "dc": "DC-East", 
                "description": "Data Processing Instance 2"
            },
            {
                "name": "service-d3",
                "type": "data-processing",
                "technology": "Java MyBatis",
                "port": 8083,
                "dc": "DC-East",
                "description": "Data Processing Instance 3"
            },
            {
                "name": "service-f",
                "type": "external-integration",
                "technology": "Python Flask",
                "port": 8085,
                "dc": "DC-West",
                "description": "External Integration - 外部API集成和支付处理"
            }
        ]
        
        for service in services:
            session.run(
                """
                CREATE (s:Service {
                    name: $name,
                    type: $type,
                    technology: $technology,
                    port: $port,
                    datacenter: $dc,
                    description: $description,
                    status: 'active',
                    created_at: datetime()
                })
                """,
                **service
            )
            logger.info(f"创建服务: {service['name']}")
    
    async def _create_infrastructure(self, session):
        """创建基础设施节点"""
        logger.info("创建基础设施节点...")
        
        # 数据中心
        datacenters = [
            {
                "name": "DC-East",
                "location": "东部数据中心", 
                "subnet": "10.1.0.0/16",
                "description": "主要数据中心"
            },
            {
                "name": "DC-West",
                "location": "西部数据中心",
                "subnet": "10.2.0.0/16", 
                "description": "备用数据中心"
            }
        ]
        
        for dc in datacenters:
            session.run(
                """
                CREATE (dc:DataCenter {
                    name: $name,
                    location: $location,
                    subnet: $subnet,
                    description: $description,
                    created_at: datetime()
                })
                """,
                **dc
            )
        
        # 主机节点
        hosts = [
            {
                "name": "host-east-1",
                "ip": "10.1.1.10",
                "datacenter": "DC-East",
                "cpu_cores": 8,
                "memory_gb": 16,
                "description": "东部主机1"
            },
            {
                "name": "host-east-2", 
                "ip": "10.1.1.11",
                "datacenter": "DC-East",
                "cpu_cores": 8,
                "memory_gb": 16,
                "description": "东部主机2"
            },
            {
                "name": "host-east-3",
                "ip": "10.1.1.12", 
                "datacenter": "DC-East",
                "cpu_cores": 16,
                "memory_gb": 32,
                "description": "东部数据库主机"
            },
            {
                "name": "host-west-1",
                "ip": "10.2.1.10",
                "datacenter": "DC-West", 
                "cpu_cores": 4,
                "memory_gb": 8,
                "description": "西部主机1"
            }
        ]
        
        for host in hosts:
            session.run(
                """
                CREATE (h:Host {
                    name: $name,
                    ip: $ip,
                    datacenter: $datacenter,
                    cpu_cores: $cpu_cores,
                    memory_gb: $memory_gb,
                    description: $description,
                    status: 'online',
                    created_at: datetime()
                })
                """,
                **host
            )
            logger.info(f"创建主机: {host['name']}")
    
    async def _create_databases(self, session):
        """创建数据库节点"""
        logger.info("创建数据库节点...")
        
        databases = [
            {
                "name": "mysql-primary",
                "type": "MySQL",
                "version": "8.0",
                "port": 3306,
                "datacenter": "DC-East",
                "connection_pool": 20,
                "description": "MySQL主数据库"
            },
            {
                "name": "postgresql-secondary", 
                "type": "PostgreSQL",
                "version": "14.0",
                "port": 5432,
                "datacenter": "DC-West",
                "connection_pool": 15,
                "description": "PostgreSQL辅助数据库"
            }
        ]
        
        for db in databases:
            session.run(
                """
                CREATE (db:Database {
                    name: $name,
                    type: $type,
                    version: $version,
                    port: $port,
                    datacenter: $datacenter,
                    connection_pool: $connection_pool,
                    description: $description,
                    status: 'online',
                    created_at: datetime()
                })
                """,
                **db
            )
    
    async def _create_dependencies(self, session):
        """创建服务依赖关系"""
        logger.info("创建服务依赖关系...")
        
        dependencies = [
            # API Gateway的依赖
            ("service-a", "service-b", "ROUTES_TO", {"weight": 0.6, "timeout": "5s"}),
            ("service-a", "service-c", "ROUTES_TO", {"weight": 0.4, "timeout": "8s"}),
            
            # Business Logic的依赖
            ("service-b", "service-d1", "CALLS", {"load_balance": True}),
            ("service-b", "service-d2", "CALLS", {"load_balance": True}),
            ("service-b", "service-d3", "CALLS", {"load_balance": True}),
            ("service-c", "service-f", "CALLS", {"cross_dc": True, "timeout": "10s"}),
            
            # Data Processing的数据库依赖
            ("service-d1", "mysql-primary", "CONNECTS_TO", {"pool_size": 5}),
            ("service-d2", "mysql-primary", "CONNECTS_TO", {"pool_size": 5}),
            ("service-d3", "mysql-primary", "CONNECTS_TO", {"pool_size": 5}),
            
            # External Integration的数据库依赖
            ("service-f", "postgresql-secondary", "CONNECTS_TO", {"pool_size": 8}),
        ]
        
        for from_node, to_node, rel_type, properties in dependencies:
            session.run(
                f"""
                MATCH (from {{name: $from_node}})
                MATCH (to {{name: $to_node}})
                CREATE (from)-[r:{rel_type} $properties]->(to)
                """,
                from_node=from_node,
                to_node=to_node,
                properties=properties
            )
            logger.info(f"创建依赖: {from_node} --{rel_type}--> {to_node}")
    
    async def _create_deployments(self, session):
        """创建部署关系"""
        logger.info("创建部署关系...")
        
        deployments = [
            ("service-a", "host-east-1"),
            ("service-b", "host-east-1"), 
            ("service-c", "host-east-2"),
            ("service-d1", "host-east-2"),
            ("service-d2", "host-east-2"),
            ("service-d3", "host-east-2"),
            ("mysql-primary", "host-east-3"),
            ("service-f", "host-west-1"),
            ("postgresql-secondary", "host-west-1")
        ]
        
        for service, host in deployments:
            session.run(
                """
                MATCH (s {name: $service})
                MATCH (h:Host {name: $host})
                CREATE (s)-[:DEPLOYED_ON]->(h)
                """,
                service=service,
                host=host
            )
            logger.info(f"创建部署关系: {service} --> {host}")
    
    async def _create_issues(self, session):
        """创建问题和故障节点"""
        logger.info("创建问题和故障节点...")
        
        issues = [
            {
                "name": "Service-B CPU过载",
                "type": "performance",
                "severity": "high",
                "category": "CPU",
                "description": "Service-B处理复杂业务逻辑导致CPU过载"
            },
            {
                "name": "Service-D1内存泄漏",
                "type": "memory", 
                "severity": "medium",
                "category": "Memory",
                "description": "Service-D1存在内存泄漏问题"
            },
            {
                "name": "MySQL连接池耗尽",
                "type": "database",
                "severity": "high", 
                "category": "Database",
                "description": "MySQL连接池被耗尽，新连接被拒绝"
            },
            {
                "name": "跨DC网络分区",
                "type": "network",
                "severity": "critical",
                "category": "Network", 
                "description": "DC-East到DC-West网络中断"
            },
            {
                "name": "Service-F外部API超时",
                "type": "external",
                "severity": "medium",
                "category": "Integration",
                "description": "Payment Gateway API响应超时"
            }
        ]
        
        for issue in issues:
            session.run(
                """
                CREATE (i:Issue {
                    name: $name,
                    type: $type,
                    severity: $severity,
                    category: $category,
                    description: $description,
                    status: 'active',
                    created_at: datetime()
                })
                """,
                **issue
            )
        
        # 创建问题影响关系
        issue_impacts = [
            ("Service-B CPU过载", "service-b"),
            ("Service-D1内存泄漏", "service-d1"),
            ("MySQL连接池耗尽", "mysql-primary"),
            ("跨DC网络分区", "service-f"),
            ("Service-F外部API超时", "service-f")
        ]
        
        for issue, affected_service in issue_impacts:
            session.run(
                """
                MATCH (i:Issue {name: $issue})
                MATCH (s {name: $affected_service})
                CREATE (i)-[:AFFECTS]->(s)
                """,
                issue=issue,
                affected_service=affected_service
            )
    
    async def _create_call_paths(self, session):
        """创建调用链路"""
        logger.info("创建调用链路...")
        
        # 主调用路径
        call_paths = [
            {
                "name": "Path-A-B-D",
                "description": "用户请求 -> A -> B -> D -> MySQL",
                "traffic_percent": 60,
                "expected_latency": "< 500ms"
            },
            {
                "name": "Path-A-C-F", 
                "description": "用户请求 -> A -> C -> F -> External API",
                "traffic_percent": 40,
                "expected_latency": "< 800ms"
            }
        ]
        
        for path in call_paths:
            session.run(
                """
                CREATE (p:CallPath {
                    name: $name,
                    description: $description, 
                    traffic_percent: $traffic_percent,
                    expected_latency: $expected_latency,
                    created_at: datetime()
                })
                """,
                **path
            )
    
    async def verify_topology(self):
        """验证拓扑完整性"""
        logger.info("验证拓扑完整性...")
        
        with self.driver.session() as session:
            # 统计节点
            counts = {}
            node_types = ["Service", "Host", "Database", "DataCenter", "Issue", "CallPath"]
            
            for node_type in node_types:
                result = session.run(f"MATCH (n:{node_type}) RETURN count(n) as count")
                counts[node_type] = result.single()["count"]
            
            # 统计关系
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_result.single()["count"]
            
            logger.info("=== 拓扑验证结果 ===")
            for node_type, count in counts.items():
                logger.info(f"{node_type}: {count} 个节点")
            logger.info(f"关系总数: {rel_count} 个")
            
            # 验证关键路径
            critical_paths = [
                "service-a --> service-b",
                "service-b --> service-d1", 
                "service-c --> service-f"
            ]
            
            for path in critical_paths:
                parts = path.split(" --> ")
                result = session.run(
                    """
                    MATCH (a {name: $from_node})-[r]->(b {name: $to_node})
                    RETURN type(r) as rel_type
                    """,
                    from_node=parts[0],
                    to_node=parts[1]
                )
                
                rel_types = [record["rel_type"] for record in result]
                if rel_types:
                    logger.info(f"✅ {path}: {', '.join(rel_types)}")
                else:
                    logger.warning(f"❌ {path}: 缺少关系")
    
    def close(self):
        self.driver.close()


async def main():
    """主函数"""
    builder = ExperimentTopologyBuilder()
    
    try:
        await builder.build_complete_topology()
        await builder.verify_topology()
        print("\n🎉 完整的实验拓扑构建成功！")
        print("包含的组件:")
        print("- 7个微服务 (A, B, C, D1-D3, F)")
        print("- 4个主机节点 (DC-East: 3台, DC-West: 1台)")
        print("- 2个数据中心 (DC-East, DC-West)")
        print("- 2个数据库 (MySQL, PostgreSQL)")
        print("- 5类问题场景")
        print("- 完整的依赖和部署关系")
        
    except Exception as e:
        logger.error(f"构建拓扑失败: {e}")
        raise
    finally:
        builder.close()


if __name__ == "__main__":
    asyncio.run(main())