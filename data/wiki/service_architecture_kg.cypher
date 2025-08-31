// AIOps Demo System - Service Architecture Knowledge Graph
// This script builds the knowledge graph for root cause analysis training

// Clear existing data
MATCH (n) DETACH DELETE n;

// Create Service Nodes
CREATE (a:Service {
  name: 'service-a',
  type: 'api-gateway', 
  description: 'Main entry point for all requests',
  deployment_location: 'dc-east',
  instances: 1,
  technology: 'Spring Boot',
  port: 8080,
  health_endpoint: '/health'
});

CREATE (b:Service {
  name: 'service-b',
  type: 'business-logic',
  description: 'Business logic processing service',
  deployment_location: 'dc-east', 
  instances: 1,
  technology: 'Java',
  port: 8081,
  health_endpoint: '/health'
});

CREATE (c:Service {
  name: 'service-c',
  type: 'business-logic',
  description: 'Alternative business logic service', 
  deployment_location: 'dc-east',
  instances: 1,
  technology: 'Node.js',
  port: 8082,
  health_endpoint: '/status'
});

CREATE (f:Service {
  name: 'service-f',
  type: 'external-integration',
  description: 'External payment and integration service',
  deployment_location: 'dc-west',
  instances: 1, 
  technology: 'Python Flask',
  port: 8085,
  health_endpoint: '/health'
});

// Create Service D instances (distributed service)
CREATE (d1:Service {
  name: 'service-d1',
  type: 'data-processing',
  description: 'Data processing service instance 1',
  deployment_location: 'dc-east',
  parent_service: 'service-d',
  instance_id: 1,
  technology: 'Java',
  port: 8083,
  health_endpoint: '/health'
});

CREATE (d2:Service {
  name: 'service-d2', 
  type: 'data-processing',
  description: 'Data processing service instance 2',
  deployment_location: 'dc-east',
  parent_service: 'service-d',
  instance_id: 2,
  technology: 'Java',
  port: 8083,
  health_endpoint: '/health'
});

CREATE (d3:Service {
  name: 'service-d3',
  type: 'data-processing', 
  description: 'Data processing service instance 3',
  deployment_location: 'dc-east',
  parent_service: 'service-d',
  instance_id: 3,
  technology: 'Java',
  port: 8083,
  health_endpoint: '/health'
});

// Create Service Dependencies (Call Paths)
MATCH (a:Service {name: 'service-a'})
MATCH (b:Service {name: 'service-b'})
CREATE (a)-[:CALLS {
  path_type: 'primary_business',
  expected_ratio: 0.6,
  timeout_ms: 5000,
  retry_count: 3
}]->(b);

MATCH (a:Service {name: 'service-a'})
MATCH (c:Service {name: 'service-c'}) 
CREATE (a)-[:CALLS {
  path_type: 'secondary_business',
  expected_ratio: 0.4,
  timeout_ms: 8000,
  retry_count: 2
}]->(c);

MATCH (b:Service {name: 'service-b'})
MATCH (d1:Service {name: 'service-d1'})
CREATE (b)-[:CALLS {
  path_type: 'load_balanced',
  load_balance_weight: 0.33,
  timeout_ms: 3000,
  retry_count: 2
}]->(d1);

MATCH (b:Service {name: 'service-b'})
MATCH (d2:Service {name: 'service-d2'})
CREATE (b)-[:CALLS {
  path_type: 'load_balanced',
  load_balance_weight: 0.33, 
  timeout_ms: 3000,
  retry_count: 2
}]->(d2);

MATCH (b:Service {name: 'service-b'})
MATCH (d3:Service {name: 'service-d3'})
CREATE (b)-[:CALLS {
  path_type: 'load_balanced',
  load_balance_weight: 0.34,
  timeout_ms: 3000,
  retry_count: 2
}]->(d3);

MATCH (c:Service {name: 'service-c'})
MATCH (f:Service {name: 'service-f'})
CREATE (c)-[:CALLS {
  path_type: 'cross_datacenter',
  timeout_ms: 10000,
  retry_count: 1,
  circuit_breaker: true
}]->(f);

// Create Infrastructure Dependencies
CREATE (db_east:Database {
  name: 'mysql-primary',
  type: 'MySQL',
  location: 'dc-east',
  version: '8.0',
  connection_pool_size: 20
});

CREATE (db_west:Database {
  name: 'postgres-secondary', 
  type: 'PostgreSQL',
  location: 'dc-west',
  version: '14.0',
  connection_pool_size: 15
});

CREATE (ext_payment:ExternalService {
  name: 'payment-gateway-api',
  provider: 'PaymentCorp',
  sla_uptime: 99.9,
  timeout_ms: 5000
});

// Link Services to Infrastructure
MATCH (d1:Service {name: 'service-d1'})
MATCH (db:Database {name: 'mysql-primary'})
CREATE (d1)-[:DEPENDS_ON {connection_type: 'read_write'}]->(db);

MATCH (d2:Service {name: 'service-d2'})
MATCH (db:Database {name: 'mysql-primary'})
CREATE (d2)-[:DEPENDS_ON {connection_type: 'read_write'}]->(db);

MATCH (d3:Service {name: 'service-d3'})
MATCH (db:Database {name: 'mysql-primary'})
CREATE (d3)-[:DEPENDS_ON {connection_type: 'read_write'}]->(db);

MATCH (f:Service {name: 'service-f'})
MATCH (db:Database {name: 'postgres-secondary'})
CREATE (f)-[:DEPENDS_ON {connection_type: 'read_write'}]->(db);

MATCH (f:Service {name: 'service-f'})
MATCH (ext:ExternalService {name: 'payment-gateway-api'})
CREATE (f)-[:DEPENDS_ON {dependency_type: 'external_api'}]->(ext);

// Create Network Segments
CREATE (net_east:NetworkSegment {
  name: 'dc-east-subnet',
  datacenter: 'dc-east',
  cidr: '10.1.0.0/16'
});

CREATE (net_west:NetworkSegment {
  name: 'dc-west-subnet', 
  datacenter: 'dc-west',
  cidr: '10.2.0.0/16'
});

// Link Services to Network Segments
MATCH (s:Service)
WHERE s.deployment_location = 'dc-east'
MATCH (net:NetworkSegment {name: 'dc-east-subnet'})
CREATE (s)-[:DEPLOYED_IN]->(net);

MATCH (s:Service)
WHERE s.deployment_location = 'dc-west'
MATCH (net:NetworkSegment {name: 'dc-west-subnet'})
CREATE (s)-[:DEPLOYED_IN]->(net);

// Add some queries to verify the graph
// Query 1: Show all call paths from service A
// MATCH (a:Service {name: 'service-a'})-[r:CALLS*1..3]->(target:Service)
// RETURN a.name as source, target.name as destination, length(r) as hops;

// Query 2: Show services and their dependencies
// MATCH (s:Service)-[r:DEPENDS_ON]->(dep)
// RETURN s.name as service, type(r) as relationship, dep.name as dependency;

// Query 3: Find potential failure points (services with multiple dependencies)
// MATCH (s:Service)-[r:DEPENDS_ON]->(dep)
// WITH s, count(dep) as dependency_count
// WHERE dependency_count > 1
// RETURN s.name as service, dependency_count;