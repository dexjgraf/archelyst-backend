"""
Database configuration and session management for Archelyst backend.

Async SQLAlchemy setup with PostgreSQL, connection pooling, and session management.
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy import MetaData, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError

from .config import settings

# ============================================================================
# Logger Setup
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# Database Metadata and Base Model
# ============================================================================

# Custom metadata with naming convention for constraints
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)


class Base(DeclarativeBase):
    """
    Base class for all database models.
    
    Provides common functionality and metadata for all models.
    """
    metadata = metadata
    
    def __repr__(self) -> str:
        """String representation of model instances."""
        class_name = self.__class__.__name__
        attributes = []
        
        # Get primary key columns for representation
        for column in self.__table__.primary_key.columns:
            value = getattr(self, column.name, None)
            attributes.append(f"{column.name}={value}")
        
        return f"<{class_name}({', '.join(attributes)})>"


# For backward compatibility with older SQLAlchemy patterns
DeclarativeBase = Base

# ============================================================================
# Database Engine and Session Configuration
# ============================================================================

class DatabaseManager:
    """
    Database manager class for handling async database operations.
    
    Manages engine creation, session lifecycle, and connection health.
    """
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._initialized:
            return
        
        # Create async engine with connection pooling
        # Note: AsyncPG handles its own connection pooling, so we use NullPool for SQLAlchemy
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            future=True,
            poolclass=NullPool,  # AsyncPG handles pooling internally
            connect_args={
                "command_timeout": 30,  # Command timeout in seconds
                "server_settings": {
                    "application_name": "archelyst_backend",
                }
            }
        )
        
        # Create async session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=True,          # Auto-flush before queries
            autocommit=False         # Explicit transaction control
        )
        
        # Add event listeners for logging and monitoring
        self._setup_event_listeners()
        
        self._initialized = True
        logger.info("Database manager initialized successfully")
    
    def _setup_event_listeners(self) -> None:
        """Setup SQLAlchemy event listeners for monitoring and logging."""
        if not self.engine:
            return
        
        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Log successful database connections."""
            logger.debug("New database connection established")
        
        @event.listens_for(self.engine.sync_engine, "close")
        def on_close(dbapi_connection, connection_record):
            """Log database connection closures."""
            logger.debug("Database connection closed")
        
        @event.listens_for(self.engine.sync_engine, "handle_error")
        def on_error(exception_context):
            """Log database errors."""
            logger.error(
                f"Database error: {exception_context.original_exception}",
                exc_info=exception_context.original_exception
            )
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    
    async def drop_tables(self) -> None:
        """Drop all database tables (use with caution)."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("All database tables dropped")
    
    async def check_connection(self) -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if not self.engine:
            return False
        
        try:
            async with self.engine.begin() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close database engine and cleanup resources."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database engine closed")
        
        self._initialized = False


# ============================================================================
# Global Database Manager Instance
# ============================================================================

# Global database manager instance
db_manager = DatabaseManager()


# ============================================================================
# Session Management Functions
# ============================================================================

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session for manual use.
    
    Yields:
        AsyncSession: Database session
    
    Example:
        async with get_async_session() as session:
            result = await session.execute(select(User))
    """
    if not db_manager.session_factory:
        db_manager.initialize()
    
    async with db_manager.session_factory() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error in database session: {e}")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with automatic transaction management.
    
    Automatically commits on success and rolls back on error.
    
    Yields:
        AsyncSession: Database session with transaction
    
    Example:
        async with get_db_transaction() as session:
            user = User(name="John")
            session.add(user)
            # Automatically commits here
    """
    if not db_manager.session_factory:
        db_manager.initialize()
    
    async with db_manager.session_factory() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error in database transaction: {e}")
            raise
        finally:
            await session.close()


# ============================================================================
# FastAPI Dependency Functions
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Provides async database session to FastAPI endpoints with proper
    cleanup and error handling.
    
    Yields:
        AsyncSession: Database session for use in endpoints
    
    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    if not db_manager.session_factory:
        db_manager.initialize()
    
    async with db_manager.session_factory() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database dependency error: {e}")
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error in database dependency: {e}")
            raise


async def get_db_with_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions with automatic transaction management.
    
    Automatically commits successful operations and rolls back on errors.
    Use this for endpoints that modify data.
    
    Yields:
        AsyncSession: Database session with transaction management
    
    Example:
        @app.post("/users")
        async def create_user(
            user_data: UserCreate,
            db: AsyncSession = Depends(get_db_with_transaction)
        ):
            user = User(**user_data.dict())
            db.add(user)
            # Automatically commits here
            return user
    """
    if not db_manager.session_factory:
        db_manager.initialize()
    
    async with db_manager.session_factory() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database transaction dependency error: {e}")
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error in database transaction dependency: {e}")
            raise


