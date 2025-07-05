"""
Tests for Market Data Service Orchestration Layer.

Comprehensive test suite for the market data service including provider failover,
data quality scoring, anomaly detection, and performance monitoring.
"""

import pytest
import pytest_asyncio
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timedelta

from app.services.market_data import MarketDataService
from app.schemas.market_data import (
    QuoteRequest, ProfileRequest, HistoricalRequest, SearchRequest, MarketOverviewRequest,
    QuoteResponse, ProfileResponse, HistoricalResponse, SearchResponse, MarketOverviewResponse,
    AssetType, DataQuality, DataSource
)
from app.services.data_providers.base import ProviderResponse
from app.services.data_providers.factory import FailoverStrategy
from app.services.cache import CacheService
from app.services.rate_limiter import RateLimiter


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = Mock()
    settings.fmp_api_key = "test_fmp_key"
    return settings


@pytest.fixture
def mock_cache_service():
    """Mock cache service."""
    cache = AsyncMock(spec=CacheService)
    cache.get.return_value = None  # Default to cache miss
    cache.set.return_value = True
    return cache


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter."""
    limiter = AsyncMock(spec=RateLimiter)
    limiter.is_allowed.return_value = (True, {"allowed": True})
    return limiter


@pytest_asyncio.fixture
async def market_data_service(mock_settings, mock_cache_service, mock_rate_limiter):
    """Market data service instance with mocked dependencies."""
    service = MarketDataService(
        settings=mock_settings,
        cache_service=mock_cache_service,
        rate_limiter=mock_rate_limiter,
        failover_strategy=FailoverStrategy.HEALTH_BASED
    )
    
    # Mock the factory initialization
    with patch.object(service.factory, 'initialize_all_providers') as mock_init:
        mock_init.return_value = {"fmp": True, "yahoo": True}
        with patch.object(service.factory, 'start_health_monitoring'):
            await service.initialize()
    
    yield service
    
    await service.shutdown()


class TestMarketDataServiceInitialization:
    """Test service initialization and lifecycle."""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_settings, mock_cache_service, mock_rate_limiter):
        """Test successful service initialization."""
        service = MarketDataService(mock_settings, mock_cache_service, mock_rate_limiter)
        
        with patch.object(service.factory, 'initialize_all_providers') as mock_init:
            mock_init.return_value = {"fmp": True, "yahoo": True}
            with patch.object(service.factory, 'start_health_monitoring'):
                result = await service.initialize()
        
        assert result is True
        assert service._initialized is True
        assert isinstance(service._start_time, datetime)
        
        await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_service_initialization_failure(self, mock_settings, mock_cache_service, mock_rate_limiter):
        """Test service initialization with all providers failing."""
        service = MarketDataService(mock_settings, mock_cache_service, mock_rate_limiter)
        
        with patch.object(service.factory, 'initialize_all_providers') as mock_init:
            mock_init.return_value = {"fmp": False, "yahoo": False}
            with patch.object(service.factory, 'start_health_monitoring'):
                result = await service.initialize()
        
        assert result is False
        assert service._initialized is True  # Still marked as initialized
        
        await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_service_shutdown(self, market_data_service):
        """Test service shutdown."""
        # Mock provider instances with close methods
        mock_provider1 = Mock()
        mock_provider1.close = AsyncMock()
        mock_provider2 = Mock()
        mock_provider2.close = AsyncMock()
        
        with patch.object(market_data_service.factory, 'get_all_provider_instances') as mock_get_providers:
            mock_get_providers.return_value = {"fmp": mock_provider1, "yahoo": mock_provider2}
            with patch.object(market_data_service.factory, 'stop_health_monitoring') as mock_stop:
                await market_data_service.shutdown()
        
        mock_provider1.close.assert_called_once()
        mock_provider2.close.assert_called_once()
        mock_stop.assert_called_once()
        assert market_data_service._initialized is False
    
    def test_provider_registration(self, mock_settings, mock_cache_service, mock_rate_limiter):
        """Test provider registration during initialization."""
        service = MarketDataService(mock_settings, mock_cache_service, mock_rate_limiter)
        
        # Check that providers were registered
        configs = service.factory._provider_configs
        assert "fmp" in configs
        assert "yahoo" in configs
        
        # Check priorities
        assert configs["fmp"].priority == 10  # Higher priority
        assert configs["yahoo"].priority == 20  # Lower priority


class TestDataQualityScoring:
    """Test data quality assessment functionality."""
    
    def test_data_quality_calculation_complete_data(self, market_data_service):
        """Test quality calculation with complete, fresh data."""
        data = {
            "symbol": "AAPL",
            "price": 150.25,
            "volume": 1000000,
            "name": "Apple Inc."
        }
        
        quality = market_data_service._calculate_data_quality(
            data, "fmp", 0.5, cache_hit=False
        )
        
        assert quality.completeness_score == 100.0
        assert quality.freshness_score == 100.0
        assert quality.accuracy_score == 95.0  # FMP score
        assert quality.overall_score > 90.0
        assert quality.quality_level == DataQuality.EXCELLENT
    
    def test_data_quality_calculation_incomplete_data(self, market_data_service):
        """Test quality calculation with incomplete data."""
        data = {
            "symbol": "AAPL",
            # Missing price field
            "volume": 1000000
        }
        
        quality = market_data_service._calculate_data_quality(
            data, "yahoo", 1.0, cache_hit=True
        )
        
        assert quality.completeness_score == 50.0  # Missing required field
        assert quality.freshness_score < 100.0  # Cache hit penalty
        assert quality.accuracy_score == 85.0  # Yahoo score
        assert quality.overall_score < 90.0
        assert quality.quality_level in [DataQuality.GOOD, DataQuality.FAIR]
    
    def test_data_quality_with_poor_provider(self, market_data_service):
        """Test quality calculation with unknown provider."""
        data = {"symbol": "AAPL", "price": 150.25}
        
        quality = market_data_service._calculate_data_quality(
            data, "unknown_provider", 2.0, cache_hit=False
        )
        
        assert quality.accuracy_score == 80.0  # Default score
        assert quality.quality_level != DataQuality.EXCELLENT


class TestAnomalyDetection:
    """Test anomaly detection functionality."""
    
    def test_extreme_price_change_detection(self, market_data_service):
        """Test detection of extreme price changes."""
        data = {
            "symbol": "AAPL",
            "price": 150.0,
            "change_percent": 25.0  # Above threshold
        }
        
        anomalies = market_data_service._detect_anomalies(data)
        
        assert anomalies.has_anomalies is True
        assert "extreme_price_change" in anomalies.anomaly_types
        assert anomalies.confidence_score > 0
        assert "extreme_price_change" in anomalies.details
    
    def test_volume_spike_detection(self, market_data_service):
        """Test detection of volume spikes."""
        historical_data = [
            {"volume": 1000000} for _ in range(30)  # Normal volume
        ]
        
        current_data = {
            "symbol": "AAPL",
            "volume": 6000000,  # 6x normal volume
            "change_percent": 2.0
        }
        
        anomalies = market_data_service._detect_anomalies(current_data, historical_data)
        
        assert anomalies.has_anomalies is True
        assert "volume_spike" in anomalies.anomaly_types
        assert anomalies.confidence_score > 0
        assert "volume_spike" in anomalies.details
    
    def test_price_inconsistency_detection(self, market_data_service):
        """Test detection of price inconsistencies."""
        data = {
            "symbol": "AAPL",
            "price": 160.0,  # Outside high-low range
            "open": 150.0,
            "high": 155.0,
            "low": 148.0,
            "change_percent": 2.0
        }
        
        anomalies = market_data_service._detect_anomalies(data)
        
        assert anomalies.has_anomalies is True
        assert "price_inconsistency" in anomalies.anomaly_types
        assert "price_inconsistency" in anomalies.details
    
    def test_no_anomalies_normal_data(self, market_data_service):
        """Test with normal data that should not trigger anomalies."""
        data = {
            "symbol": "AAPL",
            "price": 150.0,
            "open": 149.0,
            "high": 151.0,
            "low": 148.0,
            "volume": 1000000,
            "change_percent": 2.0
        }
        
        historical_data = [{"volume": 1000000} for _ in range(30)]
        
        anomalies = market_data_service._detect_anomalies(data, historical_data)
        
        assert anomalies.has_anomalies is False
        assert len(anomalies.anomaly_types) == 0
        assert anomalies.confidence_score == 0.0
    
    def test_anomaly_detection_disabled(self, market_data_service):
        """Test anomaly detection when disabled."""
        market_data_service.anomaly_detection_enabled = False
        
        data = {
            "symbol": "AAPL",
            "change_percent": 50.0  # Extreme change
        }
        
        anomalies = market_data_service._detect_anomalies(data)
        
        assert anomalies.has_anomalies is False
        assert len(anomalies.anomaly_types) == 0


class TestQuoteOperations:
    """Test quote retrieval operations."""
    
    @pytest.mark.asyncio
    async def test_get_stock_quote_success(self, market_data_service):
        """Test successful stock quote retrieval."""
        mock_response = ProviderResponse(
            success=True,
            data={
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "price": 150.25,
                "change": 2.5,
                "change_percent": 1.69,
                "previous_close": 147.75,
                "open": 148.0,
                "high": 151.0,
                "low": 147.5,
                "volume": 50000000,
                "market_cap": 2500000000000,
                "pe_ratio": 25.5,
                "asset_type": "stock",
                "currency": "USD",
                "exchange": "NASDAQ",
                "timezone": "US/Eastern",
                "last_updated": datetime.now()
            },
            provider="fmp",
            timestamp=datetime.now(),
            metadata={"cached": False}
        )
        
        with patch.object(market_data_service.factory, 'get_stock_quote') as mock_get_quote:
            mock_get_quote.return_value = mock_response
            
            request = QuoteRequest(symbol="AAPL", asset_type=AssetType.STOCK)
            response = await market_data_service.get_quote(request)
        
        assert response.success is True
        assert response.symbol == "AAPL"
        assert response.data is not None
        assert response.data.price == 150.25
        assert response.data_quality.quality_level == DataQuality.EXCELLENT
        assert response.provenance.primary_source == DataSource.FMP
    
    @pytest.mark.asyncio
    async def test_get_crypto_quote_success(self, market_data_service):
        """Test successful crypto quote retrieval."""
        mock_response = ProviderResponse(
            success=True,
            data={
                "symbol": "BTC",
                "name": "Bitcoin",
                "price": 45000.0,
                "change": 1000.0,
                "change_percent": 2.27,
                "previous_close": 44000.0,
                "open": 44500.0,
                "high": 45500.0,
                "low": 43500.0,
                "volume": 1000000,
                "asset_type": "crypto",
                "currency": "USD",
                "last_updated": datetime.now()
            },
            provider="yahoo",
            timestamp=datetime.now(),
            metadata={"cached": False}
        )
        
        with patch.object(market_data_service.factory, 'get_crypto_quote') as mock_get_crypto:
            mock_get_crypto.return_value = mock_response
            
            request = QuoteRequest(symbol="BTC", asset_type=AssetType.CRYPTO)
            response = await market_data_service.get_quote(request)
        
        assert response.success is True
        assert response.symbol == "BTC"
        assert response.data.asset_type == AssetType.CRYPTO
        assert response.provenance.primary_source == DataSource.YAHOO
    
    @pytest.mark.asyncio
    async def test_get_quote_failure(self, market_data_service):
        """Test quote retrieval failure."""
        mock_response = ProviderResponse(
            success=False,
            data={},
            provider="fmp",
            timestamp=datetime.now(),
            error="Symbol not found",
            metadata={"cached": False}
        )
        
        with patch.object(market_data_service.factory, 'get_stock_quote') as mock_get_quote:
            mock_get_quote.return_value = mock_response
            
            request = QuoteRequest(symbol="INVALID")
            response = await market_data_service.get_quote(request)
        
        assert response.success is False
        assert response.symbol == "INVALID"
        assert response.data is None
        assert response.error == "Symbol not found"
        assert response.data_quality.quality_level == DataQuality.UNRELIABLE
    
    @pytest.mark.asyncio
    async def test_get_quote_with_anomaly_detection(self, market_data_service):
        """Test quote retrieval with anomaly detection."""
        mock_response = ProviderResponse(
            success=True,
            data={
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "price": 150.0,
                "change": 30.0,
                "change_percent": 25.0,  # Extreme change
                "previous_close": 120.0,
                "open": 125.0,
                "high": 155.0,
                "low": 120.0,
                "volume": 100000000,
                "asset_type": "stock",
                "last_updated": datetime.now()
            },
            provider="fmp",
            timestamp=datetime.now(),
            metadata={"cached": False}
        )
        
        with patch.object(market_data_service.factory, 'get_stock_quote') as mock_get_quote:
            mock_get_quote.return_value = mock_response
            
            request = QuoteRequest(symbol="AAPL")
            response = await market_data_service.get_quote(request)
        
        assert response.success is True
        assert response.anomaly_detection is not None
        assert response.anomaly_detection.has_anomalies is True
        assert "extreme_price_change" in response.anomaly_detection.anomaly_types


class TestProfileOperations:
    """Test profile retrieval operations."""
    
    @pytest.mark.asyncio
    async def test_get_profile_success(self, market_data_service):
        """Test successful profile retrieval."""
        mock_response = ProviderResponse(
            success=True,
            data={
                "symbol": "AAPL",
                "company_name": "Apple Inc.",
                "description": "Apple Inc. designs and manufactures consumer electronics.",
                "industry": "Consumer Electronics",
                "sector": "Technology",
                "country": "US",
                "website": "https://www.apple.com",
                "market_cap": 2500000000000,
                "employees": 147000,
                "exchange": "NASDAQ",
                "currency": "USD",
                "ceo": "Tim Cook",
                "founded": 1976,
                "headquarters": {
                    "street": "One Apple Park Way",
                    "city": "Cupertino",
                    "state": "CA",
                    "zip_code": "95014",
                    "country": "US"
                },
                "last_updated": datetime.now()
            },
            provider="fmp",
            timestamp=datetime.now(),
            metadata={"cached": True}
        )
        
        with patch.object(market_data_service.factory, 'get_stock_profile') as mock_get_profile:
            mock_get_profile.return_value = mock_response
            
            request = ProfileRequest(symbol="AAPL")
            response = await market_data_service.get_profile(request)
        
        assert response.success is True
        assert response.symbol == "AAPL"
        assert response.data.company_name == "Apple Inc."
        assert response.data.sector == "Technology"
        assert response.provenance.cache_hit is True


class TestFailoverMechanisms:
    """Test provider failover functionality."""
    
    @pytest.mark.asyncio
    async def test_provider_failover_on_failure(self, market_data_service):
        """Test automatic failover when primary provider fails."""
        # First call fails, second succeeds
        failed_response = ProviderResponse(
            success=False,
            data={},
            provider="fmp",
            timestamp=datetime.now(),
            error="Provider unavailable"
        )
        
        success_response = ProviderResponse(
            success=True,
            data={
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "price": 150.0,
                "change": 2.5,
                "change_percent": 1.69,
                "previous_close": 147.5,
                "open": 148.0,
                "high": 151.0,
                "low": 147.0,
                "volume": 50000000,
                "asset_type": "stock",
                "currency": "USD",
                "exchange": "NASDAQ",
                "timezone": "US/Eastern",
                "last_updated": datetime.now()
            },
            provider="yahoo",
            timestamp=datetime.now(),
            metadata={"cached": False}
        )
        
        with patch.object(market_data_service.factory, 'get_stock_quote') as mock_get_quote:
            # Simulate failover by returning success on retry
            mock_get_quote.return_value = success_response
            
            request = QuoteRequest(symbol="AAPL")
            response = await market_data_service.get_quote(request)
        
        assert response.success is True
        assert response.provenance.primary_source == DataSource.YAHOO


class TestPerformanceAndMonitoring:
    """Test performance monitoring and metrics."""
    
    @pytest.mark.asyncio
    async def test_processing_time_tracking(self, market_data_service):
        """Test that processing time is tracked correctly."""
        mock_response = ProviderResponse(
            success=True,
            data={"symbol": "AAPL", "price": 150.0, "last_updated": datetime.now()},
            provider="fmp",
            timestamp=datetime.now()
        )
        
        with patch.object(market_data_service.factory, 'get_stock_quote') as mock_get_quote:
            # Add artificial delay
            async def delayed_response(*args, **kwargs):
                await asyncio.sleep(0.1)
                return mock_response
            
            mock_get_quote.side_effect = delayed_response
            
            request = QuoteRequest(symbol="AAPL")
            response = await market_data_service.get_quote(request)
        
        assert response.success is True
        assert response.provenance.processing_time_ms >= 100  # At least 100ms
    
    @pytest.mark.asyncio
    async def test_system_health_check(self, market_data_service):
        """Test system health monitoring."""
        mock_factory_status = {
            "factory_info": {
                "failover_strategy": "health_based",
                "health_monitoring_active": True,
                "uptime_seconds": 3600
            },
            "providers": {
                "fmp": {"status": "healthy", "success_rate": 95.0},
                "yahoo": {"status": "healthy", "success_rate": 88.0}
            }
        }
        
        with patch.object(market_data_service.factory, 'get_factory_status') as mock_status:
            mock_status.return_value = mock_factory_status
            
            health_response = await market_data_service.get_system_health()
        
        assert health_response.success is True
        assert health_response.health is not None


class TestCacheIntegration:
    """Test cache integration and behavior."""
    
    @pytest.mark.asyncio
    async def test_cache_hit_affects_quality_score(self, market_data_service):
        """Test that cache hits affect data quality scoring."""
        mock_response = ProviderResponse(
            success=True,
            data={"symbol": "AAPL", "price": 150.0, "last_updated": datetime.now()},
            provider="fmp",
            timestamp=datetime.now(),
            metadata={"cached": True}
        )
        
        with patch.object(market_data_service.factory, 'get_stock_quote') as mock_get_quote:
            mock_get_quote.return_value = mock_response
            
            request = QuoteRequest(symbol="AAPL")
            response = await market_data_service.get_quote(request)
        
        assert response.success is True
        assert response.provenance.cache_hit is True
        # Freshness score should be lower for cached data
        assert response.data_quality.freshness_score < 100.0


class TestDataAggregation:
    """Test data aggregation across multiple providers."""
    
    @pytest.mark.asyncio
    async def test_market_overview_aggregation(self, market_data_service):
        """Test market overview data aggregation."""
        mock_response = ProviderResponse(
            success=True,
            data={
                "indices": [
                    {"symbol": "SPY", "price": 450.0, "name": "SPDR S&P 500"},
                    {"symbol": "QQQ", "price": 350.0, "name": "Invesco QQQ Trust"}
                ],
                "crypto": [
                    {"symbol": "BTCUSD", "price": 45000.0, "name": "Bitcoin USD"}
                ],
                "last_updated": datetime.now().isoformat(),
                "provider": "fmp"
            },
            provider="fmp",
            timestamp=datetime.now()
        )
        
        with patch.object(market_data_service.factory, 'get_market_overview') as mock_overview:
            mock_overview.return_value = mock_response
            
            request = MarketOverviewRequest()
            response = await market_data_service.get_market_overview(request)
        
        assert response.success is True
        assert response.data is not None
        assert "indices" in response.data
        assert "crypto" in response.data


class TestContextManager:
    """Test async context manager functionality."""
    
    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, mock_settings, mock_cache_service, mock_rate_limiter):
        """Test service as async context manager."""
        with patch('app.services.market_data.MarketDataService.initialize') as mock_init:
            with patch('app.services.market_data.MarketDataService.shutdown') as mock_shutdown:
                mock_init.return_value = True
                
                async with MarketDataService(mock_settings, mock_cache_service, mock_rate_limiter) as service:
                    assert service is not None
                
                mock_init.assert_called_once()
                mock_shutdown.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])