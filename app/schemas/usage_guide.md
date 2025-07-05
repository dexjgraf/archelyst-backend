# Schema Usage Guide

This guide provides practical examples and best practices for using the Archelyst API schemas in development, testing, and production.

## Quick Start

### 1. Basic Response Structure

All API responses follow this pattern:

```python
from app.schemas.base import BaseResponse
from app.schemas.securities import SecurityQuote

# Every endpoint returns this structure
response = BaseResponse[SecurityQuote](
    success=True,
    message="Quote retrieved successfully", 
    data=SecurityQuote(...),
    timestamp=datetime.utcnow(),
    request_id="req_abc123"
)
```

### 2. Creating Endpoint Handlers

```python
from fastapi import APIRouter
from app.schemas.securities import QuoteResponse, SecurityQuote

router = APIRouter()

@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str) -> QuoteResponse:
    # Your business logic here
    quote_data = SecurityQuote(
        symbol=symbol.upper(),
        name="Apple Inc.",
        price=150.25,
        # ... other fields
    )
    
    return QuoteResponse(
        success=True,
        message="Quote retrieved successfully",
        data=quote_data,
        timestamp=datetime.utcnow()
    )
```

## Common Patterns

### Error Handling

```python
from app.schemas.base import BaseResponse, ErrorDetail, ErrorType

# Validation error
def create_validation_error(field: str, message: str):
    return BaseResponse[None](
        success=False,
        error=ErrorDetail(
            code=400,
            message=f"Validation failed for field: {field}",
            type=ErrorType.VALIDATION_ERROR,
            details={"field": field, "issue": message}
        ),
        timestamp=datetime.utcnow()
    )

# Not found error  
def create_not_found_error(resource: str, identifier: str):
    return BaseResponse[None](
        success=False,
        error=ErrorDetail(
            code=404,
            message=f"{resource} not found",
            type=ErrorType.NOT_FOUND_ERROR,
            details={"resource": resource, "identifier": identifier}
        ),
        timestamp=datetime.utcnow()
    )
```

### Pagination

```python
from app.schemas.base import PaginatedResponse, PaginationInfo

def create_paginated_response(items, page, page_size, total_items):
    total_pages = (total_items + page_size - 1) // page_size
    
    pagination = PaginationInfo(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )
    
    return PaginatedResponse(
        items=items,
        pagination=pagination
    )
```

### Request Validation

```python
from app.schemas.securities import SecuritySearchParams
from fastapi import HTTPException

@router.post("/search")
async def search_securities(params: SecuritySearchParams):
    # Pydantic automatically validates:
    # - params.query is 1-100 chars
    # - params.limit is 1-100
    # - params.types contains valid SecurityType enums
    # - params.exchanges contains valid ExchangeCode enums
    
    if not params.query.strip():
        raise HTTPException(400, "Search query cannot be empty")
    
    # Your search logic here
    return search_results
```

## Real-World Examples

### 1. Stock Quote Endpoint

```python
@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_stock_quote(symbol: str) -> QuoteResponse:
    try:
        # Validate symbol
        if not symbol or len(symbol) > 10:
            return QuoteResponse(
                success=False,
                error=ErrorDetail(
                    code=400,
                    message="Invalid symbol format",
                    type=ErrorType.VALIDATION_ERROR
                ),
                timestamp=datetime.utcnow()
            )
        
        # Fetch data (mock example)
        quote = SecurityQuote(
            symbol=symbol.upper(),
            name=f"{symbol} Inc.",
            price=Decimal("150.25"),
            change=Decimal("2.15"),
            change_percent=Decimal("1.45"),
            volume=1250000,
            day_high=Decimal("152.10"),
            day_low=Decimal("148.50"),
            previous_close=Decimal("148.10"),
            open_price=Decimal("149.00"),
            exchange=ExchangeCode.NASDAQ,
            market_status=MarketStatus.OPEN,
            last_update=datetime.utcnow()
        )
        
        provider_info = DataProviderInfo(
            name="financial_data_api",
            source="Financial Data API",
            timestamp=datetime.utcnow(),
            cache_hit=False
        )
        
        return QuoteResponse(
            success=True,
            message="Quote retrieved successfully",
            data=quote,
            timestamp=datetime.utcnow(),
            provider=provider_info
        )
        
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        return QuoteResponse(
            success=False,
            error=ErrorDetail(
                code=500,
                message="Internal server error",
                type=ErrorType.INTERNAL_ERROR
            ),
            timestamp=datetime.utcnow()
        )
```

