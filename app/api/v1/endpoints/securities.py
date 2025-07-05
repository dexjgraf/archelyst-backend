"""
Securities API Endpoints

RESTful API endpoints for securities data including quotes, profiles, 
and historical charts with comprehensive validation and documentation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
import structlog

from ....services.market_data import MarketDataService, get_market_data_service
from ....schemas.market_data import (
    # Request models
    QuoteRequest, ProfileRequest, HistoricalRequest,
    # Response models
    QuoteResponse, ProfileResponse, HistoricalResponse,
    # Data models
    QuoteData, ProfileData, HistoricalData,
    # Enums
    AssetType, DataQuality
)
from ....core.config import Settings

logger = structlog.get_logger(__name__)

# Create the router
router = APIRouter(prefix="/securities", tags=["securities"])

# Response models for OpenAPI documentation
QUOTE_RESPONSES = {
    200: {
        "description": "Successful quote retrieval",
        "content": {
            "application/json": {
                "example": {
                    "success": True,
                    "symbol": "AAPL",
                    "timestamp": "2025-07-05T12:00:00Z",
                    "data": {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "price": 150.25,
                        "change": 2.5,
                        "change_percent": 1.69,
                        "previous_close": 147.75,
                        "open": 148.0,
                        "high": 151.0,
                        "low": 147.5,
                        "volume": 50000000,
                        "market_cap": 2500000000000,
                        "pe_ratio": 25.5,
                        "currency": "USD",
                        "exchange": "NASDAQ",
                        "last_updated": "2025-07-05T12:00:00Z"
                    },
                    "data_quality": {
                        "overall_score": 96.5,
                        "quality_level": "excellent",
                        "completeness_score": 100.0,
                        "freshness_score": 95.0,
                        "accuracy_score": 95.0,
                        "consistency_score": 90.0
                    },
                    "provenance": {
                        "primary_source": "fmp",
                        "processing_time_ms": 245.3,
                        "cache_hit": False
                    }
                }
            }
        }
    },
    400: {"description": "Invalid symbol format"},
    404: {"description": "Symbol not found"},
    429: {"description": "Rate limit exceeded"},
    500: {"description": "Internal server error"}
}

PROFILE_RESPONSES = {
    200: {
        "description": "Successful profile retrieval",
        "content": {
            "application/json": {
                "example": {
                    "success": True,
                    "symbol": "AAPL",
                    "data": {
                        "symbol": "AAPL",
                        "company_name": "Apple Inc.",
                        "description": "Apple Inc. designs and manufactures consumer electronics.",
                        "industry": "Consumer Electronics",
                        "sector": "Technology",
                        "country": "US",
                        "market_cap": 2500000000000,
                        "employees": 147000,
                        "exchange": "NASDAQ",
                        "ceo": "Tim Cook"
                    }
                }
            }
        }
    }
}

CHART_RESPONSES = {
    200: {
        "description": "Successful historical data retrieval",
        "content": {
            "application/json": {
                "example": {
                    "success": True,
                    "symbol": "AAPL", 
                    "data": {
                        "symbol": "AAPL",
                        "period": "1y",
                        "interval": "1d",
                        "count": 252,
                        "data_points": [
                            {
                                "date": "2024-07-05",
                                "open": 150.0,
                                "high": 152.0,
                                "low": 149.0,
                                "close": 151.0,
                                "volume": 45000000
                            }
                        ]
                    }
                }
            }
        }
    }
}


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalize security symbol.
    
    Args:
        symbol: Raw symbol input
        
    Returns:
        str: Normalized symbol
        
    Raises:
        HTTPException: If symbol is invalid
    """
    if not symbol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symbol cannot be empty"
        )
    
    # Basic symbol validation
    normalized_symbol = symbol.upper().strip()
    
    if not normalized_symbol.replace("-", "").replace(".", "").isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid symbol format. Only alphanumeric characters, hyphens, and dots allowed."
        )
    
    if len(normalized_symbol) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symbol too long. Maximum 20 characters allowed."
        )
    
    return normalized_symbol


