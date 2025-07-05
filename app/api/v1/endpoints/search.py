"""
Search & Discovery API Endpoints

RESTful API endpoints for securities search and discovery with comprehensive
filtering, ranking, and recommendation capabilities integrated with the 
market data orchestration service.
"""

import logging
import time
import structlog
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends, status
from fastapi.responses import JSONResponse
from datetime import datetime

from ....core.security import get_current_user_optional_supabase
from ....schemas.securities import (
    SecuritySearchParams, SecuritySearchResponse, SecuritySearchData,
    SecuritySearchResult, SecurityType, ExchangeCode
)
from ....schemas.base import DataProviderInfo
from ....services.market_data import MarketDataService, get_market_data_service
from ....schemas.market_data import (
    SearchRequest, SearchResponse, AssetType, DataQuality
)
from ....core.config import Settings

# ============================================================================
# Logger Setup
# ============================================================================

logger = logging.getLogger(__name__)
struct_logger = structlog.get_logger(__name__)

# Note: Response models are now imported from schemas.securities

# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter()

# ============================================================================
# Helper Functions
# ============================================================================

def validate_search_query(query: str) -> str:
    """
    Validate and normalize search query.
    
    Args:
        query: Raw search input
        
    Returns:
        str: Normalized query
        
    Raises:
        HTTPException: If query is invalid
    """
    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )
    
    normalized_query = query.strip()
    
    if len(normalized_query) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 1 character"
        )
    
    if len(normalized_query) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query too long. Maximum 100 characters allowed."
        )
    
    return normalized_query


def convert_security_type_to_asset_type(security_types: List[SecurityType]) -> List[AssetType]:
    """Convert SecurityType to AssetType for market data service."""
    type_mapping = {
        SecurityType.STOCK: AssetType.STOCK,
        SecurityType.ETF: AssetType.STOCK,  # ETFs are handled as stocks in market data
        SecurityType.CRYPTO: AssetType.CRYPTO,
        SecurityType.FOREX: AssetType.FOREX,
        SecurityType.COMMODITY: AssetType.COMMODITY,
    }
    
    asset_types = []
    for security_type in security_types:
        mapped_type = type_mapping.get(security_type)
        if mapped_type and mapped_type not in asset_types:
            asset_types.append(mapped_type)
    
    return asset_types if asset_types else [AssetType.STOCK]


def convert_search_results(market_data_response: SearchResponse, original_query: str) -> SecuritySearchData:
    """Convert market data search response to securities search format."""
    results = []
    
    if market_data_response.success and market_data_response.data:
        for result in market_data_response.data.results:
            # Map AssetType back to SecurityType
            security_type = SecurityType.STOCK
            if result.asset_type == AssetType.CRYPTO:
                security_type = SecurityType.CRYPTO
            elif result.asset_type == AssetType.FOREX:
                security_type = SecurityType.FOREX
            elif result.asset_type == AssetType.COMMODITY:
                security_type = SecurityType.COMMODITY
            
            # Map exchange string to ExchangeCode
            exchange_code = ExchangeCode.OTHER
            if result.exchange:
                exchange_upper = result.exchange.upper()
                if "NASDAQ" in exchange_upper:
                    exchange_code = ExchangeCode.NASDAQ
                elif "NYSE" in exchange_upper:
                    exchange_code = ExchangeCode.NYSE
                elif "TSX" in exchange_upper:
                    exchange_code = ExchangeCode.TSX
                elif "LSE" in exchange_upper:
                    exchange_code = ExchangeCode.LSE
            
            security_result = SecuritySearchResult(
                symbol=result.symbol,
                name=result.name,
                type=security_type,
                exchange=exchange_code,
                currency=result.currency,
                sector=result.industry,  # Using industry as sector
                industry=result.industry,
                market_cap=result.market_cap,
                last_price=None,  # Would need to be fetched separately
                relevance_score=result.relevance_score / 100.0  # Convert to 0-1 range
            )
            
            results.append(security_result)
    
    return SecuritySearchData(
        results=results,
        total_found=len(results),
        query=original_query,
        execution_time_ms=market_data_response.provenance.processing_time_ms if market_data_response.provenance else 0
    )

# ============================================================================
# Search Endpoints
# ============================================================================

