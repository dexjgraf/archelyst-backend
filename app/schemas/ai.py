"""
AI services Pydantic schemas.

Contains request and response models for AI-powered analysis endpoints including
market insights, stock analysis, sentiment analysis, and predictive models.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator

from .base import BaseResponse, DataProviderInfo


# ============================================================================
# Enums and Constants
# ============================================================================

class AnalysisType(str, Enum):
    """Types of AI analysis."""
    FUNDAMENTAL = "fundamental"
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    PREDICTIVE = "predictive"
    RISK = "risk"
    COMPARATIVE = "comparative"


class SentimentScore(str, Enum):
    """Sentiment analysis scores."""
    VERY_BEARISH = "very_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    VERY_BULLISH = "very_bullish"


class ConfidenceLevel(str, Enum):
    """AI confidence levels."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class TimeHorizon(str, Enum):
    """Analysis time horizons."""
    SHORT_TERM = "short_term"    # 1-30 days
    MEDIUM_TERM = "medium_term"  # 1-6 months
    LONG_TERM = "long_term"      # 6+ months


class AIProvider(str, Enum):
    """AI service providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    CUSTOM = "custom"


# ============================================================================
# Base AI Models
# ============================================================================

class AIAnalysisMetadata(BaseModel):
    """Metadata for AI analysis."""
    
    provider: AIProvider = Field(
        ..., 
        description="AI provider used",
        example=AIProvider.OPENAI
    )
    model_name: str = Field(
        ..., 
        description="AI model name",
        example="gpt-4"
    )
    model_version: Optional[str] = Field(
        None, 
        description="Model version",
        example="gpt-4-0125-preview"
    )
    analysis_timestamp: datetime = Field(
        ..., 
        description="When analysis was performed",
        example="2024-07-04T15:30:00Z"
    )
    processing_time_ms: Optional[float] = Field(
        None, 
        description="Processing time in milliseconds",
        example=2341.5
    )
    tokens_used: Optional[int] = Field(
        None, 
        description="Number of tokens consumed",
        example=1250
    )
    confidence_score: Optional[Decimal] = Field(
        None, 
        description="Overall confidence score (0-1)",
        example=0.85,
        ge=0,
        le=1,
    )


class AIInsight(BaseModel):
    """Individual AI insight."""
    
    title: str = Field(
        ..., 
        description="Insight title",
        example="Strong Earnings Growth Trend"
    )
    content: str = Field(
        ..., 
        description="Detailed insight content",
        example="The company has demonstrated consistent earnings growth over the past 4 quarters, with revenue increasing by 15% year-over-year."
    )
    importance: str = Field(
        ..., 
        description="Importance level",
        example="high"
    )
    category: str = Field(
        ..., 
        description="Insight category",
        example="fundamental"
    )
    supporting_data: List[str] = Field(
        default_factory=list, 
        description="Supporting data points",
        example=["Q4 2023 earnings: +15%", "Revenue growth: 15% YoY", "Margin improvement: +2.3%"]
    )
    sentiment_impact: SentimentScore = Field(
        ..., 
        description="Sentiment impact",
        example=SentimentScore.BULLISH
    )


# ============================================================================
# Market Analysis Models
# ============================================================================

class MarketInsightRequest(BaseModel):
    """Market insight analysis request."""
    
    analysis_types: List[AnalysisType] = Field(
        default_factory=lambda: [AnalysisType.SENTIMENT, AnalysisType.TECHNICAL],
        description="Types of analysis to perform",
        example=[AnalysisType.SENTIMENT, AnalysisType.TECHNICAL]
    )
    time_horizon: TimeHorizon = Field(
        TimeHorizon.SHORT_TERM, 
        description="Analysis time horizon",
        example=TimeHorizon.SHORT_TERM
    )
    include_sectors: bool = Field(
        True, 
        description="Include sector analysis",
        example=True
    )
    include_economic_factors: bool = Field(
        True, 
        description="Include economic factors",
        example=True
    )
    custom_prompt: Optional[str] = Field(
        None, 
        description="Custom analysis prompt",
        example="Focus on technology sector performance"
    )


class EconomicFactor(BaseModel):
    """Economic factor analysis."""
    
    factor: str = Field(
        ..., 
        description="Economic factor name",
        example="Federal Reserve Interest Rates"
    )
    current_value: Optional[str] = Field(
        None, 
        description="Current value",
        example="5.25%-5.50%"
    )
    trend: str = Field(
        ..., 
        description="Trend direction",
        example="stable"
    )
    market_impact: SentimentScore = Field(
        ..., 
        description="Expected market impact",
        example=SentimentScore.NEUTRAL
    )
    explanation: str = Field(
        ..., 
        description="Impact explanation",
        example="Current rates are expected to remain stable, providing certainty for market planning."
    )


class SectorAnalysis(BaseModel):
    """Sector performance analysis."""
    
    sector: str = Field(
        ..., 
        description="Sector name",
        example="Technology"
    )
    performance_score: Decimal = Field(
        ..., 
        description="Performance score (-1 to 1)",
        example=0.35,
        ge=-1,
        le=1,
    )
    sentiment: SentimentScore = Field(
        ..., 
        description="Sector sentiment",
        example=SentimentScore.BULLISH
    )
    key_drivers: List[str] = Field(
        ..., 
        description="Key performance drivers",
        example=["AI adoption", "Cloud computing growth", "Strong earnings"]
    )
    top_stocks: List[str] = Field(
        default_factory=list, 
        description="Top performing stocks",
        example=["AAPL", "MSFT", "GOOGL"]
    )
    outlook: str = Field(
        ..., 
        description="Sector outlook",
        example="Positive momentum expected to continue with AI investments driving growth."
    )


class MarketInsightData(BaseModel):
    """Market insight analysis data."""
    
    overall_sentiment: SentimentScore = Field(
        ..., 
        description="Overall market sentiment",
        example=SentimentScore.BULLISH
    )
    market_score: Decimal = Field(
        ..., 
        description="Overall market score (-1 to 1)",
        example=0.25,
        ge=-1,
        le=1,
    )
    key_insights: List[AIInsight] = Field(
        ..., 
        description="Key market insights"
    )
    sector_analysis: List[SectorAnalysis] = Field(
        default_factory=list, 
        description="Sector performance analysis"
    )
    economic_factors: List[EconomicFactor] = Field(
        default_factory=list, 
        description="Economic factors analysis"
    )
    risk_factors: List[str] = Field(
        default_factory=list, 
        description="Identified risk factors",
        example=["Inflation concerns", "Geopolitical tensions", "Supply chain disruptions"]
    )
    opportunities: List[str] = Field(
        default_factory=list, 
        description="Market opportunities",
        example=["AI technology adoption", "Green energy transition", "Emerging markets growth"]
    )
    summary: str = Field(
        ..., 
        description="Executive summary",
        example="Market sentiment remains positive with technology sectors leading gains. Economic fundamentals are solid despite ongoing inflation concerns."
    )
    time_horizon: TimeHorizon = Field(
        ..., 
        description="Analysis time horizon",
        example=TimeHorizon.SHORT_TERM
    )


class MarketInsightResponse(BaseResponse[MarketInsightData]):
    """Market insight analysis response."""
    
    ai_metadata: AIAnalysisMetadata = Field(
        ..., 
        description="AI analysis metadata"
    )


# ============================================================================
# Stock Analysis Models
# ============================================================================

class StockAnalysisRequest(BaseModel):
    """Stock analysis request."""
    
    symbol: str = Field(
        ..., 
        description="Stock symbol",
        example="AAPL",
        min_length=1,
        max_length=10
    )
    analysis_types: List[AnalysisType] = Field(
        default_factory=lambda: [AnalysisType.FUNDAMENTAL, AnalysisType.TECHNICAL, AnalysisType.SENTIMENT],
        description="Types of analysis to perform"
    )
    time_horizon: TimeHorizon = Field(
        TimeHorizon.MEDIUM_TERM, 
        description="Analysis time horizon",
        example=TimeHorizon.MEDIUM_TERM
    )
    include_competitors: bool = Field(
        True, 
        description="Include competitor analysis",
        example=True
    )
    include_news_sentiment: bool = Field(
        True, 
        description="Include news sentiment analysis",
        example=True
    )
    custom_prompt: Optional[str] = Field(
        None, 
        description="Custom analysis prompt",
        example="Focus on upcoming product launches and their potential market impact"
    )


class FinancialMetric(BaseModel):
    """Financial metric analysis."""
    
    metric: str = Field(
        ..., 
        description="Metric name",
        example="Price-to-Earnings Ratio"
    )
    current_value: Optional[Decimal] = Field(
        None, 
        description="Current value",
        example=25.34,
    )
    industry_average: Optional[Decimal] = Field(
        None, 
        description="Industry average",
        example=22.45,
    )
    percentile_rank: Optional[int] = Field(
        None, 
        description="Percentile rank vs peers (0-100)",
        example=75,
        ge=0,
        le=100
    )
    trend: str = Field(
        ..., 
        description="Metric trend",
        example="improving"
    )
    interpretation: str = Field(
        ..., 
        description="Metric interpretation",
        example="Trading at a premium to industry average, indicating strong market confidence."
    )


class TechnicalIndicator(BaseModel):
    """Technical analysis indicator."""
    
    indicator: str = Field(
        ..., 
        description="Indicator name",
        example="RSI (14-day)"
    )
    value: Optional[Decimal] = Field(
        None, 
        description="Current value",
        example=67.5,
    )
    signal: str = Field(
        ..., 
        description="Signal interpretation",
        example="neutral"
    )
    strength: str = Field(
        ..., 
        description="Signal strength",
        example="moderate"
    )
    explanation: str = Field(
        ..., 
        description="Detailed explanation",
        example="RSI above 60 indicates bullish momentum but not yet overbought territory."
    )


class CompetitorComparison(BaseModel):
    """Competitor comparison data."""
    
    competitor_symbol: str = Field(
        ..., 
        description="Competitor symbol",
        example="MSFT"
    )
    competitor_name: str = Field(
        ..., 
        description="Competitor name",
        example="Microsoft Corporation"
    )
    relative_strength: Decimal = Field(
        ..., 
        description="Relative strength score (-1 to 1)",
        example=0.15,
        ge=-1,
        le=1,
    )
    key_advantages: List[str] = Field(
        default_factory=list, 
        description="Key advantages over competitor",
        example=["Brand loyalty", "Ecosystem integration", "Margins"]
    )
    key_disadvantages: List[str] = Field(
        default_factory=list, 
        description="Areas where competitor is stronger",
        example=["Cloud market share", "Enterprise software"]
    )


class PriceTarget(BaseModel):
    """AI-generated price target."""
    
    target_price: Decimal = Field(
        ..., 
        description="Target price",
        example=185.50,
    )
    time_horizon: TimeHorizon = Field(
        ..., 
        description="Time horizon for target",
        example=TimeHorizon.MEDIUM_TERM
    )
    upside_potential: Decimal = Field(
        ..., 
        description="Upside potential percentage",
        example=23.5,
    )
    confidence_level: ConfidenceLevel = Field(
        ..., 
        description="Confidence in target",
        example=ConfidenceLevel.MEDIUM
    )
    key_catalysts: List[str] = Field(
        default_factory=list, 
        description="Key catalysts for target achievement",
        example=["New product launch", "Market expansion", "Margin improvement"]
    )
    risk_factors: List[str] = Field(
        default_factory=list, 
        description="Risk factors that could prevent target",
        example=["Economic downturn", "Increased competition", "Regulatory changes"]
    )


class StockAnalysisData(BaseModel):
    """Complete stock analysis data."""
    
    symbol: str = Field(
        ..., 
        description="Stock symbol",
        example="AAPL"
    )
    company_name: str = Field(
        ..., 
        description="Company name",
        example="Apple Inc."
    )
    overall_rating: str = Field(
        ..., 
        description="Overall AI rating",
        example="BUY"
    )
    sentiment: SentimentScore = Field(
        ..., 
        description="Overall sentiment",
        example=SentimentScore.BULLISH
    )
    confidence_score: Decimal = Field(
        ..., 
        description="Analysis confidence (0-1)",
        example=0.78,
        ge=0,
        le=1,
    )
    # Analysis sections
    key_insights: List[AIInsight] = Field(
        ..., 
        description="Key insights"
    )
    financial_metrics: List[FinancialMetric] = Field(
        default_factory=list, 
        description="Financial metrics analysis"
    )
    technical_indicators: List[TechnicalIndicator] = Field(
        default_factory=list, 
        description="Technical analysis indicators"
    )
    competitor_comparison: List[CompetitorComparison] = Field(
        default_factory=list, 
        description="Competitor comparison"
    )
    price_targets: List[PriceTarget] = Field(
        default_factory=list, 
        description="AI-generated price targets"
    )
    # Summary sections
    strengths: List[str] = Field(
        default_factory=list, 
        description="Company strengths",
        example=["Strong brand", "High margins", "Innovation capability"]
    )
    weaknesses: List[str] = Field(
        default_factory=list, 
        description="Company weaknesses",
        example=["High valuation", "Regulatory scrutiny", "Market saturation"]
    )
    opportunities: List[str] = Field(
        default_factory=list, 
        description="Market opportunities",
        example=["AI integration", "Services growth", "Emerging markets"]
    )
    threats: List[str] = Field(
        default_factory=list, 
        description="Market threats",
        example=["Economic slowdown", "Competition", "Supply chain risks"]
    )
    executive_summary: str = Field(
        ..., 
        description="Executive summary",
        example="Apple demonstrates strong fundamentals with solid growth prospects in AI and services, though valuation remains elevated."
    )
    time_horizon: TimeHorizon = Field(
        ..., 
        description="Analysis time horizon",
        example=TimeHorizon.MEDIUM_TERM
    )


class StockAnalysisResponse(BaseResponse[StockAnalysisData]):
    """Stock analysis response."""
    
    ai_metadata: AIAnalysisMetadata = Field(
        ..., 
        description="AI analysis metadata"
    )


# ============================================================================
# Sentiment Analysis Models
# ============================================================================

class SentimentAnalysisRequest(BaseModel):
    """Sentiment analysis request."""
    
    symbols: List[str] = Field(
        ..., 
        description="Stock symbols to analyze",
        example=["AAPL", "MSFT", "GOOGL"],
        min_items=1,
        max_items=50
    )
    time_period_days: int = Field(
        7, 
        description="Time period for sentiment analysis in days",
        example=7,
        ge=1,
        le=90
    )
    include_social_media: bool = Field(
        True, 
        description="Include social media sentiment",
        example=True
    )
    include_news: bool = Field(
        True, 
        description="Include news sentiment",
        example=True
    )
    include_analyst_reports: bool = Field(
        False, 
        description="Include analyst report sentiment",
        example=False
    )


class SentimentSource(BaseModel):
    """Sentiment data source."""
    
    source_type: str = Field(
        ..., 
        description="Source type",
        example="news"
    )
    articles_analyzed: int = Field(
        ..., 
        description="Number of articles analyzed",
        example=156,
        ge=0
    )
    sentiment_score: Decimal = Field(
        ..., 
        description="Sentiment score (-1 to 1)",
        example=0.34,
        ge=-1,
        le=1,
    )
    confidence: Decimal = Field(
        ..., 
        description="Confidence in sentiment (0-1)",
        example=0.82,
        ge=0,
        le=1,
    )


class StockSentiment(BaseModel):
    """Stock sentiment analysis results."""
    
    symbol: str = Field(
        ..., 
        description="Stock symbol",
        example="AAPL"
    )
    overall_sentiment: SentimentScore = Field(
        ..., 
        description="Overall sentiment",
        example=SentimentScore.BULLISH
    )
    sentiment_score: Decimal = Field(
        ..., 
        description="Numerical sentiment score (-1 to 1)",
        example=0.45,
        ge=-1,
        le=1,
    )
    confidence: Decimal = Field(
        ..., 
        description="Confidence in sentiment (0-1)",
        example=0.78,
        ge=0,
        le=1,
    )
    trend: str = Field(
        ..., 
        description="Sentiment trend",
        example="improving"
    )
    sources: List[SentimentSource] = Field(
        ..., 
        description="Sentiment by source"
    )
    key_themes: List[str] = Field(
        default_factory=list, 
        description="Key sentiment themes",
        example=["product innovation", "strong earnings", "market leadership"]
    )
    sentiment_drivers: List[str] = Field(
        default_factory=list, 
        description="Main sentiment drivers",
        example=["AI announcements", "Quarterly results", "Market share gains"]
    )


class SentimentAnalysisData(BaseModel):
    """Sentiment analysis response data."""
    
    stock_sentiments: List[StockSentiment] = Field(
        ..., 
        description="Individual stock sentiments"
    )
    overall_market_sentiment: SentimentScore = Field(
        ..., 
        description="Overall market sentiment for analyzed stocks",
        example=SentimentScore.BULLISH
    )
    analysis_period: str = Field(
        ..., 
        description="Analysis time period",
        example="7 days"
    )
    total_sources_analyzed: int = Field(
        ..., 
        description="Total sources analyzed",
        example=1247,
        ge=0
    )


class SentimentAnalysisResponse(BaseResponse[SentimentAnalysisData]):
    """Sentiment analysis response."""
    
    ai_metadata: AIAnalysisMetadata = Field(
        ..., 
        description="AI analysis metadata"
    )


# ============================================================================
# Portfolio Analysis Models
# ============================================================================

class PortfolioAnalysisRequest(BaseModel):
    """Portfolio analysis request."""
    
    holdings: List[Dict[str, Any]] = Field(
        ..., 
        description="Portfolio holdings",
        example=[
            {"symbol": "AAPL", "shares": 100, "avg_cost": 150.00},
            {"symbol": "MSFT", "shares": 50, "avg_cost": 280.00}
        ]
    )
    analysis_types: List[AnalysisType] = Field(
        default_factory=lambda: [AnalysisType.RISK, AnalysisType.PREDICTIVE],
        description="Analysis types to perform"
    )
    benchmark_symbol: str = Field(
        "SPY", 
        description="Benchmark for comparison",
        example="SPY"
    )
    time_horizon: TimeHorizon = Field(
        TimeHorizon.MEDIUM_TERM, 
        description="Analysis time horizon"
    )


class PortfolioRisk(BaseModel):
    """Portfolio risk analysis."""
    
    total_risk_score: Decimal = Field(
        ..., 
        description="Overall risk score (0-10)",
        example=6.5,
        ge=0,
        le=10,
    )
    concentration_risk: Decimal = Field(
        ..., 
        description="Concentration risk score (0-10)",
        example=4.2,
        ge=0,
        le=10,
    )
    sector_diversification: Decimal = Field(
        ..., 
        description="Sector diversification score (0-10)",
        example=7.8,
        ge=0,
        le=10,
    )
    volatility_score: Decimal = Field(
        ..., 
        description="Portfolio volatility score (0-10)",
        example=5.9,
        ge=0,
        le=10,
    )
    risk_recommendations: List[str] = Field(
        default_factory=list, 
        description="Risk mitigation recommendations",
        example=["Consider reducing technology sector exposure", "Add defensive stocks"]
    )


class PortfolioOptimization(BaseModel):
    """Portfolio optimization suggestions."""
    
    suggested_rebalancing: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Suggested rebalancing actions",
        example=[
            {"action": "reduce", "symbol": "AAPL", "from_weight": 35, "to_weight": 25},
            {"action": "add", "symbol": "BRK.B", "target_weight": 10}
        ]
    )
    expected_return_improvement: Optional[Decimal] = Field(
        None, 
        description="Expected return improvement percentage",
        example=2.3,
    )
    risk_reduction: Optional[Decimal] = Field(
        None, 
        description="Expected risk reduction percentage",
        example=1.8,
    )
    rationale: str = Field(
        ..., 
        description="Optimization rationale",
        example="Rebalancing would improve diversification while maintaining growth potential."
    )


class PortfolioAnalysisData(BaseModel):
    """Portfolio analysis results."""
    
    total_value: Decimal = Field(
        ..., 
        description="Total portfolio value",
        example=75000.00,
    )
    total_return: Decimal = Field(
        ..., 
        description="Total return percentage",
        example=12.5,
    )
    benchmark_comparison: Decimal = Field(
        ..., 
        description="Performance vs benchmark",
        example=3.2,
    )
    risk_analysis: PortfolioRisk = Field(
        ..., 
        description="Risk analysis results"
    )
    optimization: PortfolioOptimization = Field(
        ..., 
        description="Optimization suggestions"
    )
    key_insights: List[AIInsight] = Field(
        ..., 
        description="Key portfolio insights"
    )
    performance_attribution: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Performance attribution by holding",
        example=[
            {"symbol": "AAPL", "contribution": 4.2, "weight": 35.0},
            {"symbol": "MSFT", "contribution": 2.1, "weight": 25.0}
        ]
    )


class PortfolioAnalysisResponse(BaseResponse[PortfolioAnalysisData]):
    """Portfolio analysis response."""
    
    ai_metadata: AIAnalysisMetadata = Field(
        ..., 
        description="AI analysis metadata"
    )


# ============================================================================
# Export all models
# ============================================================================

__all__ = [
    # Enums
    "AnalysisType",
    "SentimentScore",
    "ConfidenceLevel",
    "TimeHorizon",
    "AIProvider",
    
    # Base models
    "AIAnalysisMetadata",
    "AIInsight",
    
    # Market analysis models
    "MarketInsightRequest",
    "EconomicFactor",
    "SectorAnalysis",
    "MarketInsightData",
    "MarketInsightResponse",
    
    # Stock analysis models
    "StockAnalysisRequest",
    "FinancialMetric",
    "TechnicalIndicator",
    "CompetitorComparison",
    "PriceTarget",
    "StockAnalysisData",
    "StockAnalysisResponse",
    
    # Sentiment analysis models
    "SentimentAnalysisRequest",
    "SentimentSource",
    "StockSentiment",
    "SentimentAnalysisData",
    "SentimentAnalysisResponse",
    
    # Portfolio analysis models
    "PortfolioAnalysisRequest",
    "PortfolioRisk",
    "PortfolioOptimization",
    "PortfolioAnalysisData",
    "PortfolioAnalysisResponse"
]