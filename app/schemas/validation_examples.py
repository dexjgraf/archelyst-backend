"""
Validation Examples for Archelyst API Schemas

This file demonstrates the validation capabilities and error handling
patterns for all Pydantic schemas in the application.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List
import pytest
from pydantic import ValidationError

from .securities import SecurityQuote, SecurityType, ExchangeCode, MarketStatus
from .market import MarketOverview, IndexData, IndexType, MarketRegion
from .users import UserCreate, UserProfile, UserRole, APIKeyCreate
from .ai import StockAnalysisRequest, AnalysisType, TimeHorizon
from .base import BaseResponse, ErrorDetail, ErrorType


class ValidationExamples:
    """Collection of validation examples and test cases."""
    
    @staticmethod
    def valid_security_quote_examples():
        """Examples of valid SecurityQuote instances."""
        return [
            # Minimal valid quote
            SecurityQuote(
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
            ),
            
            # Complete quote with all optional fields
            SecurityQuote(
                symbol="MSFT",
                name="Microsoft Corporation",
                price=Decimal("420.75"),
                change=Decimal("-3.25"),
                change_percent=Decimal("-0.77"),
                volume=25847392,
                avg_volume=35234567,
                market_cap=3120000000000,
                pe_ratio=Decimal("31.25"),
                day_high=Decimal("425.50"),
                day_low=Decimal("418.90"),
                previous_close=Decimal("424.00"),
                open_price=Decimal("422.15"),
                week_52_high=Decimal("468.35"),
                week_52_low=Decimal("309.45"),
                exchange=ExchangeCode.NASDAQ,
                currency="USD",
                market_status=MarketStatus.CLOSED,
                last_update=datetime.utcnow(),
                extended_hours_price=Decimal("421.25"),
                extended_hours_change=Decimal("0.50")
            )
        ]
    
    @staticmethod
    def invalid_security_quote_examples():
        """Examples of invalid SecurityQuote data that should raise ValidationError."""
        return [
            # Empty symbol
            {
                "data": {
                    "symbol": "",
                    "name": "Test Company",
                    "price": 100.0,
                    "change": 1.0,
                    "change_percent": 1.0,
                    "volume": 1000,
                    "day_high": 101.0,
                    "day_low": 99.0,
                    "previous_close": 99.0,
                    "open_price": 99.5,
                    "exchange": "NASDAQ",
                    "market_status": "open",
                    "last_update": datetime.utcnow()
                },
                "expected_error": "Symbol must be at least 1 character"
            },
            
            # Symbol too long
            {
                "data": {
                    "symbol": "VERYLONGSYMBOLNAME",
                    "name": "Test Company",
                    "price": 100.0,
                    "change": 1.0,
                    "change_percent": 1.0,
                    "volume": 1000,
                    "day_high": 101.0,
                    "day_low": 99.0,
                    "previous_close": 99.0,
                    "open_price": 99.5,
                    "exchange": "NASDAQ",
                    "market_status": "open",
                    "last_update": datetime.utcnow()
                },
                "expected_error": "Symbol cannot exceed 20 characters"
            },
            
            # Negative price
            {
                "data": {
                    "symbol": "TEST",
                    "name": "Test Company",
                    "price": -100.0,
                    "change": 1.0,
                    "change_percent": 1.0,
                    "volume": 1000,
                    "day_high": 101.0,
                    "day_low": 99.0,
                    "previous_close": 99.0,
                    "open_price": 99.5,
                    "exchange": "NASDAQ",
                    "market_status": "open",
                    "last_update": datetime.utcnow()
                },
                "expected_error": "Price must be positive"
            },
            
            # Negative volume
            {
                "data": {
                    "symbol": "TEST",
                    "name": "Test Company",
                    "price": 100.0,
                    "change": 1.0,
                    "change_percent": 1.0,
                    "volume": -1000,
                    "day_high": 101.0,
                    "day_low": 99.0,
                    "previous_close": 99.0,
                    "open_price": 99.5,
                    "exchange": "NASDAQ",
                    "market_status": "open",
                    "last_update": datetime.utcnow()
                },
                "expected_error": "Volume cannot be negative"
            },
            
            # Invalid exchange code
            {
                "data": {
                    "symbol": "TEST",
                    "name": "Test Company",
                    "price": 100.0,
                    "change": 1.0,
                    "change_percent": 1.0,
                    "volume": 1000,
                    "day_high": 101.0,
                    "day_low": 99.0,
                    "previous_close": 99.0,
                    "open_price": 99.5,
                    "exchange": "INVALID_EXCHANGE",
                    "market_status": "open",
                    "last_update": datetime.utcnow()
                },
                "expected_error": "Invalid exchange code"
            }
        ]
    
    @staticmethod
    def valid_user_examples():
        """Examples of valid User data."""
        return [
            # Valid user creation
            UserCreate(
                email="john.doe@example.com",
                username="john_trader",
                first_name="John",
                last_name="Doe",
                password="SecurePass123!",
                confirm_password="SecurePass123!"
            ),
            
            # Valid API key creation
            APIKeyCreate(
                name="Trading Bot v1",
                description="API key for automated trading system",
                permissions=["read:quotes", "read:market", "read:profile"],
                expires_in_days=365
            )
        ]
    
    @staticmethod
    def invalid_user_examples():
        """Examples of invalid User data."""
        return [
            # Invalid email format
            {
                "data": {
                    "email": "invalid-email",
                    "username": "test_user",
                    "password": "password123",
                    "confirm_password": "password123"
                },
                "expected_error": "Invalid email format"
            },
            
            # Password mismatch
            {
                "data": {
                    "email": "user@example.com",
                    "username": "test_user",
                    "password": "password123",
                    "confirm_password": "different_password"
                },
                "expected_error": "Passwords do not match"
            },
            
            # Username too short
            {
                "data": {
                    "email": "user@example.com",
                    "username": "ab",
                    "password": "password123",
                    "confirm_password": "password123"
                },
                "expected_error": "Username must be at least 3 characters"
            },
            
            # Invalid username characters
            {
                "data": {
                    "email": "user@example.com",
                    "username": "user@name",
                    "password": "password123",
                    "confirm_password": "password123"
                },
                "expected_error": "Username can only contain letters, numbers, hyphens, and underscores"
            }
        ]
    
    @staticmethod
    def valid_ai_request_examples():
        """Examples of valid AI analysis requests."""
        return [
            # Basic stock analysis request
            StockAnalysisRequest(
                symbol="AAPL",
                analysis_types=[AnalysisType.FUNDAMENTAL, AnalysisType.TECHNICAL],
                time_horizon=TimeHorizon.MEDIUM_TERM,
                include_competitors=True,
                include_news_sentiment=True
            ),
            
            # Comprehensive analysis request
            StockAnalysisRequest(
                symbol="MSFT",
                analysis_types=[
                    AnalysisType.FUNDAMENTAL,
                    AnalysisType.TECHNICAL,
                    AnalysisType.SENTIMENT,
                    AnalysisType.RISK
                ],
                time_horizon=TimeHorizon.LONG_TERM,
                include_competitors=True,
                include_news_sentiment=True,
                custom_prompt="Focus on cloud computing revenue growth and AI market positioning"
            )
        ]
    
    @staticmethod
    def invalid_ai_request_examples():
        """Examples of invalid AI analysis requests."""
        return [
            # Empty symbol
            {
                "data": {
                    "symbol": "",
                    "analysis_types": ["fundamental"],
                    "time_horizon": "medium_term"
                },
                "expected_error": "Symbol is required"
            },
            
            # Symbol too long
            {
                "data": {
                    "symbol": "VERYLONGSYMBOL",
                    "analysis_types": ["fundamental"],
                    "time_horizon": "medium_term"
                },
                "expected_error": "Symbol cannot exceed 10 characters"
            },
            
            # Invalid analysis type
            {
                "data": {
                    "symbol": "AAPL",
                    "analysis_types": ["invalid_type"],
                    "time_horizon": "medium_term"
                },
                "expected_error": "Invalid analysis type"
            }
        ]
    
    @staticmethod
    def date_validation_examples():
        """Examples of date validation scenarios."""
        return [
            # Valid date range
            {
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 7, 4),
                "valid": True
            },
            
            # Same date (valid)
            {
                "start_date": date(2024, 7, 4),
                "end_date": date(2024, 7, 4),
                "valid": True
            },
            
            # End date before start date (invalid)
            {
                "start_date": date(2024, 7, 4),
                "end_date": date(2024, 1, 1),
                "valid": False,
                "expected_error": "end_date must be after start_date"
            }
        ]
    
    @staticmethod
    def decimal_precision_examples():
        """Examples of decimal precision validation."""
        return [
            # Valid decimal precision
            {
                "value": Decimal("123.45"),
                "decimal_places": 2,
                "valid": True
            },
            
            # Valid with fewer decimal places
            {
                "value": Decimal("123.4"),
                "decimal_places": 2,
                "valid": True
            },
            
            # Too many decimal places
            {
                "value": Decimal("123.456789"),
                "decimal_places": 2,
                "valid": False,
                "expected_error": "Too many decimal places"
            }
        ]
    
    @staticmethod
    def enum_validation_examples():
        """Examples of enum validation."""
        return [
            # Valid enum values
            {
                "security_type": SecurityType.STOCK,
                "exchange": ExchangeCode.NASDAQ,
                "market_status": MarketStatus.OPEN,
                "valid": True
            },
            
            # Invalid enum values (these would be caught by Pydantic)
            {
                "security_type": "invalid_type",
                "exchange": "INVALID_EXCHANGE",
                "market_status": "invalid_status",
                "valid": False
            }
        ]
    
    @staticmethod
    def run_validation_tests():
        """Run all validation tests and return results."""
        results = {
            "valid_examples": {
                "security_quotes": [],
                "users": [],
                "ai_requests": []
            },
            "invalid_examples": {
                "security_quotes": [],
                "users": [],
                "ai_requests": []
            }
        }
        
        # Test valid examples
        try:
            for quote in ValidationExamples.valid_security_quote_examples():
                quote.dict()  # This will validate the model
                results["valid_examples"]["security_quotes"].append("PASS")
        except Exception as e:
            results["valid_examples"]["security_quotes"].append(f"FAIL: {e}")
        
        try:
            for user in ValidationExamples.valid_user_examples():
                user.dict()  # This will validate the model
                results["valid_examples"]["users"].append("PASS")
        except Exception as e:
            results["valid_examples"]["users"].append(f"FAIL: {e}")
        
        try:
            for request in ValidationExamples.valid_ai_request_examples():
                request.dict()  # This will validate the model
                results["valid_examples"]["ai_requests"].append("PASS")
        except Exception as e:
            results["valid_examples"]["ai_requests"].append(f"FAIL: {e}")
        
        # Test invalid examples (should raise ValidationError)
        for example in ValidationExamples.invalid_security_quote_examples():
            try:
                SecurityQuote(**example["data"])
                results["invalid_examples"]["security_quotes"].append("FAIL: Should have raised ValidationError")
            except ValidationError:
                results["invalid_examples"]["security_quotes"].append("PASS: Correctly caught validation error")
            except Exception as e:
                results["invalid_examples"]["security_quotes"].append(f"UNEXPECTED: {e}")
        
        for example in ValidationExamples.invalid_user_examples():
            try:
                UserCreate(**example["data"])
                results["invalid_examples"]["users"].append("FAIL: Should have raised ValidationError")
            except ValidationError:
                results["invalid_examples"]["users"].append("PASS: Correctly caught validation error")
            except Exception as e:
                results["invalid_examples"]["users"].append(f"UNEXPECTED: {e}")
        
        for example in ValidationExamples.invalid_ai_request_examples():
            try:
                StockAnalysisRequest(**example["data"])
                results["invalid_examples"]["ai_requests"].append("FAIL: Should have raised ValidationError")
            except ValidationError:
                results["invalid_examples"]["ai_requests"].append("PASS: Correctly caught validation error")
            except Exception as e:
                results["invalid_examples"]["ai_requests"].append(f"UNEXPECTED: {e}")
        
        return results


def demonstrate_error_handling():
    """Demonstrate proper error handling patterns."""
    
    def handle_validation_error(e: ValidationError) -> Dict[str, Any]:
        """Convert Pydantic ValidationError to API error format."""
        errors = []
        for error in e.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })
        
        return {
            "code": 400,
            "message": "Validation failed",
            "type": "validation_error",
            "details": {
                "validation_errors": errors,
                "error_count": len(errors)
            }
        }
    
    # Example usage
    try:
        # This will raise a validation error
        SecurityQuote(
            symbol="",  # Invalid empty symbol
            name="Test",
            price=-100,  # Invalid negative price
            change=0,
            change_percent=0,
            volume=-1000,  # Invalid negative volume
            day_high=0,
            day_low=0,
            previous_close=0,
            open_price=0,
            exchange="INVALID",  # Invalid exchange
            market_status="invalid",  # Invalid status
            last_update=datetime.utcnow()
        )
    except ValidationError as e:
        error_response = handle_validation_error(e)
        print("Validation Error Response:", error_response)
        return error_response


def create_test_data_generators():
    """Create functions that generate test data for different scenarios."""
    
    def generate_valid_quote(symbol: str = "TEST") -> SecurityQuote:
        """Generate a valid SecurityQuote for testing."""
        return SecurityQuote(
            symbol=symbol,
            name=f"{symbol} Corporation",
            price=Decimal("100.50"),
            change=Decimal("1.25"),
            change_percent=Decimal("1.26"),
            volume=1000000,
            day_high=Decimal("101.00"),
            day_low=Decimal("99.75"),
            previous_close=Decimal("99.25"),
            open_price=Decimal("99.50"),
            exchange=ExchangeCode.NYSE,
            market_status=MarketStatus.OPEN,
            last_update=datetime.utcnow()
        )
    
    def generate_valid_user(email: str = "test@example.com") -> UserCreate:
        """Generate a valid UserCreate for testing."""
        return UserCreate(
            email=email,
            username="test_user",
            first_name="Test",
            last_name="User",
            password="TestPass123!",
            confirm_password="TestPass123!"
        )
    
    def generate_error_response(
        code: int = 400,
        message: str = "Test error",
        error_type: ErrorType = ErrorType.VALIDATION_ERROR
    ) -> BaseResponse[None]:
        """Generate a test error response."""
        return BaseResponse[None](
            success=False,
            error=ErrorDetail(
                code=code,
                message=message,
                type=error_type,
                details={"test": True}
            ),
            timestamp=datetime.utcnow()
        )
    
    return {
        "generate_valid_quote": generate_valid_quote,
        "generate_valid_user": generate_valid_user,
        "generate_error_response": generate_error_response
    }


if __name__ == "__main__":
    # Run validation examples
    print("Running validation tests...")
    test_results = ValidationExamples.run_validation_tests()
    
    print("\n=== VALIDATION TEST RESULTS ===")
    for category, results in test_results.items():
        print(f"\n{category.upper()}:")
        for test_type, test_results_list in results.items():
            print(f"  {test_type}: {test_results_list}")
    
    print("\n=== ERROR HANDLING DEMO ===")
    demonstrate_error_handling()
    
    print("\n=== TEST DATA GENERATORS ===")
    generators = create_test_data_generators()
    
    # Demo the generators
    sample_quote = generators["generate_valid_quote"]("DEMO")
    sample_user = generators["generate_valid_user"]("demo@example.com")
    sample_error = generators["generate_error_response"]()
    
    print("Generated test quote:", sample_quote.dict())
    print("Generated test user:", sample_user.dict())
    print("Generated test error:", sample_error.dict())