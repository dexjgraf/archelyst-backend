"""
Provider-specific configuration system for market data providers.

Defines configuration classes for each data provider with API keys, rate limits,
endpoints, and provider-specific settings with environment variable integration.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum
import os

from ...core.config import settings

# ============================================================================
# Logger Setup
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# Provider Configuration Enums
# ============================================================================

class ProviderTier(Enum):
    """Data provider service tiers."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class DataQuality(Enum):
    """Data quality levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PREMIUM = "premium"

class UpdateFrequency(Enum):
    """Data update frequencies."""
    REAL_TIME = "real_time"
    DELAYED_15MIN = "delayed_15min"
    DAILY = "daily"
    WEEKLY = "weekly"

# ============================================================================
# Base Provider Configuration
# ============================================================================

class BaseProviderConfig(BaseModel):
    """
    Base configuration class for all data providers.
    
    Defines common settings that all providers share.
    """
    
    # Basic provider info
    name: str = Field(..., description="Provider name")
    display_name: str = Field(..., description="Human-readable provider name")
    enabled: bool = Field(default=True, description="Whether provider is enabled")
    priority: int = Field(default=100, description="Provider priority (lower = higher priority)")
    
    # API configuration
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    base_url: str = Field(..., description="Base URL for API endpoints")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Initial retry delay in seconds")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=60, description="Requests per minute")
    rate_limit_per_hour: int = Field(default=1000, description="Requests per hour")
    rate_limit_per_day: Optional[int] = Field(default=None, description="Requests per day")
    burst_limit: int = Field(default=10, description="Burst request limit")
    
    # Health monitoring
    health_check_interval: int = Field(default=300, description="Health check interval in seconds")
    circuit_breaker_threshold: int = Field(default=5, description="Failures before circuit breaker opens")
    circuit_breaker_timeout: int = Field(default=60, description="Circuit breaker timeout in seconds")
    
    # Provider capabilities
    supports_stocks: bool = Field(default=True, description="Supports stock data")
    supports_crypto: bool = Field(default=False, description="Supports cryptocurrency data")
    supports_forex: bool = Field(default=False, description="Supports forex data")
    supports_options: bool = Field(default=False, description="Supports options data")
    supports_commodities: bool = Field(default=False, description="Supports commodity data")
    supports_indices: bool = Field(default=True, description="Supports index data")
    
    # Data characteristics
    data_quality: DataQuality = Field(default=DataQuality.MEDIUM, description="Data quality level")
    update_frequency: UpdateFrequency = Field(default=UpdateFrequency.DELAYED_15MIN, description="Data update frequency")
    historical_data_years: int = Field(default=10, description="Years of historical data available")
    
    # Service tier and costs
    tier: ProviderTier = Field(default=ProviderTier.FREE, description="Service tier")
    cost_per_request: Optional[float] = Field(default=None, description="Cost per API request")
    monthly_quota: Optional[int] = Field(default=None, description="Monthly request quota")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        extra = "allow"  # Allow provider-specific fields
    
    @validator('priority')
    def validate_priority(cls, v):
        """Validate priority is positive."""
        if v < 0:
            raise ValueError("Priority must be non-negative")
        return v
    
    @validator('rate_limit_per_minute')
    def validate_rate_limits(cls, v):
        """Validate rate limits are positive."""
        if v <= 0:
            raise ValueError("Rate limits must be positive")
        return v
    
    def get_capabilities(self) -> List[str]:
        """Get list of supported data types."""
        capabilities = []
        if self.supports_stocks:
            capabilities.append("stocks")
        if self.supports_crypto:
            capabilities.append("crypto")
        if self.supports_forex:
            capabilities.append("forex")
        if self.supports_options:
            capabilities.append("options")
        if self.supports_commodities:
            capabilities.append("commodities")
        if self.supports_indices:
            capabilities.append("indices")
        return capabilities
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.dict()


# ============================================================================
# Financial Modeling Prep Configuration
# ============================================================================

class FMPProviderConfig(BaseProviderConfig):
    """
    Configuration for Financial Modeling Prep (FMP) data provider.
    
    Premium provider with comprehensive data coverage and real-time feeds.
    """
    
    name: Literal["fmp"] = Field(default="fmp")
    display_name: Literal["Financial Modeling Prep"] = Field(default="Financial Modeling Prep")
    base_url: str = Field(default="https://financialmodelingprep.com/api/v3")
    
    # FMP-specific settings
    api_key: Optional[str] = Field(default=None, description="FMP API key")
    rate_limit_per_minute: int = Field(default=250, description="FMP rate limit per minute")
    rate_limit_per_hour: int = Field(default=10000, description="FMP rate limit per hour")
    
    # FMP capabilities - comprehensive coverage
    supports_stocks: Literal[True] = Field(default=True)
    supports_crypto: Literal[True] = Field(default=True)
    supports_forex: Literal[True] = Field(default=True)
    supports_commodities: Literal[True] = Field(default=True)
    supports_indices: Literal[True] = Field(default=True)
    supports_options: Literal[False] = Field(default=False)  # Not in v3 API
    
    # Data quality - high quality, real-time data
    data_quality: Literal[DataQuality.HIGH] = Field(default=DataQuality.HIGH)
    update_frequency: Literal[UpdateFrequency.REAL_TIME] = Field(default=UpdateFrequency.REAL_TIME)
    historical_data_years: Literal[20] = Field(default=20)
    
    # Service tier
    tier: Literal[ProviderTier.PREMIUM] = Field(default=ProviderTier.PREMIUM)
    priority: int = Field(default=10, description="High priority provider")
    
    # FMP-specific endpoints
    endpoints: Dict[str, str] = Field(default={
        "quote": "/quote/{symbol}",
        "profile": "/profile/{symbol}",
        "historical": "/historical-price-full/{symbol}",
        "search": "/search",
        "crypto": "/quote/{symbol}",
        "forex": "/fx/{symbol}",
        "commodities": "/quotes/commodity",
        "market_hours": "/market-hours",
        "market_status": "/market_status",
        "gainers": "/gainers",
        "losers": "/losers",
        "active": "/actives"
    })
    
    # API features
    features: Dict[str, bool] = Field(default={
        "real_time_quotes": True,
        "after_hours_data": True,
        "fundamental_data": True,
        "financial_statements": True,
        "insider_trading": True,
        "institutional_holdings": True,
        "analyst_estimates": True,
        "earnings_calendar": True,
        "economic_calendar": True,
        "news_feed": True
    })
    
    @classmethod
    def from_settings(cls) -> 'FMPProviderConfig':
        """Create FMP config from global settings."""
        return cls(
            api_key=settings.FMP_API_KEY,
            base_url=settings.FMP_BASE_URL,
            rate_limit_per_minute=settings.FMP_RATE_LIMIT,
            enabled=bool(settings.FMP_API_KEY)
        )


# ============================================================================
# Yahoo Finance Configuration
# ============================================================================

class YahooFinanceConfig(BaseProviderConfig):
    """
    Configuration for Yahoo Finance data provider.
    
    Free provider with good coverage but rate-limited and delayed data.
    """
    
    name: Literal["yahoo"] = Field(default="yahoo")
    display_name: Literal["Yahoo Finance"] = Field(default="Yahoo Finance")
    base_url: Literal["https://query1.finance.yahoo.com"] = Field(default="https://query1.finance.yahoo.com")
    
    # Yahoo Finance - no API key required
    api_key: Literal[None] = Field(default=None)
    rate_limit_per_minute: int = Field(default=100, description="Conservative rate limit")
    rate_limit_per_hour: int = Field(default=1000, description="Yahoo hourly limit")
    
    # Yahoo capabilities - good free coverage
    supports_stocks: Literal[True] = Field(default=True)
    supports_crypto: Literal[True] = Field(default=True)
    supports_forex: Literal[True] = Field(default=True)
    supports_commodities: Literal[True] = Field(default=True)
    supports_indices: Literal[True] = Field(default=True)
    supports_options: Literal[True] = Field(default=True)
    
    # Data quality - good but delayed
    data_quality: Literal[DataQuality.MEDIUM] = Field(default=DataQuality.MEDIUM)
    update_frequency: Literal[UpdateFrequency.DELAYED_15MIN] = Field(default=UpdateFrequency.DELAYED_15MIN)
    historical_data_years: Literal[10] = Field(default=10)
    
    # Service tier
    tier: Literal[ProviderTier.FREE] = Field(default=ProviderTier.FREE)
    priority: int = Field(default=50, description="Medium priority provider")
    
    # Yahoo-specific endpoints
    endpoints: Dict[str, str] = Field(default={
        "quote": "/v8/finance/chart/{symbol}",
        "profile": "/v10/finance/quoteSummary/{symbol}",
        "historical": "/v8/finance/chart/{symbol}",
        "search": "/v1/finance/search",
        "options": "/v7/finance/options/{symbol}",
        "fundamentals": "/v10/finance/quoteSummary/{symbol}",
        "news": "/v1/finance/search",
        "trending": "/v1/finance/trending/US"
    })
    
    # API features
    features: Dict[str, bool] = Field(default={
        "real_time_quotes": False,
        "after_hours_data": True,
        "fundamental_data": True,
        "financial_statements": True,
        "insider_trading": False,
        "institutional_holdings": True,
        "analyst_estimates": True,
        "earnings_calendar": True,
        "economic_calendar": False,
        "news_feed": True,
        "options_chains": True
    })
    
    # Rate limiting specifics
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt")
    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; Archelyst/1.0; +https://archelyst.ai)",
        description="User agent for requests"
    )
    
    @classmethod
    def from_settings(cls) -> 'YahooFinanceConfig':
        """Create Yahoo Finance config from global settings."""
        return cls(
            rate_limit_per_minute=min(settings.YAHOO_FINANCE_RATE_LIMIT // 60, 100),
            enabled=True  # Always enabled as fallback
        )


# ============================================================================
# Alpha Vantage Configuration
# ============================================================================

class AlphaVantageConfig(BaseProviderConfig):
    """
    Configuration for Alpha Vantage data provider.
    
    Freemium provider with good data quality but strict rate limits.
    """
    
    name: Literal["alpha_vantage"] = Field(default="alpha_vantage")
    display_name: Literal["Alpha Vantage"] = Field(default="Alpha Vantage")
    base_url: str = Field(default="https://www.alphavantage.co/query")
    
    # Alpha Vantage settings
    api_key: Optional[str] = Field(default=None, description="Alpha Vantage API key")
    rate_limit_per_minute: int = Field(default=5, description="Very strict rate limit")
    rate_limit_per_hour: int = Field(default=500, description="Alpha Vantage hourly limit")
    rate_limit_per_day: Optional[int] = Field(default=500, description="Daily limit for free tier")
    
    # Alpha Vantage capabilities
    supports_stocks: Literal[True] = Field(default=True)
    supports_crypto: Literal[True] = Field(default=True)
    supports_forex: Literal[True] = Field(default=True)
    supports_commodities: Literal[False] = Field(default=False)
    supports_indices: Literal[True] = Field(default=True)
    supports_options: Literal[False] = Field(default=False)
    
    # Data quality - high quality but limited
    data_quality: Literal[DataQuality.HIGH] = Field(default=DataQuality.HIGH)
    update_frequency: Literal[UpdateFrequency.DELAYED_15MIN] = Field(default=UpdateFrequency.DELAYED_15MIN)
    historical_data_years: Literal[20] = Field(default=20)
    
    # Service tier
    tier: Literal[ProviderTier.BASIC] = Field(default=ProviderTier.BASIC)
    priority: int = Field(default=30, description="Lower priority due to rate limits")
    
    # Alpha Vantage-specific endpoints
    endpoints: Dict[str, str] = Field(default={
        "quote": "/query?function=GLOBAL_QUOTE",
        "profile": "/query?function=OVERVIEW",
        "historical": "/query?function=TIME_SERIES_DAILY",
        "intraday": "/query?function=TIME_SERIES_INTRADAY",
        "crypto": "/query?function=CURRENCY_EXCHANGE_RATE",
        "forex": "/query?function=FX_DAILY",
        "search": "/query?function=SYMBOL_SEARCH",
        "fundamentals": "/query?function=OVERVIEW",
        "earnings": "/query?function=EARNINGS",
        "news": "/query?function=NEWS_SENTIMENT"
    })
    
    # API features
    features: Dict[str, bool] = Field(default={
        "real_time_quotes": False,
        "after_hours_data": False,
        "fundamental_data": True,
        "financial_statements": True,
        "insider_trading": False,
        "institutional_holdings": False,
        "analyst_estimates": False,
        "earnings_calendar": True,
        "economic_calendar": False,
        "news_feed": True,
        "technical_indicators": True
    })
    
    # Alpha Vantage specific settings
    output_size: str = Field(default="compact", description="Output size: compact or full")
    data_type: str = Field(default="json", description="Data type: json or csv")
    
    @classmethod
    def from_settings(cls) -> 'AlphaVantageConfig':
        """Create Alpha Vantage config from global settings."""
        return cls(
            api_key=settings.ALPHA_VANTAGE_API_KEY,
            base_url=settings.ALPHA_VANTAGE_BASE_URL,
            rate_limit_per_minute=settings.ALPHA_VANTAGE_RATE_LIMIT,
            enabled=bool(settings.ALPHA_VANTAGE_API_KEY)
        )


# ============================================================================
# Polygon Configuration
# ============================================================================

class PolygonConfig(BaseProviderConfig):
    """
    Configuration for Polygon.io data provider.
    
    Premium provider with excellent real-time data and comprehensive coverage.
    """
    
    name: Literal["polygon"] = Field(default="polygon")
    display_name: Literal["Polygon.io"] = Field(default="Polygon.io")
    base_url: str = Field(default="https://api.polygon.io")
    
    # Polygon settings
    api_key: Optional[str] = Field(default=None, description="Polygon API key")
    rate_limit_per_minute: int = Field(default=100, description="Polygon rate limit")
    rate_limit_per_hour: int = Field(default=5000, description="Polygon hourly limit")
    
    # Polygon capabilities - excellent coverage
    supports_stocks: Literal[True] = Field(default=True)
    supports_crypto: Literal[True] = Field(default=True)
    supports_forex: Literal[True] = Field(default=True)
    supports_commodities: Literal[False] = Field(default=False)
    supports_indices: Literal[True] = Field(default=True)
    supports_options: Literal[True] = Field(default=True)
    
    # Data quality - premium real-time
    data_quality: Literal[DataQuality.PREMIUM] = Field(default=DataQuality.PREMIUM)
    update_frequency: Literal[UpdateFrequency.REAL_TIME] = Field(default=UpdateFrequency.REAL_TIME)
    historical_data_years: Literal[15] = Field(default=15)
    
    # Service tier
    tier: Literal[ProviderTier.PREMIUM] = Field(default=ProviderTier.PREMIUM)
    priority: int = Field(default=5, description="Highest priority for real-time data")
    
    # Polygon-specific endpoints
    endpoints: Dict[str, str] = Field(default={
        "quote": "/v2/last/trade/{symbol}",
        "profile": "/v3/reference/tickers/{symbol}",
        "historical": "/v2/aggs/ticker/{symbol}/range/1/day/{from}/{to}",
        "intraday": "/v2/aggs/ticker/{symbol}/range/1/minute/{from}/{to}",
        "crypto": "/v1/last_quote/currencies/{symbol}",
        "forex": "/v1/last_quote/currencies/{symbol}",
        "options": "/v3/options/contracts/{symbol}",
        "search": "/v3/reference/tickers",
        "market_status": "/v1/marketstatus/now",
        "news": "/v2/reference/news"
    })
    
    # API features
    features: Dict[str, bool] = Field(default={
        "real_time_quotes": True,
        "after_hours_data": True,
        "fundamental_data": True,
        "financial_statements": False,
        "insider_trading": False,
        "institutional_holdings": False,
        "analyst_estimates": False,
        "earnings_calendar": False,
        "economic_calendar": False,
        "news_feed": True,
        "options_chains": True,
        "market_data_feeds": True
    })
    
    @classmethod
    def from_settings(cls) -> 'PolygonConfig':
        """Create Polygon config from global settings."""
        return cls(
            api_key=settings.POLYGON_API_KEY,
            base_url=settings.POLYGON_BASE_URL,
            enabled=bool(settings.POLYGON_API_KEY)
        )


# ============================================================================
# Provider Configuration Factory
# ============================================================================

class ProviderConfigFactory:
    """Factory for creating provider configurations."""
    
    # Registry of available provider configs
    _configs = {
        "fmp": FMPProviderConfig,
        "yahoo": YahooFinanceConfig,
        "alpha_vantage": AlphaVantageConfig,
        "polygon": PolygonConfig
    }
    
    @classmethod
    def create_config(cls, provider_name: str, **kwargs) -> BaseProviderConfig:
        """
        Create a provider configuration instance.
        
        Args:
            provider_name: Name of the provider
            **kwargs: Configuration overrides
            
        Returns:
            Provider configuration instance
            
        Raises:
            ValueError: If provider is not supported
        """
        if provider_name not in cls._configs:
            available = list(cls._configs.keys())
            raise ValueError(f"Unsupported provider: {provider_name}. Available: {available}")
        
        config_class = cls._configs[provider_name]
        return config_class(**kwargs)
    
    @classmethod
    def create_from_settings(cls, provider_name: str) -> BaseProviderConfig:
        """
        Create provider configuration from global settings.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider configuration loaded from settings
        """
        if provider_name not in cls._configs:
            available = list(cls._configs.keys())
            raise ValueError(f"Unsupported provider: {provider_name}. Available: {available}")
        
        config_class = cls._configs[provider_name]
        
        # Call the from_settings class method if available
        if hasattr(config_class, 'from_settings'):
            return config_class.from_settings()
        else:
            return config_class()
    
    @classmethod
    def get_all_configs(cls) -> Dict[str, BaseProviderConfig]:
        """
        Get all provider configurations from global settings.
        
        Returns:
            Dictionary of provider configurations
        """
        configs = {}
        
        for provider_name in cls._configs:
            try:
                config = cls.create_from_settings(provider_name)
                configs[provider_name] = config
            except Exception as e:
                logger.warning(f"Failed to create config for {provider_name}: {e}")
        
        return configs
    
    @classmethod
    def get_enabled_configs(cls) -> Dict[str, BaseProviderConfig]:
        """
        Get only enabled provider configurations.
        
        Returns:
            Dictionary of enabled provider configurations
        """
        all_configs = cls.get_all_configs()
        return {name: config for name, config in all_configs.items() if config.enabled}
    
    @classmethod
    def register_provider(cls, name: str, config_class: type) -> None:
        """
        Register a new provider configuration class.
        
        Args:
            name: Provider name
            config_class: Configuration class
        """
        if not issubclass(config_class, BaseProviderConfig):
            raise ValueError("Config class must inherit from BaseProviderConfig")
        
        cls._configs[name] = config_class
        logger.info(f"Registered provider configuration: {name}")
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available provider names."""
        return list(cls._configs.keys())


