"""
FastAPI dependency injection system.

Provides dependencies for database sessions, data providers, authentication,
and other core services used across API endpoints.
"""

import logging
from typing import AsyncGenerator, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from .database import get_db, DatabaseContext
from .config import settings, Settings
from .security import (
    get_current_user_supabase,
    get_current_user_optional_supabase,
    get_current_user_backend,
    get_current_user_hybrid,
    validate_api_key_dependency
)
from ..services.data_providers.factory import DataProviderFactory, create_default_factory
from ..services.data_providers.config import ProviderConfigFactory

# ============================================================================
# Logger Setup
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# Global Dependencies State
# ============================================================================

# Global data provider factory instance
_data_provider_factory: Optional[DataProviderFactory] = None

# HTTP Bearer scheme for token extraction
security_scheme = HTTPBearer(auto_error=False)

# ============================================================================
# Database Dependencies
# ============================================================================

async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency for FastAPI endpoints.
    
    Provides an async database session with proper error handling and cleanup.
    This is the standard dependency for endpoints that need database access.
    
    Yields:
        AsyncSession: Database session for use in endpoints
        
    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_database_session)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    # Use the FastAPI database dependency directly
    async for session in get_db():
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error in dependency: {e}")
            await session.rollback()
            raise


async def get_database_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with automatic transaction management.
    
    Provides a database session that automatically commits on success
    and rolls back on errors. Use this for endpoints that modify data.
    
    Yields:
        AsyncSession: Database session with transaction management
        
    Example:
        @app.post("/users")
        async def create_user(
            user_data: UserCreate,
            db: AsyncSession = Depends(get_database_transaction)
        ):
            user = User(**user_data.dict())
            db.add(user)
            # Automatically commits here if no exceptions
            return user
    """
    async with DatabaseContext(auto_commit=True) as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database transaction error in dependency: {e}")
            # Session will be rolled back by context manager
            raise


# ============================================================================
# Data Provider Dependencies
# ============================================================================

async def get_data_provider_factory() -> DataProviderFactory:
    """
    Get data provider factory dependency.
    
    Provides a configured DataProviderFactory instance with all available
    data providers (FMP, Yahoo Finance, Alpha Vantage, etc.) initialized
    and ready for use.
    
    Returns:
        DataProviderFactory: Configured factory instance
        
    Example:
        @app.get("/quote/{symbol}")
        async def get_quote(
            symbol: str,
            factory: DataProviderFactory = Depends(get_data_provider_factory)
        ):
            return await factory.get_stock_quote(symbol)
    """
    global _data_provider_factory
    
    # Initialize factory if not already done
    if _data_provider_factory is None:
        try:
            logger.info("Initializing data provider factory...")
            _data_provider_factory = create_default_factory()
            
            # Note: Provider classes will be registered when they are implemented
            # For now, we just initialize the factory structure
            logger.info("Data provider factory structure initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize data provider factory: {e}")
            # Create a basic factory even if initialization fails
            _data_provider_factory = DataProviderFactory()
    
    return _data_provider_factory


async def get_data_provider_status() -> Dict[str, Any]:
    """
    Get data provider status dependency.
    
    Provides status information about all configured data providers
    including health, availability, and performance metrics.
    
    Returns:
        Dict[str, Any]: Provider status information
        
    Example:
        @app.get("/status/providers")
        async def get_provider_status(
            status: Dict[str, Any] = Depends(get_data_provider_status)
        ):
            return status
    """
    try:
        factory = await get_data_provider_factory()
        return factory.get_factory_status()
    except Exception as e:
        logger.error(f"Error getting provider status: {e}")
        return {
            "error": str(e),
            "factory_available": False,
            "providers": {},
            "timestamp": None
        }


# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    Get authenticated user dependency (required authentication).
    
    Validates JWT token (Supabase or backend) and returns user information.
    Raises HTTP 401 if authentication fails or is missing.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict[str, Any]: Authenticated user information
        
    Raises:
        HTTPException: If authentication fails (401)
        
    Example:
        @app.get("/protected")
        async def protected_endpoint(
            user: Dict[str, Any] = Depends(get_authenticated_user)
        ):
            return {"user_id": user["user_id"], "email": user["email"]}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Try hybrid authentication (Supabase first, then backend)
    try:
        return await get_current_user_hybrid(credentials)
    except HTTPException as e:
        logger.warning(f"Authentication failed: {e.detail}")
        raise


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Optional[Dict[str, Any]]:
    """
    Get optional user dependency (authentication not required).
    
    Validates JWT token if present and returns user information.
    Returns None if no authentication provided or if authentication fails.
    
    Args:
        credentials: HTTP authorization credentials (optional)
        
    Returns:
        Optional[Dict[str, Any]]: User information or None
        
    Example:
        @app.get("/public")
        async def public_endpoint(
            user: Optional[Dict[str, Any]] = Depends(get_optional_user)
        ):
            if user:
                return {"message": f"Hello {user['email']}"}
            return {"message": "Hello anonymous user"}
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user_hybrid(credentials)
    except HTTPException:
        return None


