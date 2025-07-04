"""
Configuration settings for Archelyst backend.

Centralized configuration management using Pydantic BaseSettings with environment variable loading.
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses Pydantic BaseSettings for type validation and environment variable loading.
    """
    
    # ============================================================================
    # Application Settings
    # ============================================================================
    
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Archelyst Python Backend"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "High-performance Python backend for AI-enhanced financial data and analytics"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, production, test")
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # ============================================================================
    # Database Configuration
    # ============================================================================
    
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://archelyst:password@localhost:5432/archelyst",
        description="PostgreSQL database URL for async connections"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, description="Database max overflow connections")
    DATABASE_ECHO: bool = Field(default=False, description="Enable SQLAlchemy query logging")
    
    # ============================================================================
    # Redis Configuration
    # ============================================================================
    
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and background tasks"
    )
    CACHE_TTL_SECONDS: int = Field(default=300, description="Default cache TTL (5 minutes)")
    MARKET_DATA_CACHE_TTL: int = Field(default=60, description="Market data cache TTL (1 minute)")
    
    # ============================================================================
    # Data Provider API Keys
    # ============================================================================
    
    # Financial Modeling Prep (Primary)
    FMP_API_KEY: Optional[str] = Field(
        default=None,
        description="Financial Modeling Prep API key"
    )
    FMP_BASE_URL: str = Field(
        default="https://financialmodelingprep.com/api/v3",
        description="FMP API base URL"
    )
    FMP_RATE_LIMIT: int = Field(default=250, description="FMP requests per minute")
    
    # Alpha Vantage (Secondary)
    ALPHA_VANTAGE_API_KEY: Optional[str] = Field(
        default=None,
        description="Alpha Vantage API key (optional)"
    )
    ALPHA_VANTAGE_BASE_URL: str = Field(
        default="https://www.alphavantage.co/query",
        description="Alpha Vantage API base URL"
    )
    ALPHA_VANTAGE_RATE_LIMIT: int = Field(default=5, description="Alpha Vantage requests per minute")
    
    # Polygon (Optional)
    POLYGON_API_KEY: Optional[str] = Field(
        default=None,
        description="Polygon.io API key (optional)"
    )
    POLYGON_BASE_URL: str = Field(
        default="https://api.polygon.io",
        description="Polygon API base URL"
    )
    
    # Yahoo Finance (Free tier, no key required)
    YAHOO_FINANCE_RATE_LIMIT: int = Field(default=1000, description="Yahoo Finance requests per hour")
    
    # ============================================================================
    # AI Provider API Keys
    # ============================================================================
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key for GPT-4 analysis"
    )
    OPENAI_MODEL: str = Field(default="gpt-4", description="OpenAI model to use")
    OPENAI_MAX_TOKENS: int = Field(default=2000, description="OpenAI max tokens per request")
    OPENAI_TEMPERATURE: float = Field(default=0.1, description="OpenAI temperature (0.0-1.0)")
    
    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="Anthropic API key for Claude analysis"
    )
    ANTHROPIC_MODEL: str = Field(default="claude-3-sonnet-20240229", description="Anthropic model to use")
    ANTHROPIC_MAX_TOKENS: int = Field(default=2000, description="Anthropic max tokens per request")
    
    # Google AI
    GOOGLE_AI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google AI API key (optional)"
    )
    GOOGLE_AI_MODEL: str = Field(default="gemini-pro", description="Google AI model to use")
    
    # ============================================================================
    # Security Configuration
    # ============================================================================
    
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production-please-make-this-very-long-and-random",
        description="Secret key for JWT token generation"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT token expiration in minutes")
    
    # Supabase Integration
    SUPABASE_URL: Optional[str] = Field(
        default=None,
        description="Supabase project URL for frontend integration"
    )
    SUPABASE_ANON_KEY: Optional[str] = Field(
        default=None,
        description="Supabase anonymous key"
    )
    SUPABASE_JWT_SECRET: Optional[str] = Field(
        default=None,
        description="Supabase JWT secret for token validation"
    )
    
    # ============================================================================
    # CORS Configuration
    # ============================================================================
    
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001", 
            "https://archelyst.ai",
            "https://*.archelyst.ai"
        ],
        description="Allowed CORS origins"
    )
    
    # ============================================================================
    # Rate Limiting
    # ============================================================================
    
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, description="API rate limit per minute per user")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, description="API rate limit per hour per user")
    RATE_LIMIT_BURST: int = Field(default=10, description="Rate limit burst allowance")
    
    # ============================================================================
    # Performance & Monitoring
    # ============================================================================
    
    MAX_CONCURRENT_REQUESTS: int = Field(default=100, description="Maximum concurrent requests")
    REQUEST_TIMEOUT: int = Field(default=30, description="Request timeout in seconds")
    HEALTH_CHECK_INTERVAL: int = Field(default=60, description="Health check interval in seconds")
    
    # Metrics and monitoring
    ENABLE_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")
    METRICS_PORT: int = Field(default=8001, description="Metrics endpoint port")
    
    # ============================================================================
    # Background Tasks
    # ============================================================================
    
    # Celery configuration
    CELERY_BROKER_URL: Optional[str] = Field(
        default=None,
        description="Celery broker URL (defaults to REDIS_URL)"
    )
    CELERY_RESULT_BACKEND: Optional[str] = Field(
        default=None,
        description="Celery result backend URL (defaults to REDIS_URL)"
    )
    
    # Task scheduling
    MARKET_DATA_UPDATE_INTERVAL: int = Field(default=60, description="Market data update interval in seconds")
    AI_ANALYSIS_INTERVAL: int = Field(default=300, description="AI analysis interval in seconds")
    CACHE_CLEANUP_INTERVAL: int = Field(default=3600, description="Cache cleanup interval in seconds")
    
    # ============================================================================
    # Neo4j Configuration (Optional)
    # ============================================================================
    
    NEO4J_URI: Optional[str] = Field(
        default="bolt://localhost:7687",
        description="Neo4j database URI for knowledge graph"
    )
    NEO4J_USERNAME: Optional[str] = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: Optional[str] = Field(default="password", description="Neo4j password")
    
    # ============================================================================
    # Model Configuration
    # ============================================================================
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables
    
    # ============================================================================
    # Computed Properties
    # ============================================================================
    
    @property
    def celery_broker_url(self) -> str:
        """Get Celery broker URL, defaulting to Redis URL."""
        return self.CELERY_BROKER_URL or self.REDIS_URL
    
    @property
    def celery_result_backend(self) -> str:
        """Get Celery result backend URL, defaulting to Redis URL."""
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.ENVIRONMENT.lower() == "test"
    
    # ============================================================================
    # Validation Methods
    # ============================================================================
    
    def get_database_url(self, for_alembic: bool = False) -> str:
        """
        Get database URL, optionally formatted for Alembic migrations.
        
        Args:
            for_alembic: If True, return URL without asyncpg driver for Alembic
            
        Returns:
            Database URL string
        """
        if for_alembic:
            return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        return self.DATABASE_URL
    
    def has_ai_provider(self) -> bool:
        """Check if at least one AI provider is configured."""
        return bool(
            self.OPENAI_API_KEY or 
            self.ANTHROPIC_API_KEY or 
            self.GOOGLE_AI_API_KEY
        )
    
    def get_configured_data_providers(self) -> List[str]:
        """Get list of configured data providers."""
        providers = ["yahoo"]  # Always available
        
        if self.FMP_API_KEY:
            providers.append("fmp")
        if self.ALPHA_VANTAGE_API_KEY:
            providers.append("alpha_vantage")
        if self.POLYGON_API_KEY:
            providers.append("polygon")
            
        return providers
    
    def get_configured_ai_providers(self) -> List[str]:
        """Get list of configured AI providers."""
        providers = []
        
        if self.OPENAI_API_KEY:
            providers.append("openai")
        if self.ANTHROPIC_API_KEY:
            providers.append("anthropic")
        if self.GOOGLE_AI_API_KEY:
            providers.append("google")
            
        return providers


