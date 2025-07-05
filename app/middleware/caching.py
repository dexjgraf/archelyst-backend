"""
Caching middleware for FastAPI requests.

Provides automatic response caching based on request patterns and cache levels.
"""

import hashlib
import json
import time
from typing import Dict, Optional, Set
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app.services.cache import CacheService, CacheLevel
import structlog

logger = structlog.get_logger(__name__)

class CachingMiddleware:
    """FastAPI middleware for automatic response caching."""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.cacheable_endpoints = self._get_cacheable_endpoints()
        self.cache_headers = {
            "Cache-Control": "public, max-age=60",
            "X-Cache-Status": "HIT"
        }
    
    def _get_cacheable_endpoints(self) -> Dict[str, Dict[str, any]]:
        """Define which endpoints should be cached and their cache configuration."""
        return {
            # Securities endpoints
            "/api/v1/securities/quote/{symbol}": {
                "level": CacheLevel.QUOTES,
                "vary_on": ["symbol"],
                "cache_control": "public, max-age=60"
            },
            "/api/v1/securities/profile/{symbol}": {
                "level": CacheLevel.PROFILES,
                "vary_on": ["symbol"],
                "cache_control": "public, max-age=3600"
            },
            "/api/v1/securities/chart/{symbol}": {
                "level": CacheLevel.HISTORICAL,
                "vary_on": ["symbol", "period", "interval"],
                "cache_control": "public, max-age=300"
            },
            
            # Market endpoints
            "/api/v1/market/overview": {
                "level": CacheLevel.MARKET_OVERVIEW,
                "vary_on": [],
                "cache_control": "public, max-age=300"
            },
            
            # Search endpoints
            "/api/v1/search": {
                "level": CacheLevel.SEARCH,
                "vary_on": ["query", "asset_type", "limit"],
                "cache_control": "public, max-age=900"
            },
            
            # AI endpoints
            "/api/v1/ai/market-insights": {
                "level": CacheLevel.AI_INSIGHTS,
                "vary_on": [],
                "cache_control": "public, max-age=1800"
            },
            "/api/v1/ai/stock-analysis/{symbol}": {
                "level": CacheLevel.AI_INSIGHTS,
                "vary_on": ["symbol"],
                "cache_control": "public, max-age=1800"
            }
        }
    
    def _get_cache_key_from_request(self, request: Request, config: Dict[str, any]) -> str:
        """Generate cache key from request."""
        # Extract path parameters
        path_params = getattr(request, "path_params", {})
        
        # Extract query parameters
        query_params = dict(request.query_params)
        
        # Build cache key components
        key_components = {
            "path": request.url.path,
            "method": request.method
        }
        
        # Add varying parameters
        for param in config["vary_on"]:
            if param in path_params:
                key_components[param] = path_params[param]
            elif param in query_params:
                key_components[param] = query_params[param]
        
        # Create hash of components
        key_string = json.dumps(key_components, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"response_{key_hash}"
    
    def _should_cache_response(self, response: Response) -> bool:
        """Determine if response should be cached."""
        # Only cache successful responses
        if response.status_code != 200:
            return False
        
        # Don't cache responses with errors
        if hasattr(response, 'body'):
            try:
                body = json.loads(response.body)
                if isinstance(body, dict) and 'error' in body:
                    return False
            except:
                pass
        
        return True
    
    def _get_endpoint_config(self, path: str) -> Optional[Dict[str, any]]:
        """Get cache configuration for endpoint."""
        # Try exact match first
        if path in self.cacheable_endpoints:
            return self.cacheable_endpoints[path]
        
        # Try pattern matching for parameterized paths
        for pattern, config in self.cacheable_endpoints.items():
            if self._path_matches_pattern(path, pattern):
                return config
        
        return None
    
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern with parameters."""
        path_parts = path.split('/')
        pattern_parts = pattern.split('/')
        
        if len(path_parts) != len(pattern_parts):
            return False
        
        for path_part, pattern_part in zip(path_parts, pattern_parts):
            # Skip parameter placeholders
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                continue
            # Must match exactly
            if path_part != pattern_part:
                return False
        
        return True
    
    async def __call__(self, request: Request, call_next):
        """Process request through caching middleware."""
        # Only handle GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Get cache configuration for this endpoint
        config = self._get_endpoint_config(request.url.path)
        if not config:
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._get_cache_key_from_request(request, config)
        provider = getattr(request.state, "provider", "middleware")
        
        # Try to get cached response
        try:
            cached_response = await self.cache_service.get(
                config["level"], 
                provider, 
                cache_key
            )
            
            if cached_response is not None:
                logger.debug(
                    "Cache hit for request",
                    path=request.url.path,
                    cache_key=cache_key,
                    level=config["level"].value
                )
                
                # Return cached response
                response = JSONResponse(
                    content=cached_response,
                    headers={
                        "X-Cache-Status": "HIT",
                        "X-Cache-Level": config["level"].value,
                        "Cache-Control": config["cache_control"]
                    }
                )
                return response
        
        except Exception as e:
            logger.error("Cache retrieval error", error=str(e))
        
        # Cache miss - call next middleware/endpoint
        response = await call_next(request)
        
        # Cache the response if appropriate
        if self._should_cache_response(response):
            try:
                # Extract response body
                response_body = None
                if hasattr(response, 'body'):
                    response_body = json.loads(response.body)
                elif isinstance(response, JSONResponse):
                    response_body = response.body
                
                if response_body is not None:
                    await self.cache_service.set(
                        config["level"],
                        provider,
                        cache_key,
                        response_body
                    )
                    
                    logger.debug(
                        "Response cached",
                        path=request.url.path,
                        cache_key=cache_key,
                        level=config["level"].value
                    )
                    
                    # Add cache headers
                    response.headers["X-Cache-Status"] = "MISS"
                    response.headers["X-Cache-Level"] = config["level"].value
                    response.headers["Cache-Control"] = config["cache_control"]
            
            except Exception as e:
                logger.error("Cache storage error", error=str(e))
        
        return response


class CacheControlMiddleware:
    """Middleware for setting cache control headers."""
    
    def __init__(self):
        self.default_headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        
        self.endpoint_cache_rules = {
            "/api/v1/securities/quote": "public, max-age=60",
            "/api/v1/securities/profile": "public, max-age=3600",
            "/api/v1/securities/chart": "public, max-age=300",
            "/api/v1/market/overview": "public, max-age=300",
            "/api/v1/search": "public, max-age=900",
            "/api/v1/ai": "public, max-age=1800",
            "/health": "public, max-age=30",
            "/docs": "public, max-age=86400",
            "/openapi.json": "public, max-age=86400"
        }
    
    async def __call__(self, request: Request, call_next):
        """Add appropriate cache control headers."""
        response = await call_next(request)
        
        # Find matching cache rule
        cache_control = None
        for pattern, rule in self.endpoint_cache_rules.items():
            if request.url.path.startswith(pattern):
                cache_control = rule
                break
        
        # Set cache control header
        if cache_control:
            response.headers["Cache-Control"] = cache_control
        else:
            # Apply default no-cache headers for sensitive endpoints
            for header, value in self.default_headers.items():
                response.headers[header] = value
        
        # Add cache timestamp
        response.headers["X-Cache-Timestamp"] = str(int(time.time()))
        
        return response


# Utility functions for cache management
async def invalidate_cache_for_symbol(cache_service: CacheService, symbol: str, provider: str = "*"):
    """Invalidate all cached data for a specific symbol."""
    levels_to_invalidate = [CacheLevel.QUOTES, CacheLevel.PROFILES, CacheLevel.HISTORICAL]
    total_deleted = 0
    
    for level in levels_to_invalidate:
        if provider == "*":
            # Invalidate for all providers
            providers = ["fmp", "yahoo", "alpha_vantage", "polygon"]
            for prov in providers:
                deleted = await cache_service.invalidate_pattern(level, prov, symbol)
                total_deleted += deleted
        else:
            deleted = await cache_service.invalidate_pattern(level, provider, symbol)
            total_deleted += deleted
    
    logger.info(
        "Cache invalidated for symbol",
        symbol=symbol,
        provider=provider,
        keys_deleted=total_deleted
    )
    
    return total_deleted


async def invalidate_market_cache(cache_service: CacheService):
    """Invalidate market overview and general market data cache."""
    levels_to_invalidate = [CacheLevel.MARKET_OVERVIEW, CacheLevel.REAL_TIME]
    total_deleted = 0
    
    for level in levels_to_invalidate:
        providers = ["fmp", "yahoo", "alpha_vantage", "polygon"]
        for provider in providers:
            deleted = await cache_service.invalidate_pattern(level, provider, "*")
            total_deleted += deleted
    
    logger.info("Market cache invalidated", keys_deleted=total_deleted)
    return total_deleted


# FastAPI dependency
async def get_caching_middleware() -> CachingMiddleware:
    """Get caching middleware instance."""
    from app.services.cache import get_cache_service
    
    cache_service = await get_cache_service()
    return CachingMiddleware(cache_service)