"""
Tests for FMP data provider.

Comprehensive test suite for Financial Modeling Prep provider including
rate limiting, caching, error handling, and data standardization.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime
import aiohttp
from app.services.data_providers.fmp import FMPProvider
from app.services.data_providers.base import ProviderResponse, ProviderHealth
from app.services.cache import CacheService, CacheLevel
from app.services.rate_limiter import RateLimiter


class MockResponse:
    """Mock aiohttp response."""
    
    def __init__(self, data=None, status=200, headers=None):
        self.status = status
        self.headers = headers or {}
        self._data = data or {}
    
    async def text(self):
        return json.dumps(self._data)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockSession:
    """Mock aiohttp session."""
    
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.closed = False
        self.requests = []
    
    def get(self, url, params=None):
        """Mock GET request."""
        self.requests.append({"url": url, "params": params})
        
        # Return appropriate mock response
        if "quote" in url:
            return MockResponse([{
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "price": 150.25,
                "change": 2.5,
                "changesPercentage": 1.69,
                "previousClose": 147.75,
                "open": 148.0,
                "dayHigh": 151.0,
                "dayLow": 147.5,
                "volume": 50000000,
                "marketCap": 2500000000000,
                "pe": 25.5,
                "timestamp": int(datetime.utcnow().timestamp())
            }])
        elif "profile" in url:
            return MockResponse([{
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "description": "Apple Inc. designs and manufactures consumer electronics.",
                "industry": "Consumer Electronics",
                "sector": "Technology",
                "country": "US",
                "website": "https://www.apple.com",
                "mktCap": 2500000000000,
                "fullTimeEmployees": 147000,
                "exchangeShortName": "NASDAQ",
                "currency": "USD",
                "ceo": "Tim Cook",
                "foundingYear": 1976,
                "address": "One Apple Park Way",
                "city": "Cupertino",
                "state": "CA",
                "zip": "95014"
            }])
        elif "historical" in url:
            return MockResponse({
                "historical": [
                    {
                        "date": "2023-12-01",
                        "open": 150.0,
                        "high": 152.0,
                        "low": 149.0,
                        "close": 151.0,
                        "volume": 45000000
                    },
                    {
                        "date": "2023-11-30",
                        "open": 148.0,
                        "high": 150.5,
                        "low": 147.5,
                        "close": 150.0,
                        "volume": 42000000
                    }
                ]
            })
        elif "search" in url:
            return MockResponse([
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "stockExchange": "NASDAQ",
                    "currency": "USD"
                },
                {
                    "symbol": "AAPLF",
                    "name": "Apple Inc. (Foreign)",
                    "stockExchange": "OTC",
                    "currency": "USD"
                }
            ])
        else:
            return MockResponse([])
    
    async def close(self):
        self.closed = True


@pytest.fixture
def mock_settings():
    """Mock settings with FMP configuration."""
    settings = Mock()
    settings.fmp_api_key = "test_api_key"
    return settings


@pytest.fixture
def mock_cache_service():
    """Mock cache service."""
    cache = AsyncMock()
    cache.get.return_value = None  # Default to cache miss
    cache.set.return_value = True
    return cache


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter."""
    limiter = AsyncMock()
    limiter.is_allowed.return_value = (True, {"allowed": True})
    return limiter


@pytest.fixture
def fmp_provider(mock_settings, mock_cache_service, mock_rate_limiter):
    """FMP provider instance with mocked dependencies."""
    return FMPProvider(mock_settings, mock_cache_service, mock_rate_limiter)


