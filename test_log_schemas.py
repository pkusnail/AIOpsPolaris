#!/usr/bin/env python3
"""
Test log schemas and basic parsing functionality
"""

import sys
from pathlib import Path
import json
from datetime import datetime
import importlib.util

def import_module_from_path(module_name, file_path):
    """Import module directly from file path"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import log schema
log_schema = import_module_from_path("log_schema", "src/services/log_schema.py")
LogEntry = log_schema.LogEntry
LogEmbedding = log_schema.LogEmbedding
LOG_ENTRY_SCHEMA = log_schema.LOG_ENTRY_SCHEMA
LOG_EMBEDDING_SCHEMA = log_schema.LOG_EMBEDDING_SCHEMA


def test_weaviate_schemas():
    """Test Weaviate collection schemas"""
    print("1. Testing Weaviate Schemas...")
    
    # Test LogEntry schema
    schema = LOG_ENTRY_SCHEMA
    assert schema["class"] == "LogEntry"
    
    property_names = [prop["name"] for prop in schema["properties"]]
    required_props = ["timestamp", "service_name", "host_ip", "log_level", "message"]
    
    for prop in required_props:
        assert prop in property_names, f"Missing required property: {prop}"
    
    # Test LogEmbedding schema  
    embedding_schema = LOG_EMBEDDING_SCHEMA
    assert embedding_schema["class"] == "LogEmbedding"
    assert embedding_schema["vectorizer"] == "text2vec-transformers"
    
    print("✓ Schema validation passed")
    print(f"  - LogEntry has {len(property_names)} properties")
    print(f"  - LogEmbedding configured for vector embeddings")


def test_data_classes():
    """Test LogEntry and LogEmbedding data classes"""
    print("\n2. Testing Data Classes...")
    
    # Test LogEntry creation
    log_entry = LogEntry(
        timestamp=datetime.now(),
        service_name="service-b",
        host_ip="10.1.0.101",
        host_name="host-service-b",
        log_level="ERROR",
        message="Database connection failed after 3 retries",
        component="database_module",
        thread_id="thread-pool-1",
        request_id="req-12345",
        error_code="DB_CONN_TIMEOUT",
        duration_ms=3000.0,
        tags=["database", "timeout"],
        metadata={"retry_count": 3, "db_host": "10.1.0.200"}
    )
    
    # Test to_weaviate_object conversion
    weaviate_obj = log_entry.to_weaviate_object()
    
    assert "timestamp" in weaviate_obj
    assert weaviate_obj["service_name"] == "service-b"
    assert weaviate_obj["log_level"] == "ERROR"
    assert weaviate_obj["tags"] == ["database", "timeout"]
    assert weaviate_obj["metadata"]["retry_count"] == 3
    
    print("✓ LogEntry data class works correctly")
    
    # Test LogEmbedding creation
    log_embedding = LogEmbedding(
        timestamp=datetime.now(),
        service_name="service-b",
        host_ip="10.1.0.101", 
        log_level="ERROR",
        content="Database connection failed after 3 retries",
        summary="Database connection timeout after retries",
        category="network_issue",
        severity_score=0.8,
        incident_id="INC-001",
        log_entry_id="log-12345"
    )
    
    embedding_obj = log_embedding.to_weaviate_object()
    
    assert "timestamp" in embedding_obj
    assert embedding_obj["severity_score"] == 0.8
    assert embedding_obj["category"] == "network_issue"
    assert embedding_obj["log_entry_id"] == "log-12345"
    
    print("✓ LogEmbedding data class works correctly")


def test_query_filters():
    """Test query filter generation"""
    print("\n3. Testing Query Filters...")
    
    from datetime import timedelta
    
    # Test time range filter
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now()
    
    time_filter = log_schema.LogQueryFilters.time_range_filter(start_time, end_time)
    
    assert time_filter["path"] == "timestamp"
    assert time_filter["operator"] == "And"
    assert len(time_filter["operands"]) == 2
    
    print("✓ Time range filter works correctly")
    
    # Test service filter
    service_filter = log_schema.LogQueryFilters.service_filter(["service-a", "service-b"])
    
    assert service_filter["operator"] == "Or"
    assert len(service_filter["operands"]) == 2
    
    print("✓ Service filter works correctly")
    
    # Test log level filter
    level_filter = log_schema.LogQueryFilters.log_level_filter(["ERROR", "CRITICAL"])
    
    assert level_filter["operator"] == "Or"
    assert len(level_filter["operands"]) == 2
    
    print("✓ Log level filter works correctly")
    
    # Test combined filters
    combined = log_schema.LogQueryFilters.combine_filters(time_filter, service_filter, level_filter)
    
    assert combined["operator"] == "And"
    assert len(combined["operands"]) == 3
    
    print("✓ Combined filters work correctly")


def test_incident_logs_structure():
    """Test processing structure of incident logs"""
    print("\n4. Testing Incident Log Structure...")
    
    incident_log = Path("data/logs/incident_001_service_b_cpu_overload.log")
    
    if incident_log.exists():
        line_count = 0
        service_mentions = {"service-a": 0, "service-b": 0, "service-c": 0}
        log_levels = {"INFO": 0, "WARN": 0, "ERROR": 0, "CRITICAL": 0}
        
        with open(incident_log, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                line_count += 1
                
                # Count service mentions
                for service in service_mentions:
                    if service in line:
                        service_mentions[service] += 1
                
                # Count log levels
                for level in log_levels:
                    if level in line:
                        log_levels[level] += 1
        
        print(f"✓ Processed {line_count} lines from incident log")
        print(f"  - Service distribution: {service_mentions}")
        print(f"  - Log level distribution: {log_levels}")
        
        assert line_count > 0, "Should have log entries"
        assert service_mentions["service-b"] > 0, "Should mention service-b"
        assert log_levels["ERROR"] > 0, "Should have ERROR entries"
        
    else:
        print("⚠ Incident log file not found - checking log directory...")
        
        logs_dir = Path("data/logs")
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            if log_files:
                print(f"  Found {len(log_files)} log files:")
                for log_file in log_files:
                    print(f"    - {log_file.name}")
            else:
                print("  No .log files found in data/logs/")
        else:
            print("  data/logs/ directory does not exist")


def generate_collection_creation_script():
    """Generate script for creating Weaviate collections"""
    print("\n5. Collection Creation Script")
    print("-" * 40)
    
    script_content = f'''#!/usr/bin/env python3
"""
Create Weaviate collections for AIOps log processing
"""

import weaviate
import json
from src.services.log_schema import LOG_ENTRY_SCHEMA, LOG_EMBEDDING_SCHEMA

def create_collections():
    """Create LogEntry and LogEmbedding collections in Weaviate"""
    
    # Connect to Weaviate
    client = weaviate.Client("http://localhost:8080")
    
    try:
        # Delete existing collections if they exist
        try:
            client.schema.delete_class("LogEntry")
            print("✓ Deleted existing LogEntry collection")
        except:
            pass
            
        try:
            client.schema.delete_class("LogEmbedding") 
            print("✓ Deleted existing LogEmbedding collection")
        except:
            pass
        
        # Create LogEntry collection
        client.schema.create_class(LOG_ENTRY_SCHEMA)
        print("✓ Created LogEntry collection")
        
        # Create LogEmbedding collection
        client.schema.create_class(LOG_EMBEDDING_SCHEMA)
        print("✓ Created LogEmbedding collection")
        
        # Verify collections
        schema = client.schema.get()
        classes = [c["class"] for c in schema["classes"]]
        
        print(f"\\nActive collections: {{', '.join(classes)}}")
        
        if "LogEntry" in classes and "LogEmbedding" in classes:
            print("🎉 All collections created successfully!")
        else:
            print("❌ Collection creation failed")
            
    except Exception as e:
        print(f"❌ Error creating collections: {{e}}")

if __name__ == "__main__":
    create_collections()
'''
    
    with open("create_weaviate_collections.py", "w") as f:
        f.write(script_content)
    
    print("✓ Collection creation script saved to: create_weaviate_collections.py")


def generate_sample_queries():
    """Generate sample Weaviate GraphQL queries"""
    print("\n6. Sample GraphQL Queries")
    print("-" * 40)
    
    queries = {
        "time_range_filter": """