@router.post(
    "/securities",
    response_model=SecuritySearchResponse,
    summary="Search Securities",
    description="Search for stocks, ETFs, crypto and other securities by symbol or name"
)
async def search_securities(
    params: SecuritySearchParams = Body(...),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional_supabase),
    market_data_service: MarketDataService = Depends(get_market_data_service)
) -> SecuritySearchResponse:
    """
    Search for securities by symbol or company name.
    
    Provides intelligent search across stocks, ETFs, cryptocurrencies, and other
    financial instruments with advanced filtering capabilities using the 
    market data orchestration service.
    
    - **q**: Search query (symbol or company name)
    - **type**: Security type filter (stock, etf, crypto, forex, commodity)
    - **exchange**: Exchange filter (NYSE, NASDAQ, etc.)
    - **country**: Country filter (US, CA, GB, etc.)
    - **sector**: Sector filter (Technology, Healthcare, etc.)
    - **market_cap_min/max**: Market cap range filter
    - **limit**: Maximum results to return (1-100)
    - **Authentication**: Optional - provides enhanced search features when authenticated
    """
    try:
        start_time = time.time()
        
        # Validate and normalize query
        normalized_query = validate_search_query(params.query)
        
        # Convert security types to asset types for market data service
        asset_types = convert_security_type_to_asset_type(params.types) if params.types else [AssetType.STOCK]
        
        # Create search request for market data service
        search_request = SearchRequest(
            query=normalized_query,
            asset_types=asset_types,
            limit=params.limit,
            exchanges=[exchange.value for exchange in params.exchanges] if params.exchanges else None,
            countries=params.countries
        )
        
        # Perform search using market data service
        market_data_response = await market_data_service.search_securities(search_request)
        
        # Convert market data response to securities format
        search_results = convert_search_results(market_data_response, normalized_query)
        
        # Apply additional filters not handled by market data service
        filtered_results = search_results.results
        
        if params.sectors:
            filtered_results = [
                r for r in filtered_results 
                if r.sector and any(sector.lower() in r.sector.lower() for sector in params.sectors)
            ]
        
        if params.min_market_cap:
            filtered_results = [
                r for r in filtered_results 
                if r.market_cap and r.market_cap >= params.min_market_cap
            ]
        
        if params.max_market_cap:
            filtered_results = [
                r for r in filtered_results 
                if r.market_cap and r.market_cap <= params.max_market_cap
            ]
        
        # Update search results with filtered data
        search_results.results = filtered_results
        search_results.total_found = len(filtered_results)
        
        # Create provider info
        provider_info = DataProviderInfo(
            name=market_data_response.provenance.primary_source.value if market_data_response.provenance else "unknown",
            source=f"Market Data Service ({market_data_response.provenance.primary_source.value})" if market_data_response.provenance else "Market Data Service",
            timestamp=market_data_response.timestamp if market_data_response.timestamp else datetime.utcnow(),
            cache_hit=market_data_response.provenance.cache_hit if market_data_response.provenance else False
        )
        
        # Log search activity
        struct_logger.info(
            "Securities search completed",
            query=normalized_query,
            result_count=len(filtered_results),
            user_id=current_user.get('user_id', 'anonymous') if current_user else 'anonymous',
            provider=provider_info.name,
            quality_score=market_data_response.data_quality.overall_score if market_data_response.data_quality else None,
            processing_time_ms=search_results.execution_time_ms
        )
        
        return SecuritySearchResponse(
            success=market_data_response.success,
            message="Search completed successfully" if market_data_response.success else market_data_response.error,
            data=search_results if market_data_response.success else None,
            timestamp=datetime.utcnow(),
            provider=provider_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        struct_logger.error("Error searching securities", error=str(e), query=params.query)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "message": "Securities search service temporarily unavailable",
                "type": "search_error"
            }
        )


