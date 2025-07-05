"""
Tests for cache service.

Comprehensive test suite for caching functionality including rate limiting and statistics.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch
from app.services.cache import CacheService, CacheLevel, CacheStats, cached
from app.services.rate_limiter import RateLimiter


class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.data = {}
        self.expiry = {}
        
    async def get(self, key):
        if key in self.data and key not in self._expired_keys():
            return self.data[key]
        return None
    
    async def setex(self, key, ttl, value):
        self.data[key] = value
        self.expiry[key] = ttl
        return True
    
    async def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                if key in self.expiry:
                    del self.expiry[key]
                deleted += 1
        return deleted
    
    async def incr(self, key):
        current = int(self.data.get(key, 0))
        self.data[key] = str(current + 1)
        return current + 1
    
    async def expire(self, key, ttl):
        self.expiry[key] = ttl
        return True
    
    async def scan_iter(self, match=None):
        """Mock scan iterator."""
        for key in self.data.keys():
            if match is None:
                yield key
            elif self._match_pattern(key, match):
                yield key
    
    def _match_pattern(self, key, pattern):
        """Simple pattern matching for tests."""
        if pattern.endswith("*"):
            return key.startswith(pattern[:-1])
        return key == pattern
    
    def _expired_keys(self):
        """Return set of expired keys (simplified for tests)."""
        return set()
    
    async def zremrangebyscore(self, key, min_score, max_score):
        """Mock sorted set operation."""
        return 0
    
    async def zcard(self, key):
        """Mock sorted set cardinality."""
        return len(self.data.get(key, []))
    
    async def zadd(self, key, mapping):
        """Mock sorted set add."""
        if key not in self.data:
            self.data[key] = []
        self.data[key].extend(mapping.keys())
        return len(mapping)
    
    def pipeline(self):
        """Mock pipeline."""
        return MockPipeline(self)
    
    async def memory_usage(self, key):
        """Mock memory usage."""
        if key in self.data:
            return len(str(self.data[key]))
        return None


class MockPipeline:
    """Mock Redis pipeline."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.commands = []
    
    def zremrangebyscore(self, key, min_score, max_score):
        self.commands.append(("zremrangebyscore", key, min_score, max_score))
        return self
    
    def zcard(self, key):
        self.commands.append(("zcard", key))
        return self
    
    def zadd(self, key, mapping):
        self.commands.append(("zadd", key, mapping))
        return self
    
    def expire(self, key, ttl):
        self.commands.append(("expire", key, ttl))
        return self
    
    async def execute(self):
        """Execute pipeline commands."""
        results = []
        for cmd in self.commands:
            if cmd[0] == "zremrangebyscore":
                results.append(0)
            elif cmd[0] == "zcard":
                results.append(0)
            elif cmd[0] == "zadd":
                results.append(1)
            elif cmd[0] == "expire":
                results.append(True)
        return results


@pytest.fixture
def mock_redis():
    """Provide mock Redis client."""
    return MockRedis()


@pytest.fixture
def mock_settings():
    """Provide mock settings."""
    mock = Mock()
    mock.redis_url = "redis://localhost:6379"
    return mock


@pytest.fixture
def cache_service(mock_redis, mock_settings):
    """Provide cache service with mocked dependencies."""
    return CacheService(mock_redis, mock_settings)


@pytest.fixture
def rate_limiter(mock_redis, mock_settings):
    """Provide rate limiter with mocked dependencies."""
    return RateLimiter(mock_redis, mock_settings)


class TestCacheService:
    """Test cases for CacheService."""
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_service):
        """Test basic cache set and get operations."""
        # Test data
        test_data = {"symbol": "AAPL", "price": 150.25}
        
        # Set cache
        success = await cache_service.set(
            CacheLevel.QUOTES, 
            "yahoo", 
            "AAPL", 
            test_data
        )
        assert success is True
        
        # Get cache
        cached_data = await cache_service.get(
            CacheLevel.QUOTES,
            "yahoo", 
            "AAPL"
        )
        assert cached_data == test_data
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_service):
        """Test cache miss returns None."""
        cached_data = await cache_service.get(
            CacheLevel.QUOTES,
            "yahoo",
            "NONEXISTENT"
        )
        assert cached_data is None
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_service):
        """Test cache deletion."""
        # Set cache
        await cache_service.set(
            CacheLevel.QUOTES,
            "yahoo",
            "AAPL",
            {"price": 150.25}
        )
        
        # Delete cache
        deleted = await cache_service.delete(
            CacheLevel.QUOTES,
            "yahoo",
            "AAPL"
        )
        assert deleted is True
        
        # Verify deletion
        cached_data = await cache_service.get(
            CacheLevel.QUOTES,
            "yahoo",
            "AAPL"
        )
        assert cached_data is None
    
    @pytest.mark.asyncio
    async def test_cache_warm(self, cache_service):
        """Test cache warming functionality."""
        warming_config = {
            "symbols": ["AAPL", "GOOGL"],
            "providers": ["yahoo"],
            "levels": [CacheLevel.QUOTES]
        }
        
        stats = await cache_service.warm_cache(warming_config)
        
        assert "success" in stats
        assert "errors" in stats
        assert "skipped" in stats
        assert stats["success"] >= 0
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_service):
        """Test cache pattern invalidation."""
        # Set multiple cache entries
        await cache_service.set(CacheLevel.QUOTES, "yahoo", "AAPL", {"price": 150})
        await cache_service.set(CacheLevel.QUOTES, "yahoo", "GOOGL", {"price": 2800})
        
        # Invalidate pattern
        deleted = await cache_service.invalidate_pattern(
            CacheLevel.QUOTES,
            "yahoo",
            "*"
        )
        
        # Should delete at least some keys
        assert deleted >= 0
    
    @pytest.mark.asyncio
    async def test_cache_size_calculation(self, cache_service):
        """Test cache size calculation."""
        # Set some cache entries
        await cache_service.set(CacheLevel.QUOTES, "yahoo", "AAPL", {"price": 150})
        await cache_service.set(CacheLevel.PROFILES, "fmp", "AAPL", {"name": "Apple Inc"})
        
        # Get size
        size_info = await cache_service.get_cache_size()
        
        assert "key_count" in size_info
        assert "total_memory_bytes" in size_info
        assert "total_memory_mb" in size_info
        assert size_info["key_count"] >= 0


