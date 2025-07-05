"""
Base Pydantic schemas for API responses.

Provides foundational response models and common schemas used across all API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, Field, validator


# ============================================================================
# Generic Types and Enums
# ============================================================================

DataT = TypeVar('DataT')

class ResponseStatus(str, Enum):
    """Standard response status values."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class ErrorType(str, Enum):
    """Standard error type classifications."""
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND_ERROR = "not_found_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    PROVIDER_ERROR = "provider_error"
    INTERNAL_ERROR = "internal_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"


# ============================================================================
# Base Response Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail information."""
    
    code: int = Field(
        ..., 
        description="HTTP status code or custom error code",
        example=400,
        ge=100,
        le=599
    )
    message: str = Field(
        ..., 
        description="Human-readable error message",
        example="Invalid input provided"
    )
    type: ErrorType = Field(
        ..., 
        description="Error type classification",
        example=ErrorType.VALIDATION_ERROR
    )
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional error context and details",
        example={"field": "symbol", "issue": "Symbol must be 1-10 characters"}
    )
    trace_id: Optional[str] = Field(
        None, 
        description="Request trace ID for debugging",
        example="req_1234567890abcdef"
    )


class BaseResponse(BaseModel, Generic[DataT]):
    """
    Generic base response model for all API endpoints.
    
    Provides consistent structure for success and error responses across the API.
    """
    
    success: bool = Field(
        ..., 
        description="Indicates if the request was successful",
        example=True
    )
    message: Optional[str] = Field(
        None, 
        description="Optional human-readable message",
        example="Data retrieved successfully"
    )
    data: Optional[DataT] = Field(
        None, 
        description="Response data (present on success)"
    )
    error: Optional[ErrorDetail] = Field(
        None, 
        description="Error details (present on failure)"
    )
    timestamp: Optional[datetime] = Field(
        None,
        description="Response timestamp in UTC",
        example="2024-07-04T15:30:00Z"
    )
    request_id: Optional[str] = Field(
        None, 
        description="Unique request identifier",
        example="req_1234567890abcdef"
    )
    
    @validator('error')
    def error_present_when_not_success(cls, v, values):
        """Ensure error is present when success is False."""
        success = values.get('success')
        if not success and v is None:
            raise ValueError('Error details must be provided when success is False')
        if success and v is not None:
            raise ValueError('Error details should not be provided when success is True')
        return v


# ============================================================================
# Common Data Models
# ============================================================================

