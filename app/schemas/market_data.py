"""
Market data schemas for validation and API responses.

Defines Pydantic models for market data requests, responses, and validation
with data quality scoring and anomaly detection capabilities.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
import structlog

logger = structlog.get_logger(__name__)

class AssetType(str, Enum):
    """Asset type enumeration."""
    STOCK = "stock"
    CRYPTO = "crypto"
    INDEX = "index"
    COMMODITY = "commodity"
    FOREX = "forex"

class DataQuality(str, Enum):
    """Data quality levels."""
    EXCELLENT = "excellent"  # 95-100%
    GOOD = "good"           # 85-94%
    FAIR = "fair"           # 70-84%
    POOR = "poor"           # 50-69%
    UNRELIABLE = "unreliable"  # <50%

class DataSource(str, Enum):
    """Data source providers."""
    FMP = "fmp"
    YAHOO = "yahoo"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"
    AGGREGATED = "aggregated"

# Base request/response models

class MarketDataRequest(BaseModel):
    """Base market data request model."""
    symbol: str = Field(..., description="Security symbol (e.g., AAPL, BTC)")
    asset_type: Optional[AssetType] = Field(AssetType.STOCK, description="Asset type")
    preferred_provider: Optional[DataSource] = Field(None, description="Preferred data provider")
    enable_fallback: bool = Field(True, description="Enable provider fallback")
    max_age_seconds: Optional[int] = Field(300, description="Maximum acceptable data age")
    require_real_time: bool = Field(False, description="Require real-time data")

class QuoteRequest(MarketDataRequest):
    """Stock/crypto quote request."""
    include_extended_hours: bool = Field(False, description="Include extended hours data")

class ProfileRequest(MarketDataRequest):
    """Company profile request."""
    include_financials: bool = Field(False, description="Include basic financial metrics")

class HistoricalRequest(MarketDataRequest):
    """Historical data request."""
    period: str = Field("1y", description="Time period (1d, 5d, 1m, 3m, 6m, 1y, 2y, 5y, 10y, ytd, max)")
    interval: str = Field("1d", description="Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)")
    include_dividends: bool = Field(False, description="Include dividend data")
    adjust_splits: bool = Field(True, description="Adjust for stock splits")

class SearchRequest(BaseModel):
    """Securities search request."""
    query: str = Field(..., min_length=1, description="Search query")
    asset_types: List[AssetType] = Field([AssetType.STOCK], description="Asset types to search")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    exchanges: Optional[List[str]] = Field(None, description="Filter by exchanges")
    countries: Optional[List[str]] = Field(None, description="Filter by countries")

class MarketOverviewRequest(BaseModel):
    """Market overview request."""
    include_indices: bool = Field(True, description="Include major indices")
    include_crypto: bool = Field(True, description="Include major cryptocurrencies")
    include_commodities: bool = Field(False, description="Include commodities")
    include_forex: bool = Field(False, description="Include forex pairs")

# Data quality and validation models

class DataQualityMetrics(BaseModel):
    """Data quality assessment metrics."""
    completeness_score: float = Field(..., ge=0, le=100, description="Data completeness percentage")
    freshness_score: float = Field(..., ge=0, le=100, description="Data freshness score")
    accuracy_score: float = Field(..., ge=0, le=100, description="Data accuracy score")
    consistency_score: float = Field(..., ge=0, le=100, description="Cross-provider consistency score")
    overall_score: float = Field(..., ge=0, le=100, description="Overall quality score")
    quality_level: DataQuality = Field(..., description="Quality level assessment")
    
    @validator('overall_score', pre=True)
    def calculate_overall_score(cls, v, values):
        """Calculate overall score from component scores."""
        if v is not None:
            return v
        
        scores = [
            values.get('completeness_score', 0),
            values.get('freshness_score', 0), 
            values.get('accuracy_score', 0),
            values.get('consistency_score', 0)
        ]
        return sum(scores) / len(scores) if scores else 0

class AnomalyDetection(BaseModel):
    """Anomaly detection results."""
    has_anomalies: bool = Field(..., description="Whether anomalies were detected")
    anomaly_types: List[str] = Field([], description="Types of anomalies detected")
    confidence_score: float = Field(..., ge=0, le=100, description="Detection confidence")
    details: Dict[str, Any] = Field({}, description="Detailed anomaly information")

class DataProvenance(BaseModel):
    """Data source and processing information."""
    primary_source: DataSource = Field(..., description="Primary data source")
    fallback_sources: List[DataSource] = Field([], description="Fallback sources used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    cache_hit: bool = Field(..., description="Whether data came from cache")
    cache_age_seconds: Optional[float] = Field(None, description="Cache age in seconds")
    provider_health: Dict[str, str] = Field({}, description="Provider health status")

# Response models

class BaseMarketDataResponse(BaseModel):
    """Base market data response."""
    success: bool = Field(..., description="Request success status")
    symbol: str = Field(..., description="Requested symbol")
    timestamp: datetime = Field(..., description="Response timestamp")
    data_quality: DataQualityMetrics = Field(..., description="Data quality metrics")
    anomaly_detection: Optional[AnomalyDetection] = Field(None, description="Anomaly detection results")
    provenance: DataProvenance = Field(..., description="Data source information")
    error: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field([], description="Warning messages")

class QuoteData(BaseModel):
    """Quote data structure."""
    symbol: str = Field(..., description="Security symbol")
    name: str = Field(..., description="Security name")
    price: float = Field(..., description="Current price")
    change: float = Field(..., description="Price change")
    change_percent: float = Field(..., description="Percentage change")
    previous_close: float = Field(..., description="Previous close price")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Day high")
    low: float = Field(..., description="Day low")
    volume: int = Field(..., description="Trading volume")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    pe_ratio: Optional[float] = Field(None, description="P/E ratio")
    bid: Optional[float] = Field(None, description="Bid price")
    ask: Optional[float] = Field(None, description="Ask price")
    bid_size: Optional[int] = Field(None, description="Bid size")
    ask_size: Optional[int] = Field(None, description="Ask size")
    asset_type: AssetType = Field(AssetType.STOCK, description="Asset type")
    currency: str = Field("USD", description="Currency")
    exchange: Optional[str] = Field(None, description="Exchange")
    timezone: str = Field("US/Eastern", description="Timezone")
    last_updated: datetime = Field(..., description="Last update time")

class QuoteResponse(BaseMarketDataResponse):
    """Quote response with data."""
    data: Optional[QuoteData] = Field(None, description="Quote data")

class ProfileData(BaseModel):
    """Company profile data structure."""
    symbol: str = Field(..., description="Security symbol")
    company_name: str = Field(..., description="Company name")
    description: str = Field(..., description="Company description")
    industry: str = Field(..., description="Industry")
    sector: str = Field(..., description="Sector")
    country: str = Field(..., description="Country")
    website: Optional[str] = Field(None, description="Company website")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    employees: Optional[int] = Field(None, description="Number of employees")
    exchange: str = Field(..., description="Primary exchange")
    currency: str = Field("USD", description="Currency")
    ceo: Optional[str] = Field(None, description="CEO name")
    founded: Optional[int] = Field(None, description="Founded year")
    headquarters: Optional[Dict[str, str]] = Field(None, description="Headquarters address")
    financial_metrics: Optional[Dict[str, float]] = Field(None, description="Key financial metrics")
    last_updated: datetime = Field(..., description="Last update time")

class ProfileResponse(BaseMarketDataResponse):
    """Profile response with data."""
    data: Optional[ProfileData] = Field(None, description="Profile data")

class HistoricalDataPoint(BaseModel):
    """Single historical data point."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")
    adjusted_close: Optional[float] = Field(None, description="Adjusted closing price")
    dividend_amount: Optional[float] = Field(None, description="Dividend amount")
    split_coefficient: Optional[float] = Field(None, description="Split coefficient")

