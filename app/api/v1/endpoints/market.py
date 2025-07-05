"""
Market data endpoints for indices, overview, and market-wide information.

Provides endpoints for market overview, major indices, commodities,
crypto markets, and general market status information.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, status
from datetime import datetime, date

from ....core.security import get_current_user_optional_supabase
from ....schemas.market import (
    MarketOverview, MarketOverviewResponse, IndexData, IndicesResponse,
    IndicesListData, CommoditiesResponse, CommoditiesData, CommodityData,
    ForexResponse, ForexData, CurrencyRate, CryptoResponse, CryptoMarketData,
    CryptoData, MarketMoversResponse, MarketMoversData, MarketMover,
    MarketSummary, SectorPerformance, MarketRegion, IndexType,
    SectorCategory, CommodityType
)
from ....schemas.base import DataProviderInfo

# ============================================================================
# Logger Setup
# ============================================================================

logger = logging.getLogger(__name__)

# Note: Response models are now imported from schemas.market

# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter()

# ============================================================================
# Market Data Endpoints
# ============================================================================

@router.get(
    "/overview",
    response_model=MarketOverviewResponse,
    summary="Get Market Overview",
    description="Get comprehensive market overview including indices, commodities, and crypto"
)
async def get_market_overview(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional_supabase)
) -> MarketOverviewResponse:
    """
    Get comprehensive market overview.
    
    Retrieves current data for major market indices, commodities, cryptocurrencies,
    and market status across different exchanges.
    
    - **Authentication**: Optional - provides access to additional market data
    """
    try:
        # TODO: Implement actual data provider integration
        # Generate mock market overview data
        
        mock_indices = [
            IndexData(
                symbol="^GSPC",
                name="S&P 500",
                value=5537.02,
                change=15.87,
                change_percent=0.29,
                previous_close=5521.15,
                day_high=5542.35,
                day_low=5528.10,
                index_type=IndexType.BROAD_MARKET,
                region=MarketRegion.US,
                last_update=datetime.utcnow()
            ),
            IndexData(
                symbol="^IXIC",
                name="NASDAQ Composite",
                value=18188.30,
                change=87.50,
                change_percent=0.48,
                previous_close=18100.80,
                day_high=18195.45,
                day_low=18175.20,
                index_type=IndexType.BROAD_MARKET,
                region=MarketRegion.US,
                last_update=datetime.utcnow()
            ),
            IndexData(
                symbol="^DJI",
                name="Dow Jones Industrial Average",
                value=39308.00,
                change=123.75,
                change_percent=0.32,
                previous_close=39184.25,
                day_high=39315.80,
                day_low=39201.45,
                index_type=IndexType.BROAD_MARKET,
                region=MarketRegion.US,
                last_update=datetime.utcnow()
            )
        ]
        
        mock_commodities = [
            CommodityData(
                symbol="GC=F",
                name="Gold",
                price=2356.80,
                change=-5.20,
                change_percent=-0.22,
                unit="USD/oz",
                commodity_type=CommodityType.PRECIOUS_METALS,
                last_update=datetime.utcnow()
            ),
            CommodityData(
                symbol="CL=F",
                name="Crude Oil",
                price=83.45,
                change=1.25,
                change_percent=1.52,
                unit="USD/barrel",
                commodity_type=CommodityType.ENERGY,
                last_update=datetime.utcnow()
            )
        ]
        
        mock_crypto = [
            CryptoData(
                symbol="BTC",
                name="Bitcoin",
                price=57842.30,
                change_24h=1254.75,
                change_percent_24h=2.22,
                market_cap=1142000000000,
                volume_24h=28450000000,
                circulating_supply=19500000.0,
                max_supply=21000000.0,
                market_cap_rank=1,
                last_update=datetime.utcnow()
            ),
            CryptoData(
                symbol="ETH",
                name="Ethereum",
                price=3087.45,
                change_24h=95.30,
                change_percent_24h=3.19,
                market_cap=371000000000,
                volume_24h=15200000000,
                circulating_supply=120280000.0,
                market_cap_rank=2,
                last_update=datetime.utcnow()
            )
        ]
        
        # Create market summary
        market_summary = MarketSummary(
            total_market_cap=45000000000000,
            trading_volume=500000000000,
            advancing_stocks=2847,
            declining_stocks=1923,
            unchanged_stocks=230,
            new_highs=156,
            new_lows=43,
            fear_greed_index=65.5
        )
        
        # Create sector performance
        sector_performance = [
            SectorPerformance(
                sector=SectorCategory.TECHNOLOGY,
                change_percent=1.23,
                market_cap=12000000000000,
                volume=25000000000,
                top_performers=["AAPL", "MSFT", "GOOGL"],
                worst_performers=["META", "NFLX", "TSLA"]
            )
        ]
        
        mock_overview = MarketOverview(
            date=date.today(),
            market_status="CLOSED",
            session_info={
                "regular_hours": {"start": "09:30", "end": "16:00"},
                "extended_hours": {"start": "04:00", "end": "20:00"}
            },
            summary=market_summary,
            major_indices=mock_indices,
            sector_performance=sector_performance,
            market_movers={
                "top_gainers": ["AAPL", "MSFT", "GOOGL"],
                "top_losers": ["META", "NFLX", "TSLA"],
                "most_active": ["SPY", "QQQ", "AMZN"]
            },
            economic_indicators={
                "vix": 18.45,
                "dxy": 104.23,
                "ten_year_yield": 4.25
            }
        )
        
        provider_info = DataProviderInfo(
            name="mock",
            source="Mock Data Provider",
            timestamp=datetime.utcnow(),
            cache_hit=False
        )
        
        logger.info(f"Market overview requested by user: {current_user.get('user_id', 'anonymous') if current_user else 'anonymous'}")
        
        return MarketOverviewResponse(
            success=True,
            message="Market overview retrieved successfully",
            data=mock_overview,
            timestamp=datetime.utcnow(),
            provider=provider_info
        )
        
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "message": "Failed to retrieve market overview",
                "type": "market_error"
            }
        )


@router.get(
    "/indices",
    response_model=IndicesResponse,
    summary="Get Market Indices",
    description="Get current data for major market indices"
)
async def get_market_indices(
    region: MarketRegion = Query(MarketRegion.US, description="Region filter"),
    index_type: Optional[IndexType] = Query(None, description="Index type filter"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional_supabase)
) -> IndicesResponse:
    """
    Get market indices data.
    
    Retrieves current values and changes for major market indices,
    optionally filtered by geographic region.
    
    - **region**: Geographic region (US, EU, ASIA, ALL)
    - **Authentication**: Optional - provides access to additional indices
    """
    try:
        # TODO: Implement actual data provider integration
        # Generate mock indices based on region
        
        all_indices = {
            MarketRegion.US: [
                IndexData(symbol="^GSPC", name="S&P 500", value=5537.02, change=15.87, change_percent=0.29, 
                         previous_close=5521.15, day_high=5542.35, day_low=5528.10, 
                         index_type=IndexType.BROAD_MARKET, region=MarketRegion.US, last_update=datetime.utcnow()),
                IndexData(symbol="^IXIC", name="NASDAQ", value=18188.30, change=87.50, change_percent=0.48,
                         previous_close=18100.80, day_high=18195.45, day_low=18175.20,
                         index_type=IndexType.BROAD_MARKET, region=MarketRegion.US, last_update=datetime.utcnow()),
                IndexData(symbol="^DJI", name="Dow Jones", value=39308.00, change=123.75, change_percent=0.32,
                         previous_close=39184.25, day_high=39315.80, day_low=39201.45,
                         index_type=IndexType.BROAD_MARKET, region=MarketRegion.US, last_update=datetime.utcnow())
            ],
            MarketRegion.EUROPE: [
                IndexData(symbol="^STOXX50E", name="EURO STOXX 50", value=4912.15, change=-12.30, change_percent=-0.25,
                         previous_close=4924.45, day_high=4918.30, day_low=4908.80,
                         index_type=IndexType.BROAD_MARKET, region=MarketRegion.EUROPE, last_update=datetime.utcnow())
            ]
        }
        
        if region == MarketRegion.GLOBAL:
            mock_indices = []
            for region_indices in all_indices.values():
                mock_indices.extend(region_indices)
        else:
            mock_indices = all_indices.get(region, all_indices[MarketRegion.US])
        
        # Apply index type filter if specified
        if index_type:
            mock_indices = [idx for idx in mock_indices if idx.index_type == index_type]
        
        indices_data = IndicesListData(
            indices=mock_indices,
            region=region if region != MarketRegion.GLOBAL else None,
            index_type=index_type
        )
        
        provider_info = DataProviderInfo(
            name="mock",
            source="Mock Data Provider",
            timestamp=datetime.utcnow(),
            cache_hit=False
        )
        
        logger.info(f"Market indices requested for region {region} by user: {current_user.get('user_id', 'anonymous') if current_user else 'anonymous'}")
        
        return IndicesResponse(
            success=True,
            message="Market indices retrieved successfully",
            data=indices_data,
            timestamp=datetime.utcnow(),
            provider=provider_info
        )
        
    except Exception as e:
        logger.error(f"Error getting market indices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "message": "Failed to retrieve market indices",
                "type": "indices_error"
            }
        )


@router.get(
    "/movers",
    response_model=MarketMoversResponse,
    summary="Get Top Movers",
    description="Get top gaining and losing stocks"
)
async def get_top_movers(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional_supabase)
) -> MarketMoversResponse:
    """
    Get top stock movers.
    
    Retrieves top gaining stocks, losing stocks, or most actively traded stocks
    based on current market activity.
    
    - **type**: Type of movers (gainers, losers, active)
    - **limit**: Number of results (1-50)
    - **Authentication**: Optional - provides access to extended movers data
    """
    try:
        # TODO: Implement actual data provider integration
        # Generate mock movers data
        
        gainers = [
            MarketMover(symbol="NVDA", name="NVIDIA Corp", price=128.45, change=8.75, change_percent=7.31, volume=45000000, market_cap=3200000000000),
            MarketMover(symbol="AMD", name="Advanced Micro Devices", price=165.30, change=9.20, change_percent=5.90, volume=32000000, market_cap=267000000000),
            MarketMover(symbol="TSLA", name="Tesla Inc", price=251.52, change=12.85, change_percent=5.38, volume=55000000, market_cap=800000000000)
        ]
        
        losers = [
            MarketMover(symbol="INTC", name="Intel Corporation", price=31.25, change=-2.45, change_percent=-7.27, volume=28000000, market_cap=130000000000),
            MarketMover(symbol="IBM", name="IBM Corp", price=185.40, change=-8.30, change_percent=-4.28, volume=15000000, market_cap=170000000000),
            MarketMover(symbol="T", name="AT&T Inc", price=18.75, change=-0.65, change_percent=-3.35, volume=22000000, market_cap=134000000000)
        ]
        
        most_active = [
            MarketMover(symbol="AAPL", name="Apple Inc", price=191.75, change=2.25, change_percent=1.19, volume=75000000, market_cap=2940000000000),
            MarketMover(symbol="MSFT", name="Microsoft Corp", price=447.25, change=5.50, change_percent=1.25, volume=42000000, market_cap=3320000000000),
            MarketMover(symbol="AMZN", name="Amazon.com Inc", price=193.60, change=-1.85, change_percent=-0.95, volume=38000000, market_cap=2020000000000)
        ]
        
        movers_data = MarketMoversData(
            gainers=gainers,
            losers=losers,
            most_active=most_active,
            date=date.today()
        )
        
        provider_info = DataProviderInfo(
            name="mock",
            source="Mock Data Provider",
            timestamp=datetime.utcnow(),
            cache_hit=False
        )
        
        logger.info(f"Market movers requested by user: {current_user.get('user_id', 'anonymous') if current_user else 'anonymous'}")
        
        return MarketMoversResponse(
            success=True,
            message="Market movers retrieved successfully",
            data=movers_data,
            timestamp=datetime.utcnow(),
            provider=provider_info
        )
        
    except Exception as e:
        logger.error(f"Error getting top movers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "message": "Failed to retrieve top movers",
                "type": "movers_error"
            }
        )


# Note: Market status endpoint removed - functionality integrated into market overview


# ============================================================================
# Export Router
# ============================================================================

__all__ = ["router"]