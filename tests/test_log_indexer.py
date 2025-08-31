#!/usr/bin/env python3
"""
Test suite for log indexer and Weaviate collections
"""

import asyncio
import pytest
from pathlib import Path
import sys
import json
from datetime import datetime, timedelta
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.log_schema import LogEntry, LogEmbedding, LOG_ENTRY_SCHEMA, LOG_EMBEDDING_SCHEMA
from services.log_indexer import LogIndexer, LogParser, LogProcessor


class TestWeaviateCollections:
    """Test Weaviate collection schemas and operations"""
    
    def test_log_entry_schema_structure(self):
        """Test LogEntry schema structure"""
        schema = LOG_ENTRY_SCHEMA
        
        assert schema["class"] == "LogEntry"
        assert "properties" in schema
        
        # Check critical properties exist
        property_names = [prop["name"] for prop in schema["properties"]]
        required_props = ["timestamp", "service_name", "host_ip", "log_level", "message"]
        
        for prop in required_props:
            assert prop in property_names, f"Missing required property: {prop}"
    
    def test_log_embedding_schema_structure(self):
        """Test LogEmbedding schema structure"""  
        schema = LOG_EMBEDDING_SCHEMA
        
        assert schema["class"] == "LogEmbedding"
        assert schema["vectorizer"] == "text2vec-transformers"
        assert "moduleConfig" in schema
        
        # Check vector generation fields
        text_fields = schema["moduleConfig"]["text2vec-transformers"]["textFields"]
        assert "content" in text_fields
        assert "summary" in text_fields


class TestLogParser:
    """Test log parsing functionality"""
    
    @pytest.fixture
    def parser(self):
        return LogParser()
    
    def test_parse_spring_boot_log(self, parser):
        """Test parsing Spring Boot format logs"""
        log_line = "2025-08-20T14:30:22.123Z [INFO ] service-b thread-pool-1: Processing request req-12345 from 10.1.0.101"
        
        result = parser.parse_log_line(log_line)
        
        assert result is not None
        assert result["service_name"] == "service-b"
        assert result["log_level"] == "INFO"
        assert result["thread_id"] == "thread-pool-1"
        assert "Processing request req-12345" in result["message"]
    
    def test_parse_nodejs_log(self, parser):
        """Test parsing Node.js format logs"""
        log_line = "2025-08-20T14:31:15.456Z service-c ERROR: Database connection failed - Connection timeout after 5000ms"
        
        result = parser.parse_log_line(log_line)
        
        assert result is not None
        assert result["service_name"] == "service-c" 
        assert result["log_level"] == "ERROR"
        assert "Database connection failed" in result["message"]
    
    def test_parse_python_log(self, parser):
        """Test parsing Python format logs"""
        log_line = "2025-08-20 14:32:30,789 service-f WARNING payment_module: External API response time: 3.2s"
        
        result = parser.parse_log_line(log_line)
        
        assert result is not None
        assert result["service_name"] == "service-f"
        assert result["log_level"] == "WARNING"
        assert result["component"] == "payment_module"
    
    def test_parse_invalid_log(self, parser):
        """Test handling of invalid log formats"""
        invalid_line = "This is not a valid log line format"
        
        result = parser.parse_log_line(invalid_line)
        
        # Should return None for unparseable logs
        assert result is None


class TestLogProcessor:
    """Test log processing and enhancement"""
    
    @pytest.fixture
    def processor(self):
        return LogProcessor()
    
    def test_generate_summary(self, processor):
        """Test AI summary generation"""
        message = "Database connection failed after 3 retries - Connection timeout"
        
        summary = processor.generate_summary(message)
        
        assert len(summary) > 0
        assert len(summary) <= 200  # Should be concise
        assert any(word in summary.lower() for word in ["database", "connection", "failed"])
    
    def test_classify_log_category(self, processor):
        """Test log categorization"""
        test_cases = [
            ("OutOfMemoryError: Java heap space", "memory_issue"),
            ("Connection timeout to external API", "network_issue"),
            ("CPU usage: 95% for 300 seconds", "performance_issue"),
            ("User login successful", "application_event")
        ]
        
        for message, expected_category in test_cases:
            category = processor.classify_log_category(message)
            assert category == expected_category
    
    def test_calculate_severity_score(self, processor):
        """Test severity score calculation"""
        test_cases = [
            ("INFO", "User logged in successfully", 0.1),  # Low severity
            ("ERROR", "Database connection failed", 0.7),   # High severity  
            ("CRITICAL", "Service completely unavailable", 0.95)  # Critical
        ]
        
        for log_level, message, expected_min_score in test_cases:
            score = processor.calculate_severity_score(log_level, message)
            assert 0 <= score <= 1
            assert score >= expected_min_score