class HistoricalData(BaseModel):
    """Historical data structure."""
    symbol: str = Field(..., description="Security symbol")
    period: str = Field(..., description="Time period")
    interval: str = Field(..., description="Data interval")
    data_points: List[HistoricalDataPoint] = Field(..., description="Historical data points")
    start_date: str = Field(..., description="Start date")
    end_date: str = Field(..., description="End date")
    count: int = Field(..., description="Number of data points")
    currency: str = Field("USD", description="Currency")
    timezone: str = Field("US/Eastern", description="Timezone")
    last_updated: datetime = Field(..., description="Last update time")

class HistoricalResponse(BaseMarketDataResponse):
    """Historical data response."""
    data: Optional[HistoricalData] = Field(None, description="Historical data")

class SecuritySearchResult(BaseModel):
    """Security search result."""
    symbol: str = Field(..., description="Security symbol")
    name: str = Field(..., description="Security name")
    asset_type: AssetType = Field(..., description="Asset type")
    exchange: str = Field(..., description="Exchange")
    currency: str = Field("USD", description="Currency")
    country: Optional[str] = Field(None, description="Country")
    industry: Optional[str] = Field(None, description="Industry")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    relevance_score: float = Field(..., ge=0, le=100, description="Search relevance score")

class SearchData(BaseModel):
    """Search results data structure."""
    query: str = Field(..., description="Search query")
    results: List[SecuritySearchResult] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total results count")
    page_size: int = Field(..., description="Page size")
    processing_time_ms: float = Field(..., description="Search processing time")
    last_updated: datetime = Field(..., description="Last update time")

