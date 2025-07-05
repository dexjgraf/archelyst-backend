"""
Rate limiting service for data providers.

Provides Redis-based rate limiting with sliding window algorithm and provider-specific limits.
"""

import time
import asyncio
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.core.config import Settings
import structlog

logger = structlog.get_logger(__name__)

class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""
    
    def __init__(self, redis_client: redis.Redis, settings: Settings):
        self.redis = redis_client
        self.settings = settings
        self.rate_limits = self._get_provider_limits()
        
    def _get_provider_limits(self) -> Dict[str, Dict[str, int]]:
        """Get rate limits for each data provider."""
        return {
            "fmp": {
                "requests_per_minute": 300,
                "requests_per_hour": 5000,
                "requests_per_day": 25000,
                "burst_limit": 10
            },
            "yahoo": {
                "requests_per_minute": 100,
                "requests_per_hour": 2000,
                "requests_per_day": 10000,
                "burst_limit": 5
            },
            "alpha_vantage": {
                "requests_per_minute": 5,
                "requests_per_hour": 500,
                "requests_per_day": 500,
                "burst_limit": 2
            },
            "polygon": {
                "requests_per_minute": 200,
                "requests_per_hour": 10000,
                "requests_per_day": 50000,
                "burst_limit": 8
            }
        }
    
    async def is_allowed(self, provider: str, endpoint: str = "default") -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed based on rate limits.
        
        Args:
            provider: Data provider name
            endpoint: Specific endpoint (for endpoint-specific limits)
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        if provider not in self.rate_limits:
            logger.warning("Unknown provider for rate limiting", provider=provider)
            return True, {}
            
        limits = self.rate_limits[provider]
        key_base = f"rate_limit:{provider}:{endpoint}"
        
        # Check all time windows
        windows = [
            ("minute", 60, limits["requests_per_minute"]),
            ("hour", 3600, limits["requests_per_hour"]),
            ("day", 86400, limits["requests_per_day"])
        ]
        
        rate_limit_info = {
            "provider": provider,
            "endpoint": endpoint,
            "limits": limits,
            "current_usage": {},
            "reset_times": {},
            "allowed": True
        }
        
        for window_name, window_seconds, limit in windows:
            key = f"{key_base}:{window_name}"
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            # Use sliding window algorithm
            pipe = self.redis.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request timestamp
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiry
            pipe.expire(key, window_seconds)
            
            results = await pipe.execute()
            current_count = results[1]
            
            rate_limit_info["current_usage"][window_name] = current_count
            rate_limit_info["reset_times"][window_name] = current_time + window_seconds
            
            if current_count >= limit:
                rate_limit_info["allowed"] = False
                rate_limit_info["exceeded_window"] = window_name
                rate_limit_info["retry_after"] = window_seconds
                
                logger.warning(
                    "Rate limit exceeded",
                    provider=provider,
                    endpoint=endpoint,
                    window=window_name,
                    current=current_count,
                    limit=limit
                )
                
                return False, rate_limit_info
        
        # Check burst limit
        burst_key = f"{key_base}:burst"
        burst_window = 10  # 10 seconds
        burst_start = current_time - burst_window
        
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(burst_key, 0, burst_start)
        pipe.zcard(burst_key)
        pipe.zadd(burst_key, {str(current_time): current_time})
        pipe.expire(burst_key, burst_window)
        
        burst_results = await pipe.execute()
        burst_count = burst_results[1]
        
        rate_limit_info["current_usage"]["burst"] = burst_count
        rate_limit_info["reset_times"]["burst"] = current_time + burst_window
        
        if burst_count >= limits["burst_limit"]:
            rate_limit_info["allowed"] = False
            rate_limit_info["exceeded_window"] = "burst"
            rate_limit_info["retry_after"] = burst_window
            
            logger.warning(
                "Burst rate limit exceeded",
                provider=provider,
                endpoint=endpoint,
                current=burst_count,
                limit=limits["burst_limit"]
            )
            
            return False, rate_limit_info
        
        logger.debug(
            "Rate limit check passed",
            provider=provider,
            endpoint=endpoint,
            usage=rate_limit_info["current_usage"]
        )
        
        return True, rate_limit_info
    
    async def get_rate_limit_status(self, provider: str) -> Dict[str, any]:
        """Get current rate limit status for a provider."""
        if provider not in self.rate_limits:
            return {}
            
        limits = self.rate_limits[provider]
        key_base = f"rate_limit:{provider}:default"
        current_time = int(time.time())
        
        status = {
            "provider": provider,
            "limits": limits,
            "current_usage": {},
            "reset_times": {},
            "utilization_percent": {}
        }
        
        windows = [
            ("minute", 60, limits["requests_per_minute"]),
            ("hour", 3600, limits["requests_per_hour"]),
            ("day", 86400, limits["requests_per_day"]),
            ("burst", 10, limits["burst_limit"])
        ]
        
        for window_name, window_seconds, limit in windows:
            key = f"{key_base}:{window_name}"
            window_start = current_time - window_seconds
            
            # Clean and count
            await self.redis.zremrangebyscore(key, 0, window_start)
            current_count = await self.redis.zcard(key)
            
            status["current_usage"][window_name] = current_count
            status["reset_times"][window_name] = current_time + window_seconds
            status["utilization_percent"][window_name] = (current_count / limit) * 100 if limit > 0 else 0
        
        return status
    
    async def reset_rate_limits(self, provider: str) -> bool:
        """Reset rate limits for a provider (admin function)."""
        if provider not in self.rate_limits:
            return False
            
        pattern = f"rate_limit:{provider}:*"
        keys = []
        
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            await self.redis.delete(*keys)
            logger.info("Rate limits reset", provider=provider, keys_deleted=len(keys))
        
        return True
    
    async def get_all_provider_status(self) -> Dict[str, Dict[str, any]]:
        """Get rate limit status for all providers."""
        status = {}
        
        for provider in self.rate_limits.keys():
            status[provider] = await self.get_rate_limit_status(provider)
        
        return status


class RateLimitMiddleware:
    """FastAPI middleware for automatic rate limiting."""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        
    async def __call__(self, request, call_next):
        """Process request through rate limiter."""
        # Extract provider from request if available
        provider = getattr(request.state, "provider", "default")
        endpoint = request.url.path
        
        # Check rate limit
        allowed, rate_info = await self.rate_limiter.is_allowed(provider, endpoint)
        
        if not allowed:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "provider": provider,
                    "retry_after": rate_info.get("retry_after", 60),
                    "current_usage": rate_info.get("current_usage", {}),
                    "limits": rate_info.get("limits", {})
                },
                headers={
                    "Retry-After": str(rate_info.get("retry_after", 60)),
                    "X-RateLimit-Provider": provider,
                    "X-RateLimit-Exceeded": rate_info.get("exceeded_window", "unknown")
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        if rate_info:
            response.headers["X-RateLimit-Provider"] = provider
            response.headers["X-RateLimit-Remaining"] = str(
                rate_info.get("limits", {}).get("requests_per_minute", 0) - 
                rate_info.get("current_usage", {}).get("minute", 0)
            )
            response.headers["X-RateLimit-Reset"] = str(
                rate_info.get("reset_times", {}).get("minute", 0)
            )
        
        return response


# Dependency for FastAPI
async def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance."""
    from app.core.deps import get_redis, get_settings
    
    redis_client = await get_redis()
    settings = get_settings()
    
    return RateLimiter(redis_client, settings)