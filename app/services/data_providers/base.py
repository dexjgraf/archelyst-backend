"""
Abstract base class for market data providers.

Defines the standardized interface for all data providers (FMP, Yahoo Finance, 
Alpha Vantage, etc.) enabling hot-swappable data sources with consistent response formats.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import asyncio

# ============================================================================
# Logger Setup
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# Data Provider Enums and Types
# ============================================================================

class DataProviderType(Enum):
    """Types of data providers."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    FALLBACK = "fallback"
    CRYPTO = "crypto"
    OPTIONS = "options"


class SecurityType(Enum):
    """Types of securities supported."""
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    INDEX = "index"
    FOREX = "forex"
    COMMODITY = "commodity"


class DataFrequency(Enum):
    """Data frequency options."""
    REAL_TIME = "real_time"
    MINUTE = "1min"
    FIVE_MINUTE = "5min"
    FIFTEEN_MINUTE = "15min"
    HOUR = "1hour"
    DAILY = "1day"
    WEEKLY = "1week"
    MONTHLY = "1month"


# ============================================================================
# Data Provider Exceptions
# ============================================================================

class DataProviderError(Exception):
    """Base exception for data provider errors."""
    
    def __init__(self, message: str, provider: str = None, status_code: int = None):
        self.message = message
        self.provider = provider
        self.status_code = status_code
        super().__init__(self.message)


class DataProviderConnectionError(DataProviderError):
    """Exception raised when unable to connect to data provider."""
    pass


class DataProviderAuthenticationError(DataProviderError):
    """Exception raised for authentication failures."""
    pass


class DataProviderRateLimitError(DataProviderError):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class DataProviderNotFoundError(DataProviderError):
    """Exception raised when requested data is not found."""
    pass


class DataProviderValidationError(DataProviderError):
    """Exception raised for data validation failures."""
    pass


# ============================================================================
# Response Format Classes
# ============================================================================

class ProviderResponse:
    """Standardized response wrapper for all provider data."""
    
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: str = None,
        provider: str = None,
        timestamp: datetime = None,
        metadata: Dict[str, Any] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.provider = provider
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "provider": self.provider,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


# ============================================================================
# Provider Health and Status
# ============================================================================

