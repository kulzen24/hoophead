"""
Core package for HoopHead multi-sport platform.
Contains exceptions, utilities, and common functionality.
"""

from .exceptions import *
from .error_handler import ErrorHandler, ErrorContext
from .utils import *

__all__ = [
    # Base exceptions
    "HoopHeadException",
    "ValidationError",
    "ConfigurationError",
    
    # API exceptions
    "APIException",
    "APIConnectionError", 
    "APITimeoutError",
    "APIRateLimitError",
    "APIAuthenticationError",
    "APINotFoundError",
    "APIServerError",
    "APIResponseError",
    
    # Domain exceptions
    "DomainException",
    "PlayerNotFoundError",
    "TeamNotFoundError", 
    "GameNotFoundError",
    "InvalidSportError",
    "InvalidSearchCriteriaError",
    
    # Cache exceptions
    "CacheException",
    "CacheConnectionError",
    "CacheTimeoutError",
    "CacheSerializationError",
    
    # Error handler
    "ErrorHandler",
    "ErrorContext",
    
    # Utilities
    "PathManager",
    "LoggerFactory", 
    "APIResponseProcessor",
    "AsyncPatterns",
    "CacheKeyBuilder",
    "DataValidator",
    "EnvironmentManager",
    "PROJECT_ROOT",
    "BACKEND_SRC"
] 