### 2. AI Analysis Endpoint

```python
@router.post("/analyze", response_model=StockAnalysisResponse)
async def analyze_stock(
    request: StockAnalysisRequest,
    current_user: User = Depends(get_current_user)
) -> StockAnalysisResponse:
    
    # Create AI insights
    insights = [
        AIInsight(
            title="Technical Analysis",
            content="Strong bullish momentum with RSI indicating oversold conditions",
            importance="high",
            category="technical",
            supporting_data=["RSI: 28.5", "MACD: Bullish crossover"],
            sentiment_impact=SentimentScore.BULLISH
        )
    ]
    
    # Create analysis data
    analysis_data = StockAnalysisData(
        symbol=request.symbol,
        company_name=f"{request.symbol} Corp",
        overall_rating="BUY",
        sentiment=SentimentScore.BULLISH,
        confidence_score=Decimal("0.85"),
        key_insights=insights,
        strengths=["Strong fundamentals", "Market leadership"],
        weaknesses=["High valuation", "Market risks"],
        opportunities=["Growth markets", "New products"],
        threats=["Competition", "Economic headwinds"],
        executive_summary="Strong buy recommendation based on technical and fundamental analysis",
        time_horizon=request.time_horizon
    )
    
    # Create AI metadata
    ai_metadata = AIAnalysisMetadata(
        provider=AIProvider.CUSTOM,
        model_name="archelyst-analyzer-v2",
        model_version="2.1.0",
        analysis_timestamp=datetime.utcnow(),
        processing_time_ms=1250.0,
        tokens_used=850,
        confidence_score=Decimal("0.85")
    )
    
    return StockAnalysisResponse(
        success=True,
        message="Analysis completed successfully",
        data=analysis_data,
        timestamp=datetime.utcnow(),
        ai_metadata=ai_metadata
    )
```

### 3. Batch Operations

```python
@router.post("/batch-quotes", response_model=BatchQuoteResponse)
async def get_batch_quotes(request: BatchQuoteRequest) -> BatchQuoteResponse:
    quotes = []
    errors = []
    
    for symbol in request.symbols:
        try:
            # Fetch quote for each symbol
            quote = fetch_quote(symbol)  # Your implementation
            quotes.append(quote)
        except Exception as e:
            errors.append({
                "symbol": symbol,
                "error": str(e),
                "error_type": "fetch_failed"
            })
    
    batch_data = BatchQuoteData(
        quotes=quotes,
        successful=len(quotes),
        failed=len(errors),
        errors=errors
    )
    
    return BatchQuoteResponse(
        success=True,
        message=f"Retrieved {len(quotes)} quotes, {len(errors)} failed",
        data=batch_data,
        timestamp=datetime.utcnow()
    )
```

## Testing Examples

### Unit Tests

```python
import pytest
from app.schemas.securities import SecurityQuote, SecurityType, ExchangeCode

def test_security_quote_validation():
    # Valid quote
    quote = SecurityQuote(
        symbol="AAPL",
        name="Apple Inc.",
        price=Decimal("150.25"),
        change=Decimal("2.15"),
        change_percent=Decimal("1.45"),
        volume=1250000,
        day_high=Decimal("152.10"),
        day_low=Decimal("148.50"),
        previous_close=Decimal("148.10"),
        open_price=Decimal("149.00"),
        exchange=ExchangeCode.NASDAQ,
        market_status=MarketStatus.OPEN,
        last_update=datetime.utcnow()
    )
    
    assert quote.symbol == "AAPL"
    assert quote.price == Decimal("150.25")
    assert quote.exchange == ExchangeCode.NASDAQ

def test_invalid_symbol():
    with pytest.raises(ValidationError):
        SecurityQuote(
            symbol="",  # Invalid: empty symbol
            name="Test",
            price=Decimal("100"),
            # ... other required fields
        )

def test_invalid_price():
    with pytest.raises(ValidationError):
        SecurityQuote(
            symbol="TEST",
            name="Test",
            price=Decimal("-100"),  # Invalid: negative price
            # ... other required fields
        )
```

