#!/usr/bin/env python3
"""
Pytest test suite for log processing pipeline
"""

import pytest
import asyncio
from pathlib import Path
import sys
from datetime import datetime, timedelta
import json
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.log_schema import (
    LogEntry, LogEmbedding, 
    LOG_ENTRY_SCHEMA, LOG_EMBEDDING_SCHEMA,
    LogQueryFilters
)
from services.log_indexer import LogParser, LogProcessor, LogIndexer


class TestLogSchemas:
    """Test Weaviate collection schemas"""
    
    def test_log_entry_schema_structure(self):
        """Test LogEntry schema has required fields"""
        assert LOG_ENTRY_SCHEMA["class"] == "LogEntry"
        assert LOG_ENTRY_SCHEMA["vectorizer"] == "none"
        
        prop_names = [p["name"] for p in LOG_ENTRY_SCHEMA["properties"]]
        required = ["timestamp", "service_name", "host_ip", "log_level", "message"]
        
        for field in required:
            assert field in prop_names, f"Missing required field: {field}"
    
    def test_log_embedding_schema_structure(self):
        """Test LogEmbedding schema has vector configuration"""
        assert LOG_EMBEDDING_SCHEMA["class"] == "LogEmbedding"
        assert LOG_EMBEDDING_SCHEMA["vectorizer"] == "text2vec-transformers"
        
        # Check vector generation fields
        module_config = LOG_EMBEDDING_SCHEMA["moduleConfig"]["text2vec-transformers"]
        assert "content" in module_config["textFields"]
        assert "summary" in module_config["textFields"]
    
    def test_log_entry_dataclass(self):
        """Test LogEntry dataclass and Weaviate conversion"""
        entry = LogEntry(
            timestamp=datetime.now(),
            service_name="test-service",
            host_ip="10.0.0.1",
            host_name="test-host",
            log_level="ERROR",
            message="Test error message",
            tags=["test", "error"]
        )
        
        weaviate_obj = entry.to_weaviate_object()
        
        assert weaviate_obj["service_name"] == "test-service"
        assert weaviate_obj["log_level"] == "ERROR"
        assert weaviate_obj["tags"] == ["test", "error"]
        assert "timestamp" in weaviate_obj
        assert weaviate_obj["timestamp"].endswith("Z")
    
    def test_log_embedding_dataclass(self):
        """Test LogEmbedding dataclass"""
        embedding = LogEmbedding(
            timestamp=datetime.now(),
            service_name="test-service",
            host_ip="10.0.0.1",
            log_level="ERROR",
            content="Error content",
            summary="Error summary",
            category="network_issue",
            severity_score=0.8
        )
        
        weaviate_obj = embedding.to_weaviate_object()
        
        assert weaviate_obj["category"] == "network_issue"
        assert weaviate_obj["severity_score"] == 0.8
        assert "timestamp" in weaviate_obj


class TestLogParser:
    """Test log parsing functionality"""
    
    @pytest.fixture
    def parser(self):
        return LogParser()
    
    def test_parse_spring_boot_format(self, parser):
        """Test parsing Spring Boot log format"""
        log = "2025-08-20T14:30:22.123Z [INFO ] service-b thread-1: Processing request req-123"
        result = parser.parse_log_line(log)
        
        assert result is not None
        assert result["service_name"] == "service-b"
        assert result["log_level"] == "INFO"
        assert result["thread_id"] == "thread-1"
        assert "Processing request req-123" in result["message"]
    
    def test_parse_nodejs_format(self, parser):
        """Test parsing Node.js log format"""
        log = "2025-08-20T14:31:15.456Z service-c ERROR: Database connection failed"
        result = parser.parse_log_line(log)
        
        assert result is not None
        assert result["service_name"] == "service-c"
        assert result["log_level"] == "ERROR"
        assert "Database connection failed" in result["message"]
    
    def test_parse_python_format(self, parser):
        """Test parsing Python log format"""
        log = "2025-08-20 14:32:30,789 service-f WARNING payment_module: External API slow"
        result = parser.parse_log_line(log)
        
        assert result is not None
        assert result["service_name"] == "service-f"
        assert result["log_level"] == "WARNING"
        assert result["component"] == "payment_module"
    
    def test_parse_invalid_format(self, parser):
        """Test handling of invalid log format"""
        log = "This is not a valid log format"
        result = parser.parse_log_line(log)
        
        assert result is None
    
    def test_extract_metadata(self, parser):
        """Test metadata extraction from logs"""
        log = "2025-08-20T14:30:22.123Z [ERROR] service-b: Request req-123 failed, duration: 3500ms, code: DB_TIMEOUT"
        result = parser.parse_log_line(log)
        
        assert result is not None
        assert result["request_id"] == "req-123"
        assert result["duration_ms"] == 3500.0
        assert result["error_code"] == "DB_TIMEOUT"