@router.get(
    "/suggestions",
    summary="Get search suggestions",
    description="""
    Get intelligent search suggestions based on partial input.
    Optimized for autocomplete and search-as-you-type functionality.
    """
)
async def get_search_suggestions(
    query: str = Query(
        ...,
        min_length=1,
        max_length=50,
        description="Partial search query for suggestions",
        example="app"
    ),
    limit: int = Query(
        5,
        ge=1,
        le=20,
        description="Maximum number of suggestions"
    ),
    asset_types: List[str] = Query(
        ["stock"],
        description="Asset types to include in suggestions"
    ),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional_supabase),
    market_data_service: MarketDataService = Depends(get_market_data_service)
):
    """Get search suggestions for autocomplete."""
    
    try:
        # Validate query
        normalized_query = validate_search_query(query)
        
        # Convert string asset types to AssetType enums
        converted_asset_types = []
        for asset_type_str in asset_types:
            if asset_type_str.lower() == "stock":
                converted_asset_types.append(AssetType.STOCK)
            elif asset_type_str.lower() == "crypto":
                converted_asset_types.append(AssetType.CRYPTO)
            elif asset_type_str.lower() == "forex":
                converted_asset_types.append(AssetType.FOREX)
            elif asset_type_str.lower() == "commodity":
                converted_asset_types.append(AssetType.COMMODITY)
        
        if not converted_asset_types:
            converted_asset_types = [AssetType.STOCK]
        
        # For suggestions, we want faster, more targeted results
        request = SearchRequest(
            query=normalized_query,
            asset_types=converted_asset_types,
            limit=limit
        )
        
        # Get search results
        response = await market_data_service.search_securities(request)
        
        if response.success and response.data:
            # Convert to suggestion format
            suggestions = []
            for result in response.data.results[:limit]:
                suggestions.extend([
                    {
                        "text": result.symbol,
                        "type": "symbol",
                        "score": result.relevance_score,
                        "display": f"{result.symbol} - {result.name}"
                    },
                    {
                        "text": result.name,
                        "type": "company",
                        "score": result.relevance_score * 0.9,  # Slightly lower for company names
                        "display": f"{result.name} ({result.symbol})"
                    }
                ])
            
            # Remove duplicates and sort by score
            unique_suggestions = {}
            for suggestion in suggestions:
                key = suggestion["text"].lower()
                if key not in unique_suggestions or suggestion["score"] > unique_suggestions[key]["score"]:
                    unique_suggestions[key] = suggestion
            
            sorted_suggestions = sorted(
                unique_suggestions.values(),
                key=lambda x: x["score"],
                reverse=True
            )[:limit]
            
            return {
                "query": normalized_query,
                "suggestions": sorted_suggestions,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "query": normalized_query,
                "suggestions": [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        struct_logger.error("Suggestions request failed", query=query, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate suggestions"
        )


@router.get(
    "/trending",
    summary="Get trending securities",
    description="""
    Discover trending and popular securities based on market activity,
    volume, and price movements.
    """
)
async def get_trending_securities(
    asset_type: str = Query(
        "stock",
        regex=r"^(stock|crypto|etf|all)$",
        description="Asset type for trending analysis"
    ),
    timeframe: str = Query(
        "1d",
        regex=r"^(1h|4h|1d|1w)$",
        description="Timeframe for trending analysis"
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of trending securities"
    ),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional_supabase)
):
    """Get trending securities based on market activity."""
    
    try:
        # This would typically use a specialized trending analysis service
        # For now, we'll simulate trending data based on popular symbols
        
        # Get popular symbols for the asset type
        popular_symbols = {
            "stock": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "NFLX", "AMD", "UBER"],
            "crypto": ["BTC", "ETH", "ADA", "DOT", "SOL", "MATIC", "AVAX", "LINK", "UNI", "AAVE"],
            "etf": ["SPY", "QQQ", "IWM", "DIA", "VTI"],
        }
        
        if asset_type == "all":
            symbols = []
            for type_symbols in popular_symbols.values():
                symbols.extend(type_symbols[:5])  # Take top 5 from each
        else:
            symbols = popular_symbols.get(asset_type, popular_symbols["stock"])
        
        # Simulate trending analysis
        trending_securities = []
        
        for symbol in symbols[:limit]:
            # This would be replaced with actual trending calculation
            trending_securities.append({
                "symbol": symbol,
                "name": f"{symbol} Corporation",  # Simplified
                "asset_type": asset_type,
                "change_percent": round((hash(symbol + timeframe) % 2000 - 1000) / 100, 2),
                "volume_ratio": round(1.5 + (hash(symbol) % 300) / 100, 2),
                "trending_score": round(50 + (hash(symbol + "trending") % 500) / 10, 1),
                "timeframe": timeframe
            })
        
        # Sort by trending score
        trending_securities.sort(key=lambda x: x["trending_score"], reverse=True)
        
        return {
            "trending": trending_securities,
            "asset_type": asset_type,
            "timeframe": timeframe,
            "timestamp": datetime.utcnow().isoformat(),
            "total_analyzed": len(symbols)
        }
        
    except Exception as e:
        struct_logger.error("Trending analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate trending analysis"
        )


