"""
OpenAPI Examples Generator for Archelyst API Schemas

This module generates comprehensive OpenAPI/Swagger examples
for all API endpoints using the Pydantic schemas.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List

from .base import BaseResponse, ErrorDetail, ErrorType, PaginatedResponse, PaginationInfo
from .securities import (
    SecurityQuote, SecurityProfile, HistoricalData, OHLCVData,
    BatchQuoteData, SecuritySearchData, SecuritySearchResult,
    SecurityType, ExchangeCode, MarketStatus, TimeFrame
)
from .market import (
    MarketOverview, MarketSummary, IndexData, SectorPerformance,
    CommodityData, CryptoData, MarketMover, MarketMoversData,
    MarketRegion, IndexType, SectorCategory, CommodityType
)
from .users import (
    UserProfile, LoginRequest, TokenResponse, APIKey, UserPreferences,
    UserRole, AuthProvider, SubscriptionStatus, RiskTolerance
)
from .ai import (
    StockAnalysisData, MarketInsightData, SentimentAnalysisData,
    AIInsight, SentimentScore, AnalysisType, TimeHorizon, AIProvider
)


class OpenAPIExamples:
    """Generate OpenAPI examples for API documentation."""
    
    @staticmethod
    def security_quote_examples() -> Dict[str, Any]:
        """Generate OpenAPI examples for SecurityQuote endpoints."""
        
        # Success response example
        success_example = {
            "success": True,
            "message": "Quote retrieved successfully",
            "data": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "price": 192.53,
                "change": 3.47,
                "change_percent": 1.84,
                "volume": 52847392,
                "avg_volume": 68234567,
                "market_cap": 3020000000000,
                "pe_ratio": 28.45,
                "day_high": 194.12,
                "day_low": 190.85,
                "previous_close": 189.06,
                "open_price": 190.25,
                "week_52_high": 199.62,
                "week_52_low": 164.08,
                "exchange": "NASDAQ",
                "currency": "USD",
                "market_status": "open",
                "last_update": "2024-07-04T15:30:00Z",
                "extended_hours_price": 192.75,
                "extended_hours_change": 0.22
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_abc123xyz789"
        }
        
        # Error response example
        error_example = {
            "success": False,
            "error": {
                "code": 404,
                "message": "Symbol not found",
                "type": "not_found_error",
                "details": {
                    "symbol": "INVALID",
                    "suggestion": "Please check the symbol format (e.g., AAPL, MSFT)"
                },
                "trace_id": "trace_def456uvw012"
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_def456uvw012"
        }
        
        return {
            "get_quote_success": success_example,
            "get_quote_error": error_example
        }
    
    @staticmethod
    def batch_quotes_examples() -> Dict[str, Any]:
        """Generate OpenAPI examples for batch quotes endpoint."""
        
        # Request example
        request_example = {
            "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        }
        
        # Success response example
        success_example = {
            "success": True,
            "message": "Batch quotes retrieved successfully",
            "data": {
                "quotes": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "price": 192.53,
                        "change": 3.47,
                        "change_percent": 1.84,
                        "volume": 52847392,
                        "market_cap": 3020000000000,
                        "exchange": "NASDAQ",
                        "market_status": "open",
                        "last_update": "2024-07-04T15:30:00Z"
                    },
                    {
                        "symbol": "MSFT",
                        "name": "Microsoft Corporation",
                        "price": 447.25,
                        "change": 5.50,
                        "change_percent": 1.25,
                        "volume": 28456123,
                        "market_cap": 3320000000000,
                        "exchange": "NASDAQ",
                        "market_status": "open",
                        "last_update": "2024-07-04T15:30:00Z"
                    }
                ],
                "successful": 5,
                "failed": 0,
                "errors": []
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_batch123"
        }
        
        return {
            "batch_quotes_request": request_example,
            "batch_quotes_success": success_example
        }
    
    @staticmethod
    def market_overview_examples() -> Dict[str, Any]:
        """Generate OpenAPI examples for market overview endpoint."""
        
        success_example = {
            "success": True,
            "message": "Market overview retrieved successfully",
            "data": {
                "date": "2024-07-04",
                "market_status": "CLOSED",
                "session_info": {
                    "regular_hours": {"start": "09:30", "end": "16:00"},
                    "extended_hours": {"start": "04:00", "end": "20:00"},
                    "timezone": "America/New_York"
                },
                "summary": {
                    "total_market_cap": 52000000000000,
                    "trading_volume": 750000000000,
                    "advancing_stocks": 3247,
                    "declining_stocks": 1823,
                    "unchanged_stocks": 284,
                    "new_highs": 198,
                    "new_lows": 37,
                    "fear_greed_index": 67.5
                },
                "major_indices": [
                    {
                        "symbol": "^GSPC",
                        "name": "S&P 500",
                        "value": 5537.02,
                        "change": 15.87,
                        "change_percent": 0.29,
                        "previous_close": 5521.15,
                        "day_high": 5542.35,
                        "day_low": 5528.10,
                        "index_type": "broad_market",
                        "region": "US",
                        "last_update": "2024-07-04T16:00:00Z"
                    }
                ],
                "sector_performance": [
                    {
                        "sector": "Technology",
                        "change_percent": 1.23,
                        "market_cap": 15000000000000,
                        "volume": 125000000000,
                        "top_performers": ["AAPL", "MSFT", "GOOGL"],
                        "worst_performers": ["META", "NFLX", "CRM"]
                    }
                ],
                "market_movers": {
                    "top_gainers": ["NVDA", "AMD", "TSLA"],
                    "top_losers": ["INTC", "IBM", "T"],
                    "most_active": ["AAPL", "MSFT", "AMZN"]
                },
                "economic_indicators": {
                    "vix": 18.45,
                    "dxy": 104.23,
                    "ten_year_yield": 4.25
                }
            },
            "provider": {
                "name": "financial_data_api",
                "source": "Financial Data API",
                "timestamp": "2024-07-04T15:30:00Z",
                "cache_hit": False
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_market_overview"
        }
        
        return {
            "market_overview_success": success_example
        }
    
    @staticmethod
    def user_authentication_examples() -> Dict[str, Any]:
        """Generate OpenAPI examples for user authentication."""
        
        # Login request
        login_request = {
            "email": "john.doe@example.com",
            "password": "SecurePassword123!",
            "remember_me": True
        }
        
        # Login success response
        login_success = {
            "success": True,
            "message": "Login successful",
            "data": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "user_abc123xyz789",
                    "email": "john.doe@example.com",
                    "username": "john_trader",
                    "first_name": "John",
                    "last_name": "Doe",
                    "role": "premium",
                    "is_active": True,
                    "email_verified": True,
                    "subscription_status": "active",
                    "api_calls_used": 1247,
                    "api_calls_limit": 5000,
                    "created_at": "2024-01-15T10:30:00Z"
                }
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_login123"
        }
        
        # Authentication error
        auth_error = {
            "success": False,
            "error": {
                "code": 401,
                "message": "Invalid credentials",
                "type": "authentication_error",
                "details": {
                    "reason": "Email or password is incorrect",
                    "lockout_remaining": None
                }
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_login_fail"
        }
        
        return {
            "login_request": login_request,
            "login_success": login_success,
            "auth_error": auth_error
        }
    
    @staticmethod
    def ai_analysis_examples() -> Dict[str, Any]:
        """Generate OpenAPI examples for AI analysis endpoints."""
        
        # Stock analysis request
        analysis_request = {
            "symbol": "AAPL",
            "analysis_types": ["fundamental", "technical", "sentiment"],
            "time_horizon": "medium_term",
            "include_competitors": True,
            "include_news_sentiment": True,
            "custom_prompt": "Focus on AI and services revenue growth potential"
        }
        
        # Analysis success response
        analysis_success = {
            "success": True,
            "message": "Analysis completed successfully",
            "data": {
                "symbol": "AAPL",
                "company_name": "Apple Inc.",
                "overall_rating": "BUY",
                "sentiment": "bullish",
                "confidence_score": 0.823,
                "key_insights": [
                    {
                        "title": "Strong Technical Momentum",
                        "content": "RSI indicates oversold condition with potential for reversal",
                        "importance": "high",
                        "category": "technical",
                        "supporting_data": [
                            "RSI (14): 28.5 (oversold)",
                            "Price vs 50-day MA: +5.2%",
                            "Volume trend: +25% above average"
                        ],
                        "sentiment_impact": "bullish"
                    },
                    {
                        "title": "Solid Financial Fundamentals",
                        "content": "P/E ratio below industry average suggests potential undervaluation",
                        "importance": "high",
                        "category": "fundamental",
                        "supporting_data": [
                            "P/E: 18.5 vs industry 22.3",
                            "ROE: 24.7% (excellent)",
                            "Debt-to-equity: 0.35 (low)"
                        ],
                        "sentiment_impact": "bullish"
                    }
                ],
                "strengths": [
                    "Strong brand loyalty and ecosystem",
                    "High profit margins and cash generation",
                    "Innovation capability"
                ],
                "weaknesses": [
                    "High valuation compared to peers",
                    "Dependence on iPhone revenue"
                ],
                "opportunities": [
                    "AI integration across products",
                    "Services business expansion"
                ],
                "threats": [
                    "Economic slowdown",
                    "Increased competition"
                ],
                "executive_summary": "Apple demonstrates strong fundamentals with solid growth prospects in AI and services, though valuation remains elevated.",
                "time_horizon": "medium_term"
            },
            "ai_metadata": {
                "provider": "custom",
                "model_name": "archelyst-analyzer-v2",
                "model_version": "2.1.0",
                "analysis_timestamp": "2024-07-04T15:30:00Z",
                "processing_time_ms": 1250.0,
                "tokens_used": 850,
                "confidence_score": 0.823
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_analysis123"
        }
        
        return {
            "analysis_request": analysis_request,
            "analysis_success": analysis_success
        }
    
    @staticmethod
    def search_examples() -> Dict[str, Any]:
        """Generate OpenAPI examples for search endpoints."""
        
        # Search request
        search_request = {
            "query": "apple",
            "types": ["stock", "etf"],
            "exchanges": ["NASDAQ", "NYSE"],
            "sectors": ["Technology"],
            "min_market_cap": 1000000000,
            "max_market_cap": 5000000000000,
            "limit": 10
        }
        
        # Search success response
        search_success = {
            "success": True,
            "message": "Search completed successfully",
            "data": {
                "results": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "type": "stock",
                        "exchange": "NASDAQ",
                        "currency": "USD",
                        "sector": "Technology",
                        "industry": "Consumer Electronics",
                        "market_cap": 3020000000000,
                        "last_price": 192.53,
                        "relevance_score": 1.0
                    },
                    {
                        "symbol": "QQQ",
                        "name": "Invesco QQQ Trust",
                        "type": "etf",
                        "exchange": "NASDAQ",
                        "currency": "USD",
                        "market_cap": 200000000000,
                        "last_price": 485.23,
                        "relevance_score": 0.75
                    }
                ],
                "total_found": 2,
                "query": "apple",
                "execution_time_ms": 45.7
            },
            "provider": {
                "name": "search_engine",
                "source": "Securities Search API",
                "timestamp": "2024-07-04T15:30:00Z",
                "cache_hit": True
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_search123"
        }
        
        return {
            "search_request": search_request,
            "search_success": search_success
        }
    
    @staticmethod
    def error_examples() -> Dict[str, Any]:
        """Generate comprehensive error examples."""
        
        validation_error = {
            "success": False,
            "error": {
                "code": 400,
                "message": "Validation failed",
                "type": "validation_error",
                "details": {
                    "validation_errors": [
                        {
                            "field": "symbol",
                            "message": "Symbol must be 1-10 characters",
                            "type": "value_error",
                            "input": ""
                        },
                        {
                            "field": "price",
                            "message": "Price must be positive",
                            "type": "value_error",
                            "input": -100
                        }
                    ],
                    "error_count": 2
                },
                "trace_id": "trace_validation_error"
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_validation_fail"
        }
        
        rate_limit_error = {
            "success": False,
            "error": {
                "code": 429,
                "message": "Rate limit exceeded",
                "type": "rate_limit_error",
                "details": {
                    "limit": 1000,
                    "used": 1001,
                    "reset_time": "2024-07-04T16:00:00Z",
                    "retry_after": 1800
                }
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_rate_limit"
        }
        
        provider_error = {
            "success": False,
            "error": {
                "code": 503,
                "message": "External data provider unavailable",
                "type": "provider_error",
                "details": {
                    "provider": "financial_data_api",
                    "provider_status": "down",
                    "estimated_recovery": "2024-07-04T16:30:00Z"
                }
            },
            "timestamp": "2024-07-04T15:30:00Z",
            "request_id": "req_provider_error"
        }
        
        return {
            "validation_error": validation_error,
            "rate_limit_error": rate_limit_error,
            "provider_error": provider_error
        }
    
    @staticmethod
    def generate_all_examples() -> Dict[str, Any]:
        """Generate all OpenAPI examples for comprehensive documentation."""
        
        return {
            "securities": {
                **OpenAPIExamples.security_quote_examples(),
                **OpenAPIExamples.batch_quotes_examples(),
                **OpenAPIExamples.search_examples()
            },
            "market": {
                **OpenAPIExamples.market_overview_examples()
            },
            "users": {
                **OpenAPIExamples.user_authentication_examples()
            },
            "ai": {
                **OpenAPIExamples.ai_analysis_examples()
            },
            "errors": {
                **OpenAPIExamples.error_examples()
            }
        }


def create_openapi_schema_enhancements() -> Dict[str, Any]:
    """Create OpenAPI schema enhancements for better documentation."""
    
    return {
        "info": {
            "title": "Archelyst Financial API",
            "description": """
            Comprehensive financial data and AI-powered analysis API.
            
            ## Features
            - Real-time stock quotes and market data
            - Historical price data and analytics
            - AI-powered stock analysis and insights
            - Market overview and sector performance
            - User authentication and profile management
            - Advanced search and filtering capabilities
            
            ## Authentication
            Most endpoints require authentication via API key or JWT token.
            See the authentication section for details.
            
            ## Rate Limits
            API calls are rate limited based on your subscription tier:
            - Free: 100 requests/hour
            - Premium: 1,000 requests/hour
            - Professional: 10,000 requests/hour
            
            ## Data Sources
            We aggregate data from multiple reliable financial data providers
            to ensure accuracy and completeness.
            """,
            "version": "1.0.0",
            "contact": {
                "name": "Archelyst API Support",
                "email": "api-support@archelyst.com",
                "url": "https://docs.archelyst.com"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "servers": [
            {
                "url": "https://api.archelyst.com/v1",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.archelyst.com/v1",
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8000/api/v1",
                "description": "Development server"
            }
        ],
        "tags": [
            {
                "name": "Securities",
                "description": "Stock quotes, profiles, and historical data"
            },
            {
                "name": "Market",
                "description": "Market overview, indices, and sector data"
            },
            {
                "name": "AI Analysis",
                "description": "AI-powered stock analysis and insights"
            },
            {
                "name": "Users",
                "description": "User management and authentication"
            },
            {
                "name": "Search",
                "description": "Securities search and discovery"
            }
        ]
    }


if __name__ == "__main__":
    # Generate all examples
    examples = OpenAPIExamples.generate_all_examples()
    
    # Print formatted examples
    import json
    print("=== OPENAPI EXAMPLES ===")
    print(json.dumps(examples, indent=2, default=str))
    
    # Generate schema enhancements
    schema_enhancements = create_openapi_schema_enhancements()
    print("\n=== SCHEMA ENHANCEMENTS ===")
    print(json.dumps(schema_enhancements, indent=2))