def handle_market_data_response(response, symbol: str, operation: str):
    """
    Handle market data service response and convert to appropriate HTTP response.
    
    Args:
        response: MarketDataService response
        symbol: Security symbol
        operation: Operation type for logging
        
    Returns:
        Response object or raises HTTPException
    """
    if response.success:
        logger.info(
            f"{operation} successful",
            symbol=symbol,
            provider=response.provenance.primary_source,
            quality_score=response.data_quality.overall_score,
            processing_time_ms=response.provenance.processing_time_ms
        )
        return response
    else:
        # Determine appropriate HTTP status code based on error
        error_msg = response.error or "Unknown error"
        
        if "not found" in error_msg.lower() or "invalid symbol" in error_msg.lower():
            status_code = status.HTTP_404_NOT_FOUND
        elif "rate limit" in error_msg.lower():
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif "timeout" in error_msg.lower():
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        logger.error(
            f"{operation} failed",
            symbol=symbol,
            error=error_msg,
            status_code=status_code
        )
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": error_msg,
                "symbol": symbol,
                "operation": operation,
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get(
    "/quote/{symbol}",
    response_model=QuoteResponse,
    responses=QUOTE_RESPONSES,
    summary="Get real-time stock or crypto quote",
    description="""
    Retrieve real-time quote data for a stock or cryptocurrency with comprehensive
    data quality assessment and anomaly detection.
    
    **Features:**
    - Real-time price, volume, and market data
    - Automatic provider failover (FMP → Yahoo Finance)
    - Data quality scoring and validation
    - Anomaly detection for extreme price movements
    - Comprehensive market data (P/E, market cap, etc.)
    - Support for both stocks and cryptocurrencies
    
    **Supported Symbols:**
    - Stocks: AAPL, GOOGL, MSFT, AMZN, etc.
    - Crypto: BTC, ETH, ADA, DOT, etc.
    
    **Quality Levels:**
    - Excellent (95-100%): Fresh, complete, validated data
    - Good (85-94%): Recent data with minor gaps
    - Fair (70-84%): Acceptable data with some limitations
    - Poor (50-69%): Outdated or incomplete data
    - Unreliable (<50%): Data quality concerns
    """
)
async def get_quote(
    symbol: str = Path(
        ...,
        description="Security symbol (e.g., AAPL for Apple Inc., BTC for Bitcoin)",
        example="AAPL",
        regex=r"^[A-Za-z0-9\-\.]{1,20}$"
    ),
    asset_type: Optional[AssetType] = Query(
        AssetType.STOCK,
        description="Asset type - automatically detected if not specified"
    ),
    include_extended_hours: bool = Query(
        False,
        description="Include extended hours trading data (when available)"
    ),
    max_age_seconds: Optional[int] = Query(
        300,
        ge=1,
        le=3600,
        description="Maximum acceptable data age in seconds"
    ),
    market_data_service: MarketDataService = Depends(get_market_data_service)
) -> QuoteResponse:
    """Get real-time quote for a security."""
    
    # Validate and normalize symbol
    normalized_symbol = validate_symbol(symbol)
    
    # Auto-detect crypto symbols
    crypto_symbols = ["BTC", "ETH", "ADA", "DOT", "LTC", "XRP", "DOGE", "SOL", "MATIC", "AVAX"]
    if any(normalized_symbol.startswith(crypto) for crypto in crypto_symbols):
        asset_type = AssetType.CRYPTO
    
    # Create request
    request = QuoteRequest(
        symbol=normalized_symbol,
        asset_type=asset_type,
        include_extended_hours=include_extended_hours,
        max_age_seconds=max_age_seconds
    )
    
    # Get quote from market data service
    response = await market_data_service.get_quote(request)
    
    # Handle response and convert to HTTP response
    return handle_market_data_response(response, normalized_symbol, "Quote")


@router.get(
    "/profile/{symbol}",
    response_model=ProfileResponse,
    responses=PROFILE_RESPONSES,
    summary="Get company profile information",
    description="""
    Retrieve comprehensive company profile including business description,
    financial metrics, and corporate information.
    
    **Features:**
    - Company overview and business description
    - Industry and sector classification
    - Key executives and corporate structure
    - Financial metrics and market data
    - Contact information and headquarters
    - Employee count and founding information
    
    **Data Sources:**
    - Primary: Financial Modeling Prep (FMP)
    - Fallback: Yahoo Finance
    - Quality scoring and validation applied
    """
)
async def get_profile(
    symbol: str = Path(
        ...,
        description="Stock symbol (e.g., AAPL for Apple Inc.)",
        example="AAPL"
    ),
    include_financials: bool = Query(
        False,
        description="Include basic financial metrics in response"
    ),
    market_data_service: MarketDataService = Depends(get_market_data_service)
) -> ProfileResponse:
    """Get company profile information."""
    
    # Validate and normalize symbol
    normalized_symbol = validate_symbol(symbol)
    
    # Create request
    request = ProfileRequest(
        symbol=normalized_symbol,
        asset_type=AssetType.STOCK,  # Profiles are only for stocks
        include_financials=include_financials
    )
    
    # Get profile from market data service
    response = await market_data_service.get_profile(request)
    
    # Handle response
    return handle_market_data_response(response, normalized_symbol, "Profile")