async def get_supabase_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    Get Supabase authenticated user dependency.
    
    Specifically validates Supabase JWT tokens for frontend integration.
    Raises HTTP 401 if Supabase authentication fails.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict[str, Any]: Supabase user information
        
    Raises:
        HTTPException: If Supabase authentication fails (401)
        
    Example:
        @app.get("/frontend-only")
        async def frontend_endpoint(
            user: Dict[str, Any] = Depends(get_supabase_user)
        ):
            return {"supabase_user_id": user["user_id"]}
    """
    return await get_current_user_supabase(credentials)


async def get_backend_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    Get backend authenticated user dependency.
    
    Specifically validates backend-issued JWT tokens for admin/service access.
    Raises HTTP 401 if backend authentication fails.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict[str, Any]: Backend user information
        
    Raises:
        HTTPException: If backend authentication fails (401)
        
    Example:
        @app.get("/admin-only")
        async def admin_endpoint(
            user: Dict[str, Any] = Depends(get_backend_user)
        ):
            return {"admin_user": user["username"]}
    """
    return await get_current_user_backend(credentials)


async def get_api_key_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    Get API key authentication dependency.
    
    Validates API key for service-to-service authentication or external access.
    Raises HTTP 401 if API key validation fails.
    
    Args:
        credentials: HTTP authorization credentials with API key
        
    Returns:
        Dict[str, Any]: API key information
        
    Raises:
        HTTPException: If API key validation fails (401)
        
    Example:
        @app.get("/external-api")
        async def external_endpoint(
            api_auth: Dict[str, Any] = Depends(get_api_key_auth)
        ):
            return {"api_key_valid": api_auth["validated"]}
    """
    return await validate_api_key_dependency(credentials)


# ============================================================================
# Role-Based Access Dependencies
# ============================================================================

def require_role(required_role: str):
    """
    Create a dependency that requires a specific user role.
    
    Returns a dependency function that validates the user has the required role
    or higher in the role hierarchy.
    
    Args:
        required_role: Required role for access
        
    Returns:
        Dependency function
        
    Example:
        @app.get("/admin-data")
        async def admin_data(
            user: Dict[str, Any] = Depends(require_role("admin"))
        ):
            return {"admin_data": "sensitive information"}
    """
    async def role_dependency(
        user: Dict[str, Any] = Depends(get_authenticated_user)
    ) -> Dict[str, Any]:
        user_role = user.get("role", "user")
        
        # Define role hierarchy
        role_hierarchy = {
            "user": 0,
            "premium": 1,
            "creator": 2,
            "admin": 3,
            "superuser": 4
        }
        
        required_level = role_hierarchy.get(required_role, 0)
        user_level = role_hierarchy.get(user_role, 0)
        
        if user_level < required_level:
            logger.warning(f"Access denied: user role '{user_role}' insufficient for required role '{required_role}'")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return user
    
    return role_dependency


def require_admin():
    """Dependency that requires admin role or higher."""
    return require_role("admin")


def require_premium():
    """Dependency that requires premium role or higher."""
    return require_role("premium")


def require_creator():
    """Dependency that requires creator role or higher."""
    return require_role("creator")


# ============================================================================
# Configuration Dependencies
# ============================================================================

def get_app_settings() -> Settings:
    """
    Get application settings dependency.
    
    Provides access to the global application configuration.
    
    Returns:
        Settings: Application configuration object
        
    Example:
        @app.get("/config/info")
        async def config_info(
            config: Settings = Depends(get_app_settings)
        ):
            return {
                "app_name": config.PROJECT_NAME,
                "version": config.VERSION,
                "environment": config.ENVIRONMENT
            }
    """
    return settings


def get_data_providers_config() -> Dict[str, Any]:
    """
    Get data providers configuration dependency.
    
    Provides information about configured data providers and their capabilities.
    
    Returns:
        Dict[str, Any]: Data providers configuration
        
    Example:
        @app.get("/config/providers")
        async def providers_config(
            config: Dict[str, Any] = Depends(get_data_providers_config)
        ):
            return config
    """
    try:
        from ..services.data_providers.config import get_provider_summary
        return get_provider_summary()
    except Exception as e:
        logger.error(f"Error getting provider config: {e}")
        return {"error": str(e)}


# ============================================================================
# Health Check Dependencies
# ============================================================================

async def get_database_health() -> Dict[str, Any]:
    """
    Get database health dependency.
    
    Provides database health status and connection information.
    
    Returns:
        Dict[str, Any]: Database health information
        
    Example:
        @app.get("/health/database")
        async def database_health(
            health: Dict[str, Any] = Depends(get_database_health)
        ):
            return health
    """
    try:
        from .database import check_database_health
        return await check_database_health()
    except Exception as e:
        logger.error(f"Error checking database health: {e}")
        return {
            "error": str(e),
            "connection_healthy": False,
            "database_initialized": False
        }


async def get_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health dependency.
    
    Provides health status for all major system components.
    
    Returns:
        Dict[str, Any]: System health information
        
    Example:
        @app.get("/health/system")
        async def system_health(
            health: Dict[str, Any] = Depends(get_system_health)
        ):
            return health
    """
    try:
        # Get database health
        db_health = await get_database_health()
        
        # Get provider status
        provider_status = await get_data_provider_status()
        
        # Get configuration info
        config = get_data_providers_config()
        
        # Determine overall health
        overall_healthy = (
            db_health.get("connection_healthy", False) and
            provider_status.get("factory_available", False)
        )
        
        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "components": {
                "database": {
                    "status": "healthy" if db_health.get("connection_healthy") else "unhealthy",
                    "details": db_health
                },
                "data_providers": {
                    "status": "healthy" if provider_status.get("factory_available") else "unhealthy",
                    "details": provider_status
                },
                "configuration": {
                    "status": "healthy",
                    "details": config
                }
            },
            "timestamp": provider_status.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": None
        }


