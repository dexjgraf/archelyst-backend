"""
Fixed Market data Pydantic schemas compatible with Pydantic v1.

Contains simplified but functional request and response models for market data endpoints.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from .base import BaseResponse, DataProviderInfo


# ============================================================================
# Enums and Constants
# ============================================================================

class MarketRegion(str, Enum):
    """Market regions."""
    US = "US"
    EUROPE = "EUROPE"
    ASIA = "ASIA"
    AMERICAS = "AMERICAS"
    GLOBAL = "GLOBAL"


class IndexType(str, Enum):
    """Types of market indices."""
    BROAD_MARKET = "broad_market"
    SECTOR = "sector"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    BOND = "bond"
    VOLATILITY = "volatility"
    CRYPTO = "crypto"


class SectorCategory(str, Enum):
    """Market sector categories."""
    TECHNOLOGY = "Technology"
    HEALTHCARE = "Healthcare"
    FINANCIALS = "Financials"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    CONSUMER_STAPLES = "Consumer Staples"
    INDUSTRIALS = "Industrials"
    ENERGY = "Energy"
    UTILITIES = "Utilities"
    REAL_ESTATE = "Real Estate"
    MATERIALS = "Materials"
    COMMUNICATION_SERVICES = "Communication Services"


class CommodityType(str, Enum):
    """Types of commodities."""
    PRECIOUS_METALS = "precious_metals"
    ENERGY = "energy"
    AGRICULTURE = "agriculture"
    INDUSTRIAL_METALS = "industrial_metals"


class CurrencyPair(str, Enum):
    """Major currency pairs."""
    EUR_USD = "EURUSD"
    GBP_USD = "GBPUSD"
    USD_JPY = "USDJPY"
    USD_CHF = "USDCHF"
    AUD_USD = "AUDUSD"
    USD_CAD = "USDCAD"
    NZD_USD = "NZDUSD"


# ============================================================================
# Market Overview Models - Simplified for Pydantic v1
# ============================================================================

class MarketSummary(BaseModel):
    """Market summary statistics."""
    
    total_market_cap: Optional[int] = None
    trading_volume: Optional[int] = None
    advancing_stocks: Optional[int] = None
    declining_stocks: Optional[int] = None
    unchanged_stocks: Optional[int] = None
    new_highs: Optional[int] = None
    new_lows: Optional[int] = None
    fear_greed_index: Optional[Decimal] = None


class IndexData(BaseModel):
    """Market index data."""
    
    symbol: str
    name: str
    value: Decimal
    change: Decimal
    change_percent: Decimal
    previous_close: Decimal
    day_high: Decimal
    day_low: Decimal
    week_52_high: Optional[Decimal] = None
    week_52_low: Optional[Decimal] = None
    index_type: IndexType
    region: MarketRegion
    last_update: datetime


class SectorPerformance(BaseModel):
    """Sector performance data."""
    
    sector: SectorCategory
    change_percent: Decimal
    market_cap: Optional[int] = None
    volume: Optional[int] = None
    top_performers: List[str] = []
    worst_performers: List[str] = []


class MarketOverview(BaseModel):
    """Complete market overview data - Pydantic v1 compatible."""
    
    date: date
    market_status: str
    summary: MarketSummary
    major_indices: List[IndexData]
    sector_performance: List[SectorPerformance]
    market_movers: Dict[str, List[str]] = {}
    economic_indicators: Dict[str, Any] = {}


class MarketOverviewResponse(BaseResponse[MarketOverview]):
    """Market overview API response."""
    
    provider: Optional[DataProviderInfo] = None


# ============================================================================
# Simplified Models for Other Market Data
# ============================================================================

class CommodityData(BaseModel):
    """Commodity price data."""
    
    symbol: str
    name: str
    price: Decimal
    change: Decimal
    change_percent: Decimal
    unit: str
    commodity_type: CommodityType
    last_update: datetime


class CommoditiesData(BaseModel):
    """Commodities market data."""
    
    commodities: List[CommodityData]
    commodity_type: Optional[CommodityType] = None


class CurrencyRate(BaseModel):
    """Currency exchange rate data."""
    
    pair: str
    rate: Decimal
    change: Decimal
    change_percent: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    high_24h: Optional[Decimal] = None
    low_24h: Optional[Decimal] = None
    last_update: datetime


class ForexData(BaseModel):
    """Forex market data."""
    
    rates: List[CurrencyRate]
    base_currency: str = "USD"


class CryptoData(BaseModel):
    """Cryptocurrency data."""
    
    symbol: str
    name: str
    price: Decimal
    change_24h: Decimal
    change_percent_24h: Decimal
    market_cap: Optional[int] = None
    volume_24h: Optional[int] = None
    circulating_supply: Optional[Decimal] = None
    max_supply: Optional[Decimal] = None
    market_cap_rank: Optional[int] = None
    last_update: datetime


class MarketMover(BaseModel):
    """Market mover data."""
    
    symbol: str
    name: str
    price: Decimal
    change: Decimal
    change_percent: Decimal
    volume: int
    market_cap: Optional[int] = None


# ============================================================================
# Additional Required Models
# ============================================================================

class IndicesListData(BaseModel):
    """List of market indices."""
    
    indices: List[IndexData]
    region: Optional[MarketRegion] = None
    index_type: Optional[IndexType] = None


class CryptoMarketData(BaseModel):
    """Cryptocurrency market data."""
    
    cryptocurrencies: List[CryptoData]
    total_market_cap: Optional[int] = None
    total_volume_24h: Optional[int] = None
    bitcoin_dominance: Optional[Decimal] = None


class MarketMoversData(BaseModel):
    """Market movers data."""
    
    gainers: List[MarketMover]
    losers: List[MarketMover]
    most_active: List[MarketMover]
    date: date


# ============================================================================
# Response Models
# ============================================================================

class IndicesResponse(BaseResponse[IndicesListData]):
    """Indices list API response."""
    provider: Optional[DataProviderInfo] = None


class CommoditiesResponse(BaseResponse[CommoditiesData]):
    """Commodities API response."""
    provider: Optional[DataProviderInfo] = None


class ForexResponse(BaseResponse[ForexData]):
    """Forex API response."""
    provider: Optional[DataProviderInfo] = None


class CryptoResponse(BaseResponse[CryptoMarketData]):
    """Crypto market API response."""
    provider: Optional[DataProviderInfo] = None


class MarketMoversResponse(BaseResponse[MarketMoversData]):
    """Market movers API response."""
    provider: Optional[DataProviderInfo] = None


# ============================================================================
# Export all models
# ============================================================================

__all__ = [
    # Enums
    "MarketRegion",
    "IndexType", 
    "SectorCategory",
    "CommodityType",
    "CurrencyPair",
    
    # Market overview models
    "MarketSummary",
    "IndexData",
    "SectorPerformance", 
    "MarketOverview",
    "MarketOverviewResponse",
    
    # Indices models
    "IndicesListData",
    "IndicesResponse",
    
    # Commodities models
    "CommodityData",
    "CommoditiesData",
    "CommoditiesResponse",
    
    # Forex models
    "CurrencyRate",
    "ForexData", 
    "ForexResponse",
    
    # Crypto models
    "CryptoData",
    "CryptoMarketData",
    "CryptoResponse",
    
    # Market movers models
    "MarketMover",
    "MarketMoversData",
    "MarketMoversResponse"
]