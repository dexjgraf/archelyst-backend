"""
Security utilities for Archelyst backend.

Provides JWT token handling, password hashing, authentication dependencies,
and integration with Supabase for hybrid authentication architecture.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import hashlib

from .config import settings

# ============================================================================
# Logger Setup
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# Security Configuration
# ============================================================================

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme for FastAPI
security_scheme = HTTPBearer(auto_error=False)

# ============================================================================
# Password Hashing Utilities
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT Token Utilities (Local Backend Tokens)
# ============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token for backend authentication.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time (defaults to config setting)
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    
    # Create token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT access token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Dict[str, Any]: Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_refresh_token(user_id: str) -> str:
    """
    Create a refresh token for token renewal.
    
    Args:
        user_id: User identifier
        
    Returns:
        str: Refresh token
    """
    data = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=30)  # 30 days for refresh
    }
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ============================================================================
# Supabase JWT Integration
# ============================================================================

def validate_supabase_token(token: str) -> Dict[str, Any]:
    """
    Validate Supabase JWT token and extract user information.
    
    This function validates JWT tokens issued by Supabase for frontend
    authentication, enabling hybrid architecture where frontend uses
    Supabase and backend validates those tokens.
    
    Args:
        token: Supabase JWT token
        
    Returns:
        Dict[str, Any]: User information from token
        
    Raises:
        HTTPException: If token is invalid or Supabase not configured
    """
    if not settings.SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Supabase authentication not configured"
        )
    
    try:
        # Decode Supabase JWT token
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        # Extract user information
        user_info = {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated"),
            "aud": payload.get("aud"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
            "iss": payload.get("iss"),
            "provider": "supabase"
        }
        
        # Validate required fields
        if not user_info["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        logger.debug(f"Validated Supabase token for user: {user_info['user_id']}")
        return user_info
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid Supabase token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Supabase token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# API Key Utilities
# ============================================================================

def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        str: Generated API key
    """
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.
    
    Args:
        api_key: API key to hash
        
    Returns:
        str: Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.
    
    Args:
        api_key: Plain API key
        hashed_key: Hashed API key to verify against
        
    Returns:
        bool: True if API key matches, False otherwise
    """
    return hash_api_key(api_key) == hashed_key


# ============================================================================
# Authentication Dependencies for FastAPI
# ============================================================================

async def get_current_user_supabase(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current user from Supabase JWT token.
    
    This is the primary authentication method for frontend users.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict[str, Any]: Current user information
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return validate_supabase_token(credentials.credentials)


async def get_current_user_optional_supabase(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to optionally get current user from Supabase JWT token.
    
    Returns None if no authentication provided, validates if token present.
    
    Args:
        credentials: HTTP authorization credentials (optional)
        
    Returns:
        Optional[Dict[str, Any]]: Current user information or None
    """
    if not credentials:
        return None
    
    try:
        return validate_supabase_token(credentials.credentials)
    except HTTPException:
        return None


