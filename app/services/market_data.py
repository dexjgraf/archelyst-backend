"""
Market Data Service - Orchestration Layer

High-level market data service that orchestrates multiple providers with intelligent 
failover, data quality scoring, anomaly detection, and aggregation capabilities.
"""

import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import structlog

from ..schemas.market_data import (
    # Request models
    QuoteRequest, ProfileRequest, HistoricalRequest, SearchRequest, MarketOverviewRequest,
    # Response models  
    QuoteResponse, ProfileResponse, HistoricalResponse, SearchResponse, MarketOverviewResponse,
    SystemHealthResponse,
    # Data models
    QuoteData, ProfileData, HistoricalData, SecuritySearchResult, MarketOverviewData,
    # Quality models
    DataQualityMetrics, AnomalyDetection, DataProvenance,
    # Enums
    AssetType, DataQuality, DataSource
)
from .data_providers.factory import DataProviderFactory, FailoverStrategy, ProviderStatus
from .data_providers.fmp import FMPProvider
from .data_providers.yfinance import YahooFinanceProvider
from .cache import CacheService, CacheLevel
from .rate_limiter import RateLimiter
from ..core.config import Settings

logger = structlog.get_logger(__name__)

class MarketDataService:
    """
    High-level market data orchestration service.
    
    Provides intelligent data aggregation, quality scoring, anomaly detection,
    and seamless failover across multiple data providers.
    """
    
    def __init__(
        self,
        settings: Settings,
        cache_service: CacheService,
        rate_limiter: RateLimiter,
        failover_strategy: FailoverStrategy = FailoverStrategy.HEALTH_BASED
    ):
        """
        Initialize market data service.
        
        Args:
            settings: Application settings
            cache_service: Cache service instance
            rate_limiter: Rate limiter instance
            failover_strategy: Provider failover strategy
        """
        self.settings = settings
        self.cache_service = cache_service
        self.rate_limiter = rate_limiter
        
        # Initialize provider factory
        self.factory = DataProviderFactory(
            failover_strategy=failover_strategy,
            health_check_interval=300,  # 5 minutes
            global_timeout=30
        )
        
        # Register providers
        self._register_providers()
        
        # Service state
        self._initialized = False
        self._start_time = datetime.now()
        
        # Data quality thresholds
        self.quality_thresholds = {
            DataQuality.EXCELLENT: 95.0,
            DataQuality.GOOD: 85.0,
            DataQuality.FAIR: 70.0,
            DataQuality.POOR: 50.0,
            DataQuality.UNRELIABLE: 0.0
        }
        
        # Anomaly detection settings
        self.anomaly_detection_enabled = True
        self.price_change_threshold = 20.0  # 20% price change threshold
        self.volume_spike_threshold = 5.0   # 5x normal volume threshold
        
    def _register_providers(self):
        """Register available data providers with factory."""
        # Register FMP provider
        if hasattr(self.settings, 'fmp_api_key') and self.settings.fmp_api_key:
            self.factory.register_provider(
                name="fmp",
                provider_class=FMPProvider,
                priority=10,  # Highest priority
                enabled=True,
                settings=self.settings,
                cache_service=self.cache_service,
                rate_limiter=self.rate_limiter
            )
            logger.info("Registered FMP provider")
        
        # Register Yahoo Finance provider (always available)
        self.factory.register_provider(
            name="yahoo",
            provider_class=YahooFinanceProvider,
            priority=20,  # Medium priority
            enabled=True,
            settings=self.settings,
            cache_service=self.cache_service,
            rate_limiter=self.rate_limiter
        )
        logger.info("Registered Yahoo Finance provider")
    
    async def initialize(self) -> bool:
        """
        Initialize the market data service.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Initialize all providers
            init_results = await self.factory.initialize_all_providers()
            
            # Start health monitoring
            self.factory.start_health_monitoring()
            
            self._initialized = True
            healthy_providers = sum(1 for success in init_results.values() if success)
            
            logger.info(
                "Market data service initialized",
                healthy_providers=healthy_providers,
                total_providers=len(init_results)
            )
            
            return healthy_providers > 0
            
        except Exception as e:
            logger.error("Failed to initialize market data service", error=str(e))
            return False
    
    async def shutdown(self):
        """Shutdown the market data service."""
        try:
            self.factory.stop_health_monitoring()
            
            # Cleanup provider instances
            for provider in self.factory.get_all_provider_instances().values():
                if hasattr(provider, 'close'):
                    await provider.close()
            
            self._initialized = False
            logger.info("Market data service shutdown")
            
        except Exception as e:
            logger.error("Error during service shutdown", error=str(e))
    
    def _calculate_data_quality(
        self,
        data: Dict[str, Any],
        provider: str,
        request_time: float,
        cache_hit: bool = False
    ) -> DataQualityMetrics:
        """
        Calculate data quality metrics.
        
        Args:
            data: Response data
            provider: Provider name
            request_time: Request processing time
            cache_hit: Whether data came from cache
            
        Returns:
            DataQualityMetrics: Quality assessment
        """
        # Completeness - check for required fields
        required_fields = ["symbol", "price"] if "price" in str(data) else ["symbol"]
        present_fields = sum(1 for field in required_fields if field in data and data[field] is not None)
        completeness_score = (present_fields / len(required_fields)) * 100 if required_fields else 100
        
        # Freshness - based on data age and cache status
        freshness_score = 100.0 if not cache_hit else max(50.0, 100.0 - (request_time * 10))
        
        # Accuracy - based on provider reliability and data validation
        provider_scores = {"fmp": 95.0, "yahoo": 85.0, "alpha_vantage": 90.0}
        accuracy_score = provider_scores.get(provider, 80.0)
        
        # Consistency - placeholder (would compare across providers in real implementation)
        consistency_score = 90.0
        
        # Overall score
        overall_score = (
            completeness_score * 0.3 +
            freshness_score * 0.25 +
            accuracy_score * 0.25 +
            consistency_score * 0.2
        )
        
        # Determine quality level
        quality_level = DataQuality.UNRELIABLE
        for level, threshold in sorted(self.quality_thresholds.items(), key=lambda x: x[1], reverse=True):
            if overall_score >= threshold:
                quality_level = level
                break
        
        return DataQualityMetrics(
            completeness_score=completeness_score,
            freshness_score=freshness_score,
            accuracy_score=accuracy_score,
            consistency_score=consistency_score,
            overall_score=overall_score,
            quality_level=quality_level
        )
    
    def _detect_anomalies(self, data: Dict[str, Any], historical_data: Optional[List] = None) -> AnomalyDetection:
        """
        Detect data anomalies.
        
        Args:
            data: Current data point
            historical_data: Historical data for comparison
            
        Returns:
            AnomalyDetection: Anomaly detection results
        """
        if not self.anomaly_detection_enabled:
            return AnomalyDetection(
                has_anomalies=False,
                anomaly_types=[],
                confidence_score=0.0,
                details={}
            )
        
        anomalies = []
        confidence_scores = []
        details = {}
        
        # Price change anomaly detection
        if "change_percent" in data:
            change_percent = abs(data["change_percent"])
            if change_percent > self.price_change_threshold:
                anomalies.append("extreme_price_change")
                confidence_scores.append(min(100.0, change_percent / self.price_change_threshold * 50))
                details["extreme_price_change"] = {
                    "change_percent": data["change_percent"],
                    "threshold": self.price_change_threshold
                }
        
        # Volume spike detection
        if "volume" in data and historical_data:
            try:
                historical_volumes = [item.get("volume", 0) for item in historical_data[-30:]]  # Last 30 days
                if historical_volumes:
                    avg_volume = statistics.mean(historical_volumes)
                    current_volume = data["volume"]
                    if current_volume > avg_volume * self.volume_spike_threshold:
                        anomalies.append("volume_spike")
                        confidence_scores.append(min(100.0, current_volume / avg_volume / self.volume_spike_threshold * 50))
                        details["volume_spike"] = {
                            "current_volume": current_volume,
                            "average_volume": avg_volume,
                            "spike_ratio": current_volume / avg_volume
                        }
            except (TypeError, ZeroDivisionError):
                pass
        
        # Data consistency checks
        if "price" in data and "open" in data and "high" in data and "low" in data:
            price, open_price, high, low = data["price"], data["open"], data["high"], data["low"]
            if not (low <= price <= high and low <= open_price <= high):
                anomalies.append("price_inconsistency")
                confidence_scores.append(90.0)
                details["price_inconsistency"] = {
                    "price": price,
                    "open": open_price,
                    "high": high,
                    "low": low
                }
        
        # Calculate overall confidence
        overall_confidence = statistics.mean(confidence_scores) if confidence_scores else 0.0
        
        return AnomalyDetection(
            has_anomalies=len(anomalies) > 0,
            anomaly_types=anomalies,
            confidence_score=overall_confidence,
            details=details
        )
    
    def _create_data_provenance(
        self,
        provider: str,
        processing_time: float,
        cache_hit: bool = False,
        cache_age: Optional[float] = None,
        fallback_sources: List[str] = None
    ) -> DataProvenance:
        """Create data provenance information."""
        # Get provider health status
        provider_health = {}
        factory_status = self.factory.get_factory_status()
        for name, provider_info in factory_status.get("providers", {}).items():
            provider_health[name] = provider_info.get("status", "unknown")
        
        try:
            primary_source = DataSource(provider)
        except ValueError:
            primary_source = DataSource.YAHOO  # Default fallback
            
        try:
            fallback_data_sources = [DataSource(src) for src in (fallback_sources or [])]
        except ValueError:
            fallback_data_sources = []
        
        return DataProvenance(
            primary_source=primary_source,
            fallback_sources=fallback_data_sources,
            processing_time_ms=processing_time * 1000,
            cache_hit=cache_hit,
            cache_age_seconds=cache_age,
            provider_health=provider_health
        )
    
    # Core data retrieval methods
    
    async def get_quote(self, request: QuoteRequest) -> QuoteResponse:
        """
        Get stock/crypto quote with intelligent provider selection and quality scoring.
        
        Args:
            request: Quote request parameters
            
        Returns:
            QuoteResponse: Quote data with quality metrics
        """
        start_time = time.time()
        
        try:
            # Select appropriate method based on asset type
            if request.asset_type == AssetType.CRYPTO:
                provider_response = await self.factory.get_crypto_quote(request.symbol)
            else:
                provider_response = await self.factory.get_stock_quote(request.symbol)
            
            processing_time = time.time() - start_time
            
            if provider_response.success:
                # Calculate data quality
                data_quality = self._calculate_data_quality(
                    provider_response.data,
                    provider_response.provider,
                    processing_time,
                    provider_response.metadata.get("cached", False)
                )
                
                # Detect anomalies
                anomaly_detection = self._detect_anomalies(provider_response.data)
                
                # Create provenance
                provenance = self._create_data_provenance(
                    provider_response.provider,
                    processing_time,
                    provider_response.metadata.get("cached", False)
                )
                
                # Convert to schema model
                quote_data = QuoteData(**provider_response.data)
                
                return QuoteResponse(
                    success=True,
                    symbol=request.symbol,
                    timestamp=datetime.now(),
                    data=quote_data,
                    data_quality=data_quality,
                    anomaly_detection=anomaly_detection,
                    provenance=provenance
                )
            else:
                return QuoteResponse(
                    success=False,
                    symbol=request.symbol,
                    timestamp=datetime.now(),
                    data=None,
                    data_quality=DataQualityMetrics(
                        completeness_score=0, freshness_score=0, accuracy_score=0,
                        consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
                    ),
                    provenance=self._create_data_provenance("unknown", processing_time),
                    error=provider_response.error
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error("Quote request failed", symbol=request.symbol, error=str(e))
            
            return QuoteResponse(
                success=False,
                symbol=request.symbol,
                timestamp=datetime.now(),
                data=None,
                data_quality=DataQualityMetrics(
                    completeness_score=0, freshness_score=0, accuracy_score=0,
                    consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
                ),
                provenance=self._create_data_provenance("unknown", processing_time),
                error=str(e)
            )
    
    async def get_profile(self, request: ProfileRequest) -> ProfileResponse:
        """
        Get company profile with data quality assessment.
        
        Args:
            request: Profile request parameters
            
        Returns:
            ProfileResponse: Profile data with quality metrics
        """
        start_time = time.time()
        
        try:
            provider_response = await self.factory.get_stock_profile(request.symbol)
            processing_time = time.time() - start_time
            
            if provider_response.success:
                # Calculate data quality
                data_quality = self._calculate_data_quality(
                    provider_response.data,
                    provider_response.provider,
                    processing_time,
                    provider_response.metadata.get("cached", False)
                )
                
                # Create provenance
                provenance = self._create_data_provenance(
                    provider_response.provider,
                    processing_time,
                    provider_response.metadata.get("cached", False)
                )
                
                # Convert to schema model
                profile_data = ProfileData(**provider_response.data)
                
                return ProfileResponse(
                    success=True,
                    symbol=request.symbol,
                    timestamp=datetime.now(),
                    data=profile_data,
                    data_quality=data_quality,
                    provenance=provenance
                )
            else:
                return ProfileResponse(
                    success=False,
                    symbol=request.symbol,
                    timestamp=datetime.now(),
                    data=None,
                    data_quality=DataQualityMetrics(
                        completeness_score=0, freshness_score=0, accuracy_score=0,
                        consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
                    ),
                    provenance=self._create_data_provenance("unknown", processing_time),
                    error=provider_response.error
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error("Profile request failed", symbol=request.symbol, error=str(e))
            
            return ProfileResponse(
                success=False,
                symbol=request.symbol,
                timestamp=datetime.now(),
                data=None,
                data_quality=DataQualityMetrics(
                    completeness_score=0, freshness_score=0, accuracy_score=0,
                    consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
                ),
                provenance=self._create_data_provenance("unknown", processing_time),
                error=str(e)
            )
    
    async def get_historical_data(self, request: HistoricalRequest) -> HistoricalResponse:
        """
        Get historical price data with quality assessment.
        
        Args:
            request: Historical data request parameters
            
        Returns:
            HistoricalResponse: Historical data with quality metrics
        """
        start_time = time.time()
        
        try:
            provider_response = await self.factory.get_historical_data(
                request.symbol, 
                request.period, 
                request.interval
            )
            processing_time = time.time() - start_time
            
            if provider_response.success:
                # Calculate data quality
                data_quality = self._calculate_data_quality(
                    provider_response.data,
                    provider_response.provider,
                    processing_time,
                    provider_response.metadata.get("cached", False)
                )
                
                # Anomaly detection on historical data
                historical_points = provider_response.data.get("data", [])
                anomaly_detection = self._detect_anomalies(
                    provider_response.data, 
                    historical_points
                )
                
                # Create provenance
                provenance = self._create_data_provenance(
                    provider_response.provider,
                    processing_time,
                    provider_response.metadata.get("cached", False)
                )
                
                # Convert to schema model
                historical_data = HistoricalData(**provider_response.data)
                
                return HistoricalResponse(
                    success=True,
                    symbol=request.symbol,
                    timestamp=datetime.now(),
                    data=historical_data,
                    data_quality=data_quality,
                    anomaly_detection=anomaly_detection,
                    provenance=provenance
                )
            else:
                return HistoricalResponse(
                    success=False,
                    symbol=request.symbol,
                    timestamp=datetime.now(),
                    data=None,
                    data_quality=DataQualityMetrics(
                        completeness_score=0, freshness_score=0, accuracy_score=0,
                        consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
                    ),
                    provenance=self._create_data_provenance("unknown", processing_time),
                    error=provider_response.error
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error("Historical data request failed", symbol=request.symbol, error=str(e))
            
            return HistoricalResponse(
                success=False,
                symbol=request.symbol,
                timestamp=datetime.now(),
                data=None,
                data_quality=DataQualityMetrics(
                    completeness_score=0, freshness_score=0, accuracy_score=0,
                    consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
                ),
                provenance=self._create_data_provenance("unknown", processing_time),
                error=str(e)
            )
    
    async def search_securities(self, request: SearchRequest) -> SearchResponse:
        """
        Search for securities across providers.
        
        Args:
            request: Search request parameters
            
        Returns:
            SearchResponse: Search results with quality metrics
        """
        start_time = time.time()
        
        try:
            provider_response = await self.factory.search_securities(
                request.query,
                request.asset_types[0].value if request.asset_types else "stock",
                request.limit
            )
            processing_time = time.time() - start_time
            
            if provider_response.success:
                # Calculate data quality
                data_quality = self._calculate_data_quality(
                    provider_response.data,
                    provider_response.provider,
                    processing_time,
                    provider_response.metadata.get("cached", False)
                )
                
                # Create provenance
                provenance = self._create_data_provenance(
                    provider_response.provider,
                    processing_time,
                    provider_response.metadata.get("cached", False)
                )
                
                # Convert to schema model
                # Note: This would need proper conversion from provider format to SearchData
                search_data = provider_response.data  # Simplified for now
                
                return SearchResponse(
                    success=True,
                    symbol=request.query,  # Use query as symbol for search
                    timestamp=datetime.now(),
                    data=search_data,
                    data_quality=data_quality,
                    provenance=provenance
                )
            else:
                return SearchResponse(
                    success=False,
                    symbol=request.query,
                    timestamp=datetime.now(),
                    data=None,
                    data_quality=DataQualityMetrics(
                        completeness_score=0, freshness_score=0, accuracy_score=0,
                        consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
                    ),
                    provenance=self._create_data_provenance("unknown", processing_time),
                    error=provider_response.error
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error("Search request failed", query=request.query, error=str(e))
            
            return SearchResponse(
                success=False,
                symbol=request.query,
                timestamp=datetime.now(),
                data=None,
                data_quality=DataQualityMetrics(
                    completeness_score=0, freshness_score=0, accuracy_score=0,
                    consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
                ),
                provenance=self._create_data_provenance("unknown", processing_time),
                error=str(e)
            )
    
    async def get_market_overview(self, request: MarketOverviewRequest) -> MarketOverviewResponse:
        """
        Get market overview with aggregated data.
        
        Args:
            request: Market overview request parameters
            
        Returns:
            MarketOverviewResponse: Market overview with quality metrics
        """
        start_time = time.time()
        
        try:
            provider_response = await self.factory.get_market_overview()
            processing_time = time.time() - start_time
            
            if provider_response.success:
                # Calculate data quality
                data_quality = self._calculate_data_quality(
                    provider_response.data,
                    provider_response.provider,
                    processing_time,
                    provider_response.metadata.get("cached", False)
                )
                
                # Create provenance
                provenance = self._create_data_provenance(
                    provider_response.provider,
                    processing_time,
                    provider_response.metadata.get("cached", False)
                )
                
                # Convert to schema model
                # Note: This would need proper conversion from provider format to MarketOverviewData
                overview_data = provider_response.data  # Simplified for now
                
                return MarketOverviewResponse(
                    success=True,
                    symbol="MARKET_OVERVIEW",
                    timestamp=datetime.now(),
                    data=overview_data,
                    data_quality=data_quality,
                    provenance=provenance
                )
            else:
                return MarketOverviewResponse(
                    success=False,
                    symbol="MARKET_OVERVIEW",
                    timestamp=datetime.now(),
                    data=None,
                    data_quality=DataQualityMetrics(
                        completeness_score=0, freshness_score=0, accuracy_score=0,
                        consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
                    ),
                    provenance=self._create_data_provenance("unknown", processing_time),
                    error=provider_response.error
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error("Market overview request failed", error=str(e))
            
            return MarketOverviewResponse(
                success=False,
                symbol="MARKET_OVERVIEW",
                timestamp=datetime.now(),
                data=None,
                data_quality=DataQualityMetrics(
                    completeness_score=0, freshness_score=0, accuracy_score=0,
                    consistency_score=0, overall_score=0, quality_level=DataQuality.UNRELIABLE
                ),
                provenance=self._create_data_provenance("unknown", processing_time),
                error=str(e)
            )
    
    # Health and monitoring methods
    
    async def get_system_health(self) -> SystemHealthResponse:
        """
        Get comprehensive system health status.
        
        Returns:
            SystemHealthResponse: System health information
        """
        try:
            factory_status = self.factory.get_factory_status()
            
            # Convert factory status to health response format
            # This would be implemented with proper schema conversion
            
            return SystemHealthResponse(
                success=True,
                health=factory_status,  # Simplified for now
                error=None
            )
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return SystemHealthResponse(
                success=False,
                health=None,
                error=str(e)
            )
    
    # Context manager support
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()

# Global service instance
_market_data_service: Optional[MarketDataService] = None

# Dependency injection helper
async def get_market_data_service() -> MarketDataService:
    """
    Factory function to create market data service instance.
    
    Returns:
        MarketDataService: Initialized service instance
    """
    global _market_data_service
    
    if _market_data_service is None:
        from ..core.config import settings
        
        # Create cache service
        cache_service = await CacheService.create(settings.REDIS_URL)
        
        # Create rate limiter  
        rate_limiter = RateLimiter()
        
        # Create and initialize market data service
        _market_data_service = MarketDataService(settings, cache_service, rate_limiter)
        await _market_data_service.initialize()
    
    return _market_data_service