class SearchResponse(BaseMarketDataResponse):
    """Search response with results."""
    data: Optional[SearchData] = Field(None, description="Search data")

class MarketOverviewData(BaseModel):
    """Market overview data structure."""
    indices: List[QuoteData] = Field([], description="Major market indices")
    crypto: List[QuoteData] = Field([], description="Major cryptocurrencies")
    commodities: List[QuoteData] = Field([], description="Major commodities")
    forex: List[QuoteData] = Field([], description="Major forex pairs")
    market_status: Dict[str, str] = Field({}, description="Market status by exchange")
    market_summary: Dict[str, Any] = Field({}, description="Market summary statistics")
    last_updated: datetime = Field(..., description="Last update time")

class MarketOverviewResponse(BaseMarketDataResponse):
    """Market overview response."""
    data: Optional[MarketOverviewData] = Field(None, description="Market overview data")

# Aggregation and comparison models

class ProviderComparisonData(BaseModel):
    """Data comparison across providers."""
    symbol: str = Field(..., description="Security symbol")
    provider_data: Dict[str, Dict[str, Any]] = Field(..., description="Data by provider")
    consensus_data: Dict[str, Any] = Field(..., description="Consensus/aggregated data")
    variance_metrics: Dict[str, float] = Field(..., description="Variance between providers")
    outlier_detection: Dict[str, List[str]] = Field(..., description="Outlier fields by provider")
    confidence_score: float = Field(..., ge=0, le=100, description="Overall confidence")
    timestamp: datetime = Field(..., description="Comparison timestamp")

class ProviderComparisonResponse(BaseModel):
    """Provider comparison response."""
    success: bool = Field(..., description="Request success status")
    comparison: Optional[ProviderComparisonData] = Field(None, description="Comparison data")
    error: Optional[str] = Field(None, description="Error message if failed")

# Health and monitoring models

class ProviderHealthStatus(BaseModel):
    """Individual provider health status."""
    name: str = Field(..., description="Provider name")
    status: str = Field(..., description="Health status")
    last_check: datetime = Field(..., description="Last health check time")
    success_rate: float = Field(..., ge=0, le=100, description="Success rate percentage")
    average_response_time: float = Field(..., description="Average response time in seconds")
    error_count: int = Field(..., description="Recent error count")
    rate_limit_status: Optional[Dict[str, Any]] = Field(None, description="Rate limit information")

class SystemHealthData(BaseModel):
    """Overall system health data."""
    providers: List[ProviderHealthStatus] = Field(..., description="Provider health statuses")
    cache_status: Dict[str, Any] = Field(..., description="Cache system status")
    overall_status: str = Field(..., description="Overall system status")
    active_alerts: List[str] = Field([], description="Active system alerts")
    performance_metrics: Dict[str, float] = Field(..., description="Performance metrics")
    uptime_seconds: float = Field(..., description="System uptime")
    last_updated: datetime = Field(..., description="Last update time")

class SystemHealthResponse(BaseModel):
    """System health response."""
    success: bool = Field(..., description="Request success status")
    health: Optional[SystemHealthData] = Field(None, description="Health data")
    error: Optional[str] = Field(None, description="Error message if failed")

# Export all models
__all__ = [
    # Enums
    "AssetType", "DataQuality", "DataSource",
    
    # Request models
    "MarketDataRequest", "QuoteRequest", "ProfileRequest", 
    "HistoricalRequest", "SearchRequest", "MarketOverviewRequest",
    
    # Data models
    "QuoteData", "ProfileData", "HistoricalData", "HistoricalDataPoint",
    "SecuritySearchResult", "SearchData", "MarketOverviewData",
    
    # Response models  
    "BaseMarketDataResponse", "QuoteResponse", "ProfileResponse",
    "HistoricalResponse", "SearchResponse", "MarketOverviewResponse",
    
    # Quality and validation
    "DataQualityMetrics", "AnomalyDetection", "DataProvenance",
    
    # Comparison and health
    "ProviderComparisonData", "ProviderComparisonResponse",
    "ProviderHealthStatus", "SystemHealthData", "SystemHealthResponse"
]