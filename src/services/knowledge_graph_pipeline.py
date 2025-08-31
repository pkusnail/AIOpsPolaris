"""
知识图谱构建Pipeline
从GitLab/Jira/Wiki数据抽取NER信息并在Neo4j中构建知识图谱
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import logging

from .ner_service import NERService
from .graph_service import GraphService

logger = logging.getLogger(__name__)


class KnowledgeGraphPipeline:
    """知识图谱构建管道类"""
    
    def __init__(self):
        self.ner_service = NERService()
        self.graph_service = GraphService()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 预定义的运维实体映射
        self.predefined_entities = {
            'services': [
                'service-a', 'service-b', 'service-c', 'service-d', 'service-e',
                'api-gateway', 'user-service', 'order-service', 'payment-service',
                'notification-service', 'auth-service', 'web-server'
            ],
            'technologies': [
                'kubernetes', 'docker', 'mysql', 'redis', 'nginx', 'prometheus',
                'grafana', 'elasticsearch', 'kafka', 'rabbitmq', 'mongodb'
            ],
            'hosts': [
                'd1-app-01', 'd1-app-02', 'd1-db-01', 'd2-app-01', 'd2-app-02',
                'd2-db-01', 'lb-01', 'lb-02'
            ],
            'components': [
                'load-balancer', 'database', 'cache', 'message-queue',
                'monitoring', 'logging', 'security'
            ]
        }
    
    async def initialize_graph(self):
        """初始化知识图谱基础结构"""
        try:
            # 初始化约束和索引
            await self.graph_service.initialize_constraints()
            
            # 创建预定义实体
            await self._create_predefined_entities()
            
            # 创建预定义关系
            await self._create_predefined_relationships()
            
            self.logger.info("Knowledge graph initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize knowledge graph: {e}")
            raise
    
    async def _create_predefined_entities(self):
        """创建预定义的实体"""
        try:
            for entity_type, entities in self.predefined_entities.items():
                for entity_name in entities:
                    # 统一实体类型名称
                    unified_type = entity_type.upper().rstrip('S')  # services -> SERVICE
                    
                    await self.graph_service.create_entity(
                        name=entity_name,
                        entity_type=unified_type,
                        properties={
                            'predefined': True,
                            'category': entity_type
                        },
                        confidence=1.0
                    )
            
            self.logger.info("Predefined entities created")
            
        except Exception as e:
            self.logger.error(f"Failed to create predefined entities: {e}")
    
    async def _create_predefined_relationships(self):
        """创建预定义的关系"""
        try:
            # 基础架构关系
            predefined_relations = [
                # 服务部署关系
                ('service-a', 'SERVICE', 'd1-app-01', 'HOST', 'DEPLOYED_ON'),
                ('service-b', 'SERVICE', 'd1-app-02', 'HOST', 'DEPLOYED_ON'),
                ('service-c', 'SERVICE', 'd2-app-01', 'HOST', 'DEPLOYED_ON'),
                
                # 服务依赖关系
                ('api-gateway', 'SERVICE', 'service-a', 'SERVICE', 'DEPENDS_ON'),
                ('api-gateway', 'SERVICE', 'service-b', 'SERVICE', 'DEPENDS_ON'),
                ('service-a', 'SERVICE', 'mysql', 'TECHNOLOGY', 'USES'),
                ('service-b', 'SERVICE', 'redis', 'TECHNOLOGY', 'USES'),
                
                # 监控关系
                ('prometheus', 'TECHNOLOGY', 'service-a', 'SERVICE', 'MONITORS'),
                ('prometheus', 'TECHNOLOGY', 'service-b', 'SERVICE', 'MONITORS'),
                ('grafana', 'TECHNOLOGY', 'prometheus', 'TECHNOLOGY', 'DEPENDS_ON'),
            ]
            
            for source_name, source_type, target_name, target_type, rel_type in predefined_relations:
                try:
                    await self.graph_service.create_relationship(
                        source_name=source_name,
                        source_type=source_type,
                        target_name=target_name,
                        target_type=target_type,
                        relationship_type=rel_type,
                        properties={'predefined': True},
                        confidence=1.0
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to create predefined relationship: {e}")
            
            self.logger.info("Predefined relationships created")
            
        except Exception as e:
            self.logger.error(f"Failed to create predefined relationships: {e}")
    
    async def process_wiki_knowledge_graph(self, wiki_dir: str = "./data/wiki/") -> Dict[str, Any]:
        """处理Wiki数据构建知识图谱"""
        try:
            stats = {
                'processed_docs': 0,
                'extracted_entities': 0,
                'extracted_relationships': 0,
                'error_count': 0
            }
            
            wiki_path = Path(wiki_dir)
            if not wiki_path.exists():
                raise FileNotFoundError(f"Wiki directory not found: {wiki_dir}")
            
            # 处理JSON文件
            json_files = list(wiki_path.glob("*.json"))
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        wiki_data = json.load(f)
                    
                    if isinstance(wiki_data, list):
                        for doc in wiki_data:
                            doc_stats = await self._process_wiki_doc_for_kg(doc, str(json_file))
                            stats['processed_docs'] += 1
                            stats['extracted_entities'] += doc_stats['entities']
                            stats['extracted_relationships'] += doc_stats['relationships']
                    
                except Exception as e:
                    self.logger.error(f"Failed to process wiki file {json_file}: {e}")
                    stats['error_count'] += 1
            
            # 处理Markdown文件
            md_files = list(wiki_path.glob("*.md"))
            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    doc = {
                        'id': md_file.stem,
                        'title': md_file.stem.replace('_', ' ').title(),
                        'content': content,
                        'category': '技术文档',
                        'source': 'wiki'
                    }
                    
                    doc_stats = await self._process_wiki_doc_for_kg(doc, str(md_file))
                    stats['processed_docs'] += 1
                    stats['extracted_entities'] += doc_stats['entities']
                    stats['extracted_relationships'] += doc_stats['relationships']
                    
                except Exception as e:
                    self.logger.error(f"Failed to process markdown file {md_file}: {e}")
                    stats['error_count'] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to process wiki knowledge graph: {e}")
            raise
    
    async def _process_wiki_doc_for_kg(self, doc: Dict[str, Any], file_path: str) -> Dict[str, int]:
        """处理单个Wiki文档构建知识图谱"""
        try:
            title = doc.get('title', '')
            content = doc.get('content', '')
            
            # 提取实体和关系
            ner_result = await self.ner_service.extract_from_document(
                title=title,
                content=content,
                source='wiki'
            )
            
            entities = ner_result['entities']
            relationships = ner_result['relationships']
            
            # 创建文档节点
            weaviate_id = f"wiki_{doc.get('id', '')}"
            doc_node_id = await self.graph_service.create_document_node(
                weaviate_id=weaviate_id,
                title=title,
                source='wiki',
                category=doc.get('category', '知识文档')
            )
            
            # 创建实体节点
            created_entities = 0
            for entity in entities:
                try:
                    await self.graph_service.create_entity(
                        name=entity['text'],
                        entity_type=entity['label'],
                        properties={
                            'confidence': entity['confidence'],
                            'position_start': entity['start'],
                            'position_end': entity['end'],
                            'source_document': weaviate_id
                        },
                        source_document_id=weaviate_id,
                        confidence=entity['confidence']
                    )
                    
                    # 链接实体到文档
                    await self.graph_service.link_entity_to_document(
                        entity_name=entity['text'],
                        entity_type=entity['label'],
                        weaviate_id=weaviate_id
                    )
                    
                    created_entities += 1
                    
                except Exception as e:
                    self.logger.warning(f"Failed to create entity {entity['text']}: {e}")
            
            # 创建关系
            created_relationships = 0
            for relationship in relationships:
                try:
                    # 查找对应的实体
                    source_entity = next((e for e in entities if e['id'] == relationship['source_entity_id']), None)
                    target_entity = next((e for e in entities if e['id'] == relationship['target_entity_id']), None)
                    
                    if source_entity and target_entity:
                        await self.graph_service.create_relationship(
                            source_name=source_entity['text'],
                            source_type=source_entity['label'],
                            target_name=target_entity['text'],
                            target_type=target_entity['label'],
                            relationship_type=relationship['relationship_type'],
                            properties={
                                'confidence': relationship['confidence'],
                                'source_document': weaviate_id,
                                'inferred': relationship.get('inferred', False)
                            },
                            confidence=relationship['confidence']
                        )
                        created_relationships += 1
                        
                except Exception as e:
                    self.logger.warning(f"Failed to create relationship: {e}")
            
            return {
                'entities': created_entities,
                'relationships': created_relationships
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process wiki doc for KG: {e}")
            return {'entities': 0, 'relationships': 0}
    
    async def process_gitlab_knowledge_graph(self, gitlab_dir: str = "./data/gitlab/") -> Dict[str, Any]:
        """处理GitLab数据构建知识图谱"""
        try:
            stats = {
                'processed_items': 0,
                'extracted_entities': 0,
                'extracted_relationships': 0,
                'error_count': 0
            }
            
            gitlab_path = Path(gitlab_dir)
            json_files = list(gitlab_path.glob("*.json"))
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        gitlab_data = json.load(f)
                    
                    if isinstance(gitlab_data, list):
                        for item in gitlab_data:
                            item_stats = await self._process_gitlab_item_for_kg(item, str(json_file))
                            stats['processed_items'] += 1
                            stats['extracted_entities'] += item_stats['entities']
                            stats['extracted_relationships'] += item_stats['relationships']
                    
                except Exception as e:
                    self.logger.error(f"Failed to process GitLab file {json_file}: {e}")
                    stats['error_count'] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to process GitLab knowledge graph: {e}")
            raise
    
    async def _process_gitlab_item_for_kg(self, item: Dict[str, Any], file_path: str) -> Dict[str, int]:
        """处理单个GitLab项目构建知识图谱"""
        try:
            title = item.get('title', '')
            description = item.get('description', '')
            
            # 构建完整文本用于NER
            full_text = f"{title}\n{description}"
            
            # 提取实体和关系
            ner_result = await self.ner_service.extract_from_document(
                title=title,
                content=description,
                source='gitlab'
            )
            
            entities = ner_result['entities']
            relationships = ner_result['relationships']
            
            # 从GitLab元数据中提取额外实体
            additional_entities = self._extract_gitlab_entities(item)
            entities.extend(additional_entities)
            
            # 创建文档节点
            weaviate_id = f"gitlab_{item.get('id', '')}"
            doc_node_id = await self.graph_service.create_document_node(
                weaviate_id=weaviate_id,
                title=title,
                source='gitlab',
                category='代码变更'
            )
            
            # 创建实体和关系
            created_entities = await self._create_entities_and_links(entities, weaviate_id)
            created_relationships = await self._create_relationships(relationships)
            
            # 创建GitLab特有的关系
            gitlab_relations = await self._create_gitlab_relationships(item, entities)
            created_relationships += gitlab_relations
            
            return {
                'entities': created_entities,
                'relationships': created_relationships
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process GitLab item for KG: {e}")
            return {'entities': 0, 'relationships': 0}
    
    def _extract_gitlab_entities(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从GitLab元数据提取实体"""
        entities = []
        
        try:
            # 从变更文件提取
            if 'files_changed' in item:
                for file_path in item['files_changed']:
                    # 提取服务名
                    path_parts = file_path.split('/')
                    for part in path_parts:
                        if any(service in part for service in self.predefined_entities['services']):
                            entities.append({
                                'id': f'file_entity_{len(entities)}',
                                'text': part,
                                'label': 'SERVICE',
                                'confidence': 0.9,
                                'start': 0,
                                'end': len(part),
                                'source': 'gitlab_metadata'
                            })
            
            # 从标签提取
            if 'labels' in item:
                for label in item['labels']:
                    if label.lower() in ['backend', 'frontend', 'database', 'api']:
                        entities.append({
                            'id': f'label_entity_{len(entities)}',
                            'text': label,
                            'label': 'COMPONENT',
                            'confidence': 0.8,
                            'start': 0,
                            'end': len(label),
                            'source': 'gitlab_labels'
                        })
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Failed to extract GitLab entities: {e}")
            return []
    
    async def process_jira_knowledge_graph(self, jira_dir: str = "./data/jira/") -> Dict[str, Any]:
        """处理Jira数据构建知识图谱"""
        try:
            stats = {
                'processed_items': 0,
                'extracted_entities': 0,
                'extracted_relationships': 0,
                'error_count': 0
            }
            
            jira_path = Path(jira_dir)
            json_files = list(jira_path.glob("*.json"))
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        jira_data = json.load(f)
                    
                    if isinstance(jira_data, list):
                        for item in jira_data:
                            item_stats = await self._process_jira_item_for_kg(item, str(json_file))
                            stats['processed_items'] += 1
                            stats['extracted_entities'] += item_stats['entities']
                            stats['extracted_relationships'] += item_stats['relationships']
                    
                except Exception as e:
                    self.logger.error(f"Failed to process Jira file {json_file}: {e}")
                    stats['error_count'] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to process Jira knowledge graph: {e}")
            raise
    
    async def _process_jira_item_for_kg(self, item: Dict[str, Any], file_path: str) -> Dict[str, int]:
        """处理单个Jira工单构建知识图谱"""
        try:
            title = item.get('title', item.get('summary', ''))
            description = item.get('description', '')
            
            # 提取实体和关系
            ner_result = await self.ner_service.extract_from_document(
                title=title,
                content=description,
                source='jira'
            )
            
            entities = ner_result['entities']
            relationships = ner_result['relationships']
            
            # 从Jira元数据中提取额外实体
            additional_entities = self._extract_jira_entities(item)
            entities.extend(additional_entities)
            
            # 创建文档节点
            weaviate_id = f"jira_{item.get('id', item.get('key', ''))}"
            doc_node_id = await self.graph_service.create_document_node(
                weaviate_id=weaviate_id,
                title=title,
                source='jira',
                category=item.get('type', '工单')
            )
            
            # 创建实体和关系
            created_entities = await self._create_entities_and_links(entities, weaviate_id)
            created_relationships = await self._create_relationships(relationships)
            
            # 创建Jira特有的关系
            jira_relations = await self._create_jira_relationships(item, entities)
            created_relationships += jira_relations
            
            return {
                'entities': created_entities,
                'relationships': created_relationships
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process Jira item for KG: {e}")
            return {'entities': 0, 'relationships': 0}
    
    def _extract_jira_entities(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从Jira元数据提取实体"""
        entities = []
        
        try:
            # 从组件提取
            if 'components' in item:
                for component in item['components']:
                    entities.append({
                        'id': f'jira_component_{len(entities)}',
                        'text': component,
                        'label': 'COMPONENT',
                        'confidence': 0.9,
                        'start': 0,
                        'end': len(component),
                        'source': 'jira_components'
                    })
            
            # 从工单类型提取
            if 'type' in item:
                entities.append({
                    'id': f'jira_type_{len(entities)}',
                    'text': item['type'],
                    'label': 'ISSUE_TYPE',
                    'confidence': 1.0,
                    'start': 0,
                    'end': len(item['type']),
                    'source': 'jira_type'
                })
            
            # 从优先级提取
            if 'priority' in item:
                entities.append({
                    'id': f'jira_priority_{len(entities)}',
                    'text': item['priority'],
                    'label': 'PRIORITY',
                    'confidence': 1.0,
                    'start': 0,
                    'end': len(item['priority']),
                    'source': 'jira_priority'
                })
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Failed to extract Jira entities: {e}")
            return []
    
    async def _create_entities_and_links(self, entities: List[Dict[str, Any]], weaviate_id: str) -> int:
        """创建实体并链接到文档"""
        created_count = 0
        
        try:
            for entity in entities:
                try:
                    # 创建实体
                    await self.graph_service.create_entity(
                        name=entity['text'],
                        entity_type=entity['label'],
                        properties={
                            'confidence': entity['confidence'],
                            'position_start': entity['start'],
                            'position_end': entity['end'],
                            'extraction_source': entity.get('source', 'ner')
                        },
                        source_document_id=weaviate_id,
                        confidence=entity['confidence']
                    )
                    
                    # 链接到文档
                    await self.graph_service.link_entity_to_document(
                        entity_name=entity['text'],
                        entity_type=entity['label'],
                        weaviate_id=weaviate_id
                    )
                    
                    created_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Failed to create entity {entity['text']}: {e}")
            
            return created_count
            
        except Exception as e:
            self.logger.error(f"Failed to create entities and links: {e}")
            return 0
    
    async def _create_relationships(self, relationships: List[Dict[str, Any]]) -> int:
        """创建关系"""
        created_count = 0
        
        try:
            for relationship in relationships:
                try:
                    await self.graph_service.create_relationship(
                        source_name=relationship['source_text'],
                        source_type=relationship.get('source_type', 'ENTITY'),
                        target_name=relationship['target_text'],
                        target_type=relationship.get('target_type', 'ENTITY'),
                        relationship_type=relationship['relationship_type'],
                        properties={
                            'confidence': relationship['confidence'],
                            'extracted_at': relationship['extracted_at'],
                            'inferred': relationship.get('inferred', False)
                        },
                        confidence=relationship['confidence']
                    )
                    
                    created_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Failed to create relationship: {e}")
            
            return created_count
            
        except Exception as e:
            self.logger.error(f"Failed to create relationships: {e}")
            return 0
    
    async def _create_gitlab_relationships(self, item: Dict[str, Any], entities: List[Dict[str, Any]]) -> int:
        """创建GitLab特有的关系"""
        created_count = 0
        
        try:
            # 变更文件与服务的关系
            if 'files_changed' in item:
                for file_path in item['files_changed']:
                    # 找到对应的服务实体
                    for entity in entities:
                        if entity['label'] == 'SERVICE' and entity['text'] in file_path:
                            # 创建"修改"关系
                            try:
                                await self.graph_service.create_relationship(
                                    source_name=item.get('id', ''),
                                    source_type='MERGE_REQUEST',
                                    target_name=entity['text'],
                                    target_type='SERVICE',
                                    relationship_type='MODIFIES',
                                    properties={
                                        'file_path': file_path,
                                        'confidence': 0.9
                                    },
                                    confidence=0.9
                                )
                                created_count += 1
                            except Exception as e:
                                self.logger.warning(f"Failed to create GitLab relationship: {e}")
            
            return created_count
            
        except Exception as e:
            self.logger.error(f"Failed to create GitLab relationships: {e}")
            return 0
    
    async def _create_jira_relationships(self, item: Dict[str, Any], entities: List[Dict[str, Any]]) -> int:
        """创建Jira特有的关系"""
        created_count = 0
        
        try:
            # 工单与组件的关系
            if 'components' in item:
                for component in item['components']:
                    try:
                        # 创建工单实体
                        await self.graph_service.create_entity(
                            name=item.get('id', item.get('key', '')),
                            entity_type='ISSUE',
                            properties={
                                'title': item.get('title', ''),
                                'status': item.get('status', ''),
                                'priority': item.get('priority', ''),
                                'type': item.get('type', '')
                            },
                            confidence=1.0
                        )
                        
                        # 创建关系
                        await self.graph_service.create_relationship(
                            source_name=item.get('id', item.get('key', '')),
                            source_type='ISSUE',
                            target_name=component,
                            target_type='COMPONENT',
                            relationship_type='AFFECTS',
                            properties={
                                'confidence': 0.9,
                                'issue_type': item.get('type', ''),
                                'priority': item.get('priority', '')
                            },
                            confidence=0.9
                        )
                        created_count += 1
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to create Jira relationship: {e}")
            
            return created_count
            
        except Exception as e:
            self.logger.error(f"Failed to create Jira relationships: {e}")
            return 0
    
    async def enrich_graph_with_inference(self) -> Dict[str, Any]:
        """通过推理丰富知识图谱"""
        try:
            stats = {
                'inferred_relationships': 0,
                'service_clusters': 0,
                'issue_patterns': 0
            }
            
            # 1. 推断服务间依赖关系
            service_deps = await self._infer_service_dependencies()
            stats['inferred_relationships'] += service_deps
            
            # 2. 识别服务集群
            clusters = await self._identify_service_clusters()
            stats['service_clusters'] = clusters
            
            # 3. 分析问题模式
            patterns = await self._analyze_issue_patterns()
            stats['issue_patterns'] = patterns
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to enrich graph: {e}")
            return {'inferred_relationships': 0, 'service_clusters': 0, 'issue_patterns': 0}
    
    async def _infer_service_dependencies(self) -> int:
        """推断服务间依赖关系"""
        try:
            # 基于GitLab变更和Jira工单推断依赖关系
            query = """
            MATCH (issue:Entity {type: 'ISSUE'})-[:AFFECTS]->(comp1:Entity {type: 'COMPONENT'})
            MATCH (issue)-[:AFFECTS]->(comp2:Entity {type: 'COMPONENT'})
            WHERE comp1 <> comp2
            MERGE (comp1)-[r:POTENTIALLY_DEPENDS_ON]->(comp2)
            ON CREATE SET r.confidence = 0.5, r.inferred = true, r.created_at = $timestamp
            ON MATCH SET r.evidence_count = COALESCE(r.evidence_count, 0) + 1
            RETURN count(r) as created_relationships
            """
            
            async with self.graph_service.driver.session() as session:
                result = await session.run(query, {'timestamp': datetime.utcnow().isoformat()})
                record = await result.single()
                return record['created_relationships'] if record else 0
                
        except Exception as e:
            self.logger.error(f"Failed to infer service dependencies: {e}")
            return 0
    
    async def _identify_service_clusters(self) -> int:
        """识别服务集群"""
        try:
            # 基于共同依赖和部署位置识别集群
            query = """
            MATCH (s1:Entity {type: 'SERVICE'})-[:DEPLOYED_ON]->(host:Entity {type: 'HOST'})
            MATCH (s2:Entity {type: 'SERVICE'})-[:DEPLOYED_ON]->(host)
            WHERE s1 <> s2
            MERGE (s1)-[r:COLLOCATED_WITH]->(s2)
            ON CREATE SET r.confidence = 0.8, r.inferred = true, r.created_at = $timestamp
            RETURN count(r) as cluster_relationships
            """
            
            async with self.graph_service.driver.session() as session:
                result = await session.run(query, {'timestamp': datetime.utcnow().isoformat()})
                record = await result.single()
                return record['cluster_relationships'] if record else 0
                
        except Exception as e:
            self.logger.error(f"Failed to identify service clusters: {e}")
            return 0
    
    async def _analyze_issue_patterns(self) -> int:
        """分析问题模式"""
        try:
            # 识别常见的问题-组件关联模式
            query = """
            MATCH (issue:Entity {type: 'ISSUE'})-[:AFFECTS]->(comp:Entity {type: 'COMPONENT'})
            WITH comp, issue.text as issue_type, count(*) as frequency
            WHERE frequency > 1
            MERGE (comp)-[r:FREQUENTLY_HAS_ISSUE]->(pattern:Entity {type: 'ISSUE_PATTERN', name: issue_type})
            ON CREATE SET pattern.frequency = frequency, pattern.created_at = $timestamp
            ON MATCH SET pattern.frequency = frequency
            SET r.frequency = frequency, r.confidence = 0.7
            RETURN count(r) as pattern_relationships
            """
            
            async with self.graph_service.driver.session() as session:
                result = await session.run(query, {'timestamp': datetime.utcnow().isoformat()})
                record = await result.single()
                return record['pattern_relationships'] if record else 0
                
        except Exception as e:
            self.logger.error(f"Failed to analyze issue patterns: {e}")
            return 0
    
    async def process_all_knowledge_graphs(self) -> Dict[str, Any]:
        """处理所有数据源构建知识图谱"""
        try:
            start_time = datetime.utcnow()
            
            # 初始化图结构
            await self.initialize_graph()
            
            # 并行处理各数据源
            wiki_stats, gitlab_stats, jira_stats = await asyncio.gather(
                self.process_wiki_knowledge_graph(),
                self.process_gitlab_knowledge_graph(),
                self.process_jira_knowledge_graph(),
                return_exceptions=True
            )
            
            # 处理异常结果
            if isinstance(wiki_stats, Exception):
                self.logger.error(f"Wiki KG processing failed: {wiki_stats}")
                wiki_stats = {'processed_docs': 0, 'error_count': 1}
            
            if isinstance(gitlab_stats, Exception):
                self.logger.error(f"GitLab KG processing failed: {gitlab_stats}")
                gitlab_stats = {'processed_items': 0, 'error_count': 1}
            
            if isinstance(jira_stats, Exception):
                self.logger.error(f"Jira KG processing failed: {jira_stats}")
                jira_stats = {'processed_items': 0, 'error_count': 1}
            
            # 推理丰富图谱
            enrichment_stats = await self.enrich_graph_with_inference()
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            total_stats = {
                'wiki': wiki_stats,
                'gitlab': gitlab_stats,
                'jira': jira_stats,
                'enrichment': enrichment_stats,
                'total_entities': (
                    wiki_stats.get('extracted_entities', 0) +
                    gitlab_stats.get('extracted_entities', 0) +
                    jira_stats.get('extracted_entities', 0)
                ),
                'total_relationships': (
                    wiki_stats.get('extracted_relationships', 0) +
                    gitlab_stats.get('extracted_relationships', 0) +
                    jira_stats.get('extracted_relationships', 0) +
                    enrichment_stats.get('inferred_relationships', 0)
                ),
                'processing_time': processing_time
            }
            
            self.logger.info(f"Knowledge graph pipeline completed: {total_stats}")
            return total_stats
            
        except Exception as e:
            self.logger.error(f"Knowledge graph pipeline failed: {e}")
            raise


# 便利函数
async def run_knowledge_graph_pipeline():
    """运行知识图谱构建管道"""
    pipeline = KnowledgeGraphPipeline()
    try:
        stats = await pipeline.process_all_knowledge_graphs()
        print(f"Knowledge graph pipeline completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Knowledge graph pipeline failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_knowledge_graph_pipeline())