"""
Securities-related Pydantic schemas.

Contains request and response models for securities endpoints including quotes,
profiles, historical data, and search functionality.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Annotated
from pydantic import BaseModel, Field, validator

from .base import BaseResponse, DataProviderInfo, PaginatedResponse


# ============================================================================
# Pydantic v2 Configuration
# ============================================================================


# ============================================================================
# Enums and Constants
# ============================================================================

class SecurityType(str, Enum):
    """Types of securities."""
    STOCK = "stock"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    INDEX = "index"
    BOND = "bond"
    OPTION = "option"
    FUTURE = "future"
    CRYPTO = "crypto"


class ExchangeCode(str, Enum):
    """Major stock exchanges."""
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    AMEX = "AMEX"
    LSE = "LSE"
    TSE = "TSE"
    HKEX = "HKEX"
    SSE = "SSE"
    SZSE = "SZSE"
    OTHER = "OTHER"


class MarketStatus(str, Enum):
    """Market trading status."""
    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    AFTER_HOURS = "after_hours"
    HOLIDAY = "holiday"


class TimeFrame(str, Enum):
    """Time frames for historical data."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


# ============================================================================
# Security Quote Models
# ============================================================================

class SecurityQuote(BaseModel):
    """Real-time security quote information."""
    
    symbol: str = Field(
        ..., 
        description="Security symbol",
        example="AAPL",
        min_length=1,
        max_length=20
    )
    name: str = Field(
        ..., 
        description="Security name",
        example="Apple Inc."
    )
    price: Decimal = Field(
        ..., 
        description="Current price",
        example=150.25,
    )
    change: Decimal = Field(
        ..., 
        description="Price change from previous close",
        example=2.15,
    )
    change_percent: Decimal = Field(
        ..., 
        description="Percentage change from previous close",
        example=1.45,
    )
    volume: int = Field(
        ..., 
        description="Trading volume",
        example=1250000,
        ge=0
    )
    avg_volume: Optional[int] = Field(
        None, 
        description="Average daily volume",
        example=75000000,
        ge=0
    )
    market_cap: Optional[int] = Field(
        None, 
        description="Market capitalization",
        example=2500000000000
    )
    pe_ratio: Optional[Decimal] = Field(
        None, 
        description="Price-to-earnings ratio",
        example=25.34,
    )
    day_high: Decimal = Field(
        ..., 
        description="Day's high price",
        example=152.10,
    )
    day_low: Decimal = Field(
        ..., 
        description="Day's low price",
        example=148.50,
    )
    previous_close: Decimal = Field(
        ..., 
        description="Previous trading day's closing price",
        example=148.10,
    )
    open_price: Decimal = Field(
        ..., 
        description="Opening price for current trading day",
        example=149.00,
    )
    week_52_high: Optional[Decimal] = Field(
        None, 
        description="52-week high",
        example=198.23,
    )
    week_52_low: Optional[Decimal] = Field(
        None, 
        description="52-week low",
        example=124.17,
    )
    exchange: ExchangeCode = Field(
        ..., 
        description="Stock exchange",
        example=ExchangeCode.NASDAQ
    )
    currency: str = Field(
        "USD", 
        description="Currency of the price",
        example="USD",
        min_length=3,
        max_length=3
    )
    market_status: MarketStatus = Field(
        ..., 
        description="Current market status",
        example=MarketStatus.OPEN
    )
    last_update: datetime = Field(
        ..., 
        description="Last update timestamp",
        example="2024-07-04T15:30:00Z"
    )
    extended_hours_price: Optional[Decimal] = Field(
        None, 
        description="Extended hours trading price",
        example=150.75,
    )
    extended_hours_change: Optional[Decimal] = Field(
        None, 
        description="Extended hours price change",
        example=0.50,
    )


class QuoteResponse(BaseResponse[SecurityQuote]):
    """Security quote API response."""
    
    provider: Optional[DataProviderInfo] = Field(
        None, 
        description="Data provider information"
    )


# ============================================================================
# Security Profile Models
# ============================================================================