class TestFMPProvider:
    """Test cases for FMPProvider."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, fmp_provider):
        """Test FMP provider initialization."""
        assert fmp_provider.name == "fmp"
        assert fmp_provider.api_key == "test_api_key"
        assert fmp_provider.base_url == "https://financialmodelingprep.com/api/v3"
        assert hasattr(fmp_provider, '_health_status')
    
    @pytest.mark.asyncio
    async def test_get_session(self, fmp_provider):
        """Test session creation and reuse."""
        session1 = await fmp_provider._get_session()
        session2 = await fmp_provider._get_session()
        
        assert session1 is session2
        assert not session1.closed
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, fmp_provider):
        """Test cache key generation."""
        params = {"symbol": "AAPL", "apikey": "secret"}
        key = fmp_provider._generate_cache_key("/quote", params)
        
        assert "apikey" not in key  # API key should be excluded
        assert "symbol" in key
        assert "AAPL" in key
    
    @pytest.mark.asyncio
    async def test_cache_level_selection(self, fmp_provider):
        """Test cache level selection for different endpoints."""
        assert fmp_provider._get_cache_level("/quote") == CacheLevel.QUOTES
        assert fmp_provider._get_cache_level("/profile") == CacheLevel.PROFILES
        assert fmp_provider._get_cache_level("/historical") == CacheLevel.HISTORICAL
        assert fmp_provider._get_cache_level("/search") == CacheLevel.SEARCH
    
    @pytest.mark.asyncio
    async def test_response_validation(self, fmp_provider):
        """Test API response validation."""
        # Valid responses
        assert fmp_provider._is_valid_response([{"symbol": "AAPL"}], "/quote")
        assert fmp_provider._is_valid_response([{"companyName": "Apple"}], "/profile")
        assert fmp_provider._is_valid_response({"historical": []}, "/historical")
        assert fmp_provider._is_valid_response([], "/search")
        
        # Invalid responses
        assert not fmp_provider._is_valid_response(None, "/quote")
        assert not fmp_provider._is_valid_response([], "/quote")
        assert not fmp_provider._is_valid_response({"Error Message": "Invalid"}, "/quote")
    
    @pytest.mark.asyncio
    async def test_stock_quote_success(self, fmp_provider):
        """Test successful stock quote retrieval."""
        # Mock session
        mock_session = MockSession()
        fmp_provider.session = mock_session
        
        response = await fmp_provider.get_stock_quote("AAPL")
        
        assert response.success is True
        assert response.data["symbol"] == "AAPL"
        assert response.data["price"] == 150.25
        assert response.data["provider"] == "fmp"
        assert "last_updated" in response.data
    
    @pytest.mark.asyncio
    async def test_stock_profile_success(self, fmp_provider):
        """Test successful stock profile retrieval."""
        mock_session = MockSession()
        fmp_provider.session = mock_session
        
        response = await fmp_provider.get_stock_profile("AAPL")
        
        assert response.success is True
        assert response.data["symbol"] == "AAPL"
        assert response.data["company_name"] == "Apple Inc."
        assert response.data["industry"] == "Consumer Electronics"
        assert response.data["provider"] == "fmp"
    
    @pytest.mark.asyncio
    async def test_historical_data_success(self, fmp_provider):
        """Test successful historical data retrieval."""
        mock_session = MockSession()
        fmp_provider.session = mock_session
        
        response = await fmp_provider.get_historical_data("AAPL", "1y", "1d")
        
        assert response.success is True
        assert response.data["symbol"] == "AAPL"
        assert response.data["period"] == "1y"
        assert response.data["interval"] == "1d"
        assert len(response.data["data"]) == 2
        assert response.data["data"][0]["date"] == "2023-12-01"
    
    @pytest.mark.asyncio
    async def test_search_securities_success(self, fmp_provider):
        """Test successful securities search."""
        mock_session = MockSession()
        fmp_provider.session = mock_session
        
        response = await fmp_provider.search_securities("Apple", "stock", 5)
        
        assert response.success is True
        assert response.data["query"] == "Apple"
        assert response.data["count"] == 2
        assert len(response.data["results"]) == 2
        assert response.data["results"][0]["symbol"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_crypto_quote_success(self, fmp_provider):
        """Test successful crypto quote retrieval."""
        mock_session = MockSession()
        fmp_provider.session = mock_session
        
        response = await fmp_provider.get_crypto_quote("BTC")
        
        assert response.success is True
        assert response.data["asset_type"] == "crypto"
        assert response.data["provider"] == "fmp"
    
    @pytest.mark.asyncio
    async def test_market_overview_success(self, fmp_provider):
        """Test successful market overview retrieval."""
        mock_session = MockSession()
        fmp_provider.session = mock_session
        
        response = await fmp_provider.get_market_overview()
        
        assert response.success is True
        assert "indices" in response.data
        assert "crypto" in response.data
        assert response.data["provider"] == "fmp"
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, fmp_provider, mock_rate_limiter):
        """Test handling when rate limit is exceeded."""
        # Mock rate limit exceeded
        mock_rate_limiter.is_allowed.return_value = (False, {
            "allowed": False,
            "exceeded_window": "minute",
            "retry_after": 60
        })
        
        response = await fmp_provider.get_stock_quote("AAPL")
        
        assert response.success is False
        assert "Rate limit exceeded" in response.error
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, fmp_provider, mock_cache_service):
        """Test cache hit scenario."""
        # Mock cache hit
        cached_data = [{"symbol": "AAPL", "price": 150.0}]
        mock_cache_service.get.return_value = cached_data
        
        response = await fmp_provider.get_stock_quote("AAPL")
        
        assert response.success is True
        assert response.data["symbol"] == "AAPL"
        
        # Verify cache was checked
        mock_cache_service.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_network_error_retry(self, fmp_provider):
        """Test retry logic on network errors."""
        # Mock session that raises network error
        mock_session = AsyncMock()
        mock_session.get.side_effect = aiohttp.ClientError("Network error")
        fmp_provider.session = mock_session
        
        response = await fmp_provider.get_stock_quote("AAPL")
        
        assert response.success is False
        assert "failed after" in response.error
        # Error status is managed by base class
    
    @pytest.mark.asyncio
    async def test_api_authentication_error(self, fmp_provider):
        """Test handling of authentication errors."""
        # Mock 401 response
        mock_response = MockResponse(status=401)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        fmp_provider.session = mock_session
        
        response = await fmp_provider.get_stock_quote("AAPL")
        
        assert response.success is False
        assert "authentication failed" in response.error.lower()
        # Error status is managed by base class
    
    @pytest.mark.asyncio
    async def test_api_rate_limit_response(self, fmp_provider):
        """Test handling of 429 rate limit response."""
        # Mock 429 response
        mock_response = MockResponse(status=429, headers={"Retry-After": "60"})
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        fmp_provider.session = mock_session
        
        # This should timeout quickly in tests
        with patch.object(asyncio, 'sleep', return_value=None):
            response = await fmp_provider.get_stock_quote("AAPL")
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self, fmp_provider):
        """Test handling of invalid JSON responses."""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="Invalid JSON")
        
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        fmp_provider.session = mock_session
        
        response = await fmp_provider.get_stock_quote("AAPL")
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, fmp_provider):
        """Test successful health check."""
        # Mock successful quote response
        mock_session = MockSession()
        fmp_provider.session = mock_session
        
        is_healthy = await fmp_provider.health_check()
        
        assert is_healthy is True
        # Status is managed by base class
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, fmp_provider):
        """Test health check failure."""
        # Mock failed response
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Health check failed")
        fmp_provider.session = mock_session
        
        is_healthy = await fmp_provider.health_check()
        
        assert is_healthy is False
        # Error status is managed by base class
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, fmp_provider):
        """Test exponential backoff on retries."""
        # Mock session that always fails
        mock_session = AsyncMock()
        mock_session.get.side_effect = aiohttp.ClientError("Always fails")
        fmp_provider.session = mock_session
        
        # Mock sleep to verify backoff timing
        with patch.object(asyncio, 'sleep') as mock_sleep:
            response = await fmp_provider.get_stock_quote("AAPL")
            
            # Verify exponential backoff was applied
            expected_calls = [
                ((2 ** 0,),),  # First retry: 1 second
                ((2 ** 1,),),  # Second retry: 2 seconds  
                ((2 ** 2,),),  # Third retry: 4 seconds
            ]
            mock_sleep.assert_has_calls(expected_calls)
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_data_standardization(self, fmp_provider):
        """Test data standardization methods."""
        # Test quote standardization
        raw_quote = [{
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": 150.25,
            "change": 2.5,
            "changesPercentage": 1.69,
            "previousClose": 147.75,
            "volume": 50000000
        }]
        
        standardized = fmp_provider._standardize_quote_data(raw_quote)
        
        assert standardized["symbol"] == "AAPL"
        assert standardized["price"] == 150.25
        assert standardized["change"] == 2.5
        assert standardized["change_percent"] == 1.69
        assert standardized["provider"] == "fmp"
        assert "last_updated" in standardized
        
        # Test profile standardization
        raw_profile = [{
            "symbol": "AAPL",
            "companyName": "Apple Inc.",
            "industry": "Consumer Electronics",
            "sector": "Technology",
            "country": "US"
        }]
        
        standardized_profile = fmp_provider._standardize_profile_data(raw_profile)
        
        assert standardized_profile["symbol"] == "AAPL"
        assert standardized_profile["company_name"] == "Apple Inc."
        assert standardized_profile["industry"] == "Consumer Electronics"
        assert standardized_profile["provider"] == "fmp"
    
    @pytest.mark.asyncio
    async def test_provider_initialization_complete(self, fmp_provider):
        """Test provider initialization is complete."""
        assert hasattr(fmp_provider, 'api_key')
        assert hasattr(fmp_provider, 'base_url')
        assert hasattr(fmp_provider, 'endpoints')
        assert hasattr(fmp_provider, 'rate_limits')
    
    @pytest.mark.asyncio
    async def test_close_provider(self, fmp_provider):
        """Test provider cleanup."""
        # Set up a mock session
        mock_session = AsyncMock()
        mock_session.closed = False
        fmp_provider.session = mock_session
        
        await fmp_provider.close()
        
        mock_session.close.assert_called_once()


class TestFMPIntegration:
    """Integration tests for FMP provider."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_with_caching(self, fmp_provider, mock_cache_service):
        """Test complete workflow with caching."""
        # First call - cache miss
        mock_cache_service.get.return_value = None
        mock_session = MockSession()
        fmp_provider.session = mock_session
        
        response1 = await fmp_provider.get_stock_quote("AAPL")
        assert response1.success is True
        
        # Verify cache was set
        mock_cache_service.set.assert_called()
        
        # Second call - cache hit
        cached_data = [{"symbol": "AAPL", "price": 150.0}]
        mock_cache_service.get.return_value = cached_data
        
        response2 = await fmp_provider.get_stock_quote("AAPL")
        assert response2.success is True
    
    @pytest.mark.asyncio
    async def test_multiple_endpoints_workflow(self, fmp_provider):
        """Test calling multiple endpoints in sequence."""
        mock_session = MockSession()
        fmp_provider.session = mock_session
        
        # Test sequence of calls
        quote_response = await fmp_provider.get_stock_quote("AAPL")
        profile_response = await fmp_provider.get_stock_profile("AAPL")
        historical_response = await fmp_provider.get_historical_data("AAPL")
        search_response = await fmp_provider.search_securities("Apple")
        
        assert all(r.success for r in [quote_response, profile_response, 
                                     historical_response, search_response])
        assert len(mock_session.requests) == 4


if __name__ == "__main__":
    pytest.main([__file__])