# Neo4j Setup Guide for Archelyst Backend

This guide walks you through the complete setup of Neo4j graph database for the Archelyst financial platform.

## Overview

Neo4j is used in Archelyst for:
- **Relationship modeling**: Companies, sectors, industries, portfolios
- **Financial analysis**: Market correlations, dependency tracking
- **Graph algorithms**: Community detection, centrality analysis
- **Knowledge graphs**: Market events, news sentiment connections

## Quick Setup (Using Docker)

### Prerequisites
- Docker and Docker Compose installed
- Ports 7474 and 7687 available

### 1. Start Neo4j with Docker Compose

```bash
# Start all services including Neo4j
docker-compose up -d

# Or start just Neo4j
docker-compose up -d neo4j
```

### 2. Verify Neo4j is Running

```bash
# Check container status
docker-compose ps neo4j

# Check logs
docker-compose logs neo4j

# Test HTTP interface
curl http://localhost:7474/

# Test database connection
docker-compose exec neo4j cypher-shell -u neo4j -p password "RETURN 'Neo4j is working!' as message"
```

### 3. Access Neo4j Browser

Open your browser and go to: `http://localhost:7474`

**Login credentials:**
- Username: `neo4j`
- Password: `password`

## Configuration Details

### Docker Compose Configuration

```yaml
neo4j:
  image: neo4j:5.15
  ports:
    - "7474:7474"  # HTTP
    - "7687:7687"  # Bolt
  environment:
    NEO4J_AUTH: neo4j/password
    NEO4J_PLUGINS: '["apoc","graph-data-science"]'
    NEO4J_dbms_security_procedures_unrestricted: "apoc.*,gds.*"
    NEO4J_server_memory_heap_initial__size: "512M"
    NEO4J_server_memory_heap_max__size: "1G"
  volumes:
    - neo4j_data:/data
    - neo4j_logs:/logs
```

### Environment Variables

```bash
# In .env file
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

## Plugins and Extensions

### APOC (Awesome Procedures on Cypher)
- **Purpose**: Extended procedures and functions
- **Procedures Available**: 191
- **Usage**: Data import/export, graph algorithms, utilities

```cypher
# Example APOC usage
CALL apoc.meta.graph() YIELD nodes, relationships
RETURN nodes, relationships
```

### Graph Data Science (GDS)
- **Purpose**: Graph algorithms and machine learning
- **Procedures Available**: 409
- **Algorithms**: PageRank, Community Detection, Centrality, etc.

```cypher
# Example GDS usage
CALL gds.graph.exists('company-network') YIELD exists
```

## Data Model for Financial Platform

### Core Entities

1. **Companies** (:Company)
   - Properties: symbol, name, market_cap, employees, founded
   - Relationships: BELONGS_TO sector, OPERATES_IN industry

2. **Sectors** (:Sector)
   - Properties: name, description
   - Relationships: CONTAINS industries

3. **Industries** (:Industry)
   - Properties: name, description

4. **Users** (:User)
   - Properties: user_id, email, role, risk_tolerance
   - Relationships: OWNS portfolios

5. **Portfolios** (:Portfolio)
   - Properties: portfolio_id, name, strategy, total_value
   - Relationships: HOLDS companies

6. **Market Events** (:MarketEvent)
   - Properties: event_id, name, date, type, impact
   - Relationships: AFFECTS companies

### Sample Cypher Queries

```cypher
-- Create a company
CREATE (aapl:Company {
  symbol: 'AAPL',
  name: 'Apple Inc.',
  market_cap: 3000000000000,
  founded: 1976
})

-- Find all tech companies
MATCH (c:Company)-[:BELONGS_TO]->(s:Sector {name: 'Technology'})
RETURN c.symbol, c.name, c.market_cap
ORDER BY c.market_cap DESC

-- Find company correlations
MATCH (c1:Company)-[r:CORRELATED_WITH]-(c2:Company)
WHERE r.correlation > 0.7
RETURN c1.symbol, c2.symbol, r.correlation

-- Portfolio analysis
MATCH (u:User)-[:OWNS]->(p:Portfolio)-[:HOLDS]->(h:Holding)-[:OF_COMPANY]->(c:Company)
WHERE u.user_id = 'user_001'
RETURN p.name, c.symbol, h.shares, h.current_price
```

## API Integration

### Testing Neo4j Connection

```bash
# Test Neo4j status
curl http://localhost:8000/api/v1/test/neo4j/status

# Get companies from Neo4j
curl http://localhost:8000/api/v1/test/neo4j/companies
```

### Python Driver Usage

```python
from neo4j import GraphDatabase

# Create driver
driver = GraphDatabase.driver(
    "bolt://neo4j:7687",
    auth=("neo4j", "password")
)

# Execute query
with driver.session() as session:
    result = session.run(
        "MATCH (c:Company) RETURN c.symbol, c.name LIMIT 10"
    )
    companies = [record.data() for record in result]

