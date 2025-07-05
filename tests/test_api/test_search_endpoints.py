"""
Tests for Search & Discovery API Endpoints.

Comprehensive test suite for search endpoints including securities search,
suggestions, trending, and popular securities functionality.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.v1.endpoints.search import router
from app.schemas.securities import SecuritySearchParams, SecurityType, ExchangeCode
from app.schemas.market_data import (
    SearchRequest, SearchResponse, SearchData, SecuritySearchResult as MarketDataSearchResult,
    AssetType, DataQuality, DataQualityMetrics, DataProvenance, DataSource
)
from app.services.market_data import MarketDataService


# Create test app
test_app = FastAPI()
test_app.include_router(router, prefix="/search")


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(test_app)


@pytest.fixture
def mock_market_data_service():
    """Mock market data service."""
    service = AsyncMock(spec=MarketDataService)
    
    # Default successful search response
    mock_search_result = MarketDataSearchResult(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
        country="US",
        industry="Consumer Electronics",
        market_cap=2500000000000,
        relevance_score=95.0
    )
    
    mock_search_data = SearchData(
        query="apple",
        results=[mock_search_result],
        total_count=1,
        page_size=10,
        processing_time_ms=125.5,
        last_updated=datetime.now()
    )
    
    mock_data_quality = DataQualityMetrics(
        completeness_score=95.0,
        freshness_score=98.0,
        accuracy_score=92.0,
        consistency_score=90.0,
        overall_score=93.8,
        quality_level=DataQuality.EXCELLENT
    )
    
    mock_provenance = DataProvenance(
        primary_source=DataSource.FMP,
        fallback_sources=[],
        processing_time_ms=125.5,
        cache_hit=False,
        cache_age_seconds=None,
        provider_health={"fmp": "healthy"}
    )
    
    mock_response = SearchResponse(
        success=True,
        symbol="apple",
        timestamp=datetime.now(),
        data=mock_search_data,
        data_quality=mock_data_quality,
        provenance=mock_provenance
    )
    
    service.search_securities.return_value = mock_response
    return service


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {"user_id": "test_user_123", "email": "test@example.com"}


class TestSecuritiesSearch:
    """Test securities search functionality."""
    
    def test_search_securities_success(self, client, mock_market_data_service, mock_user):
        """Test successful securities search."""
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            with patch('app.api.v1.endpoints.search.get_current_user_optional_supabase') as mock_get_user:
                mock_get_user.return_value = mock_user
                
                search_params = {
                    "query": "Apple",
                    "types": ["stock"],
                    "limit": 10
                }
                
                response = client.post("/search/securities", json=search_params)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["total_found"] >= 0
                assert "query" in data["data"]
                assert "results" in data["data"]
    
    def test_search_securities_with_filters(self, client, mock_market_data_service, mock_user):
        """Test securities search with various filters."""
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            with patch('app.api.v1.endpoints.search.get_current_user_optional_supabase') as mock_get_user:
                mock_get_user.return_value = mock_user
                
                search_params = {
                    "query": "tech",
                    "types": ["stock", "etf"],
                    "exchanges": ["nasdaq", "nyse"],
                    "sectors": ["Technology"],
                    "min_market_cap": 1000000000,
                    "max_market_cap": 5000000000000,
                    "limit": 20
                }
                
                response = client.post("/search/securities", json=search_params)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
    
    def test_search_securities_empty_query(self, client, mock_market_data_service):
        """Test search with empty query."""
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            search_params = {
                "query": "",
                "limit": 10
            }
            
            response = client.post("/search/securities", json=search_params)
            
            assert response.status_code == 400
    
    def test_search_securities_long_query(self, client, mock_market_data_service):
        """Test search with query that's too long."""
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            search_params = {
                "query": "a" * 101,  # 101 characters
                "limit": 10
            }
            
            response = client.post("/search/securities", json=search_params)
            
            assert response.status_code == 400
    
    def test_search_securities_service_failure(self, client, mock_market_data_service):
        """Test search when market data service fails."""
        # Configure service to return failure
        failed_response = SearchResponse(
            success=False,
            symbol="test",
            timestamp=datetime.now(),
            data=None,
            data_quality=DataQualityMetrics(
                completeness_score=0, freshness_score=0, accuracy_score=0,
                consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
            ),
            provenance=DataProvenance(
                primary_source=DataSource.YAHOO,
                processing_time_ms=50.0,
                cache_hit=False
            ),
            error="Search service unavailable"
        )
        mock_market_data_service.search_securities.return_value = failed_response
        
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            search_params = {
                "query": "AAPL",
                "limit": 10
            }
            
            response = client.post("/search/securities", json=search_params)
            
            assert response.status_code == 200  # Still returns 200 but with success=False
            data = response.json()
            assert data["success"] is False
            assert "error" in data["message"]
    
    def test_search_securities_exception(self, client, mock_market_data_service):
        """Test search when an exception occurs."""
        mock_market_data_service.search_securities.side_effect = Exception("Database connection failed")
        
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            search_params = {
                "query": "AAPL",
                "limit": 10
            }
            
            response = client.post("/search/securities", json=search_params)
            
            assert response.status_code == 500


