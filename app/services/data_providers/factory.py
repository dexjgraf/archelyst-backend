"""
Data provider factory with automatic failover and health monitoring.

Implements a factory pattern for managing multiple data providers with automatic
failover, health checking, and resilient data access across different sources.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Type, Callable, Union
from enum import Enum
import random
import json

from .base import (
    DataProvider, DataProviderType, ProviderHealth, ProviderRegistry,
    DataProviderError, DataProviderConnectionError, DataProviderRateLimitError,
    DataProviderNotFoundError
)
from ...core.config import settings

# ============================================================================
# Logger Setup
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# Factory Configuration and Types
# ============================================================================

class FailoverStrategy(Enum):
    """Failover strategies for provider selection."""
    ROUND_ROBIN = "round_robin"
    PRIORITY_ORDER = "priority_order"
    HEALTH_BASED = "health_based"
    LOAD_BALANCED = "load_balanced"


class ProviderStatus(Enum):
    """Provider status for health monitoring."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


# ============================================================================
# Provider Configuration Classes
# ============================================================================

class ProviderConfig:
    """Configuration for a single data provider."""
    
    def __init__(
        self,
        name: str,
        provider_class: Type[DataProvider],
        priority: int = 100,
        enabled: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        health_check_interval: int = 300,  # 5 minutes
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
        **kwargs
    ):
        """
        Initialize provider configuration.
        
        Args:
            name: Provider name
            provider_class: Provider class to instantiate
            priority: Provider priority (lower = higher priority)
            enabled: Whether provider is enabled
            max_retries: Maximum retry attempts
            retry_delay: Initial retry delay in seconds
            health_check_interval: Health check interval in seconds
            circuit_breaker_threshold: Failures before circuit breaker opens
            circuit_breaker_timeout: Circuit breaker timeout in seconds
            **kwargs: Additional provider-specific configuration
        """
        self.name = name
        self.provider_class = provider_class
        self.priority = priority
        self.enabled = enabled
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.health_check_interval = health_check_interval
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.config = kwargs
        
        # Runtime state
        self.status = ProviderStatus.UNKNOWN
        self.last_health_check = None
        self.consecutive_failures = 0
        self.circuit_breaker_opened_at = None
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.average_response_time = 0.0
    
    @property
    def is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self.circuit_breaker_opened_at:
            return False
        
        timeout_elapsed = (
            datetime.utcnow() - self.circuit_breaker_opened_at
        ).total_seconds() >= self.circuit_breaker_timeout
        
        if timeout_elapsed:
            self.circuit_breaker_opened_at = None
            self.consecutive_failures = 0
            return False
        
        return True
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100
    
    def record_success(self, response_time: float = None):
        """Record a successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        
        if response_time is not None:
            # Update average response time with exponential moving average
            alpha = 0.1
            self.average_response_time = (
                alpha * response_time + (1 - alpha) * self.average_response_time
            )
    
    def record_failure(self):
        """Record a failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        
        # Check if circuit breaker should open
        if (
            self.consecutive_failures >= self.circuit_breaker_threshold
            and not self.circuit_breaker_opened_at
        ):
            self.circuit_breaker_opened_at = datetime.utcnow()
            logger.warning(f"Circuit breaker opened for provider {self.name}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "name": self.name,
            "priority": self.priority,
            "enabled": self.enabled,
            "status": self.status.value,
            "success_rate": round(self.success_rate, 2),
            "average_response_time": round(self.average_response_time, 3),
            "total_requests": self.total_requests,
            "consecutive_failures": self.consecutive_failures,
            "circuit_breaker_open": self.is_circuit_breaker_open,
            "last_health_check": (
                self.last_health_check.isoformat() 
                if self.last_health_check else None
            )
        }


# ============================================================================
# Data Provider Factory
# ============================================================================