# ============================================================================
# Global Settings Instance
# ============================================================================

settings = Settings()


# ============================================================================
# Settings Validation
# ============================================================================

def validate_settings() -> None:
    """
    Validate critical settings on startup.
    
    Raises:
        ValueError: If critical configuration is missing or invalid
    """
    # Check required database configuration
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is required")
    
    # Check required security configuration in production
    if settings.is_production and settings.SECRET_KEY.startswith("dev-secret-key"):
        raise ValueError("SECRET_KEY must be changed from default value in production")
    
    # Check that at least one data provider is available
    if not settings.FMP_API_KEY:
        print("⚠️  Warning: No FMP_API_KEY configured. Only Yahoo Finance will be available.")
    
    # Check that at least one AI provider is configured
    if not settings.has_ai_provider():
        print("⚠️  Warning: No AI providers configured. AI features will be disabled.")
    
    # Validate environment
    valid_environments = ["development", "production", "test"]
    if settings.ENVIRONMENT.lower() not in valid_environments:
        raise ValueError(f"ENVIRONMENT must be one of: {valid_environments}")
    
    print(f"✅ Configuration validated for {settings.ENVIRONMENT} environment")
    print(f"✅ Data providers: {', '.join(settings.get_configured_data_providers())}")
    if settings.has_ai_provider():
        print(f"✅ AI providers: {', '.join(settings.get_configured_ai_providers())}")


# Validate settings on import
if __name__ != "__main__":
    try:
        validate_settings()
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        # Don't raise in import to allow for testing and development