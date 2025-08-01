"""
Centralized error handling and recovery strategies for HoopHead platform.
Provides decorators, context managers, and utilities for consistent error management.
"""

import asyncio
import logging
import functools
from typing import Any, Callable, Optional, Dict, Union, TypeVar, Awaitable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from .exceptions import (
    HoopHeadException, ErrorContext,
    APIException, APIConnectionError, APITimeoutError, APIRateLimitError,
    CacheException, DomainException
)

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])
AF = TypeVar('AF', bound=Callable[..., Awaitable[Any]])


class ErrorHandler:
    """
    Centralized error handling with retry logic, fallback strategies, and logging.
    """
    
    def __init__(self, default_retries: int = 3, default_delay: float = 1.0):
        self.default_retries = default_retries
        self.default_delay = default_delay
        self.retry_history: Dict[str, Dict[str, Any]] = {}
    
    def with_retry(
        self,
        max_retries: Optional[int] = None,
        delay: Optional[float] = None,
        exponential_backoff: bool = True,
        retryable_exceptions: Optional[tuple] = None
    ):
        """
        Decorator for automatic retry with exponential backoff.
        
        Args:
            max_retries: Maximum number of retry attempts
            delay: Initial delay between retries
            exponential_backoff: Whether to use exponential backoff
            retryable_exceptions: Tuple of exception types to retry on
        """
        if retryable_exceptions is None:
            retryable_exceptions = (APIConnectionError, APITimeoutError, CacheException)
        
        def decorator(func: AF) -> AF:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                retries = max_retries or self.default_retries
                current_delay = delay or self.default_delay
                operation_id = f"{func.__module__}.{func.__name__}"
                
                for attempt in range(retries + 1):
                    try:
                        result = await func(*args, **kwargs)
                        
                        # Log successful retry recovery
                        if attempt > 0:
                            logger.info(
                                f"Operation {operation_id} succeeded after {attempt} retries"
                            )
                            
                        return result
                        
                    except retryable_exceptions as e:
                        if attempt >= retries:
                            # Record failed operation
                            self._record_failure(operation_id, e, attempt + 1)
                            logger.error(
                                f"Operation {operation_id} failed after {attempt + 1} attempts: {e}"
                            )
                            raise
                        
                        # Log retry attempt
                        logger.warning(
                            f"Operation {operation_id} failed (attempt {attempt + 1}/{retries + 1}): {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        
                        await asyncio.sleep(current_delay)
                        
                        if exponential_backoff:
                            current_delay *= 2
                    
                    except Exception as e:
                        # Non-retryable exception
                        self._record_failure(operation_id, e, attempt + 1)
                        logger.error(f"Non-retryable error in {operation_id}: {e}")
                        raise
                        
            return wrapper
        return decorator
    
    def with_fallback(self, fallback_value: Any = None, log_fallback: bool = True):
        """
        Decorator that provides a fallback value when operation fails.
        
        Args:
            fallback_value: Value to return on failure
            log_fallback: Whether to log fallback usage
        """
        def decorator(func: AF) -> AF:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                operation_id = f"{func.__module__}.{func.__name__}"
                
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if log_fallback:
                        logger.warning(
                            f"Operation {operation_id} failed, using fallback value: {e}"
                        )
                    
                    self._record_fallback(operation_id, e, fallback_value)
                    return fallback_value
                    
            return wrapper
        return decorator
    
    def with_error_context(
        self,
        operation: str,
        sport: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        """
        Decorator that adds error context to exceptions.
        
        Args:
            operation: Name of the operation
            sport: Sport context (if applicable)
            endpoint: API endpoint (if applicable)
        """
        def decorator(func: AF) -> AF:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except HoopHeadException as e:
                    # Enhance existing HoopHead exceptions
                    if not e.context:
                        e.context = ErrorContext(
                            operation=operation,
                            sport=sport,
                            endpoint=endpoint,
                            parameters=kwargs
                        )
                    raise
                except Exception as e:
                    # Wrap other exceptions
                    context = ErrorContext(
                        operation=operation,
                        sport=sport,
                        endpoint=endpoint,
                        parameters=kwargs
                    )
                    
                    # Try to map to appropriate HoopHead exception
                    if isinstance(e, (ConnectionError, OSError)):
                        raise APIConnectionError(
                            url=endpoint or "unknown",
                            context=context,
                            original_error=e
                        )
                    elif isinstance(e, asyncio.TimeoutError):
                        raise APITimeoutError(
                            timeout=kwargs.get('timeout', 30.0),
                            context=context
                        )
                    else:
                        # Generic domain exception for unclassified errors
                        raise DomainException(
                            message=f"Unexpected error in {operation}: {str(e)}",
                            context=context,
                            original_error=e
                        )
                        
            return wrapper
        return decorator
    
    @asynccontextmanager
    async def error_boundary(
        self,
        operation: str,
        fallback_result: Any = None,
        suppress_errors: bool = False
    ):
        """
        Async context manager for error boundaries with optional fallback.
        
        Args:
            operation: Name of the operation
            fallback_result: Result to return on error
            suppress_errors: Whether to suppress errors (return fallback)
        """
        try:
            yield
        except Exception as e:
            logger.error(f"Error boundary triggered for {operation}: {e}")
            
            if suppress_errors:
                logger.info(f"Suppressing error for {operation}, using fallback")
                # Note: Context managers can't return values, so we'll just suppress
                pass
            else:
                raise
    
    def _record_failure(self, operation_id: str, error: Exception, attempts: int):
        """Record operation failure for monitoring."""
        if operation_id not in self.retry_history:
            self.retry_history[operation_id] = {
                'failures': 0,
                'last_failure': None,
                'total_attempts': 0
            }
        
        history = self.retry_history[operation_id]
        history['failures'] += 1
        history['last_failure'] = datetime.utcnow()
        history['total_attempts'] += attempts
    
    def _record_fallback(self, operation_id: str, error: Exception, fallback_value: Any):
        """Record fallback usage for monitoring."""
        logger.info(
            f"Fallback used for {operation_id}: {type(error).__name__} -> {type(fallback_value).__name__}"
        )
    
    def get_failure_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get failure statistics for monitoring."""
        return self.retry_history.copy()
    
    def reset_stats(self):
        """Reset failure statistics."""
        self.retry_history.clear()


# Global error handler instance
error_handler = ErrorHandler()


def with_api_error_handling(
    max_retries: int = 3,
    delay: float = 1.0,
    fallback_value: Any = None
):
    """
    Combined decorator for API operations with retry and fallback.
    
    Args:
        max_retries: Maximum retry attempts
        delay: Initial delay between retries
        fallback_value: Fallback value on failure
    """
    def decorator(func: AF) -> AF:
        # Apply retry decorator
        retry_decorated = error_handler.with_retry(
            max_retries=max_retries,
            delay=delay,
            retryable_exceptions=(
                APIConnectionError, APITimeoutError, APIRateLimitError, CacheException
            )
        )(func)
        
        # Apply fallback if specified
        if fallback_value is not None:
            return error_handler.with_fallback(fallback_value)(retry_decorated)
        
        return retry_decorated
    
    return decorator


def with_domain_error_handling(fallback_value: Any = None, suppress_hoophead_errors: bool = False):
    """
    Decorator for domain service operations with error handling.
    
    Args:
        fallback_value: Fallback value on failure
        suppress_hoophead_errors: Whether to suppress HoopHead exceptions and use fallback
    """
    def decorator(func: AF) -> AF:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HoopHeadException as e:
                if suppress_hoophead_errors and fallback_value is not None:
                    operation = f"{func.__module__}.{func.__name__}"
                    logger.warning(f"Suppressing HoopHead error in {operation}: {e}, using fallback")
                    return fallback_value
                else:
                    # Re-raise HoopHead exceptions as-is
                    raise
            except Exception as e:
                # Wrap unexpected exceptions
                operation = f"{func.__module__}.{func.__name__}"
                logger.error(f"Unexpected error in domain operation {operation}: {e}")
                
                if fallback_value is not None:
                    logger.info(f"Using fallback value for {operation}")
                    return fallback_value
                
                # Wrap in domain exception
                raise DomainException(
                    message=f"Unexpected error in {operation}",
                    original_error=e,
                    context=ErrorContext(operation=operation, parameters=kwargs)
                )
        
        return wrapper
    
    return decorator


async def safe_execute(
    operation: Callable[..., Awaitable[Any]],
    *args,
    fallback_value: Any = None,
    log_errors: bool = True,
    **kwargs
) -> Any:
    """
    Safely execute an async operation with error handling.
    
    Args:
        operation: Async function to execute
        *args: Positional arguments for operation
        fallback_value: Value to return on error
        log_errors: Whether to log errors
        **kwargs: Keyword arguments for operation
    
    Returns:
        Operation result or fallback value
    """
    try:
        return await operation(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Safe execute failed for {operation.__name__}: {e}")
        return fallback_value 