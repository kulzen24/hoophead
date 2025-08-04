"""
Core utilities for HoopHead platform.
Common functionality used across the entire application.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional, Union, Type, TypeVar
from functools import wraps

# Type variable for generic functions
T = TypeVar('T')

# Constants
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"


class PathManager:
    """Centralized path management for consistent imports."""
    
    @staticmethod
    def setup_backend_path():
        """Add backend/src to Python path if not already present."""
        backend_path = str(BACKEND_SRC)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
    
    @staticmethod
    def setup_core_path():
        """Add core module to Python path for internal imports."""
        core_path = str(BACKEND_SRC / "core")
        if core_path not in sys.path:
            sys.path.append(core_path)
    
    @staticmethod
    def get_project_root() -> Path:
        """Get the project root directory."""
        return PROJECT_ROOT
    
    @staticmethod
    def get_backend_src() -> Path:
        """Get the backend source directory."""
        return BACKEND_SRC


class LoggerFactory:
    """Centralized logger configuration."""
    
    _configured = False
    
    @classmethod
    def setup_logging(cls, level: str = "INFO", format_string: Optional[str] = None):
        """Setup application-wide logging configuration."""
        if cls._configured:
            return
            
        if format_string is None:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=format_string,
            handlers=[logging.StreamHandler()]
        )
        cls._configured = True
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a configured logger instance."""
        LoggerFactory.setup_logging()
        return logging.getLogger(name)


class APIResponseProcessor:
    """Common API response processing utilities."""
    
    @staticmethod
    def extract_data(response_data: Dict[str, Any], key: str = "data") -> Any:
        """Extract data from API response with validation."""
        if not isinstance(response_data, dict):
            raise ValueError(f"Expected dict response, got {type(response_data)}")
        
        if key not in response_data:
            raise KeyError(f"Response missing required key: {key}")
        
        return response_data[key]
    
    @staticmethod
    def safe_extract(response_data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely extract data from API response with default fallback."""
        if not isinstance(response_data, dict):
            return default
        return response_data.get(key, default)
    
    @staticmethod
    def validate_api_response(response_data: Dict[str, Any], required_keys: list) -> bool:
        """Validate that API response contains all required keys."""
        if not isinstance(response_data, dict):
            return False
        return all(key in response_data for key in required_keys)


class AsyncPatterns:
    """Common async patterns and utilities."""
    
    @staticmethod
    def async_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
        """Decorator for async functions with retry logic."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries:
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff
                        else:
                            raise last_exception
                            
            return wrapper
        return decorator
    
    @staticmethod
    async def safe_execute(coro, default_value=None, log_errors: bool = True):
        """Safely execute async operation with error handling."""
        try:
            return await coro
        except Exception as e:
            if log_errors:
                logger = LoggerFactory.get_logger(__name__)
                logger.error(f"Async operation failed: {e}")
            return default_value


class CacheKeyBuilder:
    """Standardized cache key generation."""
    
    @staticmethod
    def build_key(sport: str, endpoint: str, params: Optional[Dict] = None) -> str:
        """Build standardized cache key."""
        key_parts = [sport, endpoint]
        
        if params:
            # Sort params for consistent key generation
            sorted_params = sorted(params.items())
            param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            key_parts.append(param_str)
        
        return ":".join(key_parts)
    
    @staticmethod
    def build_analytics_key(component: str, metric: str) -> str:
        """Build cache key for analytics data."""
        return f"analytics:{component}:{metric}"


class DataValidator:
    """Common data validation utilities."""
    
    @staticmethod
    def validate_sport_type(sport: Union[str, Any]) -> str:
        """Validate and normalize sport type."""
        if hasattr(sport, 'value'):
            return sport.value
        if isinstance(sport, str):
            return sport.upper()
        raise ValueError(f"Invalid sport type: {sport}")
    
    @staticmethod
    def validate_positive_int(value: Any, name: str) -> int:
        """Validate positive integer values."""
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer, got: {value}")
        return value
    
    @staticmethod
    def validate_optional_int(value: Any, name: str) -> Optional[int]:
        """Validate optional integer values."""
        if value is None:
            return None
        return DataValidator.validate_positive_int(value, name)


class EnvironmentManager:
    """Environment configuration management."""
    
    @staticmethod
    def load_env_vars():
        """Load environment variables with dotenv fallback."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # dotenv not available, use system env vars only
    
    @staticmethod
    def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """Get environment variable with validation."""
        value = os.getenv(key, default)
        if required and value is None:
            raise EnvironmentError(f"Required environment variable not set: {key}")
        return value
    
    @staticmethod
    def get_env_bool(key: str, default: bool = False) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')


# Setup path management on import
PathManager.setup_backend_path()

# Export commonly used utilities
__all__ = [
    'PathManager',
    'LoggerFactory', 
    'APIResponseProcessor',
    'AsyncPatterns',
    'CacheKeyBuilder',
    'DataValidator',
    'EnvironmentManager',
    'PROJECT_ROOT',
    'BACKEND_SRC'
] 