# ============================================================================
# Configuration Validation and Utilities
# ============================================================================

def validate_provider_config(config: BaseProviderConfig) -> List[str]:
    """
    Validate a provider configuration and return any warnings.
    
    Args:
        config: Provider configuration to validate
        
    Returns:
        List of validation warnings
    """
    warnings = []
    
    # Check API key for non-free providers
    if config.tier != ProviderTier.FREE and not config.api_key:
        warnings.append(f"No API key configured for {config.name} (tier: {config.tier})")
    
    # Check rate limits
    if config.rate_limit_per_minute > 1000:
        warnings.append(f"Very high rate limit for {config.name}: {config.rate_limit_per_minute}/min")
    
    if config.rate_limit_per_minute < 1:
        warnings.append(f"Very low rate limit for {config.name}: {config.rate_limit_per_minute}/min")
    
    # Check timeout settings
    if config.timeout > 60:
        warnings.append(f"High timeout for {config.name}: {config.timeout}s")
    
    if config.timeout < 5:
        warnings.append(f"Low timeout for {config.name}: {config.timeout}s")
    
    return warnings


def get_provider_summary() -> Dict[str, Any]:
    """
    Get a summary of all provider configurations.
    
    Returns:
        Dictionary with provider configuration summary
    """
    configs = ProviderConfigFactory.get_all_configs()
    
    summary = {
        "total_providers": len(configs),
        "enabled_providers": len([c for c in configs.values() if c.enabled]),
        "providers_by_tier": {},
        "providers_by_quality": {},
        "total_capabilities": set(),
        "providers": {}
    }
    
    # Analyze configurations
    for name, config in configs.items():
        # Group by tier
        tier = config.tier
        if tier not in summary["providers_by_tier"]:
            summary["providers_by_tier"][tier] = []
        summary["providers_by_tier"][tier].append(name)
        
        # Group by quality
        quality = config.data_quality
        if quality not in summary["providers_by_quality"]:
            summary["providers_by_quality"][quality] = []
        summary["providers_by_quality"][quality].append(name)
        
        # Collect capabilities
        summary["total_capabilities"].update(config.get_capabilities())
        
        # Provider details
        summary["providers"][name] = {
            "enabled": config.enabled,
            "tier": config.tier,
            "quality": config.data_quality,
            "priority": config.priority,
            "capabilities": config.get_capabilities(),
            "rate_limit": config.rate_limit_per_minute,
            "has_api_key": bool(config.api_key)
        }
    
    summary["total_capabilities"] = list(summary["total_capabilities"])
    return summary


# ============================================================================
# Export All Public APIs
# ============================================================================

__all__ = [
    # Base classes
    "BaseProviderConfig",
    
    # Provider configurations
    "FMPProviderConfig",
    "YahooFinanceConfig", 
    "AlphaVantageConfig",
    "PolygonConfig",
    
    # Enums
    "ProviderTier",
    "DataQuality",
    "UpdateFrequency",
    
    # Factory and utilities
    "ProviderConfigFactory",
    "validate_provider_config",
    "get_provider_summary",
]