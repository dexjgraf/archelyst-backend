"""
User and authentication Pydantic schemas.

Contains request and response models for user management, authentication,
and authorization functionality.
"""

from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, EmailStr, validator

from .base import BaseResponse, PaginatedResponse


# ============================================================================
# Enums and Constants
# ============================================================================

class UserRole(str, Enum):
    """User role levels."""
    USER = "user"
    PREMIUM = "premium"
    CREATOR = "creator"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class AuthProvider(str, Enum):
    """Authentication providers."""
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"
    APPLE = "apple"
    SUPABASE = "supabase"


class SubscriptionStatus(str, Enum):
    """Subscription status values."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRIAL = "trial"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RiskTolerance(str, Enum):
    """Investment risk tolerance levels."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    VERY_AGGRESSIVE = "very_aggressive"


# ============================================================================
# User Models
# ============================================================================

class UserBase(BaseModel):
    """Base user information."""
    
    email: EmailStr = Field(
        ..., 
        description="User email address",
        example="user@example.com"
    )
    username: Optional[str] = Field(
        None, 
        description="Unique username",
        example="john_doe",
        min_length=3,
        max_length=50,
        regex="^[a-zA-Z0-9_-]+$"
    )
    first_name: Optional[str] = Field(
        None, 
        description="First name",
        example="John",
        max_length=100
    )
    last_name: Optional[str] = Field(
        None, 
        description="Last name",
        example="Doe",
        max_length=100
    )
    display_name: Optional[str] = Field(
        None, 
        description="Display name",
        example="John D.",
        max_length=100
    )


class UserCreate(UserBase):
    """User creation request."""
    
    password: str = Field(
        ..., 
        description="User password",
        min_length=8,
        max_length=128
    )
    confirm_password: str = Field(
        ..., 
        description="Password confirmation"
    )
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Ensure passwords match."""
        if values.get('password') and v != values.get('password'):
            raise ValueError('Passwords do not match')
        return v


class UserUpdate(BaseModel):
    """User update request."""
    
    username: Optional[str] = Field(
        None, 
        description="Username",
        min_length=3,
        max_length=50,
        regex="^[a-zA-Z0-9_-]+$"
    )
    first_name: Optional[str] = Field(
        None, 
        description="First name",
        max_length=100
    )
    last_name: Optional[str] = Field(
        None, 
        description="Last name",
        max_length=100
    )
    display_name: Optional[str] = Field(
        None, 
        description="Display name",
        max_length=100
    )
    bio: Optional[str] = Field(
        None, 
        description="User biography",
        max_length=500
    )
    timezone: Optional[str] = Field(
        None, 
        description="User timezone",
        example="America/New_York"
    )
    preferences: Optional[Dict[str, Any]] = Field(
        None, 
        description="User preferences",
        example={"theme": "dark", "notifications": True}
    )


class UserProfile(UserBase):
    """Complete user profile information."""
    
    id: str = Field(
        ..., 
        description="Unique user ID",
        example="user_123456789"
    )
    role: UserRole = Field(
        ..., 
        description="User role",
        example=UserRole.USER
    )
    is_active: bool = Field(
        ..., 
        description="Whether user account is active",
        example=True
    )
    email_verified: bool = Field(
        ..., 
        description="Whether email is verified",
        example=True
    )
    bio: Optional[str] = Field(
        None, 
        description="User biography",
        example="Financial analyst and investor"
    )
    timezone: Optional[str] = Field(
        None, 
        description="User timezone",
        example="America/New_York"
    )
    avatar_url: Optional[str] = Field(
        None, 
        description="Profile picture URL",
        example="https://example.com/avatar.jpg"
    )
    created_at: datetime = Field(
        ..., 
        description="Account creation timestamp",
        example="2024-01-15T10:30:00Z"
    )
    updated_at: datetime = Field(
        ..., 
        description="Last profile update timestamp",
        example="2024-07-04T15:30:00Z"
    )
    last_login: Optional[datetime] = Field(
        None, 
        description="Last login timestamp",
        example="2024-07-04T09:15:00Z"
    )
    # Financial preferences
    risk_tolerance: Optional[RiskTolerance] = Field(
        None, 
        description="Investment risk tolerance",
        example=RiskTolerance.MODERATE
    )
    investment_experience: Optional[str] = Field(
        None, 
        description="Investment experience level",
        example="intermediate"
    )
    preferred_currencies: List[str] = Field(
        default_factory=lambda: ["USD"], 
        description="Preferred currencies for display",
        example=["USD", "EUR"]
    )
    # Subscription info
    subscription_status: SubscriptionStatus = Field(
        SubscriptionStatus.INACTIVE, 
        description="Subscription status",
        example=SubscriptionStatus.ACTIVE
    )
    subscription_expires: Optional[datetime] = Field(
        None, 
        description="Subscription expiration date",
        example="2024-12-31T23:59:59Z"
    )
    # Usage statistics
    api_calls_used: int = Field(
        0, 
        description="API calls used this period",
        example=1250,
        ge=0
    )
    api_calls_limit: int = Field(
        1000, 
        description="API calls limit for current plan",
        example=5000,
        ge=0
    )

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }


class UserResponse(BaseResponse[UserProfile]):
    """User profile API response."""
    pass


class UserListResponse(BaseResponse[PaginatedResponse[UserProfile]]):
    """Paginated users list API response."""
    pass


# ============================================================================
# Authentication Models
# ============================================================================

class LoginRequest(BaseModel):
    """User login request."""
    
    email: EmailStr = Field(
        ..., 
        description="User email",
        example="user@example.com"
    )
    password: str = Field(
        ..., 
        description="User password",
        min_length=8
    )
    remember_me: bool = Field(
        False, 
        description="Whether to remember the login",
        example=False
    )


class TokenResponse(BaseModel):
    """Authentication token response."""
    
    access_token: str = Field(
        ..., 
        description="JWT access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    refresh_token: Optional[str] = Field(
        None, 
        description="JWT refresh token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        "bearer", 
        description="Token type",
        example="bearer"
    )
    expires_in: int = Field(
        ..., 
        description="Token expiration time in seconds",
        example=3600
    )
    user: UserProfile = Field(
        ..., 
        description="User profile information"
    )


class LoginResponse(BaseResponse[TokenResponse]):
    """Login API response."""
    pass


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""
    
    refresh_token: str = Field(
        ..., 
        description="Refresh token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    
    email: EmailStr = Field(
        ..., 
        description="User email",
        example="user@example.com"
    )


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    
    token: str = Field(
        ..., 
        description="Reset token",
        example="abc123def456"
    )
    new_password: str = Field(
        ..., 
        description="New password",
        min_length=8,
        max_length=128
    )
    confirm_password: str = Field(
        ..., 
        description="Password confirmation"
    )
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Ensure passwords match."""
        if values.get('new_password') and v != values.get('new_password'):
            raise ValueError('Passwords do not match')
        return v


