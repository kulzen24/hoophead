"""
Comprehensive exception hierarchy for HoopHead multi-sport platform.
Provides specific exceptions for different error scenarios with context.
"""

from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ErrorContext:
    """Context information for errors."""
    operation: str
    sport: Optional[str] = None
    endpoint: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error context to dictionary."""
        return {
            'operation': self.operation,
            'sport': self.sport,
            'endpoint': self.endpoint,
            'parameters': self.parameters,
            'timestamp': self.timestamp.isoformat(),
            'user_agent': self.user_agent,
            'request_id': self.request_id
        }


class HoopHeadException(Exception):
    """
    Base exception class for all HoopHead-specific errors.
    Provides rich context and error categorization.
    """
    
    def __init__(
        self, 
        message: str,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
        error_code: Optional[str] = None,
        recoverable: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.context = context
        self.original_error = original_error
        self.error_code = error_code
        self.recoverable = recoverable
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'recoverable': self.recoverable,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context.to_dict() if self.context else None,
            'original_error': str(self.original_error) if self.original_error else None
        }
    
    def __str__(self) -> str:
        """Enhanced string representation with context."""
        base_msg = self.message
        if self.context and self.context.sport:
            base_msg += f" (Sport: {self.context.sport})"
        if self.error_code:
            base_msg += f" [Code: {self.error_code}]"
        return base_msg


# =============================================================================
# Validation and Configuration Exceptions
# =============================================================================

class ValidationError(HoopHeadException):
    """Raised when input validation fails."""
    
    def __init__(
        self, 
        field: str, 
        value: Any, 
        constraint: str,
        context: Optional[ErrorContext] = None
    ):
        message = f"Validation failed for field '{field}': {constraint}. Got: {value}"
        super().__init__(
            message=message,
            context=context,
            error_code="VALIDATION_ERROR",
            recoverable=True
        )
        self.field = field
        self.value = value
        self.constraint = constraint


class ConfigurationError(HoopHeadException):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, setting: str, message: str, context: Optional[ErrorContext] = None):
        full_message = f"Configuration error for '{setting}': {message}"
        super().__init__(
            message=full_message,
            context=context,
            error_code="CONFIG_ERROR",
            recoverable=False
        )
        self.setting = setting


# =============================================================================
# API-Related Exceptions
# =============================================================================

class APIException(HoopHeadException):
    """Base class for all API-related errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
        recoverable: bool = False
    ):
        super().__init__(
            message=message,
            context=context,
            original_error=original_error,
            error_code="API_ERROR",
            recoverable=recoverable
        )
        self.status_code = status_code
        self.response_data = response_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Enhanced dictionary representation with API details."""
        base_dict = super().to_dict()
        base_dict.update({
            'status_code': self.status_code,
            'response_data': self.response_data
        })
        return base_dict


class APIConnectionError(APIException):
    """Raised when unable to connect to the API."""
    
    def __init__(self, url: str, context: Optional[ErrorContext] = None, original_error: Optional[Exception] = None):
        message = f"Failed to connect to API endpoint: {url}"
        super().__init__(
            message=message,
            context=context,
            original_error=original_error,
            recoverable=True
        )
        self.url = url
        self.error_code = "API_CONNECTION_ERROR"


class APITimeoutError(APIException):
    """Raised when API request times out."""
    
    def __init__(self, timeout: float, context: Optional[ErrorContext] = None):
        message = f"API request timed out after {timeout} seconds"
        super().__init__(
            message=message,
            context=context,
            recoverable=True
        )
        self.timeout = timeout
        self.error_code = "API_TIMEOUT_ERROR"


class APIRateLimitError(APIException):
    """Raised when API rate limit is exceeded."""
    
    def __init__(
        self, 
        retry_after: Optional[int] = None, 
        context: Optional[ErrorContext] = None
    ):
        message = "API rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(
            message=message,
            status_code=429,
            context=context,
            recoverable=True
        )
        self.retry_after = retry_after
        self.error_code = "API_RATE_LIMIT_ERROR"


class APIAuthenticationError(APIException):
    """Raised when API authentication fails."""
    
    def __init__(self, context: Optional[ErrorContext] = None):
        message = "API authentication failed. Check your API key."
        super().__init__(
            message=message,
            status_code=401,
            context=context,
            recoverable=False
        )
        self.error_code = "API_AUTH_ERROR"


class APINotFoundError(APIException):
    """Raised when API endpoint or resource is not found."""
    
    def __init__(self, resource: str, context: Optional[ErrorContext] = None):
        message = f"API resource not found: {resource}"
        super().__init__(
            message=message,
            status_code=404,
            context=context,
            recoverable=False
        )
        self.resource = resource
        self.error_code = "API_NOT_FOUND_ERROR"


class APIServerError(APIException):
    """Raised when API server returns 5xx error."""
    
    def __init__(
        self, 
        status_code: int, 
        response_data: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None
    ):
        message = f"API server error (HTTP {status_code})"
        super().__init__(
            message=message,
            status_code=status_code,
            response_data=response_data,
            context=context,
            recoverable=True
        )
        self.error_code = "API_SERVER_ERROR"


class APIResponseError(APIException):
    """Raised when API response is invalid or malformed."""
    
    def __init__(
        self, 
        expected_format: str, 
        actual_content: Any = None,
        context: Optional[ErrorContext] = None
    ):
        message = f"Invalid API response format. Expected: {expected_format}"
        super().__init__(
            message=message,
            context=context,
            recoverable=False
        )
        self.expected_format = expected_format
        self.actual_content = actual_content
        self.error_code = "API_RESPONSE_ERROR"


# =============================================================================
# Domain-Level Exceptions
# =============================================================================

class DomainException(HoopHeadException):
    """Base class for domain logic errors."""
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
        error_code: str = "DOMAIN_ERROR",
        recoverable: bool = True
    ):
        super().__init__(
            message=message,
            context=context,
            original_error=original_error,
            error_code=error_code,
            recoverable=recoverable
        )


class PlayerNotFoundError(DomainException):
    """Raised when a player cannot be found."""
    
    def __init__(
        self, 
        player_id: Optional[int] = None, 
        player_name: Optional[str] = None,
        sport: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ):
        if player_id:
            message = f"Player with ID {player_id} not found"
        elif player_name:
            message = f"Player '{player_name}' not found"
        else:
            message = "Player not found"
        
        if sport:
            message += f" in {sport.upper()}"
            
        super().__init__(
            message=message,
            context=context,
            error_code="PLAYER_NOT_FOUND",
            recoverable=False
        )
        self.player_id = player_id
        self.player_name = player_name
        self.sport = sport


class TeamNotFoundError(DomainException):
    """Raised when a team cannot be found."""
    
    def __init__(
        self, 
        team_id: Optional[int] = None, 
        team_name: Optional[str] = None,
        sport: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ):
        if team_id:
            message = f"Team with ID {team_id} not found"
        elif team_name:
            message = f"Team '{team_name}' not found"
        else:
            message = "Team not found"
        
        if sport:
            message += f" in {sport.upper()}"
            
        super().__init__(
            message=message,
            context=context,
            error_code="TEAM_NOT_FOUND",
            recoverable=False
        )
        self.team_id = team_id
        self.team_name = team_name
        self.sport = sport


class GameNotFoundError(DomainException):
    """Raised when a game cannot be found."""
    
    def __init__(
        self, 
        game_id: Optional[int] = None,
        date: Optional[str] = None,
        sport: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ):
        if game_id:
            message = f"Game with ID {game_id} not found"
        elif date:
            message = f"No games found for date {date}"
        else:
            message = "Game not found"
        
        if sport:
            message += f" in {sport.upper()}"
            
        super().__init__(
            message=message,
            context=context,
            error_code="GAME_NOT_FOUND",
            recoverable=False
        )
        self.game_id = game_id
        self.date = date
        self.sport = sport


class InvalidSportError(DomainException):
    """Raised when an invalid sport is specified."""
    
    def __init__(
        self, 
        sport: str, 
        valid_sports: Optional[List[str]] = None,
        context: Optional[ErrorContext] = None
    ):
        message = f"Invalid sport: '{sport}'"
        if valid_sports:
            message += f". Valid sports: {', '.join(valid_sports)}"
            
        super().__init__(
            message=message,
            context=context,
            error_code="INVALID_SPORT",
            recoverable=True
        )
        self.sport = sport
        self.valid_sports = valid_sports


class InvalidSearchCriteriaError(DomainException):
    """Raised when search criteria are invalid."""
    
    def __init__(
        self, 
        criteria: str,
        reason: str,
        context: Optional[ErrorContext] = None
    ):
        message = f"Invalid search criteria '{criteria}': {reason}"
        super().__init__(
            message=message,
            context=context,
            error_code="INVALID_SEARCH_CRITERIA",
            recoverable=True
        )
        self.criteria = criteria
        self.reason = reason


# =============================================================================
# Cache-Related Exceptions
# =============================================================================

class CacheException(HoopHeadException):
    """Base class for cache-related errors."""
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
        recoverable: bool = True
    ):
        super().__init__(
            message=message,
            context=context,
            original_error=original_error,
            error_code="CACHE_ERROR",
            recoverable=recoverable
        )


class CacheConnectionError(CacheException):
    """Raised when unable to connect to cache server."""
    
    def __init__(
        self, 
        cache_url: str,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Failed to connect to cache server: {cache_url}"
        super().__init__(
            message=message,
            context=context,
            original_error=original_error,
            error_code="CACHE_CONNECTION_ERROR",
            recoverable=True
        )
        self.cache_url = cache_url


class CacheTimeoutError(CacheException):
    """Raised when cache operation times out."""
    
    def __init__(
        self, 
        operation: str,
        timeout: float,
        context: Optional[ErrorContext] = None
    ):
        message = f"Cache {operation} operation timed out after {timeout} seconds"
        super().__init__(
            message=message,
            context=context,
            error_code="CACHE_TIMEOUT_ERROR",
            recoverable=True
        )
        self.operation = operation
        self.timeout = timeout


class CacheSerializationError(CacheException):
    """Raised when cache serialization/deserialization fails."""
    
    def __init__(
        self, 
        operation: str,
        data_type: str,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        message = f"Cache {operation} failed for {data_type} data"
        super().__init__(
            message=message,
            context=context,
            original_error=original_error,
            error_code="CACHE_SERIALIZATION_ERROR",
            recoverable=True
        )
        self.operation = operation
        self.data_type = data_type 