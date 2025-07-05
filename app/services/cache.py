"""
Multi-level caching service for market data.

Provides Redis-based caching with intelligent TTL management, cache warming, and analytics.
"""

import json
import asyncio
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from enum import Enum
import redis.asyncio as redis
from app.core.config import Settings
import structlog

logger = structlog.get_logger(__name__)

class CacheLevel(Enum):
    """Cache levels with different TTL strategies."""
    REAL_TIME = "real_time"      # 30 seconds
    QUOTES = "quotes"            # 1 minute
    PROFILES = "profiles"        # 1 hour
    HISTORICAL = "historical"    # 4 hours
    SEARCH = "search"            # 15 minutes
    MARKET_OVERVIEW = "overview" # 5 minutes
    AI_INSIGHTS = "ai_insights"  # 30 minutes

class CacheService:
    """Redis-based multi-level caching service."""
    
    def __init__(self, redis_client: redis.Redis, settings: Settings):
        self.redis = redis_client
        self.settings = settings
        self.cache_ttls = self._get_cache_ttls()
        self.cache_stats = CacheStats(redis_client)
        
    def _get_cache_ttls(self) -> Dict[CacheLevel, int]:
        """Get TTL for each cache level in seconds."""
        return {
            CacheLevel.REAL_TIME: 30,
            CacheLevel.QUOTES: 60,
            CacheLevel.PROFILES: 3600,       # 1 hour
            CacheLevel.HISTORICAL: 14400,    # 4 hours
            CacheLevel.SEARCH: 900,          # 15 minutes
            CacheLevel.MARKET_OVERVIEW: 300, # 5 minutes
            CacheLevel.AI_INSIGHTS: 1800     # 30 minutes
        }
    
    def _make_cache_key(self, level: CacheLevel, provider: str, identifier: str, **kwargs) -> str:
        """Generate cache key with consistent format."""
        # Create a hash of additional parameters for consistency
        params_str = ""
        if kwargs:
            sorted_params = sorted(kwargs.items())
            params_str = "_" + hashlib.md5(
                json.dumps(sorted_params, sort_keys=True).encode()
            ).hexdigest()[:8]
        
        return f"cache:{level.value}:{provider}:{identifier}{params_str}"
    
    async def get(self, level: CacheLevel, provider: str, identifier: str, **kwargs) -> Optional[Any]:
        """
        Get cached data.
        
        Args:
            level: Cache level determining TTL
            provider: Data provider name
            identifier: Unique identifier (symbol, endpoint, etc.)
            **kwargs: Additional parameters for cache key
            
        Returns:
            Cached data or None if not found
        """
        key = self._make_cache_key(level, provider, identifier, **kwargs)
        
        try:
            data = await self.redis.get(key)
            
            if data is None:
                await self.cache_stats.record_miss(level, provider)
                logger.debug("Cache miss", key=key, level=level.value, provider=provider)
                return None
            
            await self.cache_stats.record_hit(level, provider)
            
            # Try to deserialize JSON
            try:
                result = json.loads(data)
                logger.debug("Cache hit", key=key, level=level.value, provider=provider)
                return result
            except json.JSONDecodeError:
                # Return raw data if not JSON
                return data
                
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            await self.cache_stats.record_error(level, provider)
            return None
    
    async def set(self, level: CacheLevel, provider: str, identifier: str, data: Any, 
                  ttl_override: Optional[int] = None, **kwargs) -> bool:
        """
        Set cached data.
        
        Args:
            level: Cache level determining TTL
            provider: Data provider name
            identifier: Unique identifier
            data: Data to cache
            ttl_override: Override default TTL
            **kwargs: Additional parameters for cache key
            
        Returns:
            True if successful
        """
        key = self._make_cache_key(level, provider, identifier, **kwargs)
        ttl = ttl_override or self.cache_ttls[level]
        
        try:
            # Serialize data
            if isinstance(data, (dict, list)):
                serialized_data = json.dumps(data, default=str)
            else:
                serialized_data = str(data)
            
            await self.redis.setex(key, ttl, serialized_data)
            await self.cache_stats.record_set(level, provider)
            
            logger.debug(
                "Cache set", 
                key=key, 
                level=level.value, 
                provider=provider, 
                ttl=ttl,
                data_size=len(serialized_data)
            )
            
            return True
            
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            await self.cache_stats.record_error(level, provider)
            return False
    
    async def delete(self, level: CacheLevel, provider: str, identifier: str, **kwargs) -> bool:
        """Delete cached data."""
        key = self._make_cache_key(level, provider, identifier, **kwargs)
        
        try:
            deleted = await self.redis.delete(key)
            logger.debug("Cache delete", key=key, deleted=bool(deleted))
            return bool(deleted)
            
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False
    
    async def invalidate_pattern(self, level: CacheLevel, provider: str, pattern: str = "*") -> int:
        """
        Invalidate multiple cache entries by pattern.
        
        Args:
            level: Cache level
            provider: Data provider
            pattern: Pattern to match (default: all for provider/level)
            
        Returns:
            Number of keys deleted
        """
        search_pattern = f"cache:{level.value}:{provider}:{pattern}"
        keys_deleted = 0
        
        try:
            keys = []
            async for key in self.redis.scan_iter(match=search_pattern):
                keys.append(key)
            
            if keys:
                keys_deleted = await self.redis.delete(*keys)
                logger.info(
                    "Cache invalidation",
                    pattern=search_pattern,
                    keys_deleted=keys_deleted
                )
            
        except Exception as e:
            logger.error("Cache invalidation error", pattern=search_pattern, error=str(e))
        
        return keys_deleted
    
    async def warm_cache(self, warming_config: Dict[str, Any]) -> Dict[str, int]:
        """
        Warm cache with popular securities and common queries.
        
        Args:
            warming_config: Configuration for cache warming
            
        Returns:
            Statistics of warming operation
        """
        stats = {"success": 0, "errors": 0, "skipped": 0}
        
        popular_symbols = warming_config.get("symbols", [
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX", "BTC-USD", "ETH-USD"
        ])
        
        providers = warming_config.get("providers", ["yahoo", "fmp"])
        levels = warming_config.get("levels", [CacheLevel.QUOTES, CacheLevel.PROFILES])
        
        logger.info(
            "Starting cache warming",
            symbols_count=len(popular_symbols),
            providers=providers,
            levels=[l.value for l in levels]
        )
        
        for provider in providers:
            for level in levels:
                for symbol in popular_symbols:
                    try:
                        # Check if already cached
                        existing = await self.get(level, provider, symbol)
                        if existing is not None:
                            stats["skipped"] += 1
                            continue
                        
                        # Simulate fetching data (would be replaced with actual provider calls)
                        mock_data = {
                            "symbol": symbol,
                            "provider": provider,
                            "cached_at": datetime.utcnow().isoformat(),
                            "cache_level": level.value
                        }
                        
                        success = await self.set(level, provider, symbol, mock_data)
                        if success:
                            stats["success"] += 1
                        else:
                            stats["errors"] += 1
                            
                        # Small delay to avoid overwhelming Redis
                        await asyncio.sleep(0.01)
                        
                    except Exception as e:
                        logger.error(
                            "Cache warming error",
                            symbol=symbol,
                            provider=provider,
                            level=level.value,
                            error=str(e)
                        )
                        stats["errors"] += 1
        
        logger.info("Cache warming completed", stats=stats)
        return stats
    
    async def get_cache_size(self, level: Optional[CacheLevel] = None, 
                           provider: Optional[str] = None) -> Dict[str, int]:
        """Get cache size statistics."""
        if level and provider:
            pattern = f"cache:{level.value}:{provider}:*"
        elif level:
            pattern = f"cache:{level.value}:*"
        elif provider:
            pattern = f"cache:*:{provider}:*"
        else:
            pattern = "cache:*"
        
        key_count = 0
        total_memory = 0
        
        try:
            async for key in self.redis.scan_iter(match=pattern):
                key_count += 1
                try:
                    memory = await self.redis.memory_usage(key)
                    if memory:
                        total_memory += memory
                except:
                    pass  # Key might have expired
        
        except Exception as e:
            logger.error("Cache size calculation error", error=str(e))
        
        return {
            "key_count": key_count,
            "total_memory_bytes": total_memory,
            "total_memory_mb": round(total_memory / (1024 * 1024), 2)
        }


