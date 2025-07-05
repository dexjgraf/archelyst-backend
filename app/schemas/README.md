# Pydantic Schemas Documentation

This directory contains all Pydantic schemas for the Archelyst Backend API. These schemas provide type safety, validation, and auto-generated documentation for all API endpoints.

## Overview

The schemas are organized into modules based on functionality:

- **`base.py`** - Foundation schemas used across all endpoints
- **`securities.py`** - Stock quotes, profiles, historical data, and search
- **`market.py`** - Market overview, indices, commodities, forex, crypto
- **`users.py`** - User management, authentication, and preferences  
- **`ai.py`** - AI-powered analysis, insights, and predictions

## Schema Architecture

### Base Response Pattern

All API responses follow a consistent structure using the `BaseResponse` generic:

```python
class BaseResponse(BaseModel, Generic[DataT]):
    success: bool                    # Request success status
    message: Optional[str]           # Human-readable message
    data: Optional[DataT]           # Response data (typed)
    error: Optional[ErrorDetail]    # Error details (if failed)
    timestamp: datetime             # Response timestamp
    request_id: Optional[str]       # Unique request identifier
```

### Example Response Structure

```json
{
  "success": true,
  "message": "Quote retrieved successfully",
  "data": {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "price": 150.25,
    "change": 2.15,
    "change_percent": 1.45
  },
  "timestamp": "2024-07-04T15:30:00Z",
  "request_id": "req_1234567890abcdef"
}
```

## Module Documentation

### 1. Base Schemas (`base.py`)

Foundation schemas providing common functionality:

#### Key Models:
- `BaseResponse[T]` - Generic response wrapper
- `ErrorDetail` - Structured error information
- `PaginatedResponse[T]` - Paginated data responses
- `DataProviderInfo` - Data source metadata

#### Usage Example:
```python
from app.schemas.base import BaseResponse
from app.schemas.securities import SecurityQuote

# Type-safe response model
class QuoteResponse(BaseResponse[SecurityQuote]):
    provider: Optional[DataProviderInfo] = None
```

### 2. Securities Schemas (`securities.py`)

Comprehensive models for financial securities data:

#### Key Models:
- `SecurityQuote` - Real-time stock quotes
- `SecurityProfile` - Company fundamentals and details
- `HistoricalData` - OHLCV historical price data
- `SecuritySearchResult` - Search functionality
- `BatchQuoteData` - Bulk quote operations

#### Example: Stock Quote
```python
quote = SecurityQuote(
    symbol="AAPL",
    name="Apple Inc.",
    price=150.25,
    change=2.15,
    change_percent=1.45,
    volume=1250000,
    market_cap=2500000000000,
    pe_ratio=25.34,
    day_high=152.10,
    day_low=148.50,
    previous_close=148.10,
    open_price=149.00,
    exchange=ExchangeCode.NASDAQ,
    market_status=MarketStatus.OPEN,
    last_update=datetime.utcnow()
)
```

#### Supported Security Types:
- `STOCK` - Common stocks
- `ETF` - Exchange-traded funds
- `MUTUAL_FUND` - Mutual funds
- `INDEX` - Market indices
- `BOND` - Fixed income securities
- `OPTION` - Options contracts
- `FUTURE` - Futures contracts
- `CRYPTO` - Cryptocurrencies

### 3. Market Schemas (`market.py`)

Market-wide data and overview information:

#### Key Models:
- `MarketOverview` - Comprehensive market summary
- `IndexData` - Market index information
- `CommodityData` - Commodity prices
- `CryptoData` - Cryptocurrency data
- `MarketMoversData` - Top gainers/losers/active

#### Example: Market Overview
```python
overview = MarketOverview(
    date=date.today(),
    market_status="OPEN",
    session_info={
        "regular_hours": {"start": "09:30", "end": "16:00"},
        "extended_hours": {"start": "04:00", "end": "20:00"}
    },
    summary=MarketSummary(
        total_market_cap=45000000000000,
        advancing_stocks=2847,
        declining_stocks=1923,
        fear_greed_index=65.5
    ),
    major_indices=[...],
    sector_performance=[...]
)
```

### 4. User Schemas (`users.py`)

User management, authentication, and preferences:

#### Key Models:
- `UserProfile` - Complete user information
- `LoginRequest/Response` - Authentication flow
- `APIKey` - API key management
- `UserPreferences` - User settings and preferences

#### Example: User Profile
```python
user = UserProfile(
    id="user_123456789",
    email="user@example.com",
    username="john_doe",
    first_name="John",
    last_name="Doe",
    role=UserRole.PREMIUM,
    is_active=True,
    email_verified=True,
    subscription_status=SubscriptionStatus.ACTIVE,
    risk_tolerance=RiskTolerance.MODERATE,
    api_calls_used=1250,
    api_calls_limit=5000,
    created_at=datetime.utcnow()
)
```

### 5. AI Schemas (`ai.py`)