# ============================================================================
# Database Health and Utilities
# ============================================================================

async def check_database_health() -> dict:
    """
    Check database health and return status information.
    
    Returns:
        dict: Database health status and connection info
    """
    health_info = {
        "database_initialized": db_manager._initialized,
        "connection_healthy": False,
        "engine_disposed": False,
        "pool_info": {}
    }
    
    if not db_manager.engine:
        return health_info
    
    try:
        # Check connection health
        health_info["connection_healthy"] = await db_manager.check_connection()
        
        # Get pool information
        pool = db_manager.engine.pool
        health_info["pool_info"] = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "invalidated": pool.invalidated(),
            "overflow": pool.overflow()
        }
        
        health_info["engine_disposed"] = db_manager.engine.closed
        
    except Exception as e:
        logger.error(f"Error checking database health: {e}")
        health_info["error"] = str(e)
    
    return health_info


async def initialize_database() -> None:
    """
    Initialize database connection and create tables if needed.
    
    This function should be called on application startup.
    """
    try:
        # Initialize database manager
        db_manager.initialize()
        
        # Check connection
        if await db_manager.check_connection():
            logger.info("Database connection established successfully")
        else:
            logger.error("Failed to establish database connection")
            raise RuntimeError("Database connection failed")
        
        # Create tables (this is idempotent)
        await db_manager.create_tables()
        
        logger.info("Database initialization completed")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_database() -> None:
    """
    Close database connections and cleanup resources.
    
    This function should be called on application shutdown.
    """
    try:
        await db_manager.close()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


# ============================================================================
# Database Utilities for Testing
# ============================================================================

async def reset_database() -> None:
    """
    Reset database by dropping and recreating all tables.
    
    WARNING: This will destroy all data! Use only for testing.
    """
    if settings.is_production:
        raise RuntimeError("Cannot reset database in production environment")
    
    logger.warning("Resetting database - all data will be lost")
    
    try:
        await db_manager.drop_tables()
        await db_manager.create_tables()
        logger.info("Database reset completed")
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        raise


# ============================================================================
# Context Manager for Database Operations
# ============================================================================

class DatabaseContext:
    """
    Context manager for database operations with automatic session management.
    
    Example:
        async with DatabaseContext() as db:
            user = await db.execute(select(User))
    """
    
    def __init__(self, auto_commit: bool = False):
        """
        Initialize database context.
        
        Args:
            auto_commit: Whether to automatically commit transactions
        """
        self.auto_commit = auto_commit
        self.session: Optional[AsyncSession] = None
    
    async def __aenter__(self) -> AsyncSession:
        """Enter async context and create session."""
        if not db_manager.session_factory:
            db_manager.initialize()
        
        self.session = db_manager.session_factory()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context and cleanup session."""
        if self.session:
            try:
                if exc_type is None and self.auto_commit:
                    await self.session.commit()
                elif exc_type is not None:
                    await self.session.rollback()
            except Exception as e:
                logger.error(f"Error in database context cleanup: {e}")
            finally:
                await self.session.close()


# ============================================================================
# Export All Public APIs
# ============================================================================

__all__ = [
    # Base classes
    "Base",
    "DeclarativeBase",
    
    # Database manager
    "db_manager",
    "DatabaseManager",
    
    # Session functions
    "get_async_session",
    "get_db_transaction",
    
    # FastAPI dependencies
    "get_db",
    "get_db_with_transaction",
    
    # Initialization and health
    "initialize_database",
    "close_database",
    "check_database_health",
    
    # Utilities
    "reset_database",
    "DatabaseContext",
]