class CacheStats:
    """Cache statistics tracking."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def record_hit(self, level: CacheLevel, provider: str):
        """Record cache hit."""
        await self._increment_stat("hits", level, provider)
    
    async def record_miss(self, level: CacheLevel, provider: str):
        """Record cache miss."""
        await self._increment_stat("misses", level, provider)
    
    async def record_set(self, level: CacheLevel, provider: str):
        """Record cache set operation."""
        await self._increment_stat("sets", level, provider)
    
    async def record_error(self, level: CacheLevel, provider: str):
        """Record cache error."""
        await self._increment_stat("errors", level, provider)
    
    async def _increment_stat(self, stat_type: str, level: CacheLevel, provider: str):
        """Increment a statistic counter."""
        key = f"cache_stats:{stat_type}:{level.value}:{provider}"
        try:
            await self.redis.incr(key)
            await self.redis.expire(key, 86400)  # Expire after 24 hours
        except Exception as e:
            logger.error("Cache stats error", key=key, error=str(e))
    
    async def get_stats(self, level: Optional[CacheLevel] = None, 
                       provider: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        """Get cache statistics."""
        stats = {"hits": {}, "misses": {}, "sets": {}, "errors": {}}
        
        for stat_type in stats.keys():
            if level and provider:
                pattern = f"cache_stats:{stat_type}:{level.value}:{provider}"
            elif level:
                pattern = f"cache_stats:{stat_type}:{level.value}:*"
            elif provider:
                pattern = f"cache_stats:{stat_type}:*:{provider}"
            else:
                pattern = f"cache_stats:{stat_type}:*"
            
            try:
                async for key in self.redis.scan_iter(match=pattern):
                    value = await self.redis.get(key)
                    if value:
                        key_parts = key.split(":")
                        if len(key_parts) >= 4:
                            level_name = key_parts[2]
                            provider_name = key_parts[3]
                            stats[stat_type][f"{level_name}:{provider_name}"] = int(value)
            except Exception as e:
                logger.error("Cache stats retrieval error", stat_type=stat_type, error=str(e))
        
        return stats
    
    async def get_hit_rate(self, level: Optional[CacheLevel] = None, 
                          provider: Optional[str] = None) -> float:
        """Calculate cache hit rate."""
        stats = await self.get_stats(level, provider)
        
        total_hits = sum(stats["hits"].values())
        total_misses = sum(stats["misses"].values())
        total_requests = total_hits + total_misses
        
        if total_requests == 0:
            return 0.0
        
        return (total_hits / total_requests) * 100


class CacheWarmer:
    """Background cache warming service."""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self._running = False
        
    async def start_warming_schedule(self, interval_minutes: int = 30):
        """Start scheduled cache warming."""
        self._running = True
        
        while self._running:
            try:
                warming_config = {
                    "symbols": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "BTC-USD", "ETH-USD"],
                    "providers": ["yahoo", "fmp"],
                    "levels": [CacheLevel.QUOTES, CacheLevel.PROFILES]
                }
                
                await self.cache_service.warm_cache(warming_config)
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                logger.error("Cache warming schedule error", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    def stop_warming_schedule(self):
        """Stop scheduled cache warming."""
        self._running = False


# FastAPI dependencies
async def get_cache_service() -> CacheService:
    """Get cache service instance."""
    from app.core.deps import get_redis, get_settings
    
    redis_client = await get_redis()
    settings = get_settings()
    
    return CacheService(redis_client, settings)


# Cache decorator for functions
def cached(level: CacheLevel, provider: str, ttl_override: Optional[int] = None):
    """
    Decorator for caching function results.
    
    Args:
        level: Cache level
        provider: Provider name
        ttl_override: Optional TTL override
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            cache_service = await get_cache_service()
            
            # Create cache key from function name and parameters
            identifier = f"{func.__name__}_{hashlib.md5(str(args + tuple(sorted(kwargs.items()))).encode()).hexdigest()[:8]}"
            
            # Try to get from cache
            cached_result = await cache_service.get(level, provider, identifier)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(level, provider, identifier, result, ttl_override)
            
            return result
        
        return wrapper
    return decorator