class ProviderHealth:
    """Provider health status information."""
    
    def __init__(
        self,
        is_healthy: bool,
        response_time: float = None,
        last_check: datetime = None,
        error_rate: float = None,
        rate_limit_remaining: int = None,
        next_reset: datetime = None
    ):
        self.is_healthy = is_healthy
        self.response_time = response_time
        self.last_check = last_check or datetime.utcnow()
        self.error_rate = error_rate
        self.rate_limit_remaining = rate_limit_remaining
        self.next_reset = next_reset
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health status to dictionary."""
        return {
            "is_healthy": self.is_healthy,
            "response_time": self.response_time,
            "last_check": self.last_check.isoformat(),
            "error_rate": self.error_rate,
            "rate_limit_remaining": self.rate_limit_remaining,
            "next_reset": self.next_reset.isoformat() if self.next_reset else None
        }


# ============================================================================
# Abstract Data Provider Base Class
# ============================================================================

class DataProvider(ABC):
    """
    Abstract base class for all market data providers.
    
    This class defines the standard interface that all data providers must implement,
    ensuring consistent behavior and hot-swappable functionality across different
    data sources (FMP, Yahoo Finance, Alpha Vantage, etc.).
    
    All methods are async to support high-performance concurrent operations.
    """
    
    def __init__(
        self,
        name: str,
        provider_type: DataProviderType = DataProviderType.SECONDARY,
        api_key: str = None,
        base_url: str = None,
        rate_limit: int = 60,
        timeout: int = 30
    ):
        """
        Initialize data provider.
        
        Args:
            name: Provider name (e.g., "FMP", "Yahoo Finance")
            provider_type: Type of provider (primary, secondary, fallback)
            api_key: API key for authenticated providers
            base_url: Base URL for API endpoints
            rate_limit: Requests per minute limit
            timeout: Request timeout in seconds
        """
        self.name = name
        self.provider_type = provider_type
        self.api_key = api_key
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.timeout = timeout
        self._health_status = ProviderHealth(is_healthy=True)
        self._request_count = 0
        self._last_request_time = datetime.utcnow()
    
    # ========================================================================
    # Core Abstract Methods - Stock Data
    # ========================================================================
    
    @abstractmethod
    async def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time stock quote for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL", "GOOGL")
            
        Returns:
            Dict containing:
                - symbol: str - Stock symbol
                - price: float - Current price
                - change: float - Price change
                - change_percent: float - Percentage change
                - volume: int - Trading volume
                - market_cap: int - Market capitalization
                - pe_ratio: float - Price-to-earnings ratio
                - day_high: float - Day's high price
                - day_low: float - Day's low price
                - previous_close: float - Previous close price
                - timestamp: str - Data timestamp (ISO format)
                
        Raises:
            DataProviderError: If unable to fetch quote data
        """
        pass
    
    @abstractmethod
    async def get_stock_profile(self, symbol: str) -> Dict[str, Any]:
        """
        Get company profile information for a stock.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL", "GOOGL")
            
        Returns:
            Dict containing:
                - symbol: str - Stock symbol
                - company_name: str - Full company name
                - industry: str - Industry classification
                - sector: str - Sector classification
                - description: str - Company description
                - website: str - Company website URL
                - employees: int - Number of employees
                - founded: str - Founded year
                - headquarters: str - Headquarters location
                - ceo: str - CEO name
                - market_cap: int - Market capitalization
                - revenue: int - Annual revenue
                - exchange: str - Stock exchange
                
        Raises:
            DataProviderError: If unable to fetch profile data
        """
        pass
    
    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        period: str = "1year",
        frequency: DataFrequency = DataFrequency.DAILY
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL", "GOOGL")
            period: Time period ("1day", "1week", "1month", "3months", "6months", "1year", "2years", "5years")
            frequency: Data frequency (daily, weekly, monthly)
            
        Returns:
            List of Dict containing:
                - date: str - Date (YYYY-MM-DD format)
                - open: float - Opening price
                - high: float - High price
                - low: float - Low price
                - close: float - Closing price
                - volume: int - Trading volume
                - adjusted_close: float - Adjusted closing price
                
        Raises:
            DataProviderError: If unable to fetch historical data
        """
        pass
    
    # ========================================================================
    # Core Abstract Methods - Search and Discovery
    # ========================================================================
    
    @abstractmethod
    async def search_securities(
        self,
        query: str,
        limit: int = 10,
        security_types: List[SecurityType] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for securities by symbol or company name.
        
        Args:
            query: Search query (symbol or company name)
            limit: Maximum number of results to return
            security_types: Types of securities to include in search
            
        Returns:
            List of Dict containing:
                - symbol: str - Security symbol
                - name: str - Company/security name
                - type: str - Security type (stock, etf, crypto, etc.)
                - exchange: str - Exchange code
                - currency: str - Trading currency
                - country: str - Country code
                - sector: str - Sector (if applicable)
                - market_cap: int - Market cap (if applicable)
                
        Raises:
            DataProviderError: If unable to perform search
        """
        pass
    
    # ========================================================================
    # Core Abstract Methods - Cryptocurrency
    # ========================================================================
    
    @abstractmethod
    async def get_crypto_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time cryptocurrency quote.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH", "BTCUSD")
            
        Returns:
            Dict containing:
                - symbol: str - Crypto symbol
                - price: float - Current price
                - change: float - Price change (24h)
                - change_percent: float - Percentage change (24h)
                - volume: float - 24h trading volume
                - market_cap: int - Market capitalization
                - high_24h: float - 24h high
                - low_24h: float - 24h low
                - supply: float - Circulating supply
                - timestamp: str - Data timestamp (ISO format)
                
        Raises:
            DataProviderError: If unable to fetch crypto data
        """
        pass
    
    # ========================================================================
    # Core Abstract Methods - Market Overview
    # ========================================================================
    
    @abstractmethod
    async def get_market_overview(self) -> Dict[str, Any]:
        """
        Get overall market overview and key indices.
        
        Returns:
            Dict containing:
                - indices: Dict - Major market indices (S&P 500, NASDAQ, Dow Jones)
                - crypto: Dict - Major cryptocurrencies (BTC, ETH)
                - commodities: Dict - Key commodities (Gold, Oil, etc.)
                - currencies: Dict - Major forex pairs
                - market_status: Dict - Market open/close status by exchange
                - top_gainers: List - Top gaining stocks
                - top_losers: List - Top losing stocks
                - most_active: List - Most actively traded stocks
                - timestamp: str - Data timestamp (ISO format)
                
        Raises:
            DataProviderError: If unable to fetch market overview
        """
        pass
    
    # ========================================================================
    # Provider Health and Monitoring
    # ========================================================================
    
    async def check_health(self) -> ProviderHealth:
        """
        Check provider health status.
        
        Returns:
            ProviderHealth: Current health status
        """
        try:
            start_time = datetime.utcnow()
            
            # Perform a simple health check (try to get a well-known symbol)
            await self.get_stock_quote("AAPL")
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            self._health_status = ProviderHealth(
                is_healthy=True,
                response_time=response_time,
                last_check=end_time
            )
            
        except Exception as e:
            logger.warning(f"Health check failed for {self.name}: {e}")
            self._health_status = ProviderHealth(
                is_healthy=False,
                last_check=datetime.utcnow()
            )
        
        return self._health_status
    
    def get_health_status(self) -> ProviderHealth:
        """Get current cached health status."""
        return self._health_status
    
    # ========================================================================
    # Rate Limiting and Request Management
    # ========================================================================
    
    async def _check_rate_limit(self) -> None:
        """
        Check if request is within rate limits.
        
        Raises:
            DataProviderRateLimitError: If rate limit exceeded
        """
        current_time = datetime.utcnow()
        time_window = timedelta(minutes=1)
        
        # Reset counter if outside time window
        if current_time - self._last_request_time > time_window:
            self._request_count = 0
            self._last_request_time = current_time
        
        # Check rate limit
        if self._request_count >= self.rate_limit:
            retry_after = 60 - (current_time - self._last_request_time).seconds
            raise DataProviderRateLimitError(
                f"Rate limit exceeded for {self.name}. Try again in {retry_after} seconds.",
                provider=self.name,
                retry_after=retry_after
            )
        
        self._request_count += 1
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Any:
        """
        Make HTTP request with rate limiting and error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response data
            
        Raises:
            DataProviderError: If request fails
        """
        await self._check_rate_limit()
        
        # This is a template method that concrete providers should override
        # with their specific HTTP client implementation
        raise NotImplementedError("Concrete providers must implement _make_request")
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get provider information and capabilities.
        
        Returns:
            Dict containing provider metadata
        """
        return {
            "name": self.name,
            "type": self.provider_type.value,
            "supports_stocks": True,
            "supports_crypto": True,
            "supports_options": False,
            "supports_forex": False,
            "rate_limit": self.rate_limit,
            "timeout": self.timeout,
            "authenticated": bool(self.api_key),
            "base_url": self.base_url,
            "health_status": self._health_status.to_dict()
        }
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for the provider.
        
        Args:
            symbol: Raw symbol
            
        Returns:
            str: Normalized symbol
        """
        # Default implementation - providers can override
        return symbol.upper().strip()
    
    async def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol is supported by provider.
        
        Args:
            symbol: Symbol to validate
            
        Returns:
            bool: True if symbol is valid
        """
        try:
            await self.get_stock_quote(symbol)
            return True
        except DataProviderNotFoundError:
            return False
        except Exception:
            # Other errors don't necessarily mean invalid symbol
            return True
    
    # ========================================================================
    # Context Manager Support
    # ========================================================================
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.check_health()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Override in concrete providers for cleanup
        pass
    
    # ========================================================================
    # String Representation
    # ========================================================================
    
    def __str__(self) -> str:
        """String representation of provider."""
        return f"{self.name} ({self.provider_type.value})"
    
    def __repr__(self) -> str:
        """Detailed representation of provider."""
        return (
            f"DataProvider(name='{self.name}', type='{self.provider_type.value}', "
            f"healthy={self._health_status.is_healthy})"
        )


