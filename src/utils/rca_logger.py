"""
RCA流程专用日志系统
记录完整的RCA分析过程，包括混合搜索、NER识别、Neo4j查询等
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class RCALogger:
    """RCA流程日志记录器"""
    
    def __init__(self):
        self.logs_dir = Path("./logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # 创建RCA专用日志文件
        self.rca_log_file = self.logs_dir / "rca_analysis.log"
        self.detailed_log_file = self.logs_dir / "rca_detailed.log"
        
        # 配置RCA日志记录器
        self.logger = self._setup_logger()
        self.detailed_logger = self._setup_detailed_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """设置主要RCA日志记录器"""
        logger = logging.getLogger("RCA_Analysis")
        logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not logger.handlers:
            # 文件handler
            file_handler = logging.FileHandler(self.rca_log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 格式化
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        return logger
        
    def _setup_detailed_logger(self) -> logging.Logger:
        """设置详细RCA日志记录器"""
        logger = logging.getLogger("RCA_Detailed")
        logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if not logger.handlers:
            # 文件handler  
            file_handler = logging.FileHandler(self.detailed_log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # 详细格式化
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        return logger
    
    def log_query_start(self, query: str, session_id: str = "default"):
        """记录查询开始"""
        self.logger.info(f"=== RCA查询开始 ===")
        self.logger.info(f"查询内容: {query}")
        self.logger.info(f"会话ID: {session_id}")
        
        self.detailed_logger.info(f"Query started: {query} (Session: {session_id})")
        
    def log_hybrid_search(self, query: str, results: Dict[str, Any]):
        """记录混合搜索结果"""
        total = results.get("total_results", 0)
        vector_count = results.get("vector_results", 0) 
        bm25_count = results.get("bm25_results", 0)
        search_type = results.get("search_type", "unknown")
        
        self.logger.info(f"混合搜索完成: 总结果={total}, 向量搜索={vector_count}, BM25搜索={bm25_count}, 类型={search_type}")
        
        # 详细记录前3个结果
        if results.get("results"):
            self.detailed_logger.info("搜索结果详情:")
            for i, result in enumerate(results["results"][:3], 1):
                content = result.get("content", "")[:100]
                service = result.get("service_name", "unknown")
                score = result.get("hybrid_score", 0)
                self.detailed_logger.info(f"  {i}. [{service}] 得分={score:.3f}: {content}...")
                
    def log_ner_extraction(self, query: str, entities: List[Dict[str, Any]]):
        """记录NER实体提取"""
        self.logger.info(f"NER实体提取: 找到{len(entities)}个实体")
        
        self.detailed_logger.info("NER提取结果:")
        for entity in entities:
            entity_text = entity.get("text", "")
            entity_type = entity.get("label", "")
            confidence = entity.get("confidence", 0)
            self.detailed_logger.info(f"  - {entity_text} [{entity_type}] 置信度={confidence:.3f}")
            
    def log_neo4j_query(self, service_entities: List[str], relationships: List[Dict[str, Any]]):
        """记录Neo4j拓扑查询"""
        self.logger.info(f"Neo4j拓扑查询: 查询{len(service_entities)}个服务的上下游关系")
        
        self.detailed_logger.info("Neo4j查询结果:")
        self.detailed_logger.info(f"  查询服务: {service_entities}")
        
        for rel in relationships:
            from_service = rel.get("from_service", "")
            to_service = rel.get("to_service", "")
            relation_type = rel.get("relation", "")
            self.detailed_logger.info(f"  - {from_service} --[{relation_type}]--> {to_service}")
            
    def log_reasoning_process(self, evidence_count: int, symptoms: List[Dict], potential_causes: List[Dict]):
        """记录推理过程"""
        self.logger.info(f"推理分析: 证据={evidence_count}条, 症状={len(symptoms)}个, 潜在原因={len(potential_causes)}个")
        
        self.detailed_logger.info("推理过程详情:")
        
        # 记录症状
        if symptoms:
            self.detailed_logger.info("  识别症状:")
            for symptom in symptoms:
                self.detailed_logger.info(f"    - {symptom.get('symptom', '')} (严重程度: {symptom.get('severity', '')})")
                
        # 记录潜在原因
        if potential_causes:
            self.detailed_logger.info("  潜在原因:")
            for cause in potential_causes[:5]:  # 只记录前5个
                confidence = cause.get("confidence", 0)
                cause_text = cause.get("cause", "")
                source = cause.get("source", "")
                self.detailed_logger.info(f"    - {cause_text} [来源: {source}, 置信度: {confidence:.3f}]")
                
    def log_final_result(self, primary_cause: str, confidence: float, processing_time: float):
        """记录最终结果"""
        self.logger.info(f"RCA分析完成: 主要根因='{primary_cause}', 置信度={confidence:.3f}, 耗时={processing_time:.2f}秒")
        self.logger.info("=== RCA查询结束 ===")
        
    def log_error(self, error_msg: str, stage: str = "unknown"):
        """记录错误"""
        self.logger.error(f"RCA错误 [{stage}]: {error_msg}")
        self.detailed_logger.exception(f"RCA错误详情 [{stage}]: {error_msg}")
        
    def log_data_mismatch(self, query: str, expected_issue: str, actual_data: str):
        """记录数据不匹配情况（如用户问内存但实际是磁盘问题）"""
        self.logger.warning(f"数据不匹配: 用户查询'{query}'期望{expected_issue}问题，但实际数据显示{actual_data}问题")
        self.detailed_logger.warning(f"数据不匹配详情: Query='{query}', Expected={expected_issue}, Actual={actual_data}")
        
    def export_session_log(self, session_id: str, output_file: Optional[str] = None) -> str:
        """导出特定会话的日志"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"./logs/rca_session_{session_id}_{timestamp}.log"
            
        # 这里可以实现会话日志提取逻辑
        # 简化实现：复制当前日志文件
        import shutil
        shutil.copy2(self.rca_log_file, output_file)
        
        return output_file


# 全局RCA日志实例
rca_logger = RCALogger()