class SecurityProfile(BaseModel):
    """Detailed security profile information."""
    
    symbol: str = Field(
        ..., 
        description="Security symbol",
        example="AAPL"
    )
    name: str = Field(
        ..., 
        description="Full company name",
        example="Apple Inc."
    )
    description: str = Field(
        ..., 
        description="Company description",
        example="Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide."
    )
    industry: Optional[str] = Field(
        None, 
        description="Industry classification",
        example="Technology Hardware, Storage & Peripherals"
    )
    sector: Optional[str] = Field(
        None, 
        description="Sector classification",
        example="Information Technology"
    )
    website: Optional[str] = Field(
        None, 
        description="Company website URL",
        example="https://www.apple.com"
    )
    headquarters: Optional[str] = Field(
        None, 
        description="Headquarters location",
        example="Cupertino, CA, United States"
    )
    employees: Optional[int] = Field(
        None, 
        description="Number of employees",
        example=164000,
        ge=0
    )
    founded: Optional[int] = Field(
        None, 
        description="Year founded",
        example=1976,
        ge=1800,
        le=2030
    )
    ceo: Optional[str] = Field(
        None, 
        description="Chief Executive Officer",
        example="Timothy D. Cook"
    )
    exchange: ExchangeCode = Field(
        ..., 
        description="Primary exchange",
        example=ExchangeCode.NASDAQ
    )
    currency: str = Field(
        "USD", 
        description="Trading currency",
        example="USD"
    )
    country: Optional[str] = Field(
        None, 
        description="Country of incorporation",
        example="United States"
    )
    # Financial metrics
    market_cap: Optional[int] = Field(
        None, 
        description="Market capitalization",
        example=2500000000000
    )
    enterprise_value: Optional[int] = Field(
        None, 
        description="Enterprise value",
        example=2450000000000
    )
    revenue_ttm: Optional[int] = Field(
        None, 
        description="Trailing twelve months revenue",
        example=394328000000
    )
    profit_margin: Optional[Decimal] = Field(
        None, 
        description="Profit margin",
        example=0.2531,
    )
    operating_margin: Optional[Decimal] = Field(
        None, 
        description="Operating margin",
        example=0.2987,
    )
    return_on_equity: Optional[Decimal] = Field(
        None, 
        description="Return on equity",
        example=1.4756,
    )
    return_on_assets: Optional[Decimal] = Field(
        None, 
        description="Return on assets",
        example=0.2865,
    )
    debt_to_equity: Optional[Decimal] = Field(
        None, 
        description="Debt to equity ratio",
        example=1.73,
    )
    # Trading metrics
    beta: Optional[Decimal] = Field(
        None, 
        description="Beta coefficient",
        example=1.24,
    )
    dividend_yield: Optional[Decimal] = Field(
        None, 
        description="Dividend yield",
        example=0.0044,
    )
    ex_dividend_date: Optional[date] = Field(
        None, 
        description="Ex-dividend date",
        example="2024-02-09"
    )
    # Additional info
    tags: List[str] = Field(
        default_factory=list, 
        description="Classification tags",
        example=["large-cap", "technology", "consumer-electronics"]
    )
    similar_securities: List[str] = Field(
        default_factory=list, 
        description="Similar security symbols",
        example=["MSFT", "GOOGL", "AMZN"]
    )


class ProfileResponse(BaseResponse[SecurityProfile]):
    """Security profile API response."""
    
    provider: Optional[DataProviderInfo] = Field(
        None, 
        description="Data provider information"
    )


# ============================================================================
# Historical Data Models
# ============================================================================

class OHLCVData(BaseModel):
    """OHLCV (Open, High, Low, Close, Volume) data point."""
    
    timestamp: datetime = Field(
        ..., 
        description="Data timestamp",
        example="2024-07-04T09:30:00Z"
    )
    open: Decimal = Field(
        ..., 
        description="Opening price",
        example=149.00,
    )
    high: Decimal = Field(
        ..., 
        description="High price",
        example=152.10,
    )
    low: Decimal = Field(
        ..., 
        description="Low price",
        example=148.50,
    )
    close: Decimal = Field(
        ..., 
        description="Closing price",
        example=150.25,
    )
    volume: int = Field(
        ..., 
        description="Trading volume",
        example=1250000,
        ge=0
    )
    adjusted_close: Optional[Decimal] = Field(
        None, 
        description="Adjusted closing price",
        example=150.25,
    )
    vwap: Optional[Decimal] = Field(
        None, 
        description="Volume weighted average price",
        example=150.12,
    )


class HistoricalData(BaseModel):
    """Historical price data for a security."""
    
    symbol: str = Field(
        ..., 
        description="Security symbol",
        example="AAPL"
    )
    timeframe: TimeFrame = Field(
        ..., 
        description="Data timeframe",
        example=TimeFrame.DAY_1
    )
    start_date: date = Field(
        ..., 
        description="Start date of data",
        example="2024-01-01"
    )
    end_date: date = Field(
        ..., 
        description="End date of data",
        example="2024-07-04"
    )
    data: List[OHLCVData] = Field(
        ..., 
        description="Historical OHLCV data points"
    )
    
    @validator('data')
    def data_not_empty(cls, v):
        """Ensure data list is not empty."""
        if not v:
            raise ValueError('Historical data cannot be empty')
        return v


class HistoricalDataResponse(BaseResponse[HistoricalData]):
    """Historical data API response."""
    
    provider: Optional[DataProviderInfo] = Field(
        None, 
        description="Data provider information"
    )


# ============================================================================
# Search Models
# ============================================================================

