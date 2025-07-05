"""
Financial Modeling Prep (FMP) data provider implementation.

Provides real-time market data, company profiles, and search functionality with
integrated rate limiting and caching.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import aiohttp
from app.services.data_providers.base import DataProvider, ProviderResponse, ProviderHealth
from app.services.cache import CacheService, CacheLevel
from app.services.rate_limiter import RateLimiter
from app.core.config import Settings
import structlog

logger = structlog.get_logger(__name__)

class FMPProvider(DataProvider):
    """Financial Modeling Prep data provider."""
    
    def __init__(self, settings: Settings, cache_service: CacheService, rate_limiter: RateLimiter):
        super().__init__("fmp", settings)
        self.cache_service = cache_service
        self.rate_limiter = rate_limiter
        self.api_key = settings.fmp_api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.session = None
        self._last_error = None
        self._retry_count = 0
        self._max_retries = 3
        self._backoff_base = 2
        
        # FMP-specific configuration
        self.endpoints = {
            "quote": "/quote",
            "profile": "/profile",
            "historical": "/historical-price-full",
            "search": "/search",
            "crypto": "/quote",
            "market_overview": "/quote/SPY,QQQ,DIA,BTC-USD,ETH-USD"
        }
        
        # Rate limiting configuration
        self.rate_limits = {
            "requests_per_minute": 300,
            "requests_per_hour": 5000,
            "requests_per_day": 25000,
            "burst_limit": 10
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": "Archelyst-Backend/1.0"}
            )
        return self.session
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make authenticated request to FMP API with rate limiting and caching.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response data
            
        Raises:
            Exception: On API errors or rate limit exceeded
        """
        # Check rate limits
        allowed, rate_info = await self.rate_limiter.is_allowed("fmp", endpoint)
        if not allowed:
            logger.warning(
                "FMP rate limit exceeded",
                endpoint=endpoint,
                rate_info=rate_info
            )
            raise Exception(f"Rate limit exceeded for FMP: {rate_info.get('exceeded_window', 'unknown')}")
        
        # Prepare request
        url = f"{self.base_url}{endpoint}"
        if params is None:
            params = {}
        
        params["apikey"] = self.api_key
        
        # Check cache first
        cache_key = self._generate_cache_key(endpoint, params)
        cache_level = self._get_cache_level(endpoint)
        
        cached_data = await self.cache_service.get(cache_level, "fmp", cache_key)
        if cached_data is not None:
            logger.debug("Cache hit for FMP request", endpoint=endpoint, cache_key=cache_key)
            return cached_data
        
        # Make API request with retry logic
        for attempt in range(self._max_retries + 1):
            try:
                session = await self._get_session()
                
                async with session.get(url, params=params) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            data = json.loads(response_text)
                            
                            # Validate response
                            if self._is_valid_response(data, endpoint):
                                # Cache successful response
                                await self.cache_service.set(cache_level, "fmp", cache_key, data)
                                
                                logger.debug(
                                    "FMP API request successful",
                                    endpoint=endpoint,
                                    status=response.status,
                                    cached=True
                                )
                                
                                # Provider is healthy - handled by base class
                                self._retry_count = 0
                                return data
                            else:
                                logger.warning(
                                    "Invalid FMP response format",
                                    endpoint=endpoint,
                                    data_preview=str(data)[:200]
                                )
                                
                        except json.JSONDecodeError as e:
                            logger.error(
                                "FMP JSON decode error",
                                endpoint=endpoint,
                                response_text=response_text[:500],
                                error=str(e)
                            )
                            
                    elif response.status == 429:
                        # Rate limit hit
                        logger.warning(
                            "FMP API rate limit response",
                            endpoint=endpoint,
                            status=response.status
                        )
                        await self._handle_rate_limit_response(response)
                        
                    elif response.status == 401:
                        # Invalid API key
                        logger.error(
                            "FMP API authentication failed",
                            endpoint=endpoint,
                            status=response.status
                        )
                        # Authentication error - handled by base class
                        raise Exception("FMP API authentication failed - check API key")
                        
                    else:
                        logger.warning(
                            "FMP API error response",
                            endpoint=endpoint,
                            status=response.status,
                            response_text=response_text[:500]
                        )
                        
            except aiohttp.ClientError as e:
                logger.error(
                    "FMP network error",
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
            except Exception as e:
                logger.error(
                    "FMP unexpected error",
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    error=str(e)
                )
            
            # Apply exponential backoff if not last attempt
            if attempt < self._max_retries:
                backoff_time = self._backoff_base ** attempt
                logger.info(
                    "FMP retrying request",
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    backoff_seconds=backoff_time
                )
                await asyncio.sleep(backoff_time)
        
        # All retries failed
        self._retry_count += 1
        error_msg = f"FMP API request failed after {self._max_retries + 1} attempts"
        self._last_error = error_msg
        
        logger.error(
            "FMP API request completely failed",
            endpoint=endpoint,
            max_retries=self._max_retries
        )
        
        raise Exception(error_msg)
    
    def _generate_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        # Remove API key from cache key
        cache_params = {k: v for k, v in params.items() if k != "apikey"}
        key_data = f"{endpoint}_{json.dumps(cache_params, sort_keys=True)}"
        return key_data.replace("/", "_").replace(" ", "_")
    
    def _get_cache_level(self, endpoint: str) -> CacheLevel:
        """Get appropriate cache level for endpoint."""
        if "quote" in endpoint:
            return CacheLevel.QUOTES
        elif "profile" in endpoint:
            return CacheLevel.PROFILES
        elif "historical" in endpoint:
            return CacheLevel.HISTORICAL
        elif "search" in endpoint:
            return CacheLevel.SEARCH
        else:
            return CacheLevel.REAL_TIME
    
    def _is_valid_response(self, data: Any, endpoint: str) -> bool:
        """Validate API response format."""
        if not data:
            return False
        
        # Check for error messages
        if isinstance(data, dict):
            if "Error Message" in data or "error" in data:
                return False
            if "Note" in data and "API call frequency" in str(data.get("Note", "")):
                return False
        
        # Endpoint-specific validation
        if "quote" in endpoint:
            return isinstance(data, list) and len(data) > 0
        elif "profile" in endpoint:
            return isinstance(data, list) and len(data) > 0
        elif "search" in endpoint:
            return isinstance(data, list)  # Empty list is valid for search
        elif "historical" in endpoint:
            return isinstance(data, dict) and "historical" in data
        
        return True
    
    async def _handle_rate_limit_response(self, response: aiohttp.ClientResponse):
        """Handle rate limit response."""
        retry_after = response.headers.get("Retry-After", "60")
        try:
            wait_time = int(retry_after)
        except ValueError:
            wait_time = 60
        
        logger.warning(
            "FMP rate limit hit, waiting",
            retry_after=wait_time
        )
        
        await asyncio.sleep(min(wait_time, 300))  # Max 5 minutes
    
    def _standardize_quote_data(self, raw_data: List[Dict]) -> Dict[str, Any]:
        """Standardize quote data from FMP format."""
        if not raw_data or len(raw_data) == 0:
            return {}
        
        quote = raw_data[0]
        return {
            "symbol": quote.get("symbol", ""),
            "name": quote.get("name", ""),
            "price": float(quote.get("price", 0)),
            "change": float(quote.get("change", 0)),
            "change_percent": float(quote.get("changesPercentage", 0)),
            "previous_close": float(quote.get("previousClose", 0)),
            "open": float(quote.get("open", 0)),
            "high": float(quote.get("dayHigh", 0)),
            "low": float(quote.get("dayLow", 0)),
            "volume": int(quote.get("volume", 0)),
            "market_cap": quote.get("marketCap"),
            "pe_ratio": quote.get("pe"),
            "timestamp": quote.get("timestamp"),
            "provider": "fmp",
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _standardize_profile_data(self, raw_data: List[Dict]) -> Dict[str, Any]:
        """Standardize profile data from FMP format."""
        if not raw_data or len(raw_data) == 0:
            return {}
        
        profile = raw_data[0]
        return {
            "symbol": profile.get("symbol", ""),
            "company_name": profile.get("companyName", ""),
            "description": profile.get("description", ""),
            "industry": profile.get("industry", ""),
            "sector": profile.get("sector", ""),
            "country": profile.get("country", ""),
            "website": profile.get("website", ""),
            "market_cap": profile.get("mktCap"),
            "employees": profile.get("fullTimeEmployees"),
            "exchange": profile.get("exchangeShortName", ""),
            "currency": profile.get("currency", ""),
            "ceo": profile.get("ceo", ""),
            "founded": profile.get("foundingYear"),
            "address": {
                "street": profile.get("address", ""),
                "city": profile.get("city", ""),
                "state": profile.get("state", ""),
                "zip_code": profile.get("zip", ""),
                "country": profile.get("country", "")
            },
            "provider": "fmp",
            "last_updated": datetime.utcnow().isoformat()
        }
    
    # Implement required DataProvider methods
    
    async def get_stock_quote(self, symbol: str) -> ProviderResponse:
        """Get real-time stock quote."""
        try:
            logger.info("Fetching stock quote from FMP", symbol=symbol)
            
            data = await self._make_request(self.endpoints["quote"], {"symbol": symbol})
            standardized_data = self._standardize_quote_data(data)
            
            return ProviderResponse(
                success=True,
                data=standardized_data,
                provider="fmp",
                timestamp=datetime.utcnow(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("FMP stock quote error", symbol=symbol, error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="fmp",
                timestamp=datetime.utcnow(),
                error=str(e),
                metadata={"cached": False}
            )
    
    async def get_stock_profile(self, symbol: str) -> ProviderResponse:
        """Get company profile."""
        try:
            logger.info("Fetching stock profile from FMP", symbol=symbol)
            
            data = await self._make_request(self.endpoints["profile"], {"symbol": symbol})
            standardized_data = self._standardize_profile_data(data)
            
            return ProviderResponse(
                success=True,
                data=standardized_data,
                provider="fmp",
                timestamp=datetime.utcnow(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("FMP stock profile error", symbol=symbol, error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="fmp",
                timestamp=datetime.utcnow(),
                error=str(e),
                metadata={"cached": False}
            )
    
    async def get_historical_data(self, symbol: str, period: str = "1y", 
                                interval: str = "1d") -> ProviderResponse:
        """Get historical price data."""
        try:
            logger.info("Fetching historical data from FMP", symbol=symbol, period=period)
            
            # FMP uses different parameter format
            params = {"symbol": symbol}
            if period == "5d":
                params["serietype"] = "line"
            
            data = await self._make_request(self.endpoints["historical"], params)
            
            # Standardize historical data
            historical_data = []
            if "historical" in data:
                for item in data["historical"][:100]:  # Limit to 100 records
                    historical_data.append({
                        "date": item.get("date"),
                        "open": float(item.get("open", 0)),
                        "high": float(item.get("high", 0)),
                        "low": float(item.get("low", 0)),
                        "close": float(item.get("close", 0)),
                        "volume": int(item.get("volume", 0))
                    })
            
            standardized_data = {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "data": historical_data,
                "provider": "fmp",
                "last_updated": datetime.utcnow().isoformat()
            }
            
            return ProviderResponse(
                success=True,
                data=standardized_data,
                provider="fmp",
                timestamp=datetime.utcnow(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("FMP historical data error", symbol=symbol, error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="fmp",
                timestamp=datetime.utcnow(),
                error=str(e),
                metadata={"cached": False}
            )
    
    async def search_securities(self, query: str, asset_type: str = "stock", 
                              limit: int = 10) -> ProviderResponse:
        """Search for securities."""
        try:
            logger.info("Searching securities on FMP", query=query, asset_type=asset_type)
            
            data = await self._make_request(self.endpoints["search"], {
                "query": query,
                "limit": limit
            })
            
            # Standardize search results
            results = []
            for item in data[:limit]:
                results.append({
                    "symbol": item.get("symbol", ""),
                    "name": item.get("name", ""),
                    "exchange": item.get("stockExchange", ""),
                    "currency": item.get("currency", ""),
                    "asset_type": "stock",  # FMP primarily handles stocks
                    "provider": "fmp"
                })
            
            standardized_data = {
                "query": query,
                "asset_type": asset_type,
                "results": results,
                "count": len(results),
                "provider": "fmp",
                "last_updated": datetime.utcnow().isoformat()
            }
            
            return ProviderResponse(
                success=True,
                data=standardized_data,
                provider="fmp",
                timestamp=datetime.utcnow(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("FMP search error", query=query, error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="fmp",
                timestamp=datetime.utcnow(),
                error=str(e),
                metadata={"cached": False}
            )
    
    async def get_crypto_quote(self, symbol: str) -> ProviderResponse:
        """Get cryptocurrency quote."""
        try:
            logger.info("Fetching crypto quote from FMP", symbol=symbol)
            
            # FMP uses different symbol format for crypto
            crypto_symbol = f"{symbol}-USD" if not symbol.endswith("-USD") else symbol
            
            data = await self._make_request(self.endpoints["crypto"], {"symbol": crypto_symbol})
            standardized_data = self._standardize_quote_data(data)
            
            # Mark as crypto
            standardized_data["asset_type"] = "crypto"
            
            return ProviderResponse(
                success=True,
                data=standardized_data,
                provider="fmp",
                timestamp=datetime.utcnow(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("FMP crypto quote error", symbol=symbol, error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="fmp",
                timestamp=datetime.utcnow(),
                error=str(e),
                metadata={"cached": False}
            )
    
    async def get_market_overview(self) -> ProviderResponse:
        """Get market overview with major indices."""
        try:
            logger.info("Fetching market overview from FMP")
            
            data = await self._make_request(self.endpoints["market_overview"])
            
            # Standardize market overview
            overview = {
                "indices": [],
                "crypto": [],
                "last_updated": datetime.utcnow().isoformat(),
                "provider": "fmp"
            }
            
            for item in data:
                symbol = item.get("symbol", "")
                standardized_item = self._standardize_quote_data([item])
                
                if symbol in ["SPY", "QQQ", "DIA"]:
                    overview["indices"].append(standardized_item)
                elif symbol.endswith("-USD"):
                    overview["crypto"].append(standardized_item)
            
            return ProviderResponse(
                success=True,
                data=overview,
                provider="fmp",
                timestamp=datetime.utcnow(),
                cached=False,
                error=None
            )
            
        except Exception as e:
            logger.error("FMP market overview error", error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="fmp",
                timestamp=datetime.utcnow(),
                error=str(e),
                metadata={"cached": False}
            )
    
    # Provider health methods
    
    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            # Simple health check with SPY quote
            response = await self.get_stock_quote("SPY")
            return response.success
                
        except Exception as e:
            logger.error("FMP health check failed", error=str(e))
            return False
    
    async def close(self):
        """Close provider and cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("FMP provider closed")