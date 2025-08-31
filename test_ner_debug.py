#!/usr/bin/env python3
"""
测试NER识别问题
"""

import sys
sys.path.append('/home/alejandroseaah/AIOpsPolaris')

from src.utils.ner_extractor import ner_extractor

def test_ner_patterns():
    """测试NER模式识别"""
    
    test_cases = [
        "service d1有什么问题",
        "service D1的内存问题",
        "service-d1 内存泄漏",
        "service_d1异常",
        "Service d1 timeout",
        "service d1",
        "service-d1",
        "service D1",
    ]
    
    for test_case in test_cases:
        print(f"\n测试: '{test_case}'")
        entities = ner_extractor.extract_entities(test_case)
        
        if entities:
            for entity in entities:
                print(f"  找到: {entity.text} [{entity.label}] 置信度={entity.confidence:.3f}")
        else:
            print("  未找到任何实体")
            
    # 测试服务名提取
    print("\n=== 服务名提取测试 ===")
    for test_case in test_cases:
        entities = ner_extractor.extract_entities(test_case)
        services = ner_extractor.get_services(entities)
        print(f"'{test_case}' → 服务名: {services}")

if __name__ == "__main__":
    test_ner_patterns()