async def get_current_user_backend(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current user from backend JWT token.
    
    This is for backend-issued tokens (admin, service accounts, etc.).
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict[str, Any]: Current user information
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = verify_access_token(credentials.credentials)
    
    # Extract user information from backend token
    user_info = {
        "user_id": payload.get("sub"),
        "username": payload.get("username"),
        "email": payload.get("email"),
        "role": payload.get("role", "user"),
        "provider": "backend",
        "exp": payload.get("exp"),
        "iat": payload.get("iat")
    }
    
    if not user_info["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID"
        )
    
    return user_info


async def get_current_user_hybrid(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency that accepts both Supabase and backend JWT tokens.
    
    Tries Supabase validation first, then backend validation.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict[str, Any]: Current user information
        
    Raises:
        HTTPException: If authentication fails with both methods
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Try Supabase validation first (primary for frontend users)
    if settings.SUPABASE_JWT_SECRET:
        try:
            return validate_supabase_token(token)
        except HTTPException:
            pass  # Fall through to backend validation
    
    # Try backend validation
    try:
        payload = verify_access_token(token)
        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "role": payload.get("role", "user"),
            "provider": "backend",
            "exp": payload.get("exp"),
            "iat": payload.get("iat")
        }
    except HTTPException:
        pass
    
    # Both methods failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ============================================================================
# API Key Authentication Dependencies
# ============================================================================

async def validate_api_key_dependency(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency for API key authentication.
    
    For service-to-service authentication or external integrations.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict[str, Any]: API key information
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In a real implementation, you would validate against stored API keys
    # For now, we'll implement a basic validation structure
    api_key = credentials.credentials
    
    # TODO: Implement actual API key validation against database
    # This would typically involve:
    # 1. Look up the API key in the database
    # 2. Verify it's active and not expired
    # 3. Return associated metadata
    
    return {
        "api_key": api_key,
        "type": "api_key",
        "validated": True
    }


# ============================================================================
# Role-Based Access Control
# ============================================================================

def require_role(required_role: str):
    """
    Create a dependency that requires a specific user role.
    
    Args:
        required_role: Required role for access
        
    Returns:
        Dependency function
    """
    async def role_dependency(
        current_user: Dict[str, Any] = Depends(get_current_user_hybrid)
    ) -> Dict[str, Any]:
        user_role = current_user.get("role", "user")
        
        # Define role hierarchy
        role_hierarchy = {
            "user": 0,
            "premium": 1,
            "creator": 2,
            "admin": 3,
            "superuser": 4
        }
        
        required_level = role_hierarchy.get(required_role, 0)
        user_level = role_hierarchy.get(user_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return current_user
    
    return role_dependency


def require_admin():
    """Dependency that requires admin role."""
    return require_role("admin")


def require_premium():
    """Dependency that requires premium role or higher."""
    return require_role("premium")


# ============================================================================
# Security Utilities
# ============================================================================

def generate_csrf_token() -> str:
    """
    Generate a CSRF token.
    
    Returns:
        str: CSRF token
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected_token: str) -> bool:
    """
    Verify a CSRF token.
    
    Args:
        token: Token to verify
        expected_token: Expected token value
        
    Returns:
        bool: True if tokens match, False otherwise
    """
    return secrets.compare_digest(token, expected_token)


def create_password_reset_token(user_id: str) -> str:
    """
    Create a password reset token.
    
    Args:
        user_id: User identifier
        
    Returns:
        str: Password reset token
    """
    data = {
        "sub": user_id,
        "type": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hours
    }
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password_reset_token(token: str) -> str:
    """
    Verify a password reset token and return user ID.
    
    Args:
        token: Password reset token
        
    Returns:
        str: User ID
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token: missing user ID"
            )
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired"
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token"
        )


# ============================================================================
# Security Headers and Middleware Utilities
# ============================================================================

def get_security_headers() -> Dict[str, str]:
    """
    Get recommended security headers for API responses.
    
    Returns:
        Dict[str, str]: Security headers
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'",
    }


# ============================================================================
# Token Introspection and Management
# ============================================================================

def get_token_info(token: str) -> Dict[str, Any]:
    """
    Get information about a token without full validation.
    
    Args:
        token: JWT token
        
    Returns:
        Dict[str, Any]: Token information
    """
    try:
        # Decode without verification to get header and payload info
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
        
        return {
            "header": header,
            "payload": payload,
            "user_id": payload.get("sub"),
            "expires_at": payload.get("exp"),
            "issued_at": payload.get("iat"),
            "algorithm": header.get("alg"),
            "token_type": payload.get("type", "access")
        }
    except Exception as e:
        logger.warning(f"Failed to get token info: {e}")
        return {"error": str(e)}


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired without full validation.
    
    Args:
        token: JWT token
        
    Returns:
        bool: True if expired, False otherwise
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc)
        return False
    except Exception:
        return True


# ============================================================================
# Export All Public APIs
# ============================================================================

__all__ = [
    # Password utilities
    "hash_password",
    "verify_password",
    
    # JWT utilities (backend)
    "create_access_token",
    "verify_access_token",
    "create_refresh_token",
    
    # Supabase integration
    "validate_supabase_token",
    
    # API key utilities
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    
    # FastAPI dependencies
    "get_current_user_supabase",
    "get_current_user_optional_supabase",
    "get_current_user_backend",
    "get_current_user_hybrid",
    "validate_api_key_dependency",
    
    # Role-based access control
    "require_role",
    "require_admin",
    "require_premium",
    
    # Security utilities
    "generate_csrf_token",
    "verify_csrf_token",
    "create_password_reset_token",
    "verify_password_reset_token",
    "get_security_headers",
    
    # Token management
    "get_token_info",
    "is_token_expired",
    
    # Security scheme
    "security_scheme",
]