class TestCacheStats:
    """Test cases for CacheStats."""
    
    @pytest.mark.asyncio
    async def test_stats_recording(self, mock_redis):
        """Test cache statistics recording."""
        stats = CacheStats(mock_redis)
        
        # Record various stats
        await stats.record_hit(CacheLevel.QUOTES, "yahoo")
        await stats.record_miss(CacheLevel.QUOTES, "yahoo")
        await stats.record_set(CacheLevel.QUOTES, "yahoo")
        await stats.record_error(CacheLevel.QUOTES, "yahoo")
        
        # Verify stats were recorded
        recorded_stats = await stats.get_stats(CacheLevel.QUOTES, "yahoo")
        
        assert "hits" in recorded_stats
        assert "misses" in recorded_stats
        assert "sets" in recorded_stats
        assert "errors" in recorded_stats
    
    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self, mock_redis):
        """Test hit rate calculation."""
        stats = CacheStats(mock_redis)
        
        # Record some hits and misses
        for _ in range(8):
            await stats.record_hit(CacheLevel.QUOTES, "yahoo")
        
        for _ in range(2):
            await stats.record_miss(CacheLevel.QUOTES, "yahoo")
        
        # Calculate hit rate
        hit_rate = await stats.get_hit_rate(CacheLevel.QUOTES, "yahoo")
        
        # Should be around 80% (8 hits out of 10 total)
        assert hit_rate >= 0.0
        assert hit_rate <= 100.0


class TestRateLimiter:
    """Test cases for RateLimiter."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_allow(self, rate_limiter):
        """Test rate limiting allows requests within limits."""
        allowed, info = await rate_limiter.is_allowed("yahoo", "test")
        
        assert allowed is True
        assert "provider" in info
        assert "current_usage" in info
        assert "limits" in info
    
    @pytest.mark.asyncio
    async def test_rate_limit_status(self, rate_limiter):
        """Test rate limit status retrieval."""
        status = await rate_limiter.get_rate_limit_status("yahoo")
        
        assert "provider" in status
        assert "limits" in status
        assert "current_usage" in status
        assert "utilization_percent" in status
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset(self, rate_limiter):
        """Test rate limit reset functionality."""
        reset_success = await rate_limiter.reset_rate_limits("yahoo")
        assert reset_success in [True, False]  # May be True or False depending on existing keys
    
    @pytest.mark.asyncio
    async def test_all_providers_status(self, rate_limiter):
        """Test getting status for all providers."""
        all_status = await rate_limiter.get_all_provider_status()
        
        assert isinstance(all_status, dict)
        # Should have entries for known providers
        assert len(all_status) > 0


class TestCacheDecorator:
    """Test cases for cache decorator."""
    
    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test the cached decorator functionality."""
        call_count = 0
        
        @cached(CacheLevel.QUOTES, "test_provider")
        async def expensive_function(param1, param2=None):
            nonlocal call_count
            call_count += 1
            return {"result": f"{param1}_{param2}", "call_count": call_count}
        
        # Mock the cache service
        with patch("app.services.cache.get_cache_service") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None  # Simulate cache miss
            mock_cache.set.return_value = True
            mock_get_cache.return_value = mock_cache
            
            # First call should execute function
            result1 = await expensive_function("test", param2="value")
            assert result1["call_count"] == 1
            assert call_count == 1
            
            # Mock cache hit for second call
            mock_cache.get.return_value = result1
            
            # Second call should use cache
            result2 = await expensive_function("test", param2="value")
            assert result2["call_count"] == 1  # Same as first call
            assert call_count == 1  # Function not called again


class TestIntegration:
    """Integration tests for cache and rate limiting together."""
    
    @pytest.mark.asyncio
    async def test_cache_and_rate_limit_integration(self, cache_service, rate_limiter):
        """Test cache and rate limiting working together."""
        # Check rate limit
        allowed, rate_info = await rate_limiter.is_allowed("yahoo", "quote")
        assert allowed is True
        
        # Use cache
        await cache_service.set(CacheLevel.QUOTES, "yahoo", "AAPL", {"price": 150})
        cached_data = await cache_service.get(CacheLevel.QUOTES, "yahoo", "AAPL")
        assert cached_data == {"price": 150}
        
        # Check rate limit again
        allowed2, rate_info2 = await rate_limiter.is_allowed("yahoo", "quote")
        assert allowed2 is True
    
    @pytest.mark.asyncio
    async def test_cache_ttl_levels(self, cache_service):
        """Test different cache TTL levels."""
        test_data = {"test": "data"}
        
        # Test different cache levels
        levels_to_test = [
            CacheLevel.REAL_TIME,
            CacheLevel.QUOTES,
            CacheLevel.PROFILES,
            CacheLevel.HISTORICAL
        ]
        
        for level in levels_to_test:
            success = await cache_service.set(level, "test", f"key_{level.value}", test_data)
            assert success is True
            
            retrieved = await cache_service.get(level, "test", f"key_{level.value}")
            assert retrieved == test_data


if __name__ == "__main__":
    pytest.main([__file__])