driver.close()
```

## Troubleshooting

### Common Issues

1. **Neo4j won't start**
   ```bash
   # Check logs
   docker-compose logs neo4j
   
   # Remove volumes and restart
   docker-compose down
   docker volume rm archelyst-backend_neo4j_data archelyst-backend_neo4j_logs
   docker-compose up -d neo4j
   ```

2. **Plugin errors**
   - Verify plugin names in docker-compose.yml
   - Check Neo4j version compatibility
   - Ensure plugins are downloaded during startup

3. **Memory issues**
   ```bash
   # Increase heap size in docker-compose.yml
   NEO4J_server_memory_heap_max__size: "2G"
   ```

4. **Connection refused**
   - Check if ports 7474 and 7687 are available
   - Verify Docker networking
   - Check firewall settings

### Logs and Monitoring

```bash
# View all logs
docker-compose logs neo4j

# Follow logs in real-time
docker-compose logs -f neo4j

# Check container stats
docker stats archelyst-backend-neo4j-1
```

## Performance Tuning

### Database Configuration

```bash
# Increase memory allocation
NEO4J_server_memory_heap_initial__size: "1G"
NEO4J_server_memory_heap_max__size: "2G"

# Query timeout
NEO4J_dbms_transaction_timeout: "60s"

# Page cache
NEO4J_server_memory_pagecache_size: "1G"
```

### Indexing Strategy

```cypher
-- Create indexes for better performance
CREATE INDEX company_symbol IF NOT EXISTS FOR (c:Company) ON (c.symbol);
CREATE INDEX user_email IF NOT EXISTS FOR (u:User) ON (u.email);
CREATE INDEX portfolio_user IF NOT EXISTS FOR (p:Portfolio) ON (p.user_id);

-- Create constraints
CREATE CONSTRAINT company_symbol_unique IF NOT EXISTS 
FOR (c:Company) REQUIRE c.symbol IS UNIQUE;
```

## Security Considerations

### Production Setup

1. **Change default credentials**
   ```bash
   NEO4J_AUTH: secure_username/strong_password_here
   ```

2. **Network security**
   - Use private networks in production
   - Configure SSL/TLS for connections
   - Restrict access to admin ports

3. **Database security**
   ```cypher
   -- Create read-only user
   CREATE USER analyst SET PASSWORD 'secure_password' CHANGE NOT REQUIRED;
   GRANT ROLE reader TO analyst;
   ```

## Backup and Recovery

### Backup Strategy

```bash
# Create backup
docker-compose exec neo4j neo4j-admin dump --database=neo4j --to=/backups/neo4j-backup.dump

# Restore backup
docker-compose exec neo4j neo4j-admin load --from=/backups/neo4j-backup.dump --database=neo4j --force
```

### Data Export

```cypher
-- Export data to CSV
CALL apoc.export.csv.all('/var/lib/neo4j/import/full_export.csv', {})

-- Export specific nodes
CALL apoc.export.csv.query(
  'MATCH (c:Company) RETURN c.symbol, c.name, c.market_cap',
  '/var/lib/neo4j/import/companies.csv',
  {}
)
```

## Development Workflow

### Adding New Data

1. **Design your graph model**
   - Identify entities and relationships
   - Define properties and constraints

2. **Create constraints and indexes**
   ```cypher
   CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
   ```

3. **Load data incrementally**
   ```cypher
   MERGE (c:Company {symbol: 'AAPL'})
   ON CREATE SET c.name = 'Apple Inc.', c.created = datetime()
   ON MATCH SET c.last_updated = datetime()
   ```

4. **Test queries thoroughly**
   - Use EXPLAIN and PROFILE for optimization
   - Monitor query performance

### Integration with FastAPI

The Neo4j endpoints are integrated into the FastAPI application:

- `/api/v1/test/neo4j/status` - Connection and status check
- `/api/v1/test/neo4j/companies` - Sample company data retrieval

## Next Steps

1. **Implement production data loaders**
   - Market data ingestion
   - Real-time price updates
   - News and events correlation

2. **Add graph algorithms**
   - Portfolio risk analysis
   - Market correlation detection
   - Company clustering

3. **Monitoring and alerting**
   - Performance metrics
   - Query optimization
   - Health checks

4. **Scaling considerations**
   - Clustering for high availability
   - Read replicas for analytics
   - Sharding strategies

## Resources

- [Neo4j Documentation](https://neo4j.com/docs/)
- [APOC Documentation](https://neo4j.com/labs/apoc/)
- [Graph Data Science Documentation](https://neo4j.com/docs/graph-data-science/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/)

---

**✅ Neo4j Setup Complete!**

Your Neo4j instance is now fully configured and integrated with the Archelyst backend. You can access the browser interface at http://localhost:7474 and start building graph-based financial analytics.