@router.get(
    "/chart/{symbol}",
    response_model=HistoricalResponse,
    responses=CHART_RESPONSES,
    summary="Get historical price data",
    description="""
    Retrieve historical price data for charting and analysis with flexible
    time periods and intervals.
    
    **Features:**
    - OHLCV (Open, High, Low, Close, Volume) data
    - Flexible time periods and intervals
    - Automatic data validation and gap detection
    - Split and dividend adjustments (when available)
    - Anomaly detection for unusual price movements
    
    **Time Periods:**
    - 1d, 5d, 1m, 3m, 6m, 1y, 2y, 5y, 10y, ytd, max
    
    **Intervals:**
    - Intraday: 1m, 2m, 5m, 15m, 30m, 60m, 90m
    - Daily: 1d, 5d
    - Weekly/Monthly: 1wk, 1mo, 3mo
    
    **Data Quality:**
    - Automatic gap detection and validation
    - Cross-provider consistency checks
    - Historical anomaly detection
    """
)
async def get_chart(
    symbol: str = Path(
        ...,
        description="Security symbol for historical data",
        example="AAPL"
    ),
    period: str = Query(
        "1y",
        description="Time period for historical data",
        regex=r"^(1d|5d|1m|3m|6m|1y|2y|5y|10y|ytd|max)$"
    ),
    interval: str = Query(
        "1d",
        description="Data interval",
        regex=r"^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$"
    ),
    include_dividends: bool = Query(
        False,
        description="Include dividend information in response"
    ),
    adjust_splits: bool = Query(
        True,
        description="Adjust prices for stock splits"
    ),
    market_data_service: MarketDataService = Depends(get_market_data_service)
) -> HistoricalResponse:
    """Get historical price data for charting."""
    
    # Validate and normalize symbol
    normalized_symbol = validate_symbol(symbol)
    
    # Validate period and interval combination
    intraday_intervals = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"]
    short_periods = ["1d", "5d"]
    
    if interval in intraday_intervals and period not in short_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Intraday intervals ({interval}) only supported for short periods (1d, 5d)"
        )
    
    # Create request
    request = HistoricalRequest(
        symbol=normalized_symbol,
        period=period,
        interval=interval,
        include_dividends=include_dividends,
        adjust_splits=adjust_splits
    )
    
    # Get historical data from market data service
    response = await market_data_service.get_historical_data(request)
    
    # Handle response
    return handle_market_data_response(response, normalized_symbol, "Chart")


@router.get(
    "/quote/{symbol}/realtime",
    response_model=QuoteResponse,
    summary="Get real-time quote (streaming endpoint)",
    description="""
    Real-time streaming endpoint for quote data with minimal caching
    for applications requiring the freshest possible data.
    
    **Features:**
    - Bypasses cache for real-time data
    - Optimized for low-latency requirements
    - WebSocket-compatible response format
    - Enhanced anomaly detection for rapid changes
    """
)
async def get_realtime_quote(
    symbol: str = Path(..., description="Security symbol"),
    market_data_service: MarketDataService = Depends(get_market_data_service)
) -> QuoteResponse:
    """Get real-time quote with minimal caching."""
    
    normalized_symbol = validate_symbol(symbol)
    
    request = QuoteRequest(
        symbol=normalized_symbol,
        require_real_time=True,
        max_age_seconds=30  # Very fresh data required
    )
    
    response = await market_data_service.get_quote(request)
    return handle_market_data_response(response, normalized_symbol, "Realtime Quote")


@router.get(
    "/quote/{symbol}/extended",
    response_model=QuoteResponse,
    summary="Get extended quote with additional metrics",
    description="""
    Extended quote endpoint providing additional financial metrics
    and market data beyond basic price information.
    
    **Additional Data:**
    - Extended hours trading information
    - Advanced financial ratios
    - Market sentiment indicators
    - Volume analysis and patterns
    - Historical volatility metrics
    """
)
async def get_extended_quote(
    symbol: str = Path(..., description="Security symbol"),
    market_data_service: MarketDataService = Depends(get_market_data_service)
) -> QuoteResponse:
    """Get extended quote with additional metrics."""
    
    normalized_symbol = validate_symbol(symbol)
    
    request = QuoteRequest(
        symbol=normalized_symbol,
        include_extended_hours=True
    )
    
    response = await market_data_service.get_quote(request)
    return handle_market_data_response(response, normalized_symbol, "Extended Quote")


# Health and status endpoints
@router.get(
    "/health",
    summary="Securities API health check",
    description="Check the health status of securities API endpoints and underlying services"
)
async def health_check(
    market_data_service: MarketDataService = Depends(get_market_data_service)
):
    """Health check endpoint for securities API."""
    try:
        # Get system health from market data service
        health_response = await market_data_service.get_system_health()
        
        if health_response.success:
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "services": {
                    "market_data": "healthy",
                    "providers": health_response.health.get("providers", {}),
                    "cache": "healthy"
                }
            }
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "timestamp": datetime.now().isoformat(),
                    "error": health_response.error
                }
            )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )


@router.get(
    "/status",
    summary="API status and metrics",
    description="Get detailed status information and performance metrics"
)
async def get_status(
    market_data_service: MarketDataService = Depends(get_market_data_service)
):
    """Get API status and performance metrics."""
    try:
        health_response = await market_data_service.get_system_health()
        
        return {
            "api_version": "v1",
            "timestamp": datetime.now().isoformat(),
            "uptime": "Available in health response",
            "endpoints": {
                "quote": "active",
                "profile": "active", 
                "chart": "active"
            },
            "system_health": health_response.health if health_response.success else None,
            "performance": {
                "avg_response_time_ms": "Available in health response",
                "total_requests": "Available in health response",
                "error_rate": "Available in health response"
            }
        }
    except Exception as e:
        logger.error("Status check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve status information"
        )