class TestLogIndexer:
    """Test complete log indexing pipeline"""
    
    @pytest.fixture
    def indexer(self):
        # Use mock configuration for testing
        config = {
            "weaviate": {
                "url": "http://localhost:8080",
                "api_key": "test-key"
            }
        }
        return LogIndexer(config)
    
    def test_create_sample_log_file(self):
        """Create sample log file for testing"""
        sample_logs = [
            "2025-08-20T14:30:00.000Z [INFO ] service-a nginx: Request started GET /api/users",
            "2025-08-20T14:30:05.123Z [INFO ] service-b thread-1: Processing user lookup req-001", 
            "2025-08-20T14:30:07.456Z [WARN ] service-b thread-1: Database query slow: 2.3s",
            "2025-08-20T14:30:12.789Z [ERROR] service-b thread-2: OutOfMemoryError in sortLargeDataset()",
            "2025-08-20T14:30:15.234Z [CRITICAL] service-b health-check: Service unhealthy - CPU 98%",
        ]
        
        # Create temporary log file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write('\n'.join(sample_logs))
            return Path(f.name)
    
    def test_log_file_processing_structure(self, indexer):
        """Test log file processing without actual Weaviate connection"""
        sample_file = self.test_create_sample_log_file()
        
        try:
            # Test parsing only (without Weaviate writes)
            parser = LogParser()
            processor = LogProcessor()
            
            log_entries = []
            log_embeddings = []
            
            with open(sample_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Parse log line
                    parsed = parser.parse_log_line(line)
                    if not parsed:
                        continue
                    
                    # Create LogEntry
                    log_entry = LogEntry(
                        timestamp=parsed["timestamp"],
                        service_name=parsed["service_name"],
                        host_ip=parsed.get("host_ip", "10.1.0.100"),
                        host_name=parsed.get("host_name", f"host-{parsed['service_name']}"),
                        log_level=parsed["log_level"],
                        message=parsed["message"],
                        component=parsed.get("component"),
                        thread_id=parsed.get("thread_id"),
                        request_id=parsed.get("request_id"),
                        error_code=parsed.get("error_code"),
                        duration_ms=parsed.get("duration_ms"),
                        tags=parsed.get("tags"),
                        metadata=parsed.get("metadata")
                    )
                    log_entries.append(log_entry)
                    
                    # Create LogEmbedding
                    summary = processor.generate_summary(parsed["message"])
                    category = processor.classify_log_category(parsed["message"])
                    severity = processor.calculate_severity_score(parsed["log_level"], parsed["message"])
                    
                    log_embedding = LogEmbedding(
                        timestamp=parsed["timestamp"],
                        service_name=parsed["service_name"], 
                        host_ip=parsed.get("host_ip", "10.1.0.100"),
                        log_level=parsed["log_level"],
                        content=parsed["message"],
                        summary=summary,
                        category=category,
                        severity_score=severity,
                        log_entry_id=f"log-{line_num}"
                    )
                    log_embeddings.append(log_embedding)
            
            # Verify processing results
            assert len(log_entries) >= 4  # Should parse most sample logs
            assert len(log_embeddings) == len(log_entries)
            
            # Check data quality
            for entry in log_entries:
                assert entry.service_name in ["service-a", "service-b"]
                assert entry.log_level in ["INFO", "WARN", "ERROR", "CRITICAL"]
                assert len(entry.message) > 0
            
            for embedding in log_embeddings:
                assert 0 <= embedding.severity_score <= 1
                assert len(embedding.summary) > 0
                assert embedding.category in ["network_issue", "performance_issue", "memory_issue", "application_event"]
            
            print(f"✓ Processed {len(log_entries)} log entries successfully")
            print(f"✓ Generated {len(log_embeddings)} embeddings successfully")
            
        finally:
            # Clean up temp file
            sample_file.unlink()
    
    def test_real_incident_log_processing(self, indexer):
        """Test processing real incident log files"""
        incident_log = Path("/home/alejandroseaah/AIOpsPolaris/data/logs/incident_001_service_b_cpu_overload.log")
        
        if incident_log.exists():
            parser = LogParser()
            processor = LogProcessor()
            
            processed_count = 0
            error_logs = 0
            critical_logs = 0
            
            with open(incident_log, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parsed = parser.parse_log_line(line)
                    if parsed:
                        processed_count += 1
                        if parsed["log_level"] == "ERROR":
                            error_logs += 1
                        elif parsed["log_level"] == "CRITICAL":
                            critical_logs += 1
            
            print(f"✓ Processed {processed_count} lines from incident log")
            print(f"✓ Found {error_logs} ERROR and {critical_logs} CRITICAL entries")
            
            assert processed_count > 0, "Should process some log entries"
            assert error_logs > 0, "Incident log should contain ERROR entries"
        else:
            print("⚠ Incident log file not found, skipping real log test")


async def run_integration_test():
    """Run integration test with sample data"""
    print("🧪 Starting Log Indexer Integration Tests")
    print("=" * 50)
    
    # Test schema validation
    print("1. Testing Weaviate schemas...")
    schema_test = TestWeaviateCollections()
    schema_test.test_log_entry_schema_structure()
    schema_test.test_log_embedding_schema_structure()
    print("✓ Schema validation passed")
    
    # Test log parsing
    print("\n2. Testing log parsing...")
    parser_test = TestLogParser()
    parser = LogParser()
    parser_test.test_parse_spring_boot_log(parser)
    parser_test.test_parse_nodejs_log(parser)
    parser_test.test_parse_python_log(parser)
    parser_test.test_parse_invalid_log(parser)
    print("✓ Log parsing tests passed")
    
    # Test log processing
    print("\n3. Testing log processing...")
    processor_test = TestLogProcessor()
    processor = LogProcessor()
    processor_test.test_generate_summary(processor)
    processor_test.test_classify_log_category(processor)
    processor_test.test_calculate_severity_score(processor)
    print("✓ Log processing tests passed")
    
    # Test indexing pipeline
    print("\n4. Testing indexing pipeline...")
    indexer_test = TestLogIndexer()
    config = {"weaviate": {"url": "http://localhost:8080", "api_key": "test"}}
    indexer = LogIndexer(config)
    indexer_test.test_log_file_processing_structure(indexer)
    indexer_test.test_real_incident_log_processing(indexer)
    print("✓ Indexing pipeline tests passed")
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed successfully!")
    print("\nNext steps:")
    print("- Start Weaviate service: docker-compose up weaviate")
    print("- Run actual indexing: python src/services/log_indexer.py")


if __name__ == "__main__":
    asyncio.run(run_integration_test())