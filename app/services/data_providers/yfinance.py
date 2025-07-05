"""
Yahoo Finance data provider implementation.

Provides free market data as a fallback provider with async support and
data standardization compatible with the FMP provider format.
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from app.services.data_providers.base import DataProvider, ProviderResponse, ProviderHealth
from app.services.cache import CacheService, CacheLevel
from app.services.rate_limiter import RateLimiter
from app.core.config import Settings
import structlog

logger = structlog.get_logger(__name__)

class YahooFinanceProvider(DataProvider):
    """Yahoo Finance free data provider with async support."""
    
    def __init__(self, settings: Settings, cache_service: CacheService, rate_limiter: RateLimiter):
        super().__init__("yahoo", settings)
        self.cache_service = cache_service
        self.rate_limiter = rate_limiter
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="yfinance")
        self._last_error = None
        self._retry_count = 0
        self._max_retries = 3
        self._backoff_base = 2
        
        # Yahoo Finance specific configuration
        self.crypto_mapping = {
            "BTC": "BTC-USD",
            "ETH": "ETH-USD", 
            "ADA": "ADA-USD",
            "DOT": "DOT-USD",
            "LTC": "LTC-USD",
            "XRP": "XRP-USD",
            "DOGE": "DOGE-USD",
            "SOL": "SOL-USD",
            "MATIC": "MATIC-USD",
            "AVAX": "AVAX-USD"
        }
        
        # Rate limiting configuration for Yahoo Finance (conservative limits)
        self.rate_limits = {
            "requests_per_minute": 100,
            "requests_per_hour": 2000,
            "requests_per_day": 10000,
            "burst_limit": 5
        }
    
    async def _run_in_executor(self, func, *args, **kwargs):
        """Run blocking yfinance operations in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)
    
    async def _make_yfinance_request(self, symbol: str, operation: str, **kwargs) -> Any:
        """
        Make request to Yahoo Finance with rate limiting and caching.
        
        Args:
            symbol: Stock/crypto symbol
            operation: Type of operation (info, history, etc.)
            **kwargs: Additional parameters for the operation
            
        Returns:
            Yahoo Finance data
            
        Raises:
            Exception: On API errors or rate limit exceeded
        """
        # Check rate limits
        allowed, rate_info = await self.rate_limiter.is_allowed("yahoo", operation)
        if not allowed:
            logger.warning(
                "Yahoo Finance rate limit exceeded",
                symbol=symbol,
                operation=operation,
                rate_info=rate_info
            )
            raise Exception(f"Rate limit exceeded for Yahoo Finance: {rate_info.get('exceeded_window', 'unknown')}")
        
        # Check cache first
        cache_key = f"{symbol}_{operation}_{hash(str(kwargs))}"
        cache_level = self._get_cache_level(operation)
        
        cached_data = await self.cache_service.get(cache_level, "yahoo", cache_key)
        if cached_data is not None:
            logger.debug("Cache hit for Yahoo Finance request", symbol=symbol, operation=operation)
            return cached_data
        
        # Make request with retry logic
        for attempt in range(self._max_retries + 1):
            try:
                # Create ticker object and call appropriate method
                def sync_request():
                    ticker = yf.Ticker(symbol)
                    
                    if operation == "info":
                        return ticker.info
                    elif operation == "history":
                        period = kwargs.get("period", "1y")
                        interval = kwargs.get("interval", "1d")
                        return ticker.history(period=period, interval=interval)
                    elif operation == "financials":
                        return ticker.financials
                    else:
                        raise ValueError(f"Unsupported operation: {operation}")
                
                data = await self._run_in_executor(sync_request)
                
                if self._is_valid_response(data, operation):
                    # Cache successful response
                    await self.cache_service.set(cache_level, "yahoo", cache_key, data)
                    
                    logger.debug(
                        "Yahoo Finance request successful",
                        symbol=symbol,
                        operation=operation,
                        cached=True
                    )
                    
                    self._retry_count = 0
                    return data
                else:
                    logger.warning(
                        "Invalid Yahoo Finance response",
                        symbol=symbol,
                        operation=operation,
                        data_preview=str(data)[:200] if data else "None"
                    )
                    
            except Exception as e:
                logger.error(
                    "Yahoo Finance request error",
                    symbol=symbol,
                    operation=operation,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
                # Don't retry on certain errors
                if "delisted" in str(e).lower() or "not found" in str(e).lower():
                    break
            
            # Apply exponential backoff if not last attempt
            if attempt < self._max_retries:
                backoff_time = self._backoff_base ** attempt
                logger.info(
                    "Yahoo Finance retrying request",
                    symbol=symbol,
                    operation=operation,
                    attempt=attempt + 1,
                    backoff_seconds=backoff_time
                )
                await asyncio.sleep(backoff_time)
        
        # All retries failed
        self._retry_count += 1
        error_msg = f"Yahoo Finance request failed after {self._max_retries + 1} attempts"
        self._last_error = error_msg
        
        logger.error(
            "Yahoo Finance request completely failed",
            symbol=symbol,
            operation=operation,
            max_retries=self._max_retries
        )
        
        raise Exception(error_msg)
    
    def _get_cache_level(self, operation: str) -> CacheLevel:
        """Get appropriate cache level for operation."""
        if operation in ["info", "quote"]:
            return CacheLevel.QUOTES
        elif operation == "profile":
            return CacheLevel.PROFILES
        elif operation == "history":
            return CacheLevel.HISTORICAL
        elif operation == "search":
            return CacheLevel.SEARCH
        else:
            return CacheLevel.REAL_TIME
    
    def _is_valid_response(self, data: Any, operation: str) -> bool:
        """Validate Yahoo Finance response."""
        if data is None:
            return False
        
        if operation == "info":
            return isinstance(data, dict) and len(data) > 0
        elif operation == "history":
            return hasattr(data, 'index') and len(data) > 0  # pandas DataFrame
        elif operation == "search":
            return isinstance(data, list)
        
        return True
    
    def _normalize_symbol(self, symbol: str, asset_type: str = "stock") -> str:
        """Normalize symbol for Yahoo Finance."""
        if asset_type == "crypto":
            return self.crypto_mapping.get(symbol, f"{symbol}-USD")
        return symbol.upper()
    
    def _standardize_quote_data(self, ticker_info: Dict, symbol: str) -> Dict[str, Any]:
        """Standardize quote data to match FMP format."""
        try:
            current_price = ticker_info.get("currentPrice") or ticker_info.get("regularMarketPrice", 0)
            previous_close = ticker_info.get("previousClose", current_price)
            change = current_price - previous_close if current_price and previous_close else 0
            change_percent = (change / previous_close * 100) if previous_close and previous_close != 0 else 0
            
            return {
                "symbol": symbol,
                "name": ticker_info.get("longName", ticker_info.get("shortName", "")),
                "price": float(current_price) if current_price else 0.0,
                "change": float(change),
                "change_percent": float(change_percent),
                "previous_close": float(previous_close) if previous_close else 0.0,
                "open": float(ticker_info.get("regularMarketOpen", ticker_info.get("open", 0))),
                "high": float(ticker_info.get("regularMarketDayHigh", ticker_info.get("dayHigh", 0))),
                "low": float(ticker_info.get("regularMarketDayLow", ticker_info.get("dayLow", 0))),
                "volume": int(ticker_info.get("regularMarketVolume", ticker_info.get("volume", 0))),
                "market_cap": ticker_info.get("marketCap"),
                "pe_ratio": ticker_info.get("trailingPE"),
                "timestamp": int(datetime.now().timestamp()),
                "provider": "yahoo",
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error("Error standardizing Yahoo Finance quote data", symbol=symbol, error=str(e))
            return {}
    
    def _standardize_profile_data(self, ticker_info: Dict, symbol: str) -> Dict[str, Any]:
        """Standardize profile data to match FMP format."""
        try:
            return {
                "symbol": symbol,
                "company_name": ticker_info.get("longName", ticker_info.get("shortName", "")),
                "description": ticker_info.get("longBusinessSummary", ""),
                "industry": ticker_info.get("industry", ""),
                "sector": ticker_info.get("sector", ""),
                "country": ticker_info.get("country", ""),
                "website": ticker_info.get("website", ""),
                "market_cap": ticker_info.get("marketCap"),
                "employees": ticker_info.get("fullTimeEmployees"),
                "exchange": ticker_info.get("exchange", ""),
                "currency": ticker_info.get("currency", "USD"),
                "ceo": ticker_info.get("companyOfficers", [{}])[0].get("name", "") if ticker_info.get("companyOfficers") else "",
                "founded": None,  # Yahoo Finance doesn't provide founding year
                "address": {
                    "street": ticker_info.get("address1", ""),
                    "city": ticker_info.get("city", ""),
                    "state": ticker_info.get("state", ""),
                    "zip_code": ticker_info.get("zip", ""),
                    "country": ticker_info.get("country", "")
                },
                "provider": "yahoo",
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error("Error standardizing Yahoo Finance profile data", symbol=symbol, error=str(e))
            return {}
    
    # Implement required DataProvider methods
    
    async def get_stock_quote(self, symbol: str) -> ProviderResponse:
        """Get real-time stock quote."""
        try:
            logger.info("Fetching stock quote from Yahoo Finance", symbol=symbol)
            
            normalized_symbol = self._normalize_symbol(symbol)
            ticker_info = await self._make_yfinance_request(normalized_symbol, "info")
            standardized_data = self._standardize_quote_data(ticker_info, symbol)
            
            return ProviderResponse(
                success=True,
                data=standardized_data,
                provider="yahoo",
                timestamp=datetime.now(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("Yahoo Finance stock quote error", symbol=symbol, error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="yahoo",
                timestamp=datetime.now(),
                error=str(e),
                metadata={"cached": False}
            )
    
    async def get_stock_profile(self, symbol: str) -> ProviderResponse:
        """Get company profile."""
        try:
            logger.info("Fetching stock profile from Yahoo Finance", symbol=symbol)
            
            normalized_symbol = self._normalize_symbol(symbol)
            ticker_info = await self._make_yfinance_request(normalized_symbol, "info")
            standardized_data = self._standardize_profile_data(ticker_info, symbol)
            
            return ProviderResponse(
                success=True,
                data=standardized_data,
                provider="yahoo",
                timestamp=datetime.now(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("Yahoo Finance stock profile error", symbol=symbol, error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="yahoo",
                timestamp=datetime.now(),
                error=str(e),
                metadata={"cached": False}
            )
    
    async def get_historical_data(self, symbol: str, period: str = "1y", 
                                interval: str = "1d") -> ProviderResponse:
        """Get historical price data."""
        try:
            logger.info("Fetching historical data from Yahoo Finance", symbol=symbol, period=period)
            
            normalized_symbol = self._normalize_symbol(symbol)
            history_df = await self._make_yfinance_request(
                normalized_symbol, 
                "history", 
                period=period, 
                interval=interval
            )
            
            # Convert pandas DataFrame to standardized format
            historical_data = []
            for date, row in history_df.iterrows():
                historical_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume']) if not pd.isna(row['Volume']) else 0
                })
            
            # Limit to 100 records for consistency
            historical_data = historical_data[-100:]
            
            standardized_data = {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "data": historical_data,
                "provider": "yahoo",
                "last_updated": datetime.now().isoformat()
            }
            
            return ProviderResponse(
                success=True,
                data=standardized_data,
                provider="yahoo",
                timestamp=datetime.now(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("Yahoo Finance historical data error", symbol=symbol, error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="yahoo",
                timestamp=datetime.now(),
                error=str(e),
                metadata={"cached": False}
            )
    
    async def search_securities(self, query: str, asset_type: str = "stock", 
                              limit: int = 10) -> ProviderResponse:
        """Search for securities - basic implementation using common symbols."""
        try:
            logger.info("Searching securities on Yahoo Finance", query=query, asset_type=asset_type)
            
            # Yahoo Finance doesn't have a direct search API
            # This is a basic implementation using common symbol patterns
            results = []
            
            # For demonstration, return some common matches
            common_symbols = {
                "apple": [{"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"}],
                "microsoft": [{"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"}],
                "google": [{"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"}],
                "amazon": [{"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"}],
                "tesla": [{"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ"}],
            }
            
            query_lower = query.lower()
            for key, symbols in common_symbols.items():
                if query_lower in key or any(query.upper() in s["symbol"] for s in symbols):
                    for symbol_info in symbols:
                        results.append({
                            "symbol": symbol_info["symbol"],
                            "name": symbol_info["name"],
                            "exchange": symbol_info["exchange"],
                            "currency": "USD",
                            "asset_type": asset_type,
                            "provider": "yahoo"
                        })
                        if len(results) >= limit:
                            break
                if len(results) >= limit:
                    break
            
            standardized_data = {
                "query": query,
                "asset_type": asset_type,
                "results": results,
                "count": len(results),
                "provider": "yahoo",
                "last_updated": datetime.now().isoformat()
            }
            
            return ProviderResponse(
                success=True,
                data=standardized_data,
                provider="yahoo",
                timestamp=datetime.now(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("Yahoo Finance search error", query=query, error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="yahoo",
                timestamp=datetime.now(),
                error=str(e),
                metadata={"cached": False}
            )
    
    async def get_crypto_quote(self, symbol: str) -> ProviderResponse:
        """Get cryptocurrency quote."""
        try:
            logger.info("Fetching crypto quote from Yahoo Finance", symbol=symbol)
            
            normalized_symbol = self._normalize_symbol(symbol, "crypto")
            ticker_info = await self._make_yfinance_request(normalized_symbol, "info")
            standardized_data = self._standardize_quote_data(ticker_info, symbol)
            
            # Mark as crypto
            standardized_data["asset_type"] = "crypto"
            
            return ProviderResponse(
                success=True,
                data=standardized_data,
                provider="yahoo",
                timestamp=datetime.now(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("Yahoo Finance crypto quote error", symbol=symbol, error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="yahoo",
                timestamp=datetime.now(),
                error=str(e),
                metadata={"cached": False}
            )
    
    async def get_market_overview(self) -> ProviderResponse:
        """Get market overview with major indices."""
        try:
            logger.info("Fetching market overview from Yahoo Finance")
            
            # Major market indices and crypto
            symbols = {
                "indices": ["^GSPC", "^IXIC", "^DJI"],  # S&P 500, NASDAQ, Dow Jones
                "crypto": ["BTC-USD", "ETH-USD"]
            }
            
            overview = {
                "indices": [],
                "crypto": [],
                "last_updated": datetime.now().isoformat(),
                "provider": "yahoo"
            }
            
            # Fetch data for each symbol
            for category, symbol_list in symbols.items():
                for symbol in symbol_list:
                    try:
                        ticker_info = await self._make_yfinance_request(symbol, "info")
                        standardized_item = self._standardize_quote_data(ticker_info, symbol)
                        overview[category].append(standardized_item)
                    except Exception as e:
                        logger.warning(f"Failed to fetch {symbol} for market overview", error=str(e))
                        continue
            
            return ProviderResponse(
                success=True,
                data=overview,
                provider="yahoo",
                timestamp=datetime.now(),
                metadata={"cached": False}
            )
            
        except Exception as e:
            logger.error("Yahoo Finance market overview error", error=str(e))
            return ProviderResponse(
                success=False,
                data={},
                provider="yahoo",
                timestamp=datetime.now(),
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
            logger.error("Yahoo Finance health check failed", error=str(e))
            return False
    
    async def close(self):
        """Close provider and cleanup resources."""
        if self.executor:
            self.executor.shutdown(wait=True)
        logger.info("Yahoo Finance provider closed")