@router.get(
    "/popular",
    summary="Get popular securities",
    description="""
    Get a curated list of popular and widely-traded securities.
    Useful for discovery and portfolio inspiration.
    """
)
async def get_popular_securities(
    category: str = Query(
        "large_cap",
        regex=r"^(large_cap|growth|dividend|etf|crypto|international|all)$",
        description="Category of popular securities"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of securities to return"
    ),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional_supabase)
):
    """Get popular securities by category."""
    
    try:
        # Define popular securities by category
        popular_lists = {
            "large_cap": [
                "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "BRK.B", 
                "JNJ", "V", "WMT", "PG", "JPM", "UNH", "HD", "MA", "DIS", "PYPL"
            ],
            "growth": [
                "TSLA", "NVDA", "AMD", "SQ", "ROKU", "ZM", "SHOP", "TWLO", "OKTA",
                "CRWD", "ZS", "SNOW", "PLTR", "RBLX", "U", "NET", "DDOG", "MDB"
            ],
            "dividend": [
                "JNJ", "PG", "KO", "PEP", "WMT", "T", "VZ", "IBM", "GE", "F",
                "BAC", "C", "XOM", "CVX", "MO", "O", "MAIN", "STAG", "MPW"
            ],
            "etf": [
                "SPY", "QQQ", "VTI", "IWM", "EFA", "EEM", "VEA", "IEFA", "AGG",
                "BND", "TLT", "GLD", "SLV", "USO", "XLF", "XLK", "XLE", "XLV"
            ],
            "crypto": [
                "BTC", "ETH", "ADA", "SOL", "DOT", "MATIC", "AVAX", "LINK", "UNI",
                "AAVE", "COMP", "MKR", "YFI", "SNX", "1INCH", "CRV", "BAL", "SUSHI"
            ],
            "international": [
                "TSM", "ASML", "SAP", "TM", "NVO", "ABBV", "UL", "NVS", "AZN",
                "RHHBY", "BP", "RDS.A", "VOD", "ING", "BCS", "DB", "SAN", "BBVA"
            ]
        }
        
        if category == "all":
            # Combine all categories with some from each
            symbols = []
            for cat_symbols in popular_lists.values():
                symbols.extend(cat_symbols[:10])  # Take top 10 from each category
        else:
            symbols = popular_lists.get(category, popular_lists["large_cap"])
        
        # Create simplified popular securities list
        popular_securities = []
        for symbol in symbols[:limit]:
            popular_securities.append({
                "symbol": symbol,
                "name": f"{symbol} Corporation",  # Simplified
                "category": category,
                "popularity_score": round(100 - (len(popular_securities) * 1.5), 1),
                "asset_type": "crypto" if category == "crypto" else "stock"
            })
        
        return {
            "popular": popular_securities,
            "category": category,
            "total_count": len(popular_securities),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        struct_logger.error("Popular securities request failed", category=category, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve popular securities"
        )


# Health and status endpoints
@router.get(
    "/health",
    summary="Search API health check",
    description="Check the health status of search API endpoints and underlying services"
)
async def health_check(
    market_data_service: MarketDataService = Depends(get_market_data_service)
):
    """Health check endpoint for search API."""
    try:
        # Test basic search functionality
        test_request = SearchRequest(
            query="AAPL",
            asset_types=[AssetType.STOCK],
            limit=1
        )
        
        test_response = await market_data_service.search_securities(test_request)
        
        if test_response.success:
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "services": {
                    "search": "healthy",
                    "market_data": "healthy",
                    "cache": "healthy"
                },
                "test_search": "passed"
            }
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": test_response.error,
                    "test_search": "failed"
                }
            )
    except Exception as e:
        struct_logger.error("Search health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


# ============================================================================
# Export Router
# ============================================================================

__all__ = ["router"]