class PaginationInfo(BaseModel):
    """Pagination information for list responses."""
    
    page: int = Field(
        ..., 
        description="Current page number (1-based)",
        example=1,
        ge=1
    )
    page_size: int = Field(
        ..., 
        description="Number of items per page",
        example=20,
        ge=1,
        le=1000
    )
    total_items: int = Field(
        ..., 
        description="Total number of items available",
        example=150,
        ge=0
    )
    total_pages: int = Field(
        ..., 
        description="Total number of pages",
        example=8,
        ge=0
    )
    has_next: bool = Field(
        ..., 
        description="Whether there are more pages after current",
        example=True
    )
    has_previous: bool = Field(
        ..., 
        description="Whether there are pages before current",
        example=False
    )


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Generic paginated response wrapper."""
    
    items: List[DataT] = Field(
        ..., 
        description="List of items for current page"
    )
    pagination: PaginationInfo = Field(
        ..., 
        description="Pagination metadata"
    )


class HealthStatus(BaseModel):
    """Health check status information."""
    
    status: str = Field(
        ..., 
        description="Overall health status",
        example="healthy"
    )
    version: str = Field(
        ..., 
        description="Application version",
        example="1.0.0"
    )
    environment: str = Field(
        ..., 
        description="Current environment",
        example="development"
    )
    uptime_seconds: Optional[float] = Field(
        None, 
        description="Application uptime in seconds",
        example=3600.5
    )
    checks: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Individual component health checks",
        example={
            "database": {
                "status": "healthy", 
                "response_time_ms": 15,
                "connection_pool": "active",
                "last_migration": "2024-07-04T10:00:00Z"
            },
            "redis": {
                "status": "healthy", 
                "response_time_ms": 2,
                "memory_usage": "45%",
                "connected_clients": 12
            },
            "external_apis": {
                "financial_data_provider": {
                    "status": "healthy",
                    "response_time_ms": 145,
                    "rate_limit_remaining": 995
                },
                "ai_service": {
                    "status": "healthy",
                    "response_time_ms": 890,
                    "queue_depth": 3
                }
            }
        }
    )


# ============================================================================
# Request Models
# ============================================================================

class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    
    page: int = Field(
        1, 
        description="Page number (1-based)",
        example=1,
        ge=1
    )
    page_size: int = Field(
        20, 
        description="Number of items per page",
        example=20,
        ge=1,
        le=1000
    )


class SortParams(BaseModel):
    """Standard sorting parameters."""
    
    sort_by: Optional[str] = Field(
        None, 
        description="Field to sort by",
        example="created_at"
    )
    sort_order: Optional[str] = Field(
        "asc", 
        description="Sort direction",
        example="desc",
        regex="^(asc|desc)$"
    )


class DateRangeParams(BaseModel):
    """Date range filter parameters."""
    
    start_date: Optional[datetime] = Field(
        None, 
        description="Start date for filtering (ISO 8601)",
        example="2024-01-01T00:00:00Z"
    )
    end_date: Optional[datetime] = Field(
        None, 
        description="End date for filtering (ISO 8601)",
        example="2024-12-31T23:59:59Z"
    )
    
    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        """Ensure end_date is after start_date if both are provided."""
        start_date = values.get('start_date')
        if start_date and v and v <= start_date:
            raise ValueError('end_date must be after start_date')
        return v


# ============================================================================
# Metadata Models
# ============================================================================

class DataProviderInfo(BaseModel):
    """Information about data provider for response."""
    
    name: str = Field(
        ..., 
        description="Provider name",
        example="financial_modeling_prep"
    )
    source: str = Field(
        ..., 
        description="Data source description",
        example="Financial Modeling Prep API"
    )
    timestamp: datetime = Field(
        ..., 
        description="When the data was retrieved",
        example="2024-07-04T15:30:00Z"
    )
    rate_limit_remaining: Optional[int] = Field(
        None, 
        description="Remaining API calls for provider",
        example=995
    )
    cache_hit: bool = Field(
        False, 
        description="Whether data was served from cache",
        example=False
    )


class APIMetadata(BaseModel):
    """API response metadata."""
    
    version: str = Field(
        "1.0.0", 
        description="API version",
        example="1.0.0"
    )
    endpoint: str = Field(
        ..., 
        description="Endpoint that served the request",
        example="/api/v1/securities/quote/AAPL"
    )
    execution_time_ms: Optional[float] = Field(
        None, 
        description="Request execution time in milliseconds",
        example=145.7
    )
    data_provider: Optional[DataProviderInfo] = Field(
        None, 
        description="Information about the data provider used"
    )


# ============================================================================
# Status Response Models
# ============================================================================

class StatusResponse(BaseResponse[Dict[str, Any]]):
    """Standard status response model."""
    pass


class HealthResponse(BaseResponse[HealthStatus]):
    """Health check response model."""
    pass


# ============================================================================
# Export all models
# ============================================================================

__all__ = [
    # Enums
    "ResponseStatus",
    "ErrorType",
    
    # Base models
    "ErrorDetail",
    "BaseResponse",
    "PaginatedResponse",
    "HealthStatus",
    
    # Request models
    "PaginationParams",
    "SortParams", 
    "DateRangeParams",
    
    # Metadata models
    "DataProviderInfo",
    "APIMetadata",
    "PaginationInfo",
    
    # Response models
    "StatusResponse",
    "HealthResponse"
]