class TestLogProcessor:
    """Test log processing and enhancement"""
    
    @pytest.fixture
    def processor(self):
        return LogProcessor()
    
    def test_generate_summary(self, processor):
        """Test summary generation"""
        message = "Database connection failed after 3 retries - Connection timeout to host 10.1.0.200"
        summary = processor.generate_summary(message)
        
        assert len(summary) > 0
        assert len(summary) <= 200
        # Check key terms are in summary
        assert any(term in summary.lower() for term in ["database", "connection", "failed", "timeout"])
    
    def test_classify_log_category(self, processor):
        """Test log categorization"""
        test_cases = [
            ("OutOfMemoryError: Java heap space", "memory_issue"),
            ("Connection timeout to external API", "network_issue"),
            ("CPU usage: 95% for 300 seconds", "performance_issue"),
            ("User login successful for user@example.com", "application_event"),
            ("Unknown error occurred", "unknown")
        ]
        
        for message, expected in test_cases:
            category = processor.classify_log_category(message)
            assert category == expected, f"Expected {expected} for: {message}"
    
    def test_calculate_severity_score(self, processor):
        """Test severity score calculation"""
        test_cases = [
            ("INFO", "User logged in", 0.0, 0.3),
            ("WARN", "Database query slow", 0.3, 0.6),
            ("ERROR", "Connection failed", 0.5, 0.8),
            ("CRITICAL", "Service down", 0.8, 1.0)
        ]
        
        for level, message, min_score, max_score in test_cases:
            score = processor.calculate_severity_score(level, message)
            assert min_score <= score <= max_score, \
                f"Score {score} not in range [{min_score}, {max_score}] for {level}: {message}"
    
    def test_ai_processing_chain(self, processor):
        """Test complete AI processing chain"""
        parsed_log = {
            "timestamp": datetime.now(),
            "service_name": "service-b",
            "log_level": "ERROR",
            "message": "OutOfMemoryError: Java heap space exceeded in processLargeDataset()"
        }
        
        result = processor.process_for_embedding(parsed_log)
        
        assert "summary" in result
        assert "category" in result
        assert "severity_score" in result
        assert result["category"] == "memory_issue"
        assert result["severity_score"] >= 0.7


class TestQueryFilters:
    """Test Weaviate query filter generation"""
    
    def test_time_range_filter(self):
        """Test time range filter generation"""
        start = datetime(2025, 8, 20, 14, 0, 0)
        end = datetime(2025, 8, 20, 15, 0, 0)
        
        filter_obj = LogQueryFilters.time_range_filter(start, end)
        
        assert filter_obj["path"] == "timestamp"
        assert filter_obj["operator"] == "And"
        assert len(filter_obj["operands"]) == 2
        assert filter_obj["operands"][0]["operator"] == "GreaterThanEqual"
        assert filter_obj["operands"][1]["operator"] == "LessThanEqual"
    
    def test_service_filter_single(self):
        """Test service filter with single service"""
        filter_obj = LogQueryFilters.service_filter(["service-a"])
        
        assert filter_obj["path"] == "service_name"
        assert filter_obj["operator"] == "Equal"
        assert filter_obj["valueText"] == "service-a"
    
    def test_service_filter_multiple(self):
        """Test service filter with multiple services"""
        filter_obj = LogQueryFilters.service_filter(["service-a", "service-b"])
        
        assert filter_obj["operator"] == "Or"
        assert len(filter_obj["operands"]) == 2
        for operand in filter_obj["operands"]:
            assert operand["path"] == "service_name"
            assert operand["operator"] == "Equal"
    
    def test_combine_filters(self):
        """Test combining multiple filters"""
        time_filter = LogQueryFilters.time_range_filter(
            datetime.now() - timedelta(hours=1),
            datetime.now()
        )
        service_filter = LogQueryFilters.service_filter(["service-b"])
        level_filter = LogQueryFilters.log_level_filter(["ERROR", "CRITICAL"])
        
        combined = LogQueryFilters.combine_filters(
            time_filter, service_filter, level_filter
        )
        
        assert combined["operator"] == "And"
        assert len(combined["operands"]) == 3


