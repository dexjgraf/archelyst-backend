"""
Comprehensive examples for all Pydantic schemas.

This file demonstrates how to create and use all schema models
with realistic data examples for testing and documentation.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import List

# Import all schema modules
from .base import BaseResponse, ErrorDetail, ErrorType, PaginatedResponse, PaginationInfo, DataProviderInfo
from .securities import (
    SecurityQuote, SecurityProfile, HistoricalData, OHLCVData, 
    SecuritySearchResult, BatchQuoteData, SecurityType, ExchangeCode, 
    MarketStatus, TimeFrame
)
from .market import (
    MarketOverview, MarketSummary, IndexData, SectorPerformance,
    CommodityData, CryptoData, MarketMover, MarketRegion, IndexType,
    SectorCategory, CommodityType
)
from .users import (
    UserProfile, UserRole, AuthProvider, SubscriptionStatus, RiskTolerance,
    APIKey, UserPreferences, NotificationPreferences, DisplayPreferences
)
from .ai import (
    StockAnalysisData, MarketInsightData, SentimentAnalysisData,
    PortfolioAnalysisData, AIInsight, SentimentScore, AnalysisType,
    TimeHorizon, AIProvider, AIAnalysisMetadata
)


def create_example_security_quote() -> SecurityQuote:
    """Create a realistic SecurityQuote example."""
    return SecurityQuote(
        symbol="AAPL",
        name="Apple Inc.",
        price=Decimal("192.53"),
        change=Decimal("3.47"),
        change_percent=Decimal("1.84"),
        volume=52847392,
        avg_volume=68234567,
        market_cap=3020000000000,
        pe_ratio=Decimal("28.45"),
        day_high=Decimal("194.12"),
        day_low=Decimal("190.85"),
        previous_close=Decimal("189.06"),
        open_price=Decimal("190.25"),
        week_52_high=Decimal("199.62"),
        week_52_low=Decimal("164.08"),
        exchange=ExchangeCode.NASDAQ,
        currency="USD",
        market_status=MarketStatus.OPEN,
        last_update=datetime(2024, 7, 4, 15, 30, 0),
        extended_hours_price=Decimal("192.75"),
        extended_hours_change=Decimal("0.22")
    )


def create_example_security_profile() -> SecurityProfile:
    """Create a realistic SecurityProfile example."""
    return SecurityProfile(
        symbol="AAPL",
        name="Apple Inc.",
        description="Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company serves consumers, and small and mid-sized businesses; and the education, enterprise, and government markets.",
        industry="Technology Hardware, Storage & Peripherals",
        sector="Information Technology",
        website="https://www.apple.com",
        headquarters="Cupertino, California, United States",
        employees=164000,
        founded=1976,
        ceo="Timothy D. Cook",
        exchange=ExchangeCode.NASDAQ,
        currency="USD",
        country="United States",
        market_cap=3020000000000,
        enterprise_value=2985000000000,
        revenue_ttm=394328000000,
        profit_margin=Decimal("0.2531"),
        operating_margin=Decimal("0.2987"),
        return_on_equity=Decimal("1.4756"),
        return_on_assets=Decimal("0.2865"),
        debt_to_equity=Decimal("1.73"),
        beta=Decimal("1.24"),
        dividend_yield=Decimal("0.0044"),
        ex_dividend_date=date(2024, 2, 9),
        tags=["large-cap", "technology", "consumer-electronics", "dividend"],
        similar_securities=["MSFT", "GOOGL", "AMZN", "META"]
    )


def create_example_historical_data() -> HistoricalData:
    """Create a realistic HistoricalData example."""
    ohlcv_data = [
        OHLCVData(
            timestamp=datetime(2024, 7, 1, 9, 30),
            open=Decimal("188.50"),
            high=Decimal("192.25"),
            low=Decimal("187.80"),
            close=Decimal("190.25"),
            volume=45823456,
            adjusted_close=Decimal("190.25"),
            vwap=Decimal("189.87")
        ),
        OHLCVData(
            timestamp=datetime(2024, 7, 2, 9, 30),
            open=Decimal("190.30"),
            high=Decimal("193.50"),
            low=Decimal("189.75"),
            close=Decimal("192.10"),
            volume=52734189,
            adjusted_close=Decimal("192.10"),
            vwap=Decimal("191.42")
        ),
        OHLCVData(
            timestamp=datetime(2024, 7, 3, 9, 30),
            open=Decimal("192.00"),
            high=Decimal("194.80"),
            low=Decimal("190.90"),
            close=Decimal("193.75"),
            volume=48956321,
            adjusted_close=Decimal("193.75"),
            vwap=Decimal("192.98")
        )
    ]
    
    return HistoricalData(
        symbol="AAPL",
        timeframe=TimeFrame.DAY_1,
        start_date=date(2024, 7, 1),
        end_date=date(2024, 7, 3),
        data=ohlcv_data
    )


def create_example_market_overview() -> MarketOverview:
    """Create a realistic MarketOverview example."""
    market_summary = MarketSummary(
        total_market_cap=52000000000000,
        trading_volume=750000000000,
        advancing_stocks=3247,
        declining_stocks=1823,
        unchanged_stocks=284,
        new_highs=198,
        new_lows=37,
        fear_greed_index=Decimal("67.5")
    )
    
    major_indices = [
        IndexData(
            symbol="^GSPC",
            name="S&P 500",
            value=Decimal("5537.02"),
            change=Decimal("15.87"),
            change_percent=Decimal("0.29"),
            previous_close=Decimal("5521.15"),
            day_high=Decimal("5542.35"),
            day_low=Decimal("5528.10"),
            week_52_high=Decimal("5669.67"),
            week_52_low=Decimal("4103.78"),
            index_type=IndexType.BROAD_MARKET,
            region=MarketRegion.US,
            last_update=datetime(2024, 7, 4, 16, 0)
        ),
        IndexData(
            symbol="^IXIC",
            name="NASDAQ Composite",
            value=Decimal("18188.30"),
            change=Decimal("87.50"),
            change_percent=Decimal("0.48"),
            previous_close=Decimal("18100.80"),
            day_high=Decimal("18195.45"),
            day_low=Decimal("18175.20"),
            index_type=IndexType.BROAD_MARKET,
            region=MarketRegion.US,
            last_update=datetime(2024, 7, 4, 16, 0)
        )
    ]
    
    sector_performance = [
        SectorPerformance(
            sector=SectorCategory.TECHNOLOGY,
            change_percent=Decimal("1.23"),
            market_cap=15000000000000,
            volume=125000000000,
            top_performers=["AAPL", "MSFT", "GOOGL", "NVDA"],
            worst_performers=["META", "NFLX", "CRM"]
        ),
        SectorPerformance(
            sector=SectorCategory.HEALTHCARE,
            change_percent=Decimal("0.45"),
            market_cap=8500000000000,
            volume=45000000000,
            top_performers=["JNJ", "PFE", "UNH"],
            worst_performers=["MRNA", "BNTX"]
        )
    ]
    
    return MarketOverview(
        date=date(2024, 7, 4),
        market_status="CLOSED",
        session_info={
            "regular_hours": {"start": "09:30", "end": "16:00"},
            "extended_hours": {"start": "04:00", "end": "20:00"},
            "timezone": "America/New_York"
        },
        summary=market_summary,
        major_indices=major_indices,
        sector_performance=sector_performance,
        market_movers={
            "top_gainers": ["NVDA", "AMD", "TSLA", "COIN"],
            "top_losers": ["INTC", "IBM", "T", "VZ"],
            "most_active": ["AAPL", "MSFT", "AMZN", "GOOGL", "SPY"]
        },
        economic_indicators={
            "vix": 18.45,
            "dxy": 104.23,
            "ten_year_yield": 4.25,
            "fed_funds_rate": 5.375,
            "unemployment_rate": 3.7
        }
    )


def create_example_user_profile() -> UserProfile:
    """Create a realistic UserProfile example."""
    return UserProfile(
        id="user_abc123xyz789",
        email="john.doe@example.com",
        username="john_trader",
        first_name="John",
        last_name="Doe",
        display_name="John D.",
        role=UserRole.PREMIUM,
        is_active=True,
        email_verified=True,
        bio="Experienced trader and financial analyst with 10+ years in equity markets",
        timezone="America/New_York",
        avatar_url="https://avatars.example.com/john_trader.jpg",
        created_at=datetime(2024, 1, 15, 10, 30),
        updated_at=datetime(2024, 7, 4, 15, 30),
        last_login=datetime(2024, 7, 4, 9, 15),
        risk_tolerance=RiskTolerance.MODERATE,
        investment_experience="intermediate",
        preferred_currencies=["USD", "EUR", "GBP"],
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_expires=datetime(2024, 12, 31, 23, 59, 59),
        api_calls_used=1247,
        api_calls_limit=5000
    )


def create_example_ai_stock_analysis() -> StockAnalysisData:
    """Create a realistic StockAnalysisData example."""
    key_insights = [
        AIInsight(
            title="Strong Technical Momentum",
            content="RSI indicates oversold condition with potential for reversal. Price is trading above key moving averages with increasing volume confirming the uptrend.",
            importance="high",
            category="technical",
            supporting_data=[
                "RSI (14): 28.5 (oversold)",
                "Price vs 50-day MA: +5.2%",
                "Volume trend: +25% above average",
                "MACD: Bullish crossover"
            ],
            sentiment_impact=SentimentScore.BULLISH
        ),
        AIInsight(
            title="Solid Financial Fundamentals",
            content="P/E ratio below industry average suggests potential undervaluation. Strong balance sheet metrics indicate financial stability and growth potential.",
            importance="high",
            category="fundamental",
            supporting_data=[
                "P/E: 18.5 vs industry 22.3",
                "Debt-to-equity: 0.35 (low)",
                "Current ratio: 2.1 (healthy)",
                "ROE: 24.7% (excellent)"
            ],
            sentiment_impact=SentimentScore.BULLISH
        ),
        AIInsight(
            title="Positive Market Sentiment",
            content="Recent earnings beat and positive guidance have driven increased institutional interest. Social sentiment trending positive with growing retail investor attention.",
            importance="medium",
            category="sentiment",
            supporting_data=[
                "Earnings surprise: +8.2%",
                "Institutional flow: +$2.4B (30 days)",
                "Social sentiment score: 0.73",
                "News sentiment: 78% positive"
            ],
            sentiment_impact=SentimentScore.VERY_BULLISH
        )
    ]
    
    return StockAnalysisData(
        symbol="AAPL",
        company_name="Apple Inc.",
        overall_rating="BUY",
        sentiment=SentimentScore.BULLISH,
        confidence_score=Decimal("0.823"),
        key_insights=key_insights,
        financial_metrics=[],  # Would include FinancialMetric objects
        technical_indicators=[],  # Would include TechnicalIndicator objects
        competitor_comparison=[],  # Would include CompetitorComparison objects
        price_targets=[],  # Would include PriceTarget objects
        strengths=[
            "Strong brand loyalty and ecosystem",
            "High profit margins and cash generation",
            "Innovation capability and R&D investment",
            "Global market presence",
            "Services revenue growth"
        ],
        weaknesses=[
            "High valuation compared to peers",
            "Dependence on iPhone revenue",
            "Regulatory scrutiny in key markets",
            "Currency exposure from international sales"
        ],
        opportunities=[
            "AI integration across product portfolio",
            "Services business expansion",
            "Emerging market penetration",
            "Health technology development",
            "Autonomous vehicle technology"
        ],
        threats=[
            "Economic slowdown reducing consumer spending",
            "Increased competition in smartphone market",
            "Supply chain disruptions",
            "Regulatory restrictions on app store",
            "Trade tensions with China"
        ],
        executive_summary="Apple demonstrates strong fundamentals with solid growth prospects in AI and services, though valuation remains elevated. Technical indicators suggest near-term upside potential with positive sentiment drivers supporting the bullish thesis.",
        time_horizon=TimeHorizon.MEDIUM_TERM
    )


def create_example_api_responses():
    """Create example API responses using the schemas."""
    
    # Success response example
    quote = create_example_security_quote()
    provider_info = DataProviderInfo(
        name="financial_modeling_prep",
        source="Financial Modeling Prep API",
        timestamp=datetime(2024, 7, 4, 15, 30),
        rate_limit_remaining=995,
        cache_hit=False
    )
    
    success_response = BaseResponse[SecurityQuote](
        success=True,
        message="Quote retrieved successfully",
        data=quote,
        timestamp=datetime(2024, 7, 4, 15, 30),
        request_id="req_abc123xyz789"
    )
    
    # Error response example
    error_detail = ErrorDetail(
        code=400,
        message="Invalid symbol provided",
        type=ErrorType.VALIDATION_ERROR,
        details={
            "field": "symbol",
            "issue": "Symbol must be 1-10 characters",
            "provided_value": "",
            "valid_examples": ["AAPL", "MSFT", "GOOGL"]
        },
        trace_id="trace_def456uvw012"
    )
    
    error_response = BaseResponse[None](
        success=False,
        error=error_detail,
        timestamp=datetime(2024, 7, 4, 15, 30),
        request_id="req_def456uvw012"
    )
    
    # Paginated response example
    quotes = [create_example_security_quote() for _ in range(3)]
    pagination_info = PaginationInfo(
        page=1,
        page_size=20,
        total_items=156,
        total_pages=8,
        has_next=True,
        has_previous=False
    )
    
    paginated_response = PaginatedResponse[SecurityQuote](
        items=quotes,
        pagination=pagination_info
    )
    
    return {
        "success_response": success_response,
        "error_response": error_response,
        "paginated_response": paginated_response,
        "provider_info": provider_info
    }


def create_comprehensive_examples():
    """Create comprehensive examples of all major schema types."""
    
    examples = {
        # Security data examples
        "security_quote": create_example_security_quote(),
        "security_profile": create_example_security_profile(),
        "historical_data": create_example_historical_data(),
        
        # Market data examples
        "market_overview": create_example_market_overview(),
        
        # User data examples
        "user_profile": create_example_user_profile(),
        
        # AI analysis examples
        "stock_analysis": create_example_ai_stock_analysis(),
        
        # API response examples
        "api_responses": create_example_api_responses()
    }
    
    return examples


# Example usage for testing and documentation
if __name__ == "__main__":
    examples = create_comprehensive_examples()
    
    # Print example JSON for documentation
    import json
    from pydantic.json import pydantic_encoder
    
    for name, example in examples.items():
        print(f"\n=== {name.upper()} EXAMPLE ===")
        if hasattr(example, 'dict'):
            print(json.dumps(example.dict(), indent=2, default=pydantic_encoder))
        else:
            print(json.dumps(example, indent=2, default=pydantic_encoder))