### Integration Tests

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_quote_success():
    response = client.get("/api/v1/securities/quote/AAPL")
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate response structure
    assert data["success"] is True
    assert "data" in data
    assert "timestamp" in data
    
    # Validate quote data
    quote = data["data"]
    assert quote["symbol"] == "AAPL"
    assert "price" in quote
    assert "change" in quote

def test_get_quote_invalid_symbol():
    response = client.get("/api/v1/securities/quote/INVALID_SYMBOL_TOO_LONG")
    
    assert response.status_code == 400
    data = response.json()
    
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["type"] == "validation_error"
```

## Production Considerations

### Error Handling Strategy

```python
from app.schemas.base import BaseResponse, ErrorDetail, ErrorType
import logging

logger = logging.getLogger(__name__)

def handle_api_error(e: Exception, context: str = "") -> BaseResponse[None]:
    """Centralized error handling for API endpoints."""
    
    if isinstance(e, ValidationError):
        return BaseResponse[None](
            success=False,
            error=ErrorDetail(
                code=400,
                message="Validation failed",
                type=ErrorType.VALIDATION_ERROR,
                details={"validation_errors": e.errors()}
            ),
            timestamp=datetime.utcnow()
        )
    
    elif isinstance(e, HTTPException):
        error_type_map = {
            401: ErrorType.AUTHENTICATION_ERROR,
            403: ErrorType.AUTHORIZATION_ERROR,
            404: ErrorType.NOT_FOUND_ERROR,
            429: ErrorType.RATE_LIMIT_ERROR
        }
        
        return BaseResponse[None](
            success=False,
            error=ErrorDetail(
                code=e.status_code,
                message=str(e.detail),
                type=error_type_map.get(e.status_code, ErrorType.INTERNAL_ERROR)
            ),
            timestamp=datetime.utcnow()
        )
    
    else:
        # Log unexpected errors
        logger.error(f"Unexpected error in {context}: {e}", exc_info=True)
        
        return BaseResponse[None](
            success=False,
            error=ErrorDetail(
                code=500,
                message="Internal server error",
                type=ErrorType.INTERNAL_ERROR
            ),
            timestamp=datetime.utcnow()
        )
```

### Data Provider Integration

```python
from app.schemas.base import DataProviderInfo

class DataProviderClient:
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
    
    def create_provider_info(self, cache_hit: bool = False) -> DataProviderInfo:
        return DataProviderInfo(
            name=self.provider_name,
            source=f"{self.provider_name.title()} API",
            timestamp=datetime.utcnow(),
            rate_limit_remaining=self.get_rate_limit_remaining(),
            cache_hit=cache_hit
        )
    
    def get_rate_limit_remaining(self) -> Optional[int]:
        # Implementation to check rate limits
        return 995
```

### Monitoring and Observability

```python
import time
from app.schemas.base import BaseResponse

def track_api_performance(endpoint_name: str):
    """Decorator to track API performance metrics."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Track success metrics
                processing_time = (time.time() - start_time) * 1000
                logger.info(f"{endpoint_name} completed in {processing_time:.2f}ms")
                
                return result
                
            except Exception as e:
                # Track error metrics
                processing_time = (time.time() - start_time) * 1000
                logger.error(f"{endpoint_name} failed after {processing_time:.2f}ms: {e}")
                raise
                
        return wrapper
    return decorator

@track_api_performance("get_stock_quote")
@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    # Implementation
    pass
```

This guide provides the foundation for effectively using the Archelyst API schemas in your development workflow. The schemas ensure type safety, consistent API responses, and comprehensive validation across all endpoints.