@pytest.mark.asyncio
class TestLogIndexer:
    """Test complete log indexing pipeline"""
    
    @pytest.fixture
    def indexer(self):
        config = {
            "weaviate": {
                "url": "http://localhost:8080",
                "api_key": "test-key"
            }
        }
        return LogIndexer(config)
    
    @pytest.fixture
    def sample_log_file(self):
        """Create a temporary log file for testing"""
        content = """2025-08-20T14:30:00.000Z [INFO ] service-a nginx: Request started GET /api/users
2025-08-20T14:30:05.123Z [INFO ] service-b thread-1: Processing user lookup req-001
2025-08-20T14:30:07.456Z [WARN ] service-b thread-1: Database query slow: 2.3s
2025-08-20T14:30:12.789Z [ERROR] service-b thread-2: OutOfMemoryError in sortLargeDataset()
2025-08-20T14:30:15.234Z [CRITICAL] service-b health-check: Service unhealthy - CPU 98%"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(content)
            return Path(f.name)
    
    async def test_batch_processing(self, indexer, sample_log_file):
        """Test batch processing logic"""
        entries = []
        embeddings = []
        
        # Process log file without actual Weaviate writes
        with open(sample_log_file, 'r') as f:
            for line in f:
                parsed = indexer.parser.parse_log_line(line.strip())
                if parsed:
                    entry = LogEntry(
                        timestamp=parsed["timestamp"],
                        service_name=parsed["service_name"],
                        host_ip="10.1.0.100",
                        host_name=f"host-{parsed['service_name']}",
                        log_level=parsed["log_level"],
                        message=parsed["message"]
                    )
                    entries.append(entry)
                    
                    ai_data = indexer.processor.process_for_embedding(parsed)
                    embedding = LogEmbedding(
                        timestamp=parsed["timestamp"],
                        service_name=parsed["service_name"],
                        host_ip="10.1.0.100",
                        log_level=parsed["log_level"],
                        content=parsed["message"],
                        summary=ai_data["summary"],
                        category=ai_data["category"],
                        severity_score=ai_data["severity_score"]
                    )
                    embeddings.append(embedding)
        
        assert len(entries) == 5
        assert len(embeddings) == 5
        
        # Verify processing quality
        error_count = sum(1 for e in entries if e.log_level in ["ERROR", "CRITICAL"])
        assert error_count == 2
        
        high_severity = sum(1 for e in embeddings if e.severity_score > 0.7)
        assert high_severity >= 2
        
        # Clean up
        sample_log_file.unlink()


class TestRealIncidentLogs:
    """Test processing of real incident log files"""
    
    def test_incident_001_log(self):
        """Test processing incident 001 CPU overload log"""
        log_file = Path("data/logs/incident_001_service_b_cpu_overload.log")
        
        if not log_file.exists():
            pytest.skip("Incident log file not found")
        
        parser = LogParser()
        processor = LogProcessor()
        
        stats = {
            "total": 0,
            "parsed": 0,
            "levels": {},
            "services": set(),
            "categories": {},
            "high_severity": 0
        }
        
        with open(log_file, 'r') as f:
            for line in f:
                stats["total"] += 1
                parsed = parser.parse_log_line(line.strip())
                
                if parsed:
                    stats["parsed"] += 1
                    
                    # Track log levels
                    level = parsed["log_level"]
                    stats["levels"][level] = stats["levels"].get(level, 0) + 1
                    
                    # Track services
                    stats["services"].add(parsed["service_name"])
                    
                    # Process for AI enhancement
                    ai_data = processor.process_for_embedding(parsed)
                    category = ai_data["category"]
                    stats["categories"][category] = stats["categories"].get(category, 0) + 1
                    
                    if ai_data["severity_score"] > 0.7:
                        stats["high_severity"] += 1
        
        # Assertions
        assert stats["parsed"] > 0, "Should parse some log lines"
        assert "ERROR" in stats["levels"], "Should have ERROR logs"
        assert "service-b" in stats["services"], "Should mention service-b"
        assert stats["high_severity"] > 0, "Should have high severity logs"
        
        print(f"Processed {stats['parsed']}/{stats['total']} lines")
        print(f"Services: {stats['services']}")
        print(f"Log levels: {stats['levels']}")
        print(f"Categories: {stats['categories']}")
        print(f"High severity: {stats['high_severity']}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])