class SecuritySearchResult(BaseModel):
    """Security search result item."""
    
    symbol: str = Field(
        ..., 
        description="Security symbol",
        example="AAPL"
    )
    name: str = Field(
        ..., 
        description="Security name",
        example="Apple Inc."
    )
    type: SecurityType = Field(
        ..., 
        description="Security type",
        example=SecurityType.STOCK
    )
    exchange: ExchangeCode = Field(
        ..., 
        description="Primary exchange",
        example=ExchangeCode.NASDAQ
    )
    currency: str = Field(
        "USD", 
        description="Trading currency",
        example="USD"
    )
    sector: Optional[str] = Field(
        None, 
        description="Sector",
        example="Technology"
    )
    industry: Optional[str] = Field(
        None, 
        description="Industry",
        example="Consumer Electronics"
    )
    market_cap: Optional[int] = Field(
        None, 
        description="Market capitalization",
        example=2500000000000
    )
    last_price: Optional[Decimal] = Field(
        None, 
        description="Last traded price",
        example=150.25,
    )
    relevance_score: Optional[Decimal] = Field(
        None, 
        description="Search relevance score (0-1)",
        example=0.95,
        ge=0,
        le=1,
    )


class SecuritySearchParams(BaseModel):
    """Security search parameters."""
    
    query: str = Field(
        ..., 
        description="Search query (symbol, name, or description)",
        example="apple",
        min_length=1,
        max_length=100
    )
    types: Optional[List[SecurityType]] = Field(
        None, 
        description="Filter by security types",
        example=[SecurityType.STOCK, SecurityType.ETF]
    )
    exchanges: Optional[List[ExchangeCode]] = Field(
        None, 
        description="Filter by exchanges",
        example=[ExchangeCode.NYSE, ExchangeCode.NASDAQ]
    )
    sectors: Optional[List[str]] = Field(
        None, 
        description="Filter by sectors",
        example=["Technology", "Healthcare"]
    )
    min_market_cap: Optional[int] = Field(
        None, 
        description="Minimum market capitalization",
        example=1000000000,
        ge=0
    )
    max_market_cap: Optional[int] = Field(
        None, 
        description="Maximum market capitalization",
        example=1000000000000
    )
    limit: int = Field(
        20, 
        description="Maximum number of results",
        example=20,
        ge=1,
        le=100
    )


class SecuritySearchData(BaseModel):
    """Security search response data."""
    
    results: List[SecuritySearchResult] = Field(
        ..., 
        description="Search results"
    )
    total_found: int = Field(
        ..., 
        description="Total number of matching securities",
        example=156,
        ge=0
    )
    query: str = Field(
        ..., 
        description="Original search query",
        example="apple"
    )
    execution_time_ms: Optional[float] = Field(
        None, 
        description="Search execution time in milliseconds",
        example=45.7
    )


class SecuritySearchResponse(BaseResponse[SecuritySearchData]):
    """Security search API response."""
    
    provider: Optional[DataProviderInfo] = Field(
        None, 
        description="Data provider information"
    )


# ============================================================================
# Batch Operations
# ============================================================================

class BatchQuoteRequest(BaseModel):
    """Batch quote request parameters."""
    
    symbols: List[str] = Field(
        ..., 
        description="List of security symbols",
        example=["AAPL", "MSFT", "GOOGL"],
        min_items=1,
        max_items=100
    )
    
    @validator('symbols')
    def symbols_valid(cls, v):
        """Validate symbol format."""
        for symbol in v:
            if not symbol or len(symbol) > 20:
                raise ValueError(f'Invalid symbol: {symbol}')
        return v


class BatchQuoteData(BaseModel):
    """Batch quote response data."""
    
    quotes: List[SecurityQuote] = Field(
        ..., 
        description="Security quotes"
    )
    successful: int = Field(
        ..., 
        description="Number of successful quotes",
        example=3,
        ge=0
    )
    failed: int = Field(
        ..., 
        description="Number of failed quotes",
        example=0,
        ge=0
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Error details for failed quotes",
        example=[{"symbol": "INVALID", "error": "Symbol not found"}]
    )


class BatchQuoteResponse(BaseResponse[BatchQuoteData]):
    """Batch quote API response."""
    
    provider: Optional[DataProviderInfo] = Field(
        None, 
        description="Data provider information"
    )


# ============================================================================
# Export all models
# ============================================================================

__all__ = [
    # Enums
    "SecurityType",
    "ExchangeCode", 
    "MarketStatus",
    "TimeFrame",
    
    # Quote models
    "SecurityQuote",
    "QuoteResponse",
    
    # Profile models
    "SecurityProfile",
    "ProfileResponse",
    
    # Historical data models
    "OHLCVData",
    "HistoricalData",
    "HistoricalDataResponse",
    
    # Search models
    "SecuritySearchResult",
    "SecuritySearchParams",
    "SecuritySearchData",
    "SecuritySearchResponse",
    
    # Batch models
    "BatchQuoteRequest",
    "BatchQuoteData",
    "BatchQuoteResponse"
]