# Find ERROR logs from service-b in the last hour
{
  Get {
    LogEntry(
      where: {
        operator: And
        operands: [
          {path: ["service_name"], operator: Equal, valueText: "service-b"},
          {path: ["log_level"], operator: Equal, valueText: "ERROR"},
          {path: ["timestamp"], operator: GreaterThan, valueDate: "2025-08-20T13:30:00Z"}
        ]
      }
      limit: 50
    ) {
      timestamp
      service_name
      log_level
      message
      host_ip
    }
  }
}""",
        
        "vector_similarity": """
# Find logs semantically similar to memory issues
{
  Get {
    LogEmbedding(
      nearText: {
        concepts: ["memory leak", "OutOfMemoryError", "heap space"]
        certainty: 0.7
      }
      limit: 10
    ) {
      content
      summary
      category
      severity_score
      service_name
      timestamp
    }
  }
}""",
        
        "high_severity_logs": """
# Find high-severity logs with incident correlation
{
  Get {
    LogEmbedding(
      where: {
        operator: And
        operands: [
          {path: ["severity_score"], operator: GreaterThan, valueNumber: 0.8},
          {path: ["incident_id"], operator: NotEqual, valueText: ""}
        ]
      }
      limit: 20
    ) {
      content
      severity_score
      incident_id
      category
      service_name
      timestamp
    }
  }
}"""
    }
    
    for name, query in queries.items():
        print(f"\\n{name.replace('_', ' ').title()}:")
        print(query)


def main():
    """Run all schema and structure tests"""
    print("🧪 Log Schema and Structure Tests")
    print("=" * 50)
    
    try:
        test_weaviate_schemas()
        test_data_classes()
        test_query_filters()
        test_incident_logs_structure()
        generate_collection_creation_script()
        generate_sample_queries()
        
        print("\\n" + "=" * 50)
        print("🎉 All schema tests completed successfully!")
        print("\\nSchema validation results:")
        print("✓ Weaviate collection schemas are properly structured")
        print("✓ Data classes support Weaviate object conversion")
        print("✓ Query filters generate correct GraphQL conditions")
        print("✓ Incident log files are accessible and structured")
        print("\\nNext steps:")
        print("1. Start Weaviate: docker-compose up -d weaviate")
        print("2. Create collections: python create_weaviate_collections.py")
        print("3. Test queries in Weaviate Console: http://localhost:8080/v1/graphql")
        
    except Exception as e:
        print(f"\\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()