AI-powered analysis and insights:

#### Key Models:
- `StockAnalysisData` - Comprehensive stock analysis
- `MarketInsightData` - Market-wide AI insights
- `SentimentAnalysisData` - Multi-source sentiment
- `PortfolioAnalysisData` - Portfolio optimization

#### Example: Stock Analysis
```python
analysis = StockAnalysisData(
    symbol="AAPL",
    company_name="Apple Inc.",
    overall_rating="BUY",
    sentiment=SentimentScore.BULLISH,
    confidence_score=0.785,
    key_insights=[
        AIInsight(
            title="Strong Technical Momentum",
            content="RSI indicates oversold condition with potential for reversal",
            importance="high",
            category="technical",
            sentiment_impact=SentimentScore.BULLISH
        )
    ],
    strengths=["Strong brand", "High margins"],
    weaknesses=["High valuation"],
    opportunities=["AI integration"],
    threats=["Economic slowdown"],
    time_horizon=TimeHorizon.MEDIUM_TERM
)
```

## Validation Features

### Input Validation
All schemas include comprehensive validation:

```python
class SecurityQuote(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    price: Decimal = Field(..., decimal_places=4)
    volume: int = Field(..., ge=0)
    change_percent: Decimal = Field(..., decimal_places=4)
```

### Custom Validators
Complex validation logic using Pydantic validators:

```python
@validator('end_date')
def end_date_after_start_date(cls, v, values):
    start_date = values.get('start_date')
    if start_date and v and v <= start_date:
        raise ValueError('end_date must be after start_date')
    return v
```

### Enum Validation
Strict enumeration validation:

```python
class SecurityType(str, Enum):
    STOCK = "stock"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    # ... etc
```

## Error Handling

### Structured Error Responses
Consistent error format across all endpoints:

```python
class ErrorDetail(BaseModel):
    code: int = Field(..., ge=100, le=599)
    message: str
    type: ErrorType
    details: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
```

### Error Types
Standardized error classifications:

- `VALIDATION_ERROR` - Input validation failures
- `AUTHENTICATION_ERROR` - Auth failures
- `AUTHORIZATION_ERROR` - Permission denied
- `NOT_FOUND_ERROR` - Resource not found
- `RATE_LIMIT_ERROR` - Rate limiting
- `PROVIDER_ERROR` - External data provider issues
- `INTERNAL_ERROR` - Server errors

## Usage Patterns

### 1. Endpoint Response Models

```python
from app.schemas.securities import QuoteResponse

@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str) -> QuoteResponse:
    # Implementation
    return QuoteResponse(
        success=True,
        message="Quote retrieved successfully",
        data=quote_data,
        timestamp=datetime.utcnow()
    )
```

### 2. Request Validation

```python
from app.schemas.securities import BatchQuoteRequest

@router.post("/batch-quotes")
async def batch_quotes(request: BatchQuoteRequest):
    # Automatic validation of request.symbols
    for symbol in request.symbols:  # Already validated
        # Process each symbol
        pass
```

### 3. Type Safety

```python
# Type hints provide IDE support and validation
def process_quote(quote: SecurityQuote) -> str:
    return f"{quote.symbol}: ${quote.price}"

# Pydantic ensures quote is properly structured
```

## OpenAPI/Swagger Integration

All schemas automatically generate OpenAPI documentation:

- **Request/Response Examples**: Embedded in schema definitions
- **Field Descriptions**: Comprehensive documentation
- **Validation Rules**: Min/max values, patterns, etc.
- **Type Information**: Full type definitions

## Best Practices

### 1. Use Specific Types
```python
# Good
price: Decimal = Field(..., decimal_places=4)

# Avoid
price: float
```

### 2. Provide Examples
```python
symbol: str = Field(
    ..., 
    description="Stock symbol",
    example="AAPL",
    min_length=1,
    max_length=10
)
```

### 3. Use Enums for Constants
```python
# Good
exchange: ExchangeCode = Field(..., example=ExchangeCode.NASDAQ)

# Avoid
exchange: str = Field(..., example="NASDAQ")
```

### 4. Include Metadata
```python
class QuoteResponse(BaseResponse[SecurityQuote]):
    provider: Optional[DataProviderInfo] = Field(
        None, 
        description="Data provider information"
    )
```

## Migration from Legacy Models

If updating existing endpoints:

1. **Import new schemas**: Replace inline models
2. **Update response_model**: Use typed response classes
3. **Update return statements**: Return structured responses
4. **Test thoroughly**: Ensure validation works correctly

## Development Workflow

1. **Define Schema**: Create or update Pydantic model
2. **Add Validation**: Include field validators
3. **Write Tests**: Test validation and serialization
4. **Update Endpoints**: Use schema in API endpoints
5. **Generate Docs**: OpenAPI docs auto-update

This schema architecture provides a robust foundation for type-safe, well-documented, and maintainable API development.