# ============================================================================
# Provider Registry and Discovery
# ============================================================================

class ProviderRegistry:
    """Registry for managing multiple data providers."""
    
    def __init__(self):
        self._providers: Dict[str, DataProvider] = {}
        self._primary_provider: Optional[DataProvider] = None
    
    def register(self, provider: DataProvider, is_primary: bool = False) -> None:
        """Register a data provider."""
        self._providers[provider.name] = provider
        
        if is_primary:
            self._primary_provider = provider
    
    def get_provider(self, name: str) -> Optional[DataProvider]:
        """Get provider by name."""
        return self._providers.get(name)
    
    def get_primary_provider(self) -> Optional[DataProvider]:
        """Get the primary provider."""
        return self._primary_provider
    
    def get_all_providers(self) -> List[DataProvider]:
        """Get all registered providers."""
        return list(self._providers.values())
    
    def get_healthy_providers(self) -> List[DataProvider]:
        """Get all healthy providers."""
        return [p for p in self._providers.values() if p.get_health_status().is_healthy]
    
    async def health_check_all(self) -> Dict[str, ProviderHealth]:
        """Run health checks on all providers."""
        results = {}
        
        # Run health checks concurrently
        tasks = [
            (name, provider.check_health())
            for name, provider in self._providers.items()
        ]
        
        for name, task in tasks:
            try:
                health = await task
                results[name] = health
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = ProviderHealth(is_healthy=False)
        
        return results


# ============================================================================
# Export All Public APIs
# ============================================================================

__all__ = [
    # Base classes
    "DataProvider",
    "ProviderResponse",
    "ProviderHealth",
    "ProviderRegistry",
    
    # Enums
    "DataProviderType",
    "SecurityType", 
    "DataFrequency",
    
    # Exceptions
    "DataProviderError",
    "DataProviderConnectionError",
    "DataProviderAuthenticationError",
    "DataProviderRateLimitError",
    "DataProviderNotFoundError",
    "DataProviderValidationError",
]