"""
Search endpoints for securities discovery and market search functionality.

Provides endpoints for searching stocks, ETFs, crypto, and other securities
with intelligent filtering and ranking capabilities.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends, status
from datetime import datetime

from ....core.security import get_current_user_optional_supabase
from ....schemas.securities import (
    SecuritySearchParams, SecuritySearchResponse, SecuritySearchData,
    SecuritySearchResult, SecurityType, ExchangeCode
)
from ....schemas.base import DataProviderInfo

# ============================================================================
# Logger Setup
# ============================================================================

logger = logging.getLogger(__name__)

# Note: Response models are now imported from schemas.securities

# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter()

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
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional_supabase)
) -> SecuritySearchResponse:
    """
    Search for securities by symbol or company name.
    
    Provides intelligent search across stocks, ETFs, cryptocurrencies, and other
    financial instruments with advanced filtering capabilities.
    
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
        query = params.query.strip()
        
        # TODO: Implement actual securities search with data providers
        # For now, return mock search results
        
        # Generate mock results based on query
        if query.upper() in ["AAPL", "APPLE"]:
            mock_results = [
                SecuritySearchResult(
                    symbol="AAPL",
                    name="Apple Inc.",
                    type=SecurityType.STOCK,
                    exchange=ExchangeCode.NASDAQ,
                    currency="USD",
                    sector="Technology",
                    industry="Consumer Electronics",
                    market_cap=3000000000000,
                    last_price=191.75,
                    relevance_score=1.0
                )
            ]
        elif query.upper() in ["MSFT", "MICROSOFT"]:
            mock_results = [
                SecuritySearchResult(
                    symbol="MSFT",
                    name="Microsoft Corporation",
                    type=SecurityType.STOCK,
                    exchange=ExchangeCode.NASDAQ,
                    currency="USD",
                    sector="Technology",
                    industry="Software",
                    market_cap=2800000000000,
                    last_price=447.25,
                    relevance_score=1.0
                )
            ]
        elif "tech" in query.lower():
            mock_results = [
                SecuritySearchResult(
                    symbol="AAPL",
                    name="Apple Inc.",
                    type=SecurityType.STOCK,
                    exchange=ExchangeCode.NASDAQ,
                    currency="USD",
                    sector="Technology",
                    industry="Consumer Electronics",
                    market_cap=3000000000000,
                    last_price=191.75,
                    relevance_score=0.95
                ),
                SecuritySearchResult(
                    symbol="MSFT",
                    name="Microsoft Corporation",
                    type=SecurityType.STOCK,
                    exchange=ExchangeCode.NASDAQ,
                    currency="USD",
                    sector="Technology",
                    industry="Software",
                    market_cap=2800000000000,
                    last_price=447.25,
                    relevance_score=0.90
                ),
                SecuritySearchResult(
                    symbol="GOOGL",
                    name="Alphabet Inc. Class A",
                    type=SecurityType.STOCK,
                    exchange=ExchangeCode.NASDAQ,
                    currency="USD",
                    sector="Technology",
                    industry="Internet Services",
                    market_cap=2100000000000,
                    last_price=185.30,
                    relevance_score=0.88
                )
            ]
        else:
            # Generic search results
            mock_results = [
                SecuritySearchResult(
                    symbol="SPY",
                    name="SPDR S&P 500 ETF Trust",
                    type=SecurityType.ETF,
                    exchange=ExchangeCode.NYSE,
                    currency="USD",
                    market_cap=550000000000,
                    last_price=553.20,
                    relevance_score=0.75
                ),
                SecuritySearchResult(
                    symbol="BTC",
                    name="Bitcoin",
                    type=SecurityType.CRYPTO,
                    exchange=ExchangeCode.OTHER,
                    currency="USD",
                    market_cap=1142000000000,
                    last_price=57842.30,
                    relevance_score=0.70
                )
            ]
        
        # Apply filters
        filtered_results = mock_results
        
        if params.types:
            filtered_results = [r for r in filtered_results if r.type in params.types]
        
        if params.exchanges:
            filtered_results = [r for r in filtered_results if r.exchange in params.exchanges]
        
        if params.sectors:
            filtered_results = [r for r in filtered_results if r.sector and any(sector.lower() in r.sector.lower() for sector in params.sectors)]
        
        if params.min_market_cap:
            filtered_results = [r for r in filtered_results if r.market_cap and r.market_cap >= params.min_market_cap]
        
        if params.max_market_cap:
            filtered_results = [r for r in filtered_results if r.market_cap and r.market_cap <= params.max_market_cap]
        
        # Apply limit
        filtered_results = filtered_results[:params.limit]
        
        # Calculate search time
        search_time = (time.time() - start_time) * 1000
        
        search_results = SecuritySearchData(
            results=filtered_results,
            total_found=len(filtered_results),
            query=query,
            execution_time_ms=search_time
        )
        
        provider_info = DataProviderInfo(
            name="mock",
            source="Mock Data Provider",
            timestamp=datetime.utcnow(),
            cache_hit=False
        )
        
        logger.info(f"Securities search: '{query}' returned {len(filtered_results)} results for user: {current_user.get('user_id', 'anonymous') if current_user else 'anonymous'}")
        
        return SecuritySearchResponse(
            success=True,
            message="Search completed successfully",
            data=search_results,
            timestamp=datetime.utcnow(),
            provider=provider_info
        )
        
    except Exception as e:
        logger.error(f"Error searching securities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "message": "Securities search service temporarily unavailable",
                "type": "search_error"
            }
        )


# Note: Trending and similar securities endpoints removed - functionality integrated into market movers and AI analysis


# ============================================================================
# Export Router
# ============================================================================

__all__ = ["router"]