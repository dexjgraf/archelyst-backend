# Docker Development Setup

This document describes the Docker configuration for the Archelyst backend development environment.

## Services Overview

The Docker Compose setup includes the following services:

### 1. API Service (FastAPI)
- **Image**: Custom build from Dockerfile
- **Port**: 8000 (external) → 8000 (internal)
- **Features**: 
  - Hot reload for development
  - Health checks enabled
  - Volume mounted for live code changes
  - Non-root user for security

### 2. PostgreSQL Database
- **Image**: postgres:15
- **Port**: 5433 (external) → 5432 (internal)
- **Database**: archelyst
- **User**: archelyst
- **Password**: password
- **Features**:
  - Automatic database initialization via init-db.sql
  - Persistent data storage
  - Pre-configured schemas and roles

### 3. Redis Cache
- **Image**: redis:7-alpine
- **Port**: 6379 (external) → 6379 (internal)
- **Features**:
  - Persistent data with appendonly mode
  - Used for caching and Celery broker

### 4. Neo4j Graph Database
- **Image**: neo4j:5.15
- **Ports**: 
  - 7474 (HTTP)
  - 7687 (Bolt)
- **Auth**: neo4j/password
- **Plugins**: APOC, Graph Data Science

### 5. Celery Worker
- **Image**: Custom build from Dockerfile
- **Features**:
  - Background task processing
  - Hot reload for development
  - Health checks for task processing

### 6. Celery Beat Scheduler
- **Image**: Custom build from Dockerfile
- **Features**:
  - Periodic task scheduling
  - Health checks and monitoring
  - System maintenance tasks

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- Port 8000, 5433, 6379, 7474, 7687 available

### Starting the Services

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
```

### Stopping the Services

```bash
# Stop all services
docker-compose down

# Stop services and remove volumes
docker-compose down --volumes
```

## Configuration Files

### Dockerfile
- Based on Python 3.11 slim
- Installs system dependencies (gcc, curl, git, etc.)
- Uses requirements-docker.txt for Python packages
- Creates non-root user for security
- Includes health check endpoint

### docker-compose.yml
- Defines all 6 services
- Sets up networking and dependencies
- Configures volumes for persistence
- Environment variable configuration

### .env
- Environment variables for all services
- Database URLs configured for Docker networking
- API keys and security settings

### scripts/init-db.sql
- Database initialization script
- Creates schemas: users, securities, market_data, ai_analytics, system
- Sets up user roles and permissions
- Creates indexes for performance

## Development Workflow

### Code Changes
- Files in `/app` directory are volume-mounted
- Changes trigger automatic reload in API service
- No rebuild required for code changes

### Database Changes
- Database persists data between restarts
- To reset database: `docker-compose down --volumes`
- Schema changes require rebuilding init-db.sql

### Adding Dependencies
- Edit requirements-docker.txt
- Rebuild containers: `docker-compose up -d --build`

## Health Checks

### API Health
```bash
curl http://localhost:8000/health
```

### Database Connection
```bash
docker-compose exec postgres psql -U archelyst -d archelyst -c "SELECT version();"
```

### Redis Connection
```bash
docker-compose exec redis redis-cli ping
```

### Neo4j Connection
```bash
curl http://localhost:7474/browser/
```

### Celery Tasks
```bash
docker-compose logs celery | grep "Task.*succeeded"
```

## Troubleshooting

### Port Conflicts
- PostgreSQL uses port 5433 (external) to avoid conflicts
- Change ports in docker-compose.yml if needed

### Container Won't Start
```bash
# Check logs
docker-compose logs [service-name]

# Rebuild if needed
docker-compose up -d --build [service-name]
```

### Database Issues
```bash
# Reset database
docker-compose down --volumes
docker-compose up -d postgres

# Check initialization
docker-compose logs postgres
```

### Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER ./app
```

## Security Considerations

### Development Environment
- Default passwords are used (change for production)
- All services exposed on localhost
- Non-root user in containers
- Security headers middleware enabled

### Production Deployment
- Use secrets management for passwords
- Configure TLS/SSL
- Restrict network access
- Use production-grade images

## Performance Tuning

### PostgreSQL
- Configured with reasonable defaults
- Consider connection pooling for production
- Database uses NullPool (AsyncPG handles pooling)

### Redis
- Appendonly persistence enabled
- Memory usage monitoring recommended

### Celery
- Worker prefetch multiplier set to 1
- Task time limits configured
- Health check tasks run every minute

## Monitoring

### Service Status
```bash
# Check all services
docker-compose ps

# Service health
curl http://localhost:8000/api/v1/status
```

### Resource Usage
```bash
# Container stats
docker stats

# Service logs
docker-compose logs -f --tail=50
```

## File Structure

```
archelyst-backend/
├── Dockerfile                 # API container configuration
├── docker-compose.yml         # Multi-service orchestration
├── requirements-docker.txt    # Python dependencies for Docker
├── .env                      # Environment variables
├── scripts/
│   └── init-db.sql           # Database initialization
├── app/                      # Application code (volume mounted)
│   ├── main.py              # FastAPI application
│   ├── api/                 # API endpoints
│   ├── core/                # Core functionality
│   └── workers/             # Celery tasks
└── DOCKER_SETUP.md          # This documentation
```

## Acceptance Criteria ✅

All acceptance criteria for Issue #11 have been met:

- [x] **Docker Compose runs without errors** - `docker-compose up` works successfully
- [x] **All services start correctly** - API, PostgreSQL, Redis, Neo4j, Celery workers running
- [x] **Health checks work** - API health endpoint returns healthy status
- [x] **API accessible at localhost:8000** - All endpoints responding correctly
- [x] **Database connections work** - PostgreSQL initialized and accessible from API
- [x] **Hot reload works** - Code changes trigger automatic reload
- [x] **Proper volume mounts** - Development files mounted for live editing

## Next Steps

1. Set up CI/CD pipeline with Docker
2. Create production Docker configuration
3. Add monitoring and logging
4. Configure automatic backups
5. Set up development vs production environments