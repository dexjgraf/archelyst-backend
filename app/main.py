"""
Main FastAPI application for Archelyst backend.

Core application setup with middleware, CORS, exception handling, and documentation.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from .core.config import settings, validate_settings
from .core.database import initialize_database, close_database
from .core.deps import cleanup_dependencies
from .api.v1.api import api_router

# ============================================================================
# Logger Setup
# ============================================================================

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Custom Middleware Classes
# ============================================================================

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track requests with unique IDs and timing."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Add request ID to response headers
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log request
        logger.info(
            f"Request {request_id} - {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {process_time:.4f}s"
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS header for HTTPS in production
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


# ============================================================================
# Application Lifecycle Events
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting Archelyst backend...")
    
    try:
        # Validate configuration
        validate_settings()
        logger.info("✅ Configuration validation completed")
        
        # Initialize database
        await initialize_database()
        logger.info("✅ Database initialization completed")
        
        # Additional startup tasks can be added here
        # - Initialize Redis connection
        # - Setup background tasks
        # - Initialize data providers
        
        logger.info("🚀 Archelyst backend startup completed successfully")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Archelyst backend...")
        
        try:
            # Cleanup dependencies
            await cleanup_dependencies()
            logger.info("✅ Dependencies cleaned up")
            
            # Close database connections
            await close_database()
            logger.info("✅ Database connections closed")
            
            # Additional cleanup tasks can be added here
            # - Close Redis connections
            # - Stop background tasks
            
            logger.info("✅ Archelyst backend shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}")


# ============================================================================
# FastAPI Application Creation
# ============================================================================

def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    # Create FastAPI app with metadata
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )
    
    # Add middleware (order matters - last added is executed first)
    setup_middleware(app)
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    # Add routes
    setup_routes(app)
    
    return app


def setup_middleware(app: FastAPI) -> None:
    """Setup middleware for the FastAPI application."""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"]
    )
    
    # Trusted host middleware (for production)
    if settings.is_production:
        allowed_hosts = ["*"]  # Configure based on your domain
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    
    # Custom middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestTrackingMiddleware)
    
    logger.info("✅ Middleware configuration completed")


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup global exception handlers."""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions with structured responses."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "http_error"
                },
                "request_id": request_id,
                "timestamp": time.time()
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": 422,
                    "message": "Validation error",
                    "type": "validation_error",
                    "details": exc.errors()
                },
                "request_id": request_id,
                "timestamp": time.time()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Log the error
        logger.error(f"Unhandled exception for request {request_id}: {exc}", exc_info=True)
        
        # Return generic error in production, detailed in development
        if settings.is_production:
            message = "Internal server error"
            details = None
        else:
            message = str(exc)
            details = {
                "type": type(exc).__name__,
                "args": exc.args
            }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": 500,
                    "message": message,
                    "type": "internal_error",
                    "details": details
                },
                "request_id": request_id,
                "timestamp": time.time()
            }
        )
    
    logger.info("✅ Exception handlers configured")


def setup_routes(app: FastAPI) -> None:
    """Setup application routes."""
    
    @app.get("/", tags=["Root"])
    async def root() -> Dict[str, Any]:
        """
        Root endpoint with API information.
        
        Returns basic information about the API and available endpoints.
        """
        return {
            "success": True,
            "data": {
                "name": settings.PROJECT_NAME,
                "description": settings.DESCRIPTION,
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT,
                "documentation": {
                    "swagger_ui": "/docs",
                    "redoc": "/redoc",
                    "openapi_spec": f"{settings.API_V1_STR}/openapi.json"
                },
                "endpoints": {
                    "api_v1": settings.API_V1_STR,
                    "health": "/health",
                    "metrics": "/metrics" if settings.ENABLE_METRICS else None
                }
            },
            "timestamp": time.time()
        }
    
    @app.get("/health", tags=["Health"])
    async def health_check() -> Dict[str, Any]:
        """
        Health check endpoint.
        
        Returns the current health status of the application and its dependencies.
        """
        # Import here to avoid circular imports
        from .core.database import check_database_health
        
        try:
            # Check database health
            db_health = await check_database_health()
            
            # Determine overall health
            overall_healthy = (
                db_health.get("connection_healthy", False) and
                db_health.get("database_initialized", False)
            )
            
            health_status = {
                "success": True,
                "data": {
                    "status": "healthy" if overall_healthy else "unhealthy",
                    "version": settings.VERSION,
                    "environment": settings.ENVIRONMENT,
                    "checks": {
                        "database": {
                            "status": "healthy" if db_health.get("connection_healthy") else "unhealthy",
                            "details": db_health
                        },
                        "configuration": {
                            "status": "healthy",
                            "providers": {
                                "data_providers": settings.get_configured_data_providers(),
                                "ai_providers": settings.get_configured_ai_providers()
                            }
                        }
                    }
                },
                "timestamp": time.time()
            }
            
            # Return appropriate status code
            status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
            
            return JSONResponse(
                status_code=status_code,
                content=health_status
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "success": False,
                    "error": {
                        "code": 503,
                        "message": "Health check failed",
                        "type": "health_check_error"
                    },
                    "timestamp": time.time()
                }
            )
    
    # Include API router
    app.include_router(api_router)
    
    logger.info("✅ Core routes and API endpoints configured")


# ============================================================================
# Application Instance
# ============================================================================

# Create the FastAPI application
app = create_application()

# ============================================================================
# Development Server
# ============================================================================

def run_dev_server():
    """Run the development server with hot reload."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    # Run development server if called directly
    logger.info("Starting development server...")
    run_dev_server()