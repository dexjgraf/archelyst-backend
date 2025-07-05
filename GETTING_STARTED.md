# 🚀 Archelyst Backend - Complete Getting Started Guide

This comprehensive guide will help you set up the complete Archelyst backend development environment with all services running locally using Docker.

## 📋 What You'll Get

By the end of this guide, you'll have a fully functional development environment with:

- **FastAPI Backend** (port 8000) - Main API server with hot reload
- **PostgreSQL Database** (port 5433) - Primary data storage with pre-configured schemas
- **Redis Cache** (port 6379) - Caching and task queue
- **Neo4j Graph Database** (ports 7474, 7687) - Knowledge graph with APOC and GDS plugins
- **Celery Workers** - Background task processing
- **Celery Beat** - Scheduled task management

## 🛠️ Prerequisites

Before starting, ensure you have:

### Required Software
- **Docker Desktop** (v4.0+) - [Download here](https://www.docker.com/products/docker-desktop/)
- **Git** - For cloning the repository
- **Text Editor** - VS Code, PyCharm, or your preferred editor

### System Requirements
- **RAM**: 8GB minimum (16GB recommended for smooth operation)
- **Disk Space**: 5GB free space for Docker images and volumes
- **Ports**: Ensure these ports are available:
  - 8000 (FastAPI)
  - 5433 (PostgreSQL) 
  - 6379 (Redis)
  - 7474 (Neo4j HTTP)
  - 7687 (Neo4j Bolt)

### Platform Compatibility
✅ **macOS** (Intel & Apple Silicon)  
✅ **Windows** (with WSL2)  
✅ **Linux** (Ubuntu, CentOS, etc.)

## 📥 Step 1: Clone and Setup

### 1.1 Clone the Repository

```bash
# Clone the repository
git clone https://github.com/dexjgraf/archelyst-backend.git
cd archelyst-backend

# Verify you're in the correct directory
ls -la
# You should see: docker-compose.yml, Dockerfile, requirements.txt, etc.
```

### 1.2 Create Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Open .env in your text editor
# Example for VS Code:
code .env

# Example for nano:
nano .env
```

### 1.3 Configure Environment Variables

The `.env` file contains all necessary configuration. **For development**, the default values work fine, but you can customize:

```bash
# Database Configuration (✅ Already configured for Docker)
DATABASE_URL=postgresql+asyncpg://archelyst:password@postgres:5432/archelyst
REDIS_URL=redis://redis:6379/0

# Neo4j Configuration (✅ Already configured for Docker)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Security (✅ Default values work for development)
SECRET_KEY=your_secret_key_here_make_it_long_and_random
ALGORITHM=HS256

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=info

# API Keys (Optional - can be added later)
FMP_API_KEY=your_fmp_api_key_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**💡 Tip**: For development, you can leave the API keys as placeholders. The system will work with mock data.

## 🐳 Step 2: Start the Complete Environment

### 2.1 Start All Services

```bash
# Start all services in the background
docker-compose up -d

# This will:
# 1. Download Docker images (first time only, ~5-10 minutes)
# 2. Build the FastAPI application
# 3. Start all 6 services
# 4. Initialize the databases
```

### 2.2 Monitor the Startup

```bash
# Watch the logs to see everything starting up
docker-compose logs -f

# Or check individual services:
docker-compose logs api
docker-compose logs postgres
docker-compose logs neo4j
docker-compose logs redis
docker-compose logs celery
docker-compose logs celery-beat
```

### 2.3 Verify All Services Are Running

```bash
# Check service status
docker-compose ps

# You should see all services as "Up" or "healthy":
# NAME                              STATUS
# archelyst-backend-api-1           Up (healthy)
# archelyst-backend-postgres-1      Up
# archelyst-backend-redis-1         Up  
# archelyst-backend-neo4j-1         Up
# archelyst-backend-celery-1        Up
# archelyst-backend-celery-beat-1   Up
```

## ✅ Step 3: Verify Everything Works

### 3.1 Test the Main API

```bash
# Test the health endpoint
curl http://localhost:8000/health

# Expected response: {"success": true, "data": {"status": "healthy", ...}}
```

**🌐 Alternative**: Open http://localhost:8000/health in your browser

### 3.2 Access the API Documentation

Open your browser and visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Info**: http://localhost:8000/api/v1/

### 3.3 Test Sample API Endpoints

```bash
# Get a stock quote (mock data)
curl http://localhost:8000/api/v1/securities/quote/AAPL

# Test Neo4j integration
curl http://localhost:8000/api/v1/test/neo4j/status

# Get market overview
curl http://localhost:8000/api/v1/market/overview
```

### 3.4 Access Database Interfaces

#### PostgreSQL
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U archelyst -d archelyst

# Test query
\dt users.*
SELECT name, level FROM users.roles;
\q
```

#### Neo4j Browser
1. Open http://localhost:7474 in your browser
2. Login with:
   - **Username**: `neo4j`
   - **Password**: `password`
3. Test query: `MATCH (c:Company) RETURN c.symbol, c.name`

#### Redis
```bash
# Test Redis
docker-compose exec redis redis-cli ping
# Expected response: PONG
```

## 🔧 Step 4: Development Workflow

### 4.1 Making Code Changes

The FastAPI application supports **hot reload**:

1. Edit any file in the `app/` directory
2. Save the file
3. The API server automatically restarts
4. Test your changes at http://localhost:8000

```bash
# Example: Edit the main API response
echo '# Modified at $(date)' >> app/main.py

# Watch the logs to see the reload
docker-compose logs -f api
```

### 4.2 Database Operations

```bash
# Run database migrations (when available)
docker-compose exec api alembic upgrade head

# Access database directly
docker-compose exec postgres psql -U archelyst -d archelyst

# Reset database (removes all data)
docker-compose down --volumes
docker-compose up -d postgres
```

### 4.3 Managing Background Tasks

```bash
# View Celery worker status
docker-compose logs celery

# View scheduled tasks
docker-compose logs celery-beat

# Execute a test task
docker-compose exec api python -c "
from app.workers.celery_app import debug_task
result = debug_task.delay()
print(f'Task ID: {result.id}')
"
```

## 🛑 Common Issues and Solutions

### Issue 1: Port Already in Use

**Error**: `Port 5432 is already allocated`

**Solution**:
```bash
# Check what's using the port
sudo lsof -i :5432

# Kill the process or change the port in docker-compose.yml
# We already use port 5433 for PostgreSQL to avoid conflicts
```

### Issue 2: Docker Out of Memory

**Error**: Services crashing or slow performance

**Solution**:
```bash
# Increase Docker memory allocation
# Docker Desktop > Settings > Resources > Memory > 8GB+

# Clean up unused Docker resources
docker system prune -a
```

### Issue 3: Neo4j Won't Start

**Error**: Neo4j container keeps restarting

**Solution**:
```bash
# Check Neo4j logs
docker-compose logs neo4j

# Reset Neo4j data
docker-compose down
docker volume rm archelyst-backend_neo4j_data
docker-compose up -d neo4j
```

### Issue 4: API Returns 500 Errors

**Error**: FastAPI endpoints returning server errors

**Solution**:
```bash
# Check API logs
docker-compose logs api

# Common fixes:
# 1. Wait for database to fully initialize
# 2. Check .env configuration
# 3. Restart the API service
docker-compose restart api
```

### Issue 5: Hot Reload Not Working

**Error**: Code changes not reflected

**Solution**:
```bash
# Ensure volume mounts are working
docker-compose down
docker-compose up -d

# Check volume mounts
docker-compose exec api ls -la /app/app/
```

## 🔄 Managing the Environment

### Starting and Stopping

```bash
# Start all services
docker-compose up -d

# Stop all services (keeps data)
docker-compose down

# Stop and remove all data
docker-compose down --volumes

# Restart a specific service
docker-compose restart api

# View service logs
docker-compose logs -f [service-name]
```

### Updating the Code

```bash
# Pull latest changes
git pull origin main

# Rebuild containers if Dockerfile changed
docker-compose up -d --build

# Update Python dependencies
docker-compose build --no-cache api
docker-compose up -d
```

## 📊 Monitoring and Health Checks

### Service Health

```bash
# Check all services
docker-compose ps

# API health check
curl http://localhost:8000/health | jq

# Database health
curl http://localhost:8000/api/v1/status | jq

# Neo4j health
curl http://localhost:8000/api/v1/test/neo4j/status | jq
```

### Resource Monitoring

```bash
# Container resource usage
docker stats

# Service logs
docker-compose logs --tail=50 -f

# Disk usage
docker system df
```

## 🧪 Testing Your Setup

### Run the Complete Test Suite

```bash
# Execute all verification tests
./scripts/verify-setup.sh

# Or manually test each component:

# 1. API Response Test
curl -f http://localhost:8000/health || echo "❌ API not responding"

# 2. Database Test
docker-compose exec postgres psql -U archelyst -d archelyst -c "SELECT 1;" || echo "❌ Database not working"

# 3. Redis Test
docker-compose exec redis redis-cli ping || echo "❌ Redis not working"

# 4. Neo4j Test
curl -f http://localhost:8000/api/v1/test/neo4j/status || echo "❌ Neo4j not working"

# 5. Background Tasks Test
docker-compose exec api python -c "
from app.workers.tasks import system_health_check
result = system_health_check.delay()
print(f'✅ Celery working: {result.id}')
"
```

## 🎯 Next Steps

Now that your environment is running, you can:

### 1. Explore the API
- Visit http://localhost:8000/docs to see all endpoints
- Try the sample endpoints with different stock symbols
- Test the AI-powered analysis features

### 2. Add Real Data
- Sign up for API keys from [Financial Modeling Prep](https://financialmodelingprep.com/)
- Add your keys to the `.env` file
- Restart the services: `docker-compose restart api`

### 3. Develop New Features
- Add new endpoints in `app/api/v1/endpoints/`
- Create new background tasks in `app/workers/tasks.py`
- Expand the Neo4j data model

### 4. Learn the Architecture
- Review `app/core/` for configuration and security
- Explore `app/services/` for business logic
- Check `app/models/` for database schemas

## 📚 Additional Resources

- **[Docker Setup Guide](DOCKER_SETUP.md)** - Detailed Docker configuration
- **[Neo4j Setup Guide](NEO4J_SETUP.md)** - Graph database configuration  
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs
- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** - Framework reference
- **[Neo4j Documentation](https://neo4j.com/docs/)** - Graph database guide

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs**: `docker-compose logs [service-name]`
2. **Verify ports**: `docker-compose ps`
3. **Reset environment**: `docker-compose down --volumes && docker-compose up -d`
4. **Create an issue**: [GitHub Issues](https://github.com/dexjgraf/archelyst-backend/issues)

## 🎉 Success!

**Congratulations!** 🎊 You now have a complete Archelyst backend development environment running with:

- ✅ FastAPI backend with hot reload
- ✅ PostgreSQL database with schemas
- ✅ Redis caching system  
- ✅ Neo4j graph database with plugins
- ✅ Celery background workers
- ✅ All services containerized and networked

**Your development environment is ready for building financial analytics and AI-powered features!**

---

*Happy coding! 🚀*