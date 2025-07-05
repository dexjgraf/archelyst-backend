"""
Main API router for version 1 endpoints.

Combines all endpoint modules and provides centralized routing with
consistent middleware, error handling, and response formats.
"""

import logging
from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

from .endpoints import securities, market, ai, search, neo4j_test
from ...core.deps import get_data_providers_config
from fastapi import Depends

# ============================================================================
# Logger Setup
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# API Router Middleware
# ============================================================================

class APILoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for API-specific request/response logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip if not an API request
        if not request.url.path.startswith('/api/'):
            return await call_next(request)
        
        # Log API request
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        logger.info(
            f"API Request {request_id} - {request.method} {request.url.path} - "
            f"Query: {dict(request.query_params)} - User-Agent: {request.headers.get('user-agent', 'unknown')}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Log API response
        process_time = time.time() - start_time
        logger.info(
            f"API Response {request_id} - Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        
        return response


# ============================================================================
# Main API Router
# ============================================================================

# Create the main API router for v1
api_router = APIRouter(
    prefix="/api/v1",
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)

# ============================================================================
# Include Endpoint Routers
# ============================================================================

# Securities endpoints - stock quotes, profiles, historical data
api_router.include_router(
    securities.router,
    prefix="/securities",
    tags=["Securities"],
    responses={
        404: {"description": "Security not found"},
        422: {"description": "Invalid security symbol"}
    }
)

# Market data endpoints - overview, indices, commodities
api_router.include_router(
    market.router,
    prefix="/market",
    tags=["Market Data"],
    responses={
        503: {"description": "Market data service unavailable"}
    }
)

# AI services endpoints - analysis, predictions, insights
api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI Services"],
    responses={
        503: {"description": "AI service unavailable"},
        429: {"description": "AI service rate limit exceeded"}
    }
)

# Search endpoints - securities search, discovery
api_router.include_router(
    search.router,
    prefix="/search",
    tags=["Search"],
    responses={
        400: {"description": "Invalid search query"}
    }
)

# Neo4j test endpoints - graph database testing
api_router.include_router(
    neo4j_test.router,
    prefix="/test",
    tags=["Testing"],
    responses={
        503: {"description": "Neo4j service unavailable"}
    }
)

# ============================================================================
# API Root Endpoint
# ============================================================================

@api_router.get("/", summary="API Information", tags=["API Info"])
async def api_root():
    """
    Get API version information and available endpoints.
    
    Returns basic information about the API version, available endpoints,
    and documentation links.
    """
    return {
        "success": True,
        "data": {
            "version": "1.0.0",
            "name": "Archelyst API v1",
            "description": "High-performance financial data and AI analytics API",
            "endpoints": {
                "securities": "/api/v1/securities",
                "market": "/api/v1/market", 
                "ai": "/api/v1/ai",
                "search": "/api/v1/search"
            },
            "documentation": {
                "openapi": "/api/v1/openapi.json",
                "swagger": "/docs",
                "redoc": "/redoc"
            },
            "features": [
                "Real-time stock quotes",
                "Historical market data",
                "AI-powered analysis",
                "Securities search",
                "Market overview",
                "Crypto and forex data"
            ]
        },
        "timestamp": time.time()
    }


# ============================================================================
# API Status Endpoint
# ============================================================================

@api_router.get("/status", summary="API Status", tags=["API Info"])
async def api_status(
    provider_config: dict = Depends(get_data_providers_config)
):
    """
    Get API operational status and service health.
    
    Returns information about API service health, data provider status,
    and operational metrics.
    """
    try:
        return {
            "success": True,
            "data": {
                "status": "operational",
                "version": "1.0.0",
                "uptime": "calculated_at_runtime",  # TODO: Implement actual uptime tracking
                "services": {
                    "securities": "operational",
                    "market_data": "operational", 
                    "ai_services": "operational",
                    "search": "operational"
                },
                "data_providers": {
                    "total": provider_config.get("total_providers", 0),
                    "enabled": provider_config.get("enabled_providers", 0),
                    "available_capabilities": provider_config.get("total_capabilities", [])
                },
                "rate_limits": {
                    "authenticated": "1000/hour",
                    "unauthenticated": "100/hour"
                }
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error getting API status: {e}")
        return {
            "success": False,
            "error": {
                "code": 503,
                "message": "Unable to retrieve API status",
                "type": "service_error"
            },
            "timestamp": time.time()
        }


# ============================================================================
# Export API Router
# ============================================================================

__all__ = ["api_router", "APILoggingMiddleware"]