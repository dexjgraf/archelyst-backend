#!/bin/bash

# Archelyst Backend Setup Verification Script
# This script verifies that all services are running correctly

echo "🚀 Archelyst Backend Setup Verification"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track overall status
OVERALL_STATUS=0

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to test HTTP endpoint
test_http() {
    local url=$1
    local description=$2
    local expected_pattern=$3
    
    echo -n "Testing $description... "
    
    response=$(curl -s "$url" 2>/dev/null)
    status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$status_code" = "200" ] && [[ "$response" == *"$expected_pattern"* ]]; then
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (HTTP $status_code)"
        OVERALL_STATUS=1
        return 1
    fi
}

# Function to test Docker service
test_docker_service() {
    local service=$1
    local description=$2
    
    echo -n "Checking $description... "
    
    if docker-compose ps "$service" 2>/dev/null | grep -q "Up"; then
        echo -e "${GREEN}✅ RUNNING${NC}"
        return 0
    else
        echo -e "${RED}❌ NOT RUNNING${NC}"
        OVERALL_STATUS=1
        return 1
    fi
}

echo "📋 Step 1: Prerequisites Check"
echo "-----------------------------"

# Check Docker
echo -n "Docker installed... "
if command_exists docker; then
    echo -e "${GREEN}✅ FOUND${NC}"
else
    echo -e "${RED}❌ NOT FOUND${NC}"
    echo -e "${YELLOW}⚠️  Please install Docker Desktop: https://www.docker.com/products/docker-desktop/${NC}"
    OVERALL_STATUS=1
fi

# Check Docker Compose
echo -n "Docker Compose available... "
if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
    echo -e "${GREEN}✅ FOUND${NC}"
else
    echo -e "${RED}❌ NOT FOUND${NC}"
    echo -e "${YELLOW}⚠️  Docker Compose is required${NC}"
    OVERALL_STATUS=1
fi

# Check if .env file exists
echo -n ".env file exists... "
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ FOUND${NC}"
else
    echo -e "${YELLOW}⚠️  NOT FOUND${NC}"
    echo -e "${YELLOW}   Run: cp .env.example .env${NC}"
fi

echo ""
echo "🐳 Step 2: Docker Services Status"
echo "---------------------------------"

# Check each Docker service
test_docker_service "api" "FastAPI Backend"
test_docker_service "postgres" "PostgreSQL Database"
test_docker_service "redis" "Redis Cache"
test_docker_service "neo4j" "Neo4j Graph Database"
test_docker_service "celery" "Celery Worker"
test_docker_service "celery-beat" "Celery Beat Scheduler"

echo ""
echo "🌐 Step 3: API Endpoints Testing"
echo "--------------------------------"

# Test main API endpoints
test_http "http://localhost:8000/health" "API Health Check" '"success":true'
test_http "http://localhost:8000/api/v1/" "API v1 Root" '"success":true'
test_http "http://localhost:8000/api/v1/securities/quote/AAPL" "Sample Stock Quote" '"symbol":"AAPL"'
test_http "http://localhost:8000/api/v1/market/overview" "Market Overview" '"success":true'

echo ""
echo "🔗 Step 4: Database Connectivity"
echo "--------------------------------"

# Test PostgreSQL
echo -n "PostgreSQL connection... "
if docker-compose exec -T postgres psql -U archelyst -d archelyst -c "SELECT 1;" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ CONNECTED${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    OVERALL_STATUS=1
fi

# Test PostgreSQL schema
echo -n "PostgreSQL schema initialization... "
if docker-compose exec -T postgres psql -U archelyst -d archelyst -c "SELECT name FROM users.roles LIMIT 1;" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ INITIALIZED${NC}"
else
    echo -e "${RED}❌ NOT INITIALIZED${NC}"
    OVERALL_STATUS=1
fi

# Test Redis
echo -n "Redis connection... "
if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    echo -e "${GREEN}✅ CONNECTED${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    OVERALL_STATUS=1
fi

# Test Neo4j
test_http "http://localhost:8000/api/v1/test/neo4j/status" "Neo4j via API" '"status":"connected"'

echo ""
echo "⚙️  Step 5: Background Services"
echo "------------------------------"

# Test Celery
echo -n "Celery worker status... "
if docker-compose logs celery 2>/dev/null | grep -q "ready"; then
    echo -e "${GREEN}✅ READY${NC}"
else
    echo -e "${YELLOW}⚠️  CHECK LOGS${NC}"
fi

# Test Celery Beat
echo -n "Celery beat scheduler... "
if docker-compose logs celery-beat 2>/dev/null | grep -q "Scheduler"; then
    echo -e "${GREEN}✅ RUNNING${NC}"
else
    echo -e "${YELLOW}⚠️  CHECK LOGS${NC}"
fi

echo ""
echo "🎯 Step 6: Access Points Summary"
echo "-------------------------------"

echo -e "${BLUE}🌐 Web Interfaces:${NC}"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • Alternative Docs:   http://localhost:8000/redoc"
echo "   • Neo4j Browser:      http://localhost:7474 (neo4j/password)"
echo ""
echo -e "${BLUE}📡 API Endpoints:${NC}"
echo "   • Health Check:       http://localhost:8000/health"
echo "   • API Root:           http://localhost:8000/api/v1/"
echo "   • Stock Quote:        http://localhost:8000/api/v1/securities/quote/AAPL"
echo "   • Neo4j Status:       http://localhost:8000/api/v1/test/neo4j/status"
echo ""
echo -e "${BLUE}🔧 Direct Database Access:${NC}"
echo "   • PostgreSQL: docker-compose exec postgres psql -U archelyst -d archelyst"
echo "   • Redis:      docker-compose exec redis redis-cli"
echo "   • Neo4j:      docker-compose exec neo4j cypher-shell -u neo4j -p password"

echo ""
echo "📊 Overall Status"
echo "=================="

if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}🎉 SUCCESS! All systems are operational.${NC}"
    echo ""
    echo -e "${GREEN}Your Archelyst backend is ready for development!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Visit http://localhost:8000/docs to explore the API"
    echo "2. Check out the sample endpoints"
    echo "3. Add your API keys to .env for real data"
    echo "4. Start building awesome financial features! 🚀"
else
    echo -e "${RED}❌ ISSUES DETECTED - Some services may not be working correctly.${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check service logs: docker-compose logs [service-name]"
    echo "2. Restart services: docker-compose restart"
    echo "3. Full reset: docker-compose down --volumes && docker-compose up -d"
    echo "4. Check the Getting Started guide: GETTING_STARTED.md"
fi

echo ""
echo "For help:"
echo "• Documentation: GETTING_STARTED.md"
echo "• Docker Guide: DOCKER_SETUP.md"
echo "• Neo4j Guide: NEO4J_SETUP.md"
echo "• Issues: https://github.com/dexjgraf/archelyst-backend/issues"

exit $OVERALL_STATUS