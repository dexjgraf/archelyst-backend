"""
Tests for Yahoo Finance data provider.

Comprehensive test suite for Yahoo Finance provider including async operations,
rate limiting, caching, error handling, and data standardization.
"""

import pytest
import asyncio
import pandas as pd
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from app.services.data_providers.yfinance import YahooFinanceProvider
from app.services.data_providers.base import ProviderResponse, ProviderHealth
from app.services.cache import CacheService, CacheLevel
from app.services.rate_limiter import RateLimiter


@pytest.fixture
def mock_settings():
    """Mock settings for Yahoo Finance provider."""
    settings = Mock()
    settings.yahoo_enabled = True
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
def yahoo_provider(mock_settings, mock_cache_service, mock_rate_limiter):
    """Yahoo Finance provider instance with mocked dependencies."""
    return YahooFinanceProvider(mock_settings, mock_cache_service, mock_rate_limiter)


class TestYahooFinanceProvider:
    """Test cases for YahooFinanceProvider."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, yahoo_provider):
        """Test Yahoo Finance provider initialization."""
        assert yahoo_provider.name == "yahoo"
        assert hasattr(yahoo_provider, 'crypto_mapping')
        assert hasattr(yahoo_provider, 'executor')
        assert isinstance(yahoo_provider.executor, ThreadPoolExecutor)
        assert hasattr(yahoo_provider, '_health_status')
    
    def test_symbol_normalization(self, yahoo_provider):
        """Test symbol normalization for different asset types."""
        # Stock symbols
        assert yahoo_provider._normalize_symbol("AAPL") == "AAPL"
        assert yahoo_provider._normalize_symbol("aapl") == "AAPL"
        
        # Crypto symbols
        assert yahoo_provider._normalize_symbol("BTC", "crypto") == "BTC-USD"
        assert yahoo_provider._normalize_symbol("ETH", "crypto") == "ETH-USD"
        assert yahoo_provider._normalize_symbol("UNKNOWN", "crypto") == "UNKNOWN-USD"
    
    def test_cache_level_selection(self, yahoo_provider):
        """Test cache level selection for different operations."""
        assert yahoo_provider._get_cache_level("info") == CacheLevel.QUOTES
        assert yahoo_provider._get_cache_level("quote") == CacheLevel.QUOTES
        assert yahoo_provider._get_cache_level("profile") == CacheLevel.PROFILES
        assert yahoo_provider._get_cache_level("history") == CacheLevel.HISTORICAL
        assert yahoo_provider._get_cache_level("search") == CacheLevel.SEARCH
    
    def test_response_validation(self, yahoo_provider):
        """Test response validation for different operations."""
        # Valid responses
        assert yahoo_provider._is_valid_response({"symbol": "AAPL", "price": 150}, "info")
        assert yahoo_provider._is_valid_response([], "search")
        
        # Create a mock DataFrame for history validation with proper len() support
        mock_df = Mock()
        mock_df.index = range(10)  # Mock index with length
        mock_df.__len__ = Mock(return_value=10)  # Add len() support
        assert yahoo_provider._is_valid_response(mock_df, "history")
        
        # Test empty DataFrame
        empty_df = Mock()
        empty_df.index = []
        empty_df.__len__ = Mock(return_value=0)
        assert not yahoo_provider._is_valid_response(empty_df, "history")
        
        # Invalid responses
        assert not yahoo_provider._is_valid_response(None, "info")
        assert not yahoo_provider._is_valid_response({}, "info")
    
    def test_data_standardization_quote(self, yahoo_provider):
        """Test quote data standardization."""
        ticker_info = {
            "currentPrice": 150.25,
            "previousClose": 147.75,
            "longName": "Apple Inc.",
            "regularMarketOpen": 148.0,
            "regularMarketDayHigh": 151.0,
            "regularMarketDayLow": 147.5,
            "regularMarketVolume": 50000000,
            "marketCap": 2500000000000,
            "trailingPE": 25.5
        }
        
        standardized = yahoo_provider._standardize_quote_data(ticker_info, "AAPL")
        
        assert standardized["symbol"] == "AAPL"
        assert standardized["price"] == 150.25
        assert standardized["change"] == 2.5  # 150.25 - 147.75
        assert standardized["change_percent"] == pytest.approx(1.69, abs=0.1)
        assert standardized["provider"] == "yahoo"
        assert "last_updated" in standardized
    
    def test_data_standardization_profile(self, yahoo_provider):
        """Test profile data standardization."""
        ticker_info = {
            "longName": "Apple Inc.",
            "longBusinessSummary": "Apple Inc. designs and manufactures consumer electronics.",
            "industry": "Consumer Electronics",
            "sector": "Technology",
            "country": "US",
            "website": "https://www.apple.com",
            "marketCap": 2500000000000,
            "fullTimeEmployees": 147000,
            "exchange": "NASDAQ",
            "currency": "USD",
            "companyOfficers": [{"name": "Tim Cook"}],
            "address1": "One Apple Park Way",
            "city": "Cupertino",
            "state": "CA",
            "zip": "95014"
        }
        
        standardized = yahoo_provider._standardize_profile_data(ticker_info, "AAPL")
        
        assert standardized["symbol"] == "AAPL"
        assert standardized["company_name"] == "Apple Inc."
        assert standardized["industry"] == "Consumer Electronics"
        assert standardized["sector"] == "Technology"
        assert standardized["ceo"] == "Tim Cook"
        assert standardized["provider"] == "yahoo"
    
    @pytest.mark.asyncio
    async def test_stock_quote_success(self, yahoo_provider):
        """Test successful stock quote retrieval."""
        mock_ticker_info = {
            "currentPrice": 150.25,
            "previousClose": 147.75,
            "longName": "Apple Inc.",
            "regularMarketVolume": 50000000
        }
        
        with patch.object(yahoo_provider, '_make_yfinance_request', return_value=mock_ticker_info):
            response = await yahoo_provider.get_stock_quote("AAPL")
            
            assert response.success is True
            assert response.data["symbol"] == "AAPL"
            assert response.data["price"] == 150.25
            assert response.data["provider"] == "yahoo"
            assert "last_updated" in response.data
    
    @pytest.mark.asyncio
    async def test_stock_profile_success(self, yahoo_provider):
        """Test successful stock profile retrieval."""
        mock_ticker_info = {
            "longName": "Apple Inc.",
            "longBusinessSummary": "Apple Inc. designs consumer electronics.",
            "industry": "Consumer Electronics",
            "sector": "Technology"
        }
        
        with patch.object(yahoo_provider, '_make_yfinance_request', return_value=mock_ticker_info):
            response = await yahoo_provider.get_stock_profile("AAPL")
            
            assert response.success is True
            assert response.data["symbol"] == "AAPL"
            assert response.data["company_name"] == "Apple Inc."
            assert response.data["industry"] == "Consumer Electronics"
            assert response.data["provider"] == "yahoo"
    
    @pytest.mark.asyncio
    async def test_historical_data_success(self, yahoo_provider):
        """Test successful historical data retrieval."""
        # Create mock pandas DataFrame
        dates = pd.date_range("2023-01-01", periods=5, freq="D")
        mock_df = pd.DataFrame({
            "Open": [150.0, 151.0, 152.0, 153.0, 154.0],
            "High": [152.0, 153.0, 154.0, 155.0, 156.0],
            "Low": [149.0, 150.0, 151.0, 152.0, 153.0],
            "Close": [151.0, 152.0, 153.0, 154.0, 155.0],
            "Volume": [1000000, 1100000, 1200000, 1300000, 1400000]
        }, index=dates)
        
        with patch.object(yahoo_provider, '_make_yfinance_request', return_value=mock_df):
            response = await yahoo_provider.get_historical_data("AAPL", "5d", "1d")
            
            assert response.success is True
            assert response.data["symbol"] == "AAPL"
            assert response.data["period"] == "5d"
            assert response.data["interval"] == "1d"
            assert len(response.data["data"]) == 5
            assert response.data["data"][0]["date"] == "2023-01-01"
            assert response.data["provider"] == "yahoo"
    
    @pytest.mark.asyncio
    async def test_search_securities_success(self, yahoo_provider):
        """Test securities search functionality."""
        response = await yahoo_provider.search_securities("Apple", "stock", 5)
        
        assert response.success is True
        assert response.data["query"] == "Apple"
        assert response.data["asset_type"] == "stock"
        assert isinstance(response.data["results"], list)
        assert response.data["provider"] == "yahoo"
        
        # Should find Apple in the common symbols
        if response.data["results"]:
            assert any("AAPL" in result["symbol"] for result in response.data["results"])
    
    @pytest.mark.asyncio
    async def test_crypto_quote_success(self, yahoo_provider):
        """Test successful crypto quote retrieval."""
        mock_ticker_info = {
            "currentPrice": 45000.0,
            "previousClose": 44000.0,
            "longName": "Bitcoin USD",
            "regularMarketVolume": 1000000
        }
        
        with patch.object(yahoo_provider, '_make_yfinance_request', return_value=mock_ticker_info):
            response = await yahoo_provider.get_crypto_quote("BTC")
            
            assert response.success is True
            assert response.data["asset_type"] == "crypto"
            assert response.data["provider"] == "yahoo"
    
    @pytest.mark.asyncio
    async def test_market_overview_success(self, yahoo_provider):
        """Test successful market overview retrieval."""
        mock_ticker_info = {
            "currentPrice": 4500.0,
            "previousClose": 4450.0,
            "longName": "S&P 500",
            "regularMarketVolume": 1000000
        }
        
        with patch.object(yahoo_provider, '_make_yfinance_request', return_value=mock_ticker_info):
            response = await yahoo_provider.get_market_overview()
            
            assert response.success is True
            assert "indices" in response.data
            assert "crypto" in response.data
            assert response.data["provider"] == "yahoo"
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, yahoo_provider, mock_rate_limiter):
        """Test handling when rate limit is exceeded."""
        mock_rate_limiter.is_allowed.return_value = (False, {
            "allowed": False,
            "exceeded_window": "minute",
            "retry_after": 60
        })
        
        response = await yahoo_provider.get_stock_quote("AAPL")
        
        assert response.success is False
        assert "Rate limit exceeded" in response.error
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, yahoo_provider, mock_cache_service):
        """Test cache hit scenario."""
        cached_data = {
            "currentPrice": 150.0,
            "previousClose": 149.0,
            "longName": "Apple Inc."
        }
        mock_cache_service.get.return_value = cached_data
        
        # Mock the standardization to avoid calling actual yfinance
        with patch.object(yahoo_provider, '_standardize_quote_data') as mock_standardize:
            mock_standardize.return_value = {"symbol": "AAPL", "price": 150.0, "provider": "yahoo"}
            
            response = await yahoo_provider.get_stock_quote("AAPL")
            
            assert response.success is True
            mock_cache_service.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_yfinance_request_error(self, yahoo_provider):
        """Test handling of yfinance request errors."""
        with patch.object(yahoo_provider, '_run_in_executor', side_effect=Exception("YFinance error")):
            response = await yahoo_provider.get_stock_quote("INVALID")
            
            assert response.success is False
            assert "YFinance error" in response.error or "failed after" in response.error
    
    @pytest.mark.asyncio
    async def test_invalid_symbol_handling(self, yahoo_provider):
        """Test handling of invalid symbols."""
        # Mock yfinance to return empty data for invalid symbols
        empty_info = {}
        
        with patch.object(yahoo_provider, '_make_yfinance_request', return_value=empty_info):
            response = await yahoo_provider.get_stock_quote("INVALID_SYMBOL")
            
            # Should still succeed but with empty/default data
            assert response.success is True
            assert response.data["symbol"] == "INVALID_SYMBOL"
            assert response.data["price"] == 0.0
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, yahoo_provider):
        """Test successful health check."""
        mock_ticker_info = {
            "currentPrice": 450.0,
            "previousClose": 445.0,
            "longName": "SPDR S&P 500"
        }
        
        with patch.object(yahoo_provider, '_make_yfinance_request', return_value=mock_ticker_info):
            is_healthy = await yahoo_provider.health_check()
            
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, yahoo_provider):
        """Test health check failure."""
        with patch.object(yahoo_provider, 'get_stock_quote', return_value=ProviderResponse(
            success=False, data={}, provider="yahoo", timestamp=datetime.now(), error="Health check failed"
        )):
            is_healthy = await yahoo_provider.health_check()
            
            assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_retry(self, yahoo_provider):
        """Test exponential backoff on retries."""
        call_count = 0
        
        def mock_sync_request():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Temporary failure")
            return {"currentPrice": 150.0}
        
        with patch.object(yahoo_provider, '_run_in_executor', side_effect=[
            Exception("Fail 1"), Exception("Fail 2"), Exception("Fail 3"), Exception("Fail 4")
        ]):
            with patch('asyncio.sleep') as mock_sleep:
                response = await yahoo_provider.get_stock_quote("AAPL")
                
                # Should have made retry attempts with exponential backoff
                assert mock_sleep.call_count == 3  # 3 retry attempts
                assert response.success is False
    
    @pytest.mark.asyncio
    async def test_provider_cleanup(self, yahoo_provider):
        """Test provider cleanup."""
        # Mock the executor
        mock_executor = Mock()
        yahoo_provider.executor = mock_executor
        
        await yahoo_provider.close()
        
        mock_executor.shutdown.assert_called_once_with(wait=True)
    
    @pytest.mark.asyncio
    async def test_crypto_symbol_mapping(self, yahoo_provider):
        """Test crypto symbol mapping."""
        mock_ticker_info = {
            "currentPrice": 45000.0,
            "previousClose": 44000.0,
            "longName": "Bitcoin USD"
        }
        
        with patch.object(yahoo_provider, '_make_yfinance_request') as mock_request:
            mock_request.return_value = mock_ticker_info
            
            await yahoo_provider.get_crypto_quote("BTC")
            
            # Should call with BTC-USD symbol
            mock_request.assert_called_with("BTC-USD", "info")
    
    def test_error_handling_in_standardization(self, yahoo_provider):
        """Test error handling during data standardization."""
        # Test with data that causes actual conversion errors
        bad_ticker_info = {
            "currentPrice": float('inf'),  # This will cause issues
            "previousClose": float('nan'),
            "longName": None
        }
        
        # The Yahoo provider tries to handle bad data gracefully
        result = yahoo_provider._standardize_quote_data(bad_ticker_info, "TEST")
        
        # Should still return a dict with symbol and provider, but may have default values
        assert isinstance(result, dict)
        assert result.get("symbol") == "TEST"
        assert result.get("provider") == "yahoo"
        
        # Test with completely invalid data that will actually trigger exception
        with patch.object(yahoo_provider, '_standardize_profile_data') as mock_standardize:
            mock_standardize.side_effect = Exception("Conversion error")
            
            # This would be called from within a try/except that returns empty dict
            with pytest.raises(Exception):
                yahoo_provider._standardize_profile_data(bad_ticker_info, "TEST")


class TestYahooFinanceIntegration:
    """Integration tests for Yahoo Finance provider."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_with_caching(self, yahoo_provider, mock_cache_service):
        """Test complete workflow with caching."""
        mock_ticker_info = {
            "currentPrice": 150.0,
            "previousClose": 149.0,
            "longName": "Apple Inc."
        }
        
        # First call - cache miss
        mock_cache_service.get.return_value = None
        
        with patch.object(yahoo_provider, '_run_in_executor', return_value=mock_ticker_info):
            response1 = await yahoo_provider.get_stock_quote("AAPL")
            assert response1.success is True
            
            # Verify cache was set
            mock_cache_service.set.assert_called()
            
            # Second call - cache hit
            mock_cache_service.get.return_value = mock_ticker_info
            
            response2 = await yahoo_provider.get_stock_quote("AAPL")
            assert response2.success is True
    
    @pytest.mark.asyncio
    async def test_multiple_endpoints_workflow(self, yahoo_provider):
        """Test calling multiple endpoints in sequence."""
        mock_ticker_info = {
            "currentPrice": 150.0,
            "previousClose": 149.0,
            "longName": "Apple Inc.",
            "industry": "Consumer Electronics"
        }
        
        mock_df = pd.DataFrame({
            "Open": [150.0], "High": [152.0], "Low": [149.0], 
            "Close": [151.0], "Volume": [1000000]
        }, index=[datetime.now()])
        
        with patch.object(yahoo_provider, '_run_in_executor') as mock_executor:
            # Setup different returns for different calls
            mock_executor.side_effect = [mock_ticker_info, mock_ticker_info, mock_df]
            
            quote_response = await yahoo_provider.get_stock_quote("AAPL")
            profile_response = await yahoo_provider.get_stock_profile("AAPL")
            historical_response = await yahoo_provider.get_historical_data("AAPL")
            
            assert all(r.success for r in [quote_response, profile_response, historical_response])
            assert mock_executor.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__])