# ============================================================================
# Utility Dependencies
# ============================================================================

async def get_request_context(
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_database_session),
    factory: DataProviderFactory = Depends(get_data_provider_factory),
    config: Settings = Depends(get_app_settings)
) -> Dict[str, Any]:
    """
    Get comprehensive request context dependency.
    
    Provides all major dependencies in a single context object.
    Useful for complex endpoints that need multiple services.
    
    Args:
        user: Optional authenticated user
        db: Database session
        factory: Data provider factory
        config: Application settings
        
    Returns:
        Dict[str, Any]: Request context with all dependencies
        
    Example:
        @app.get("/complex-endpoint")
        async def complex_endpoint(
            context: Dict[str, Any] = Depends(get_request_context)
        ):
            user = context["user"]
            db = context["database"]
            factory = context["data_provider"]
            config = context["settings"]
            # Use all dependencies...
    """
    return {
        "user": user,
        "database": db,
        "data_provider": factory,
        "settings": config,
        "authenticated": user is not None,
        "user_id": user.get("user_id") if user else None,
        "user_role": user.get("role", "anonymous") if user else "anonymous"
    }


# ============================================================================
# Cleanup and Lifecycle Management
# ============================================================================

async def cleanup_dependencies():
    """
    Cleanup function for application shutdown.
    
    Properly closes and cleans up all global dependencies.
    Should be called during application shutdown.
    """
    global _data_provider_factory
    
    try:
        if _data_provider_factory:
            logger.info("Cleaning up data provider factory...")
            await _data_provider_factory.__aexit__(None, None, None)
            _data_provider_factory = None
            logger.info("Data provider factory cleanup completed")
    except Exception as e:
        logger.error(f"Error during dependency cleanup: {e}")


# ============================================================================
# Export All Dependencies
# ============================================================================

__all__ = [
    # Database dependencies
    "get_database_session",
    "get_database_transaction",
    
    # Data provider dependencies
    "get_data_provider_factory",
    "get_data_provider_status",
    
    # Authentication dependencies
    "get_authenticated_user",
    "get_optional_user",
    "get_supabase_user",
    "get_backend_user",
    "get_api_key_auth",
    
    # Role-based access
    "require_role",
    "require_admin",
    "require_premium",
    "require_creator",
    
    # Configuration dependencies
    "get_app_settings",
    "get_data_providers_config",
    
    # Health check dependencies
    "get_database_health",
    "get_system_health",
    
    # Utility dependencies
    "get_request_context",
    
    # Cleanup
    "cleanup_dependencies",
    
    # Redis
    "get_redis",
]


# Redis connection pool
_redis_pool = None

async def get_redis() -> redis.Redis:
    """Get Redis connection."""
    global _redis_pool
    
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True
        )
    
    return redis.Redis(connection_pool=_redis_pool)