class ChangePasswordRequest(BaseModel):
    """Password change request."""
    
    current_password: str = Field(
        ..., 
        description="Current password"
    )
    new_password: str = Field(
        ..., 
        description="New password",
        min_length=8,
        max_length=128
    )
    confirm_password: str = Field(
        ..., 
        description="Password confirmation"
    )
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Ensure passwords match."""
        if values.get('new_password') and v != values.get('new_password'):
            raise ValueError('Passwords do not match')
        return v


# ============================================================================
# API Key Models
# ============================================================================

class APIKeyCreate(BaseModel):
    """API key creation request."""
    
    name: str = Field(
        ..., 
        description="API key name",
        example="My Trading Bot",
        min_length=1,
        max_length=100
    )
    description: Optional[str] = Field(
        None, 
        description="API key description",
        example="API key for automated trading system",
        max_length=500
    )
    permissions: List[str] = Field(
        default_factory=list, 
        description="API key permissions",
        example=["read:quotes", "read:market"]
    )
    expires_in_days: Optional[int] = Field(
        None, 
        description="Expiration in days (null for no expiration)",
        example=365,
        ge=1,
        le=3650
    )


class APIKey(BaseModel):
    """API key information."""
    
    id: str = Field(
        ..., 
        description="API key ID",
        example="key_123456789"
    )
    name: str = Field(
        ..., 
        description="API key name",
        example="My Trading Bot"
    )
    description: Optional[str] = Field(
        None, 
        description="API key description"
    )
    key_preview: str = Field(
        ..., 
        description="API key preview (first 8 chars)",
        example="ak_12345..."
    )
    permissions: List[str] = Field(
        ..., 
        description="API key permissions",
        example=["read:quotes", "read:market"]
    )
    is_active: bool = Field(
        ..., 
        description="Whether API key is active",
        example=True
    )
    created_at: datetime = Field(
        ..., 
        description="Creation timestamp",
        example="2024-01-15T10:30:00Z"
    )
    expires_at: Optional[datetime] = Field(
        None, 
        description="Expiration timestamp",
        example="2025-01-15T10:30:00Z"
    )
    last_used: Optional[datetime] = Field(
        None, 
        description="Last usage timestamp",
        example="2024-07-04T09:15:00Z"
    )
    usage_count: int = Field(
        0, 
        description="Total usage count",
        example=1543,
        ge=0
    )


class APIKeyWithSecret(APIKey):
    """API key with secret (only returned on creation)."""
    
    secret_key: str = Field(
        ..., 
        description="Full API key secret",
        example="ak_123456789abcdef0123456789abcdef0123456789"
    )


class APIKeyResponse(BaseResponse[APIKeyWithSecret]):
    """API key creation response."""
    pass


class APIKeyListResponse(BaseResponse[List[APIKey]]):
    """API keys list response."""
    pass


# ============================================================================
# Session Models
# ============================================================================

class UserSession(BaseModel):
    """User session information."""
    
    id: str = Field(
        ..., 
        description="Session ID",
        example="sess_123456789"
    )
    user_id: str = Field(
        ..., 
        description="User ID",
        example="user_123456789"
    )
    ip_address: Optional[str] = Field(
        None, 
        description="IP address",
        example="192.168.1.100"
    )
    user_agent: Optional[str] = Field(
        None, 
        description="User agent",
        example="Mozilla/5.0..."
    )
    location: Optional[str] = Field(
        None, 
        description="Approximate location",
        example="New York, NY, US"
    )
    is_current: bool = Field(
        ..., 
        description="Whether this is the current session",
        example=True
    )
    created_at: datetime = Field(
        ..., 
        description="Session creation timestamp",
        example="2024-07-04T09:15:00Z"
    )
    last_activity: datetime = Field(
        ..., 
        description="Last activity timestamp",
        example="2024-07-04T15:30:00Z"
    )
    expires_at: datetime = Field(
        ..., 
        description="Session expiration timestamp",
        example="2024-07-18T09:15:00Z"
    )


class SessionListResponse(BaseResponse[List[UserSession]]):
    """User sessions list response."""
    pass


# ============================================================================
# Preferences Models
# ============================================================================

class NotificationPreferences(BaseModel):
    """User notification preferences."""
    
    email_notifications: bool = Field(
        True, 
        description="Email notifications enabled",
        example=True
    )
    push_notifications: bool = Field(
        False, 
        description="Push notifications enabled",
        example=False
    )
    market_alerts: bool = Field(
        True, 
        description="Market alerts enabled",
        example=True
    )
    portfolio_updates: bool = Field(
        True, 
        description="Portfolio update notifications",
        example=True
    )
    news_updates: bool = Field(
        False, 
        description="News update notifications",
        example=False
    )
    ai_insights: bool = Field(
        True, 
        description="AI insights notifications",
        example=True
    )


class DisplayPreferences(BaseModel):
    """User display preferences."""
    
    theme: str = Field(
        "light", 
        description="UI theme",
        example="dark"
    )
    currency: str = Field(
        "USD", 
        description="Primary display currency",
        example="USD"
    )
    date_format: str = Field(
        "YYYY-MM-DD", 
        description="Date format preference",
        example="MM/DD/YYYY"
    )
    time_format: str = Field(
        "24h", 
        description="Time format preference",
        example="12h"
    )
    decimal_places: int = Field(
        2, 
        description="Decimal places for prices",
        example=4,
        ge=0,
        le=8
    )


class UserPreferences(BaseModel):
    """Complete user preferences."""
    
    notifications: NotificationPreferences = Field(
        default_factory=NotificationPreferences, 
        description="Notification preferences"
    )
    display: DisplayPreferences = Field(
        default_factory=DisplayPreferences, 
        description="Display preferences"
    )
    risk_tolerance: RiskTolerance = Field(
        RiskTolerance.MODERATE, 
        description="Risk tolerance",
        example=RiskTolerance.MODERATE
    )
    watchlists: List[str] = Field(
        default_factory=list, 
        description="Default watchlist symbols",
        example=["AAPL", "MSFT", "GOOGL"]
    )
    custom_settings: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Custom user settings",
        example={"auto_refresh": True, "chart_type": "candlestick"}
    )


class PreferencesResponse(BaseResponse[UserPreferences]):
    """User preferences API response."""
    pass


# ============================================================================
# Export all models
# ============================================================================

__all__ = [
    # Enums
    "UserRole",
    "AuthProvider",
    "SubscriptionStatus",
    "RiskTolerance",
    
    # User models
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserProfile",
    "UserResponse",
    "UserListResponse",
    
    # Authentication models
    "LoginRequest",
    "TokenResponse",
    "LoginResponse",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "ChangePasswordRequest",
    
    # API key models
    "APIKeyCreate",
    "APIKey",
    "APIKeyWithSecret",
    "APIKeyResponse",
    "APIKeyListResponse",
    
    # Session models
    "UserSession",
    "SessionListResponse",
    
    # Preferences models
    "NotificationPreferences",
    "DisplayPreferences",
    "UserPreferences",
    "PreferencesResponse"
]