class DataProviderFactory:
    """
    Factory for managing multiple data providers with automatic failover.
    
    Provides resilient data access by managing multiple provider instances,
    monitoring their health, and automatically switching between providers
    when failures occur.
    """
    
    def __init__(
        self,
        failover_strategy: FailoverStrategy = FailoverStrategy.PRIORITY_ORDER,
        health_check_interval: int = 300,
        global_timeout: int = 30,
        max_concurrent_health_checks: int = 5
    ):
        """
        Initialize data provider factory.
        
        Args:
            failover_strategy: Strategy for provider selection
            health_check_interval: Default health check interval
            global_timeout: Global timeout for operations
            max_concurrent_health_checks: Max concurrent health checks
        """
        self.failover_strategy = failover_strategy
        self.health_check_interval = health_check_interval
        self.global_timeout = global_timeout
        self.max_concurrent_health_checks = max_concurrent_health_checks
        
        # Provider management
        self._providers: Dict[str, DataProvider] = {}
        self._provider_configs: Dict[str, ProviderConfig] = {}
        self._provider_instances: Dict[str, DataProvider] = {}
        
        # Health monitoring
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._health_monitoring_active = False
        
        # Statistics
        self._request_count = 0
        self._failover_count = 0
        self._last_reset_time = datetime.utcnow()
        
        # Provider selection state
        self._last_used_provider = None
        self._round_robin_index = 0
        
        logger.info(f"DataProviderFactory initialized with {failover_strategy.value} strategy")
    
    # ========================================================================
    # Provider Registration and Management
    # ========================================================================
    
    def register_provider(
        self,
        name: str,
        provider_class: Type[DataProvider],
        priority: int = 100,
        enabled: bool = True,
        **kwargs
    ) -> None:
        """
        Register a data provider with the factory.
        
        Args:
            name: Provider name
            provider_class: Provider class to instantiate
            priority: Provider priority (lower = higher priority)
            enabled: Whether provider is enabled
            **kwargs: Additional provider configuration
        """
        config = ProviderConfig(
            name=name,
            provider_class=provider_class,
            priority=priority,
            enabled=enabled,
            **kwargs
        )
        
        self._provider_configs[name] = config
        logger.info(f"Registered provider: {name} (priority: {priority})")
    
    async def initialize_provider(self, name: str) -> bool:
        """
        Initialize a specific provider instance.
        
        Args:
            name: Provider name
            
        Returns:
            bool: True if initialization successful
        """
        if name not in self._provider_configs:
            logger.error(f"Provider {name} not registered")
            return False
        
        config = self._provider_configs[name]
        
        try:
            # Create provider instance
            provider = config.provider_class(**config.config)
            self._provider_instances[name] = provider
            
            # Initial health check
            health = await provider.check_health()
            config.status = ProviderStatus.HEALTHY if health.is_healthy else ProviderStatus.UNHEALTHY
            config.last_health_check = datetime.utcnow()
            
            logger.info(f"Initialized provider: {name} (healthy: {health.is_healthy})")
            return health.is_healthy
            
        except Exception as e:
            logger.error(f"Failed to initialize provider {name}: {e}")
            config.status = ProviderStatus.UNHEALTHY
            return False
    
    async def initialize_all_providers(self) -> Dict[str, bool]:
        """
        Initialize all registered providers.
        
        Returns:
            Dict[str, bool]: Initialization results for each provider
        """
        results = {}
        
        for name in self._provider_configs:
            if self._provider_configs[name].enabled:
                results[name] = await self.initialize_provider(name)
            else:
                results[name] = False
                self._provider_configs[name].status = ProviderStatus.DISABLED
        
        logger.info(f"Initialized {sum(results.values())}/{len(results)} providers")
        return results
    
    def get_provider_instance(self, name: str) -> Optional[DataProvider]:
        """Get a provider instance by name."""
        return self._provider_instances.get(name)
    
    def get_all_provider_instances(self) -> Dict[str, DataProvider]:
        """Get all provider instances."""
        return self._provider_instances.copy()
    
    # ========================================================================
    # Provider Selection and Failover Logic
    # ========================================================================
    
    def _get_available_providers(self) -> List[str]:
        """Get list of available (enabled and healthy) providers."""
        available = []
        
        for name, config in self._provider_configs.items():
            if (
                config.enabled
                and config.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]
                and not config.is_circuit_breaker_open
                and name in self._provider_instances
            ):
                available.append(name)
        
        return available
    
    def _select_provider_by_priority(self) -> Optional[str]:
        """Select provider based on priority order."""
        available = self._get_available_providers()
        if not available:
            return None
        
        # Sort by priority (lower number = higher priority)
        sorted_providers = sorted(
            available,
            key=lambda name: self._provider_configs[name].priority
        )
        
        return sorted_providers[0]
    
    def _select_provider_by_round_robin(self) -> Optional[str]:
        """Select provider using round-robin strategy."""
        available = self._get_available_providers()
        if not available:
            return None
        
        # Sort by name for consistent ordering
        available.sort()
        
        if self._round_robin_index >= len(available):
            self._round_robin_index = 0
        
        selected = available[self._round_robin_index]
        self._round_robin_index = (self._round_robin_index + 1) % len(available)
        
        return selected
    
    def _select_provider_by_health(self) -> Optional[str]:
        """Select provider based on health metrics."""
        available = self._get_available_providers()
        if not available:
            return None
        
        # Score providers based on success rate and response time
        scored_providers = []
        
        for name in available:
            config = self._provider_configs[name]
            
            # Health score (0-100)
            success_weight = 0.7
            speed_weight = 0.3
            
            success_score = config.success_rate
            
            # Speed score (inverse of response time, normalized)
            max_response_time = 10.0  # Consider 10s as worst case
            speed_score = max(0, 100 - (config.average_response_time / max_response_time) * 100)
            
            total_score = success_weight * success_score + speed_weight * speed_score
            scored_providers.append((name, total_score))
        
        # Sort by score (highest first)
        scored_providers.sort(key=lambda x: x[1], reverse=True)
        
        return scored_providers[0][0]
    
    def _select_provider_by_load_balance(self) -> Optional[str]:
        """Select provider using load balancing."""
        available = self._get_available_providers()
        if not available:
            return None
        
        # Weight providers by inverse of their current load
        weighted_providers = []
        
        for name in available:
            config = self._provider_configs[name]
            
            # Simple load metric: requests per minute
            load = config.total_requests / max(1, (datetime.utcnow() - self._last_reset_time).total_seconds() / 60)
            weight = 1.0 / (load + 1.0)  # +1 to avoid division by zero
            
            weighted_providers.append((name, weight))
        
        # Weighted random selection
        total_weight = sum(weight for _, weight in weighted_providers)
        if total_weight == 0:
            return available[0]
        
        rand = random.uniform(0, total_weight)
        current_weight = 0
        
        for name, weight in weighted_providers:
            current_weight += weight
            if rand <= current_weight:
                return name
        
        return available[0]  # Fallback
    
    def select_provider(self) -> Optional[str]:
        """
        Select the best available provider based on the configured strategy.
        
        Returns:
            Optional[str]: Selected provider name or None if no providers available
        """
        if self.failover_strategy == FailoverStrategy.PRIORITY_ORDER:
            return self._select_provider_by_priority()
        elif self.failover_strategy == FailoverStrategy.ROUND_ROBIN:
            return self._select_provider_by_round_robin()
        elif self.failover_strategy == FailoverStrategy.HEALTH_BASED:
            return self._select_provider_by_health()
        elif self.failover_strategy == FailoverStrategy.LOAD_BALANCED:
            return self._select_provider_by_load_balance()
        else:
            return self._select_provider_by_priority()
    
    # ========================================================================
    # High-Level Data Access Methods
    # ========================================================================
    
    async def get_with_failover(
        self,
        method_name: str,
        *args,
        max_retries: int = None,
        timeout: float = None,
        **kwargs
    ) -> Any:
        """
        Execute a provider method with automatic failover.
        
        Args:
            method_name: Method name to call on provider
            *args: Method arguments
            max_retries: Maximum retry attempts across all providers
            timeout: Operation timeout
            **kwargs: Method keyword arguments
            
        Returns:
            Method result from successful provider
            
        Raises:
            DataProviderError: If all providers fail
        """
        max_retries = max_retries or 3
        timeout = timeout or self.global_timeout
        
        last_exception = None
        attempted_providers = set()
        
        for attempt in range(max_retries):
            # Select provider
            provider_name = self.select_provider()
            
            if not provider_name:
                raise DataProviderError(
                    "No available providers for request",
                    provider="factory"
                )
            
            # Skip if we've already tried this provider
            if provider_name in attempted_providers:
                available = [
                    name for name in self._get_available_providers()
                    if name not in attempted_providers
                ]
                if available:
                    provider_name = available[0]
                else:
                    break  # No more providers to try
            
            attempted_providers.add(provider_name)
            provider = self._provider_instances[provider_name]
            config = self._provider_configs[provider_name]
            
            try:
                # Execute method with timeout
                start_time = datetime.utcnow()
                
                method = getattr(provider, method_name)
                result = await asyncio.wait_for(
                    method(*args, **kwargs),
                    timeout=timeout
                )
                
                # Record success
                response_time = (datetime.utcnow() - start_time).total_seconds()
                config.record_success(response_time)
                
                self._request_count += 1
                self._last_used_provider = provider_name
                
                logger.debug(f"Request successful via {provider_name}")
                return result
                
            except asyncio.TimeoutError:
                config.record_failure()
                last_exception = DataProviderError(
                    f"Request timeout for provider {provider_name}",
                    provider=provider_name
                )
                logger.warning(f"Timeout for provider {provider_name}")
                
            except DataProviderRateLimitError as e:
                # Don't count rate limits as failures
                last_exception = e
                logger.warning(f"Rate limit exceeded for provider {provider_name}")
                
            except Exception as e:
                config.record_failure()
                last_exception = e
                logger.warning(f"Request failed for provider {provider_name}: {e}")
            
            # Increment failover count if we're trying another provider
            if attempt < max_retries - 1:
                self._failover_count += 1
        
        # All providers failed
        if last_exception:
            raise last_exception
        else:
            raise DataProviderError(
                f"All providers failed after {max_retries} attempts",
                provider="factory"
            )
    
    # ========================================================================
    # Convenient Data Access Methods
    # ========================================================================
    
    async def get_stock_quote(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Get stock quote with automatic failover."""
        return await self.get_with_failover("get_stock_quote", symbol, **kwargs)
    
    async def get_stock_profile(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Get stock profile with automatic failover."""
        return await self.get_with_failover("get_stock_profile", symbol, **kwargs)
    
    async def get_historical_data(self, symbol: str, period: str = "1year", **kwargs) -> List[Dict[str, Any]]:
        """Get historical data with automatic failover."""
        return await self.get_with_failover("get_historical_data", symbol, period, **kwargs)
    
    async def search_securities(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Search securities with automatic failover."""
        return await self.get_with_failover("search_securities", query, limit, **kwargs)
    
    async def get_crypto_quote(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Get crypto quote with automatic failover."""
        return await self.get_with_failover("get_crypto_quote", symbol, **kwargs)
    
    async def get_market_overview(self, **kwargs) -> Dict[str, Any]:
        """Get market overview with automatic failover."""
        return await self.get_with_failover("get_market_overview", **kwargs)
    
    # ========================================================================
    # Health Monitoring and Background Tasks
    # ========================================================================
    
    async def _health_check_provider(self, name: str) -> None:
        """Perform health check for a specific provider."""
        if name not in self._provider_instances:
            return
        
        provider = self._provider_instances[name]
        config = self._provider_configs[name]
        
        try:
            health = await provider.check_health()
            
            if health.is_healthy:
                if config.status == ProviderStatus.UNHEALTHY:
                    logger.info(f"Provider {name} recovered")
                config.status = ProviderStatus.HEALTHY
            else:
                if config.status == ProviderStatus.HEALTHY:
                    logger.warning(f"Provider {name} became unhealthy")
                config.status = ProviderStatus.UNHEALTHY
            
            config.last_health_check = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Health check failed for provider {name}: {e}")
            config.status = ProviderStatus.UNHEALTHY
            config.last_health_check = datetime.utcnow()
    
    async def run_health_monitoring(self) -> None:
        """Run continuous health monitoring for all providers."""
        if self._health_monitoring_active:
            return
        
        self._health_monitoring_active = True
        logger.info("Started health monitoring")
        
        try:
            while self._health_monitoring_active:
                # Check all enabled providers
                tasks = []
                
                for name, config in self._provider_configs.items():
                    if config.enabled and name in self._provider_instances:
                        # Check if health check is due
                        now = datetime.utcnow()
                        last_check = config.last_health_check or datetime.min
                        
                        if (now - last_check).total_seconds() >= config.health_check_interval:
                            task = asyncio.create_task(self._health_check_provider(name))
                            tasks.append(task)
                        
                        # Limit concurrent health checks
                        if len(tasks) >= self.max_concurrent_health_checks:
                            break
                
                # Wait for health checks to complete
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Wait before next round
                await asyncio.sleep(30)  # Check every 30 seconds for due health checks
                
        except asyncio.CancelledError:
            logger.info("Health monitoring cancelled")
        except Exception as e:
            logger.error(f"Health monitoring error: {e}")
        finally:
            self._health_monitoring_active = False
    
    def start_health_monitoring(self) -> None:
        """Start background health monitoring."""
        if not self._health_monitoring_active:
            task = asyncio.create_task(self.run_health_monitoring())
            self._health_check_tasks["monitor"] = task
    
    def stop_health_monitoring(self) -> None:
        """Stop background health monitoring."""
        self._health_monitoring_active = False
        
        for task in self._health_check_tasks.values():
            if not task.done():
                task.cancel()
        
        self._health_check_tasks.clear()
    
    # ========================================================================
    # Factory Status and Statistics
    # ========================================================================
    
    def get_factory_status(self) -> Dict[str, Any]:
        """Get comprehensive factory status and statistics."""
        uptime = (datetime.utcnow() - self._last_reset_time).total_seconds()
        
        return {
            "factory_info": {
                "failover_strategy": self.failover_strategy.value,
                "health_monitoring_active": self._health_monitoring_active,
                "uptime_seconds": round(uptime, 2),
                "last_used_provider": self._last_used_provider
            },
            "statistics": {
                "total_requests": self._request_count,
                "failover_count": self._failover_count,
                "requests_per_minute": round(self._request_count / max(uptime / 60, 1), 2),
                "failover_rate": round(self._failover_count / max(self._request_count, 1) * 100, 2)
            },
            "providers": {
                name: config.to_dict()
                for name, config in self._provider_configs.items()
            },
            "available_providers": self._get_available_providers(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def reset_statistics(self) -> None:
        """Reset factory statistics."""
        self._request_count = 0
        self._failover_count = 0
        self._last_reset_time = datetime.utcnow()
        
        # Reset provider statistics
        for config in self._provider_configs.values():
            config.total_requests = 0
            config.successful_requests = 0
            config.failed_requests = 0
            config.consecutive_failures = 0
            config.average_response_time = 0.0
        
        logger.info("Factory statistics reset")
    
    # ========================================================================
    # Context Manager and Cleanup
    # ========================================================================
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_all_providers()
        self.start_health_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.stop_health_monitoring()
        
        # Cleanup provider instances
        for provider in self._provider_instances.values():
            if hasattr(provider, '__aexit__'):
                try:
                    await provider.__aexit__(exc_type, exc_val, exc_tb)
                except Exception as e:
                    logger.warning(f"Error cleaning up provider: {e}")


# ============================================================================
# Factory Configuration Helper
# ============================================================================

def create_default_factory() -> DataProviderFactory:
    """
    Create a factory with default provider configuration based on settings.
    
    Returns:
        DataProviderFactory: Configured factory instance
    """
    factory = DataProviderFactory(
        failover_strategy=FailoverStrategy.PRIORITY_ORDER,
        health_check_interval=300,  # 5 minutes
        global_timeout=30
    )
    
    # Register providers based on configuration
    # Note: Actual provider classes will be imported when they're implemented
    
    provider_configs = [
        {
            "name": "fmp",
            "enabled": bool(settings.FMP_API_KEY),
            "priority": 10,  # Highest priority
            "api_key": settings.FMP_API_KEY,
            "base_url": settings.FMP_BASE_URL,
            "rate_limit": settings.FMP_RATE_LIMIT,
        },
        {
            "name": "yahoo_finance",
            "enabled": True,  # Always available
            "priority": 20,  # Medium priority
            "rate_limit": settings.YAHOO_FINANCE_RATE_LIMIT,
        },
        {
            "name": "alpha_vantage",
            "enabled": bool(settings.ALPHA_VANTAGE_API_KEY),
            "priority": 30,  # Lower priority
            "api_key": settings.ALPHA_VANTAGE_API_KEY,
            "base_url": settings.ALPHA_VANTAGE_BASE_URL,
            "rate_limit": settings.ALPHA_VANTAGE_RATE_LIMIT,
        }
    ]
    
    logger.info("Created default factory configuration")
    return factory


# ============================================================================
# Export All Public APIs
# ============================================================================

__all__ = [
    # Main factory class
    "DataProviderFactory",
    
    # Configuration classes
    "ProviderConfig",
    
    # Enums
    "FailoverStrategy",
    "ProviderStatus",
    
    # Factory creation
    "create_default_factory",
]