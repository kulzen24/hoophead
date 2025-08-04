# HoopHead Error Handling Guide

## Overview

HoopHead implements a comprehensive error handling system designed to provide clear error messages, automatic recovery, and detailed context for debugging. This guide covers the exception hierarchy, recovery patterns, and best practices for handling errors in your applications.

## Table of Contents

- [Exception Hierarchy](#exception-hierarchy)
- [Error Categories](#error-categories)
- [Error Context](#error-context)
- [Recovery Patterns](#recovery-patterns)
- [Best Practices](#best-practices)
- [Logging and Monitoring](#logging-and-monitoring)
- [Client-Side Error Handling](#client-side-error-handling)
- [Testing Error Scenarios](#testing-error-scenarios)

## Exception Hierarchy

### Base Exception Classes

```python
from backend.src.core.exceptions import (
    HoopHeadException,           # Base exception for all HoopHead errors
    ErrorContext,                # Rich error context information
    
    # Validation and Configuration
    ValidationError,
    ConfigurationError,
    
    # API-related exceptions
    APIException,                # Base for all API errors
    APIConnectionError,          # Network connectivity issues
    APITimeoutError,            # Request timeout
    APIRateLimitError,          # Rate limit exceeded
    APIAuthenticationError,      # Invalid API key
    APINotFoundError,           # Resource not found
    APIServerError,             # Server-side errors
    APIResponseError,           # Invalid/unexpected response format
    
    # Domain exceptions
    DomainException,            # Business logic errors
    PlayerNotFoundError,
    TeamNotFoundError,
    GameNotFoundError,
    InvalidSportError,
    InvalidSearchCriteriaError,
    
    # Cache exceptions
    CacheException,             # Base cache error
    CacheConnectionError,       # Cache service unavailable
    CacheTimeoutError,         # Cache operation timeout
    CacheSerializationError    # Data serialization issues
)
```

### Exception Hierarchy Diagram

```
HoopHeadException (Base)
├── ValidationError
├── ConfigurationError
├── APIException
│   ├── APIConnectionError
│   ├── APITimeoutError
│   ├── APIRateLimitError
│   ├── APIAuthenticationError
│   ├── APINotFoundError
│   ├── APIServerError
│   └── APIResponseError
├── DomainException
│   ├── PlayerNotFoundError
│   ├── TeamNotFoundError
│   ├── GameNotFoundError
│   ├── InvalidSportError
│   └── InvalidSearchCriteriaError
└── CacheException
    ├── CacheConnectionError
    ├── CacheTimeoutError
    └── CacheSerializationError
```

## Error Categories

### 1. API Connection Errors

These errors occur when there are network connectivity issues or API service problems.

```python
# Example: Handling connection errors
from backend.src.core.exceptions import APIConnectionError, APITimeoutError

async def robust_api_call():
    try:
        async with BallDontLieClient() as client:
            response = await client.get_teams(Sport.NBA)
            return response.data
    
    except APIConnectionError as e:
        print(f"Network connectivity issue: {e}")
        print(f"URL: {e.url}")
        print(f"Retry after: {e.retry_after} seconds" if e.retry_after else "No retry info")
        
        # Implement exponential backoff
        if e.retry_after:
            await asyncio.sleep(e.retry_after)
            # Retry logic here
        
        return None
    
    except APITimeoutError as e:
        print(f"Request timed out: {e}")
        print(f"Timeout duration: {e.timeout} seconds")
        
        # Consider reducing timeout or implementing pagination
        return None
```

### 2. Authentication Errors

Handle API key issues and authentication failures.

```python
from backend.src.core.exceptions import APIAuthenticationError
from backend.src.adapters.external.auth_manager import AuthenticationManager

async def handle_auth_errors():
    try:
        client = BallDontLieClient(api_key="invalid-key")
        response = await client.get_teams(Sport.NBA)
    
    except APIAuthenticationError as e:
        print(f"Authentication failed: {e}")
        print(f"Error code: {e.error_code}")
        
        # Check if using authentication manager
        if hasattr(e.context, 'key_id') and e.context.key_id:
            auth_manager = AuthenticationManager()
            key_info = auth_manager.get_key_info(e.context.key_id)
            
            if key_info:
                print(f"Key tier: {key_info.tier.value}")
                print(f"Key status: {'Active' if key_info.active else 'Inactive'}")
            
            # Try backup key
            backup_key = auth_manager.get_backup_key()
            if backup_key:
                print("Attempting with backup key...")
                client = BallDontLieClient(key_id=backup_key)
                # Retry request
        
        else:
            print("Check your API key configuration:")
            print("1. Verify BALLDONTLIE_API_KEY environment variable")
            print("2. Ensure key is valid and active")
            print("3. Check API tier limits")
        
        return None
```

### 3. Rate Limiting Errors

Handle rate limit exceptions with automatic retry logic.

```python
from backend.src.core.exceptions import APIRateLimitError
import asyncio

async def handle_rate_limits():
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with BallDontLieClient() as client:
                response = await client.get_teams(Sport.NBA)
                return response.data
        
        except APIRateLimitError as e:
            retry_count += 1
            
            print(f"Rate limit exceeded (attempt {retry_count}/{max_retries})")
            print(f"Error: {e}")
            print(f"Rate limit info:")
            print(f"  Requests per hour: {e.requests_per_hour}")
            print(f"  Requests per minute: {e.requests_per_minute}")
            print(f"  Current usage: {e.current_usage}")
            
            if e.retry_after:
                print(f"Waiting {e.retry_after} seconds before retry...")
                await asyncio.sleep(e.retry_after)
            else:
                # Exponential backoff
                wait_time = 2 ** retry_count
                print(f"Exponential backoff: waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        except Exception as e:
            print(f"Other error occurred: {e}")
            break
    
    print("Max retries exceeded for rate limiting")
    return None
```

### 4. Domain Logic Errors

Handle business logic and data validation errors.

```python
from backend.src.core.exceptions import (
    PlayerNotFoundError, 
    InvalidSportError, 
    InvalidSearchCriteriaError
)

async def handle_domain_errors():
    try:
        # Example of domain validation
        sport_code = "invalid_sport"
        
        try:
            sport = Sport(sport_code)
        except ValueError:
            raise InvalidSportError(
                sport_code=sport_code,
                valid_sports=list(Sport),
                message=f"Invalid sport code: {sport_code}"
            )
        
        # Search for player
        client = BallDontLieClient()
        response = await client.get_players(sport, search="")
        
        if not response.data['data']:
            raise PlayerNotFoundError(
                search_term="",
                sport=sport,
                message="Empty search term provided"
            )
    
    except InvalidSportError as e:
        print(f"Invalid sport: {e.sport_code}")
        print(f"Valid sports: {[s.value for s in e.valid_sports]}")
        return {"error": "invalid_sport", "valid_sports": [s.value for s in Sport]}
    
    except PlayerNotFoundError as e:
        print(f"Player not found: {e.search_term} in {e.sport.value}")
        print("Suggestions:")
        print("- Check spelling")
        print("- Try partial name (e.g., 'LeBron' instead of 'LeBron James')")
        print("- Use different sport")
        return {"error": "player_not_found", "suggestions": ["check_spelling", "try_partial_name"]}
    
    except InvalidSearchCriteriaError as e:
        print(f"Invalid search criteria: {e}")
        print(f"Context: {e.context}")
        return {"error": "invalid_search", "details": str(e)}
```

### 5. Cache Errors

Handle caching system failures gracefully.

```python
from backend.src.core.exceptions import CacheException, CacheConnectionError

async def handle_cache_errors():
    try:
        client = BallDontLieClient(enable_cache=True)
        response = await client.get_teams(Sport.NBA)
        return response.data
    
    except CacheConnectionError as e:
        print(f"Cache service unavailable: {e}")
        print("Falling back to direct API calls...")
        
        # Disable cache and retry
        client = BallDontLieClient(enable_cache=False)
        response = await client.get_teams(Sport.NBA)
        return response.data
    
    except CacheException as e:
        print(f"Cache error (non-critical): {e}")
        print("Continuing with degraded performance...")
        
        # Log cache issue for monitoring
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Cache operation failed: {e}", extra={
            'error_type': 'cache_failure',
            'operation': e.context.operation if e.context else 'unknown'
        })
        
        # Continue without cache
        return await handle_cache_errors_fallback()

async def handle_cache_errors_fallback():
    """Fallback for cache errors."""
    client = BallDontLieClient(enable_cache=False)
    response = await client.get_teams(Sport.NBA)
    return response.data
```

## Error Context

### ErrorContext Class

HoopHead provides rich error context for better debugging:

```python
@dataclass
class ErrorContext:
    """Rich error context for debugging and logging."""
    operation: str
    sport: Optional[str] = None
    endpoint: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging."""
        return {
            'operation': self.operation,
            'sport': self.sport,
            'endpoint': self.endpoint,
            'parameters': self.parameters,
            'user_id': self.user_id,
            'request_id': self.request_id,
            'timestamp': self.timestamp.isoformat()
        }
```

### Using Error Context

```python
from backend.src.core.exceptions import ErrorContext, DomainException

async def operation_with_context():
    context = ErrorContext(
        operation="get_player_stats",
        sport="nba",
        endpoint="/players/search",
        parameters={"search": "LeBron", "season": 2023},
        user_id="user_123",
        request_id="req_456"
    )
    
    try:
        # Your operation here
        result = await some_operation()
        return result
    
    except Exception as e:
        # Wrap exception with rich context
        raise DomainException(
            message=f"Failed to get player stats: {str(e)}",
            context=context,
            original_error=e
        )

# Accessing error context
try:
    await operation_with_context()
except DomainException as e:
    print(f"Operation failed: {e.message}")
    print(f"Context: {e.context.to_dict()}")
    print(f"Original error: {e.original_error}")
```

## Recovery Patterns

### 1. Retry with Exponential Backoff

```python
from backend.src.core.error_handler import with_api_error_handling
import asyncio
import random

@with_api_error_handling(max_retries=3, delay=1.0)
async def api_call_with_retry():
    """Automatically retry API calls with exponential backoff."""
    async with BallDontLieClient() as client:
        return await client.get_teams(Sport.NBA)

# Custom retry logic
async def custom_retry_logic(operation, max_retries=3, base_delay=1.0):
    """Custom retry with jitter and exponential backoff."""
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        
        except (APIConnectionError, APITimeoutError, APIServerError) as e:
            if attempt == max_retries:
                raise
            
            # Exponential backoff with jitter
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"Attempt {attempt + 1} failed: {e}")
            print(f"Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)
        
        except APIRateLimitError as e:
            if attempt == max_retries:
                raise
            
            # Use retry_after from rate limit response
            delay = e.retry_after or (base_delay * (2 ** attempt))
            print(f"Rate limited. Waiting {delay} seconds...")
            await asyncio.sleep(delay)
        
        except (APIAuthenticationError, APINotFoundError):
            # Don't retry authentication or not found errors
            raise

# Usage
async def robust_api_call():
    return await custom_retry_logic(
        lambda: BallDontLieClient().get_teams(Sport.NBA),
        max_retries=3,
        base_delay=1.0
    )
```

### 2. Circuit Breaker Pattern

```python
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Test if service recovered

class CircuitBreaker:
    """Circuit breaker pattern for API calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: timedelta = timedelta(minutes=1),
        recovery_timeout: timedelta = timedelta(seconds=30)
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, operation: Callable) -> Any:
        """Execute operation with circuit breaker protection."""
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            result = await operation()
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        return datetime.utcnow() - self.last_failure_time > self.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass

# Usage
api_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=timedelta(minutes=2))

async def protected_api_call():
    """API call protected by circuit breaker."""
    try:
        return await api_circuit_breaker.call(
            lambda: BallDontLieClient().get_teams(Sport.NBA)
        )
    except CircuitBreakerOpenError:
        print("API service is temporarily unavailable")
        return {"error": "service_unavailable", "retry_after": 120}
```

### 3. Fallback and Degradation

```python
from typing import Optional, List, Dict, Any

class SportsDataService:
    """Service with fallback and graceful degradation."""
    
    def __init__(self):
        self.primary_client = BallDontLieClient()
        self.cache_client = None  # Separate cache-only client
        self.fallback_data = {}   # Static fallback data
    
    async def get_teams_with_fallback(self, sport: Sport) -> Dict[str, Any]:
        """Get teams with multiple fallback strategies."""
        
        # Strategy 1: Primary API
        try:
            response = await self.primary_client.get_teams(sport)
            return {
                "data": response.data['data'],
                "source": "api",
                "success": True
            }
        
        except APIRateLimitError as e:
            print(f"Rate limited: {e}. Trying cache...")
        
        except APIConnectionError as e:
            print(f"Connection error: {e}. Trying cache...")
        
        except Exception as e:
            print(f"API error: {e}. Trying fallback strategies...")
        
        # Strategy 2: Cache-only (if available)
        try:
            if self.cache_client:
                cached_response = await self.cache_client.get_teams(sport)
                return {
                    "data": cached_response.data['data'],
                    "source": "cache",
                    "success": True,
                    "warning": "Data may be stale"
                }
        except Exception as e:
            print(f"Cache error: {e}. Using static fallback...")
        
        # Strategy 3: Static fallback data
        static_teams = self.fallback_data.get(sport.value, [])
        if static_teams:
            return {
                "data": static_teams,
                "source": "static",
                "success": True,
                "warning": "Using static fallback data"
            }
        
        # Strategy 4: Minimal response
        return {
            "data": [],
            "source": "none",
            "success": False,
            "error": "All data sources unavailable"
        }
    
    async def get_player_with_degradation(
        self, 
        sport: Sport, 
        search: str
    ) -> Dict[str, Any]:
        """Get player data with graceful degradation."""
        
        try:
            # Full search
            response = await self.primary_client.get_players(sport, search=search)
            players = response.data['data']
            
            if players:
                return {
                    "players": players,
                    "source": "full_search",
                    "success": True
                }
        
        except Exception as e:
            print(f"Full search failed: {e}")
        
        # Degraded mode: Try cached popular players
        try:
            popular_players = await self._get_popular_players_cache(sport)
            matching_players = [
                player for player in popular_players
                if search.lower() in player.get('first_name', '').lower() or
                   search.lower() in player.get('last_name', '').lower()
            ]
            
            if matching_players:
                return {
                    "players": matching_players,
                    "source": "cached_search",
                    "success": True,
                    "warning": "Limited to popular players only"
                }
        
        except Exception as e:
            print(f"Cache search failed: {e}")
        
        # Minimal response
        return {
            "players": [],
            "source": "none",
            "success": False,
            "error": "Player search unavailable",
            "suggestion": "Try again later or use team listings"
        }
    
    async def _get_popular_players_cache(self, sport: Sport) -> List[Dict]:
        """Get cached popular players."""
        # Implementation would check cache for pre-loaded popular players
        popular_names = {
            Sport.NBA: ["LeBron James", "Stephen Curry", "Kevin Durant"],
            Sport.NFL: ["Tom Brady", "Patrick Mahomes", "Aaron Rodgers"],
            Sport.MLB: ["Shohei Ohtani", "Mike Trout", "Aaron Judge"]
        }
        
        # Return mock data for this example
        return [
            {"first_name": name.split()[0], "last_name": name.split()[1]}
            for name in popular_names.get(sport, [])
        ]
```

## Best Practices

### 1. Error Handling Decorator

```python
from functools import wraps
import logging

def handle_sports_api_errors(fallback_value=None, log_errors=True):
    """Decorator for consistent error handling."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            
            except APIAuthenticationError as e:
                if log_errors:
                    logging.error(f"Authentication error in {func.__name__}: {e}")
                return {
                    "error": "authentication_failed",
                    "message": "Invalid API key or authentication failed",
                    "action": "check_api_key"
                }
            
            except APIRateLimitError as e:
                if log_errors:
                    logging.warning(f"Rate limit in {func.__name__}: {e}")
                return {
                    "error": "rate_limited",
                    "message": f"Rate limit exceeded. Retry after {e.retry_after}s",
                    "retry_after": e.retry_after
                }
            
            except APIConnectionError as e:
                if log_errors:
                    logging.error(f"Connection error in {func.__name__}: {e}")
                return {
                    "error": "connection_failed",
                    "message": "Unable to connect to sports data service",
                    "action": "check_connectivity"
                }
            
            except APINotFoundError as e:
                if log_errors:
                    logging.info(f"Resource not found in {func.__name__}: {e}")
                return {
                    "error": "not_found",
                    "message": f"Resource not found: {e.resource}",
                    "resource": e.resource
                }
            
            except HoopHeadException as e:
                if log_errors:
                    logging.error(f"HoopHead error in {func.__name__}: {e}")
                return {
                    "error": "service_error",
                    "message": str(e),
                    "context": e.context.to_dict() if e.context else None
                }
            
            except Exception as e:
                if log_errors:
                    logging.exception(f"Unexpected error in {func.__name__}: {e}")
                
                if fallback_value is not None:
                    return fallback_value
                
                return {
                    "error": "unexpected_error",
                    "message": "An unexpected error occurred",
                    "details": str(e)
                }
        
        return wrapper
    return decorator

# Usage
@handle_sports_api_errors(fallback_value={"teams": []})
async def get_nba_teams():
    """Get NBA teams with error handling."""
    async with BallDontLieClient() as client:
        response = await client.get_teams(Sport.NBA)
        return {"teams": response.data['data']}
```

### 2. Centralized Error Response

```python
from typing import Optional, Dict, Any
from enum import Enum

class ErrorCode(str, Enum):
    # Authentication errors
    INVALID_API_KEY = "invalid_api_key"
    API_KEY_EXPIRED = "api_key_expired"
    
    # Rate limiting
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    TIER_LIMIT_EXCEEDED = "tier_limit_exceeded"
    
    # Connectivity
    SERVICE_UNAVAILABLE = "service_unavailable"
    CONNECTION_TIMEOUT = "connection_timeout"
    
    # Data errors
    RESOURCE_NOT_FOUND = "resource_not_found"
    INVALID_SPORT = "invalid_sport"
    INVALID_SEARCH = "invalid_search"
    
    # Cache errors
    CACHE_UNAVAILABLE = "cache_unavailable"
    
    # Generic
    UNEXPECTED_ERROR = "unexpected_error"

class ErrorResponseBuilder:
    """Build standardized error responses."""
    
    @staticmethod
    def build_error_response(
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        retry_after: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build standardized error response."""
        
        response = {
            "success": False,
            "error": {
                "code": error_code.value,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        if details:
            response["error"]["details"] = details
        
        if suggestions:
            response["error"]["suggestions"] = suggestions
        
        if retry_after:
            response["error"]["retry_after"] = retry_after
        
        return response
    
    @classmethod
    def from_exception(cls, exception: Exception) -> Dict[str, Any]:
        """Create error response from exception."""
        
        if isinstance(exception, APIAuthenticationError):
            return cls.build_error_response(
                ErrorCode.INVALID_API_KEY,
                "Authentication failed. Please check your API key.",
                suggestions=[
                    "Verify your API key is correct",
                    "Check if your API key has expired",
                    "Ensure you have the required tier access"
                ]
            )
        
        elif isinstance(exception, APIRateLimitError):
            return cls.build_error_response(
                ErrorCode.RATE_LIMIT_EXCEEDED,
                f"Rate limit exceeded. You have made too many requests.",
                details={
                    "requests_per_hour": exception.requests_per_hour,
                    "current_usage": exception.current_usage
                },
                retry_after=exception.retry_after,
                suggestions=[
                    "Wait before making additional requests",
                    "Consider upgrading your API tier",
                    "Implement request throttling"
                ]
            )
        
        elif isinstance(exception, APIConnectionError):
            return cls.build_error_response(
                ErrorCode.SERVICE_UNAVAILABLE,
                "Unable to connect to the sports data service.",
                suggestions=[
                    "Check your internet connection",
                    "Verify the service is operational",
                    "Try again in a few moments"
                ]
            )
        
        elif isinstance(exception, APINotFoundError):
            return cls.build_error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"The requested resource was not found: {exception.resource}",
                details={"resource": exception.resource},
                suggestions=[
                    "Check the spelling of your search terms",
                    "Verify the resource exists",
                    "Try a broader search"
                ]
            )
        
        elif isinstance(exception, InvalidSportError):
            return cls.build_error_response(
                ErrorCode.INVALID_SPORT,
                f"Invalid sport: {exception.sport_code}",
                details={
                    "provided_sport": exception.sport_code,
                    "valid_sports": [s.value for s in exception.valid_sports]
                },
                suggestions=[
                    f"Use one of: {', '.join(s.value for s in exception.valid_sports)}"
                ]
            )
        
        else:
            return cls.build_error_response(
                ErrorCode.UNEXPECTED_ERROR,
                "An unexpected error occurred.",
                details={"error_type": type(exception).__name__}
            )

# Usage in API endpoints
from fastapi import HTTPException

@app.get("/api/{sport}/teams")
async def get_teams_endpoint(sport: str):
    try:
        sport_enum = Sport(sport.lower())
        async with BallDontLieClient() as client:
            response = await client.get_teams(sport_enum)
            return {
                "success": True,
                "data": response.data['data']
            }
    
    except Exception as e:
        error_response = ErrorResponseBuilder.from_exception(e)
        status_code = 400 if error_response["error"]["code"] in [
            ErrorCode.INVALID_SPORT.value,
            ErrorCode.INVALID_SEARCH.value
        ] else 500
        
        raise HTTPException(status_code=status_code, detail=error_response)
```

### 3. Error Monitoring and Alerting

```python
import logging
from typing import Dict, Any
import json

class SportsDataErrorLogger:
    """Specialized error logging for sports data operations."""
    
    def __init__(self):
        self.logger = logging.getLogger("hoophead.errors")
        
        # Configure structured logging
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_api_error(
        self,
        exception: Exception,
        operation: str,
        sport: Optional[str] = None,
        endpoint: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Log API errors with structured data."""
        
        error_data = {
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "operation": operation,
            "sport": sport,
            "endpoint": endpoint,
            "user_id": user_id
        }
        
        # Add exception-specific data
        if isinstance(exception, APIRateLimitError):
            error_data.update({
                "rate_limit_info": {
                    "requests_per_hour": exception.requests_per_hour,
                    "current_usage": exception.current_usage,
                    "retry_after": exception.retry_after
                }
            })
        
        elif isinstance(exception, APIAuthenticationError):
            error_data.update({
                "auth_info": {
                    "error_code": exception.error_code,
                    "key_id": getattr(exception.context, 'key_id', None) if exception.context else None
                }
            })
        
        elif isinstance(exception, HoopHeadException) and exception.context:
            error_data.update({
                "context": exception.context.to_dict()
            })
        
        # Log with appropriate level
        if isinstance(exception, (APIRateLimitError, APINotFoundError)):
            self.logger.warning(f"API Warning: {operation}", extra=error_data)
        elif isinstance(exception, (APIConnectionError, APITimeoutError)):
            self.logger.error(f"API Error: {operation}", extra=error_data)
        elif isinstance(exception, APIAuthenticationError):
            self.logger.critical(f"Authentication Error: {operation}", extra=error_data)
        else:
            self.logger.error(f"Unexpected Error: {operation}", extra=error_data)
    
    def log_performance_issue(
        self,
        operation: str,
        duration_ms: float,
        threshold_ms: float = 5000
    ):
        """Log performance issues."""
        if duration_ms > threshold_ms:
            self.logger.warning(
                f"Performance Issue: {operation}",
                extra={
                    "performance": {
                        "duration_ms": duration_ms,
                        "threshold_ms": threshold_ms,
                        "operation": operation
                    }
                }
            )

# Global error logger instance
error_logger = SportsDataErrorLogger()

# Context manager for error logging
from contextlib import asynccontextmanager
import time

@asynccontextmanager
async def log_operation(operation: str, **context):
    """Context manager for logging operations."""
    start_time = time.time()
    
    try:
        yield
        
        # Log successful operation timing
        duration_ms = (time.time() - start_time) * 1000
        error_logger.log_performance_issue(operation, duration_ms)
    
    except Exception as e:
        error_logger.log_api_error(e, operation, **context)
        raise

# Usage
async def monitored_api_call():
    async with log_operation("get_nba_teams", sport="nba", user_id="user_123"):
        async with BallDontLieClient() as client:
            response = await client.get_teams(Sport.NBA)
            return response.data
```

## Client-Side Error Handling

### JavaScript/TypeScript Error Handling

```typescript
// types/errors.ts
interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    timestamp: string;
    details?: Record<string, any>;
    suggestions?: string[];
    retry_after?: number;
  };
}

interface SuccessResponse<T> {
  success: true;
  data: T;
}

type ApiResponse<T> = SuccessResponse<T> | ErrorResponse;

// utils/error-handler.ts
export class ApiErrorHandler {
  static isErrorResponse<T>(response: ApiResponse<T>): response is ErrorResponse {
    return !response.success;
  }
  
  static handleError(error: ErrorResponse): {
    userMessage: string;
    shouldRetry: boolean;
    retryAfter?: number;
    actionRequired?: string;
  } {
    const { code, message, retry_after, suggestions } = error.error;
    
    switch (code) {
      case 'invalid_api_key':
        return {
          userMessage: 'Authentication failed. Please contact support.',
          shouldRetry: false,
          actionRequired: 'contact_support'
        };
      
      case 'rate_limit_exceeded':
        return {
          userMessage: `Too many requests. Please wait ${retry_after || 60} seconds.`,
          shouldRetry: true,
          retryAfter: retry_after || 60
        };
      
      case 'service_unavailable':
        return {
          userMessage: 'Service temporarily unavailable. Please try again.',
          shouldRetry: true,
          retryAfter: 30
        };
      
      case 'resource_not_found':
        return {
          userMessage: 'No results found. Try adjusting your search.',
          shouldRetry: false,
          actionRequired: 'modify_search'
        };
      
      case 'invalid_sport':
        const validSports = error.error.details?.valid_sports?.join(', ') || 'NBA, NFL, MLB, NHL, EPL';
        return {
          userMessage: `Invalid sport. Valid options: ${validSports}`,
          shouldRetry: false,
          actionRequired: 'correct_input'
        };
      
      default:
        return {
          userMessage: message || 'An unexpected error occurred.',
          shouldRetry: true,
          retryAfter: 10
        };
    }
  }
}

// hooks/useApiCall.ts (React hook)
import { useState, useCallback } from 'react';

interface UseApiCallResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  retry: () => Promise<void>;
  canRetry: boolean;
}

export function useApiCall<T>(
  apiCall: () => Promise<ApiResponse<T>>,
  dependencies: any[] = []
): UseApiCallResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [canRetry, setCanRetry] = useState(false);
  
  const executeCall = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiCall();
      
      if (ApiErrorHandler.isErrorResponse(response)) {
        const errorInfo = ApiErrorHandler.handleError(response);
        setError(errorInfo.userMessage);
        setCanRetry(errorInfo.shouldRetry);
        
        // Auto-retry for rate limits
        if (errorInfo.shouldRetry && errorInfo.retryAfter) {
          setTimeout(() => {
            executeCall();
          }, errorInfo.retryAfter * 1000);
        }
      } else {
        setData(response.data);
        setCanRetry(false);
      }
    } catch (err) {
      setError('Network error. Please check your connection.');
      setCanRetry(true);
    } finally {
      setLoading(false);
    }
  }, dependencies);
  
  return {
    data,
    loading,
    error,
    retry: executeCall,
    canRetry
  };
}

// components/ErrorBoundary.tsx
import React, { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class SportsDataErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }
  
  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Sports data error:', error, errorInfo);
    
    // Send error to monitoring service
    if (process.env.NODE_ENV === 'production') {
      // Analytics.track('sports_data_error', {
      //   error: error.message,
      //   component: errorInfo.componentStack
      // });
    }
  }
  
  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 m-4">
          <h3 className="text-red-800 font-medium">Something went wrong</h3>
          <p className="text-red-600 text-sm mt-1">
            Unable to load sports data. Please refresh the page or try again later.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-3 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Refresh Page
          </button>
        </div>
      );
    }
    
    return this.props.children;
  }
}
```

## Testing Error Scenarios

### Unit Tests for Error Handling

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from backend.src.core.exceptions import *
from backend.src.adapters.external.ball_dont_lie_client import BallDontLieClient, Sport

class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock client for testing."""
        return AsyncMock(spec=BallDontLieClient)
    
    @pytest.mark.asyncio
    async def test_api_authentication_error(self, mock_client):
        """Test authentication error handling."""
        mock_client.get_teams.side_effect = APIAuthenticationError(
            "Invalid API key",
            error_code="invalid_key"
        )
        
        with pytest.raises(APIAuthenticationError) as exc_info:
            await mock_client.get_teams(Sport.NBA)
        
        assert exc_info.value.error_code == "invalid_key"
        assert "Invalid API key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, mock_client):
        """Test rate limit error handling."""
        mock_client.get_teams.side_effect = APIRateLimitError(
            retry_after=60,
            requests_per_hour=300,
            current_usage=300
        )
        
        with pytest.raises(APIRateLimitError) as exc_info:
            await mock_client.get_teams(Sport.NBA)
        
        assert exc_info.value.retry_after == 60
        assert exc_info.value.requests_per_hour == 300
    
    @pytest.mark.asyncio
    async def test_connection_error_retry(self):
        """Test connection error with retry logic."""
        
        async def mock_operation():
            # Fail twice, then succeed
            if not hasattr(mock_operation, 'call_count'):
                mock_operation.call_count = 0
            
            mock_operation.call_count += 1
            
            if mock_operation.call_count <= 2:
                raise APIConnectionError("Connection failed", url="http://example.com")
            
            return {"data": {"teams": []}}
        
        # Test retry logic
        result = await custom_retry_logic(mock_operation, max_retries=3, base_delay=0.1)
        assert result["data"]["teams"] == []
        assert mock_operation.call_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self):
        """Test circuit breaker pattern."""
        circuit_breaker = CircuitBreaker(failure_threshold=2, timeout=timedelta(seconds=1))
        
        async def failing_operation():
            raise APIConnectionError("Service down", url="http://example.com")
        
        # First failure
        with pytest.raises(APIConnectionError):
            await circuit_breaker.call(failing_operation)
        
        # Second failure - should open circuit
        with pytest.raises(APIConnectionError):
            await circuit_breaker.call(failing_operation)
        
        # Third call - circuit should be open
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(failing_operation)
    
    def test_error_response_builder(self):
        """Test error response builder."""
        error = APIRateLimitError(retry_after=30, requests_per_hour=300, current_usage=300)
        response = ErrorResponseBuilder.from_exception(error)
        
        assert not response["success"]
        assert response["error"]["code"] == ErrorCode.RATE_LIMIT_EXCEEDED.value
        assert response["error"]["retry_after"] == 30
        assert "suggestions" in response["error"]
    
    def test_error_context_serialization(self):
        """Test error context serialization."""
        context = ErrorContext(
            operation="get_teams",
            sport="nba",
            endpoint="/teams",
            parameters={"page": 1}
        )
        
        context_dict = context.to_dict()
        
        assert context_dict["operation"] == "get_teams"
        assert context_dict["sport"] == "nba"
        assert context_dict["parameters"]["page"] == 1
        assert "timestamp" in context_dict

# Integration tests
class TestErrorIntegration:
    """Integration tests for error scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_api_key_integration(self):
        """Test integration with invalid API key."""
        client = BallDontLieClient(api_key="invalid-key")
        
        with pytest.raises(APIAuthenticationError):
            async with client:
                await client.get_teams(Sport.NBA)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_network_timeout_integration(self):
        """Test network timeout handling."""
        # Mock network timeout
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()
            
            client = BallDontLieClient(api_key="test-key")
            
            with pytest.raises(APITimeoutError):
                async with client:
                    await client.get_teams(Sport.NBA)
    
    @pytest.mark.asyncio
    async def test_fallback_service_integration(self):
        """Test service with fallback capabilities."""
        service = SportsDataService()
        
        # Mock primary client to fail
        with patch.object(service.primary_client, 'get_teams') as mock_get:
            mock_get.side_effect = APIConnectionError("Service down", url="http://example.com")
            
            # Set up fallback data
            service.fallback_data["nba"] = [
                {"id": 1, "name": "Lakers", "full_name": "Los Angeles Lakers"}
            ]
            
            result = await service.get_teams_with_fallback(Sport.NBA)
            
            assert result["source"] == "static"
            assert len(result["data"]) == 1
            assert result["data"][0]["name"] == "Lakers"

# Performance tests
@pytest.mark.performance
class TestErrorPerformance:
    """Test error handling performance."""
    
    @pytest.mark.asyncio
    async def test_error_logging_performance(self):
        """Test error logging doesn't impact performance significantly."""
        import time
        
        error = APIRateLimitError(retry_after=30, requests_per_hour=300, current_usage=300)
        logger = SportsDataErrorLogger()
        
        # Test logging performance
        start_time = time.time()
        
        for _ in range(100):
            logger.log_api_error(error, "test_operation", sport="nba")
        
        duration = time.time() - start_time
        
        # Should complete 100 log operations in less than 1 second
        assert duration < 1.0

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

This comprehensive error handling guide provides the foundation for building robust applications with HoopHead. The patterns and examples shown here help ensure your application can gracefully handle any error scenarios while providing clear feedback to users and detailed information for debugging.

For more information, see:
- [API Reference](API_REFERENCE.md) for complete API documentation
- [Integration Guide](INTEGRATION_GUIDE.md) for implementation patterns
- [Extension Guide](EXTENSION_GUIDE.md) for customization options 