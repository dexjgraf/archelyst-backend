# 📋 Archelyst Backend - Quick Reference

## 🚀 Essential Commands

### Start/Stop the Environment
```bash
# Start all services
docker-compose up -d

# Stop all services (keeps data)
docker-compose down

# Stop and remove all data
docker-compose down --volumes

# Restart a specific service
docker-compose restart api
```

### Verify Everything is Working
```bash
# Run complete verification
./scripts/verify-setup.sh

# Quick health check
curl http://localhost:8000/health
```

## 🌐 Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **API Documentation** | http://localhost:8000/docs | None |
| **API Health** | http://localhost:8000/health | None |
| **Neo4j Browser** | http://localhost:7474 | neo4j/password |
| **PostgreSQL** | localhost:5433 | archelyst/password |
| **Redis** | localhost:6379 | None |

## 📡 Key API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Stock quote (mock data)
curl http://localhost:8000/api/v1/securities/quote/AAPL

# Market overview
curl http://localhost:8000/api/v1/market/overview

# Neo4j status
curl http://localhost:8000/api/v1/test/neo4j/status

# All available endpoints
curl http://localhost:8000/api/v1/
```

## 🔧 Database Access

### PostgreSQL
```bash
# Connect to database
docker-compose exec postgres psql -U archelyst -d archelyst

# Check user roles
SELECT name, level FROM users.roles;

# Exit
\q
```

### Neo4j
```bash
# Connect via command line
docker-compose exec neo4j cypher-shell -u neo4j -p password

# Check companies
MATCH (c:Company) RETURN c.symbol, c.name;

# Exit
:exit
```

### Redis
```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Test connection
ping

# Exit
exit
```

## 📊 Monitoring

### Check Service Status
```bash
# All services
docker-compose ps

# Service logs
docker-compose logs api
docker-compose logs postgres
docker-compose logs neo4j
docker-compose logs redis
docker-compose logs celery

# Follow logs in real-time
docker-compose logs -f api
```

### Resource Usage
```bash
# Container stats
docker stats

# Docker disk usage
docker system df
```

## 🔄 Development Workflow

### Making Code Changes
1. Edit files in `app/` directory
2. Save the file
3. API automatically reloads (watch logs: `docker-compose logs -f api`)
4. Test changes at http://localhost:8000

### Adding Dependencies
1. Edit `requirements-docker.txt`
2. Rebuild: `docker-compose up -d --build api`

### Database Changes
1. Edit `scripts/init-db.sql`
2. Reset database: `docker-compose down --volumes && docker-compose up -d postgres`

## 🆘 Troubleshooting

### Common Issues

**Port conflicts:**
```bash
# Check what's using port 8000
sudo lsof -i :8000

# Kill process using port
sudo kill -9 <PID>
```

**Services won't start:**
```bash
# Check logs
docker-compose logs [service-name]

# Full reset
docker-compose down --volumes
docker-compose up -d
```

**API returns errors:**
```bash
# Check API logs
docker-compose logs api

# Restart API
docker-compose restart api
```

**Database connection issues:**
```bash
# Reset database
docker-compose down
docker volume rm archelyst-backend_postgres_data
docker-compose up -d postgres
```

**Neo4j issues:**
```bash
# Reset Neo4j
docker-compose down
docker volume rm archelyst-backend_neo4j_data archelyst-backend_neo4j_logs
docker-compose up -d neo4j
```

### Complete Reset
```bash
# Nuclear option - removes everything
docker-compose down --volumes --remove-orphans
docker system prune -a
docker-compose up -d
```

## 📁 Project Structure

```
archelyst-backend/
├── app/
│   ├── api/v1/endpoints/     # API endpoints
│   ├── core/                 # Configuration & security
│   ├── models/              # Database models
│   ├── services/            # Business logic
│   └── workers/             # Background tasks
├── scripts/
│   ├── init-db.sql          # Database initialization
│   ├── neo4j-init.cypher    # Neo4j setup
│   └── verify-setup.sh      # Setup verification
├── docker-compose.yml       # Service orchestration
├── Dockerfile              # API container config
├── .env                    # Environment variables
└── requirements-docker.txt  # Python dependencies
```

## 🔑 Environment Variables

Key variables in `.env`:

```bash
# Database URLs (configured for Docker)
DATABASE_URL=postgresql+asyncpg://archelyst:password@postgres:5432/archelyst
REDIS_URL=redis://redis:6379/0
NEO4J_URI=bolt://neo4j:7687

# API Keys (add your own)
FMP_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Security
SECRET_KEY=your_secret_key_here
ENVIRONMENT=development
DEBUG=true
```

## 📚 Documentation Links

- **[Complete Setup Guide](GETTING_STARTED.md)** - Full setup instructions
- **[Docker Guide](DOCKER_SETUP.md)** - Docker configuration details
- **[Neo4j Guide](NEO4J_SETUP.md)** - Graph database setup
- **[API Docs](http://localhost:8000/docs)** - Interactive API documentation

---

💡 **Pro Tip**: Bookmark this page for quick reference while developing!