class TestSearchSuggestions:
    """Test search suggestions functionality."""
    
    def test_get_suggestions_success(self, client, mock_market_data_service):
        """Test successful suggestions retrieval."""
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            response = client.get("/search/suggestions?query=app&limit=5")
            
            assert response.status_code == 200
            data = response.json()
            assert "query" in data
            assert "suggestions" in data
            assert "timestamp" in data
            assert isinstance(data["suggestions"], list)
    
    def test_get_suggestions_with_asset_types(self, client, mock_market_data_service):
        """Test suggestions with specific asset types."""
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            response = client.get("/search/suggestions?query=btc&asset_types=crypto&limit=3")
            
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "btc"
    
    def test_get_suggestions_empty_query(self, client):
        """Test suggestions with empty query."""
        response = client.get("/search/suggestions?query=")
        
        assert response.status_code == 422  # Validation error
    
    def test_get_suggestions_service_failure(self, client, mock_market_data_service):
        """Test suggestions when service fails."""
        mock_market_data_service.search_securities.side_effect = Exception("Service error")
        
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            response = client.get("/search/suggestions?query=app")
            
            assert response.status_code == 500


class TestTrendingSecurities:
    """Test trending securities functionality."""
    
    def test_get_trending_stocks(self, client):
        """Test trending stocks retrieval."""
        response = client.get("/search/trending?asset_type=stock&timeframe=1d&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "trending" in data
        assert "asset_type" in data
        assert "timeframe" in data
        assert "timestamp" in data
        assert data["asset_type"] == "stock"
        assert data["timeframe"] == "1d"
        assert isinstance(data["trending"], list)
        assert len(data["trending"]) <= 10
    
    def test_get_trending_crypto(self, client):
        """Test trending crypto retrieval."""
        response = client.get("/search/trending?asset_type=crypto&timeframe=1w&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["asset_type"] == "crypto"
        assert data["timeframe"] == "1w"
        assert len(data["trending"]) <= 5
    
    def test_get_trending_all_types(self, client):
        """Test trending with all asset types."""
        response = client.get("/search/trending?asset_type=all&limit=15")
        
        assert response.status_code == 200
        data = response.json()
        assert data["asset_type"] == "all"
        assert len(data["trending"]) <= 15
    
    def test_get_trending_invalid_asset_type(self, client):
        """Test trending with invalid asset type."""
        response = client.get("/search/trending?asset_type=invalid")
        
        assert response.status_code == 422  # Validation error
    
    def test_get_trending_invalid_timeframe(self, client):
        """Test trending with invalid timeframe."""
        response = client.get("/search/trending?timeframe=invalid")
        
        assert response.status_code == 422  # Validation error


class TestPopularSecurities:
    """Test popular securities functionality."""
    
    def test_get_popular_large_cap(self, client):
        """Test popular large cap securities."""
        response = client.get("/search/popular?category=large_cap&limit=20")
        
        assert response.status_code == 200
        data = response.json()
        assert "popular" in data
        assert "category" in data
        assert "total_count" in data
        assert "timestamp" in data
        assert data["category"] == "large_cap"
        assert isinstance(data["popular"], list)
        assert len(data["popular"]) <= 20
    
    def test_get_popular_crypto(self, client):
        """Test popular crypto securities."""
        response = client.get("/search/popular?category=crypto&limit=15")
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "crypto"
        assert len(data["popular"]) <= 15
    
    def test_get_popular_all_categories(self, client):
        """Test popular securities from all categories."""
        response = client.get("/search/popular?category=all&limit=50")
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "all"
        assert len(data["popular"]) <= 50
    
    def test_get_popular_invalid_category(self, client):
        """Test popular with invalid category."""
        response = client.get("/search/popular?category=invalid")
        
        assert response.status_code == 422  # Validation error
    
    def test_get_popular_limit_validation(self, client):
        """Test popular with invalid limit."""
        response = client.get("/search/popular?limit=300")  # Above max limit
        
        assert response.status_code == 422  # Validation error


class TestHealthCheck:
    """Test health check functionality."""
    
    def test_health_check_success(self, client, mock_market_data_service):
        """Test successful health check."""
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            response = client.get("/search/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "version" in data
            assert "services" in data
            assert data["test_search"] == "passed"
    
    def test_health_check_service_failure(self, client, mock_market_data_service):
        """Test health check when search service fails."""
        # Configure service to return failure
        failed_response = SearchResponse(
            success=False,
            symbol="AAPL",
            timestamp=datetime.now(),
            data=None,
            data_quality=DataQualityMetrics(
                completeness_score=0, freshness_score=0, accuracy_score=0,
                consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
            ),
            provenance=DataProvenance(
                primary_source=DataSource.YAHOO,
                processing_time_ms=50.0,
                cache_hit=False
            ),
            error="Service unavailable"
        )
        mock_market_data_service.search_securities.return_value = failed_response
        
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            response = client.get("/search/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["test_search"] == "failed"
    
    def test_health_check_exception(self, client, mock_market_data_service):
        """Test health check when an exception occurs."""
        mock_market_data_service.search_securities.side_effect = Exception("Connection failed")
        
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            response = client.get("/search/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_validate_search_query_valid(self):
        """Test validate_search_query with valid inputs."""
        from app.api.v1.endpoints.search import validate_search_query
        
        assert validate_search_query("AAPL") == "AAPL"
        assert validate_search_query("  Apple  ") == "Apple"
        assert validate_search_query("Microsoft Corporation") == "Microsoft Corporation"
    
    def test_validate_search_query_invalid(self):
        """Test validate_search_query with invalid inputs."""
        from app.api.v1.endpoints.search import validate_search_query
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException):
            validate_search_query("")
        
        with pytest.raises(HTTPException):
            validate_search_query("   ")
        
        with pytest.raises(HTTPException):
            validate_search_query("a" * 101)  # Too long
    
    def test_convert_security_type_to_asset_type(self):
        """Test security type to asset type conversion."""
        from app.api.v1.endpoints.search import convert_security_type_to_asset_type
        from app.schemas.securities import SecurityType
        
        result = convert_security_type_to_asset_type([SecurityType.STOCK, SecurityType.CRYPTO])
        assert AssetType.STOCK in result
        assert AssetType.CRYPTO in result
        
        result = convert_security_type_to_asset_type([SecurityType.ETF])
        assert AssetType.STOCK in result  # ETF maps to STOCK
        
        result = convert_security_type_to_asset_type([])
        assert result == [AssetType.STOCK]  # Default


class TestIntegration:
    """Integration tests."""
    
    def test_full_search_workflow(self, client, mock_market_data_service):
        """Test complete search workflow."""
        with patch('app.api.v1.endpoints.search.get_market_data_service') as mock_get_service:
            mock_get_service.return_value = mock_market_data_service
            
            # 1. Search for securities
            search_params = {
                "query": "Apple",
                "types": ["stock"],
                "limit": 5
            }
            
            search_response = client.post("/search/securities", json=search_params)
            assert search_response.status_code == 200
            
            # 2. Get suggestions
            suggestions_response = client.get("/search/suggestions?query=app&limit=3")
            assert suggestions_response.status_code == 200
            
            # 3. Get trending
            trending_response = client.get("/search/trending?asset_type=stock&limit=10")
            assert trending_response.status_code == 200
            
            # 4. Get popular
            popular_response = client.get("/search/popular?category=large_cap&limit=10")
            assert popular_response.status_code == 200
            
            # 5. Health check
            health_response = client.get("/search/health")
            assert health_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])