"""
Comprehensive test suite for error handling and exception management.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add backend src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

from core.exceptions import (
    HoopHeadException, ErrorContext, APIException,
    APIConnectionError, APITimeoutError, APIRateLimitError,
    APIAuthenticationError, APINotFoundError, APIServerError,
    APIResponseError, DomainException, PlayerNotFoundError,
    TeamNotFoundError, CacheException
)
from core.error_handler import ErrorHandler, with_api_error_handling, with_domain_error_handling


class TestExceptionHierarchy:
    """Test the exception hierarchy and context handling."""
    
    def test_base_exception_creation(self):
        """Test HoopHeadException creation with context."""
        context = ErrorContext(
            operation="test_operation",
            sport="nba",
            endpoint="/players",
            parameters={"search": "james"}
        )
        
        exception = HoopHeadException(
            message="Test error message",
            context=context,
            error_code="TEST_ERROR",
            recoverable=True
        )
        
        assert exception.message == "Test error message"
        assert exception.context == context
        assert exception.error_code == "TEST_ERROR"
        assert exception.recoverable is True
        assert "TEST_ERROR" in str(exception)
        assert "nba" in str(exception)
    
    def test_api_exception_with_status_code(self):
        """Test API exception with HTTP status code."""
        context = ErrorContext(operation="api_call", sport="nba")
        
        exception = APIException(
            message="API error",
            status_code=500,
            response_data={"error": "Internal server error"},
            context=context
        )
        
        assert exception.status_code == 500
        assert exception.response_data["error"] == "Internal server error"
        
        # Test dictionary representation
        exception_dict = exception.to_dict()
        assert exception_dict["status_code"] == 500
        assert exception_dict["response_data"]["error"] == "Internal server error"
    
    def test_domain_exceptions(self):
        """Test domain-specific exceptions."""
        # Test PlayerNotFoundError
        player_error = PlayerNotFoundError(
            player_id=123,
            player_name="LeBron James",
            sport="nba"
        )
        assert "Player with ID 123 not found" in str(player_error)
        assert "NBA" in str(player_error)
        assert player_error.player_id == 123
        assert player_error.sport == "nba"
        
        # Test TeamNotFoundError
        team_error = TeamNotFoundError(
            team_name="Lakers",
            sport="nba"
        )
        assert "Team 'Lakers' not found" in str(team_error)
        assert "NBA" in str(team_error)
    
    def test_error_context_serialization(self):
        """Test ErrorContext serialization."""
        context = ErrorContext(
            operation="test_op",
            sport="nba",
            endpoint="/teams",
            parameters={"id": 1}
        )
        
        context_dict = context.to_dict()
        assert context_dict["operation"] == "test_op"
        assert context_dict["sport"] == "nba"
        assert context_dict["endpoint"] == "/teams"
        assert context_dict["parameters"] == {"id": 1}
        assert "timestamp" in context_dict


class TestErrorHandler:
    """Test the ErrorHandler utility and decorators."""
    
    @pytest.fixture
    def error_handler(self):
        """Create an ErrorHandler instance for testing."""
        return ErrorHandler(default_retries=2, default_delay=0.1)
    
    @pytest.mark.asyncio
    async def test_retry_decorator_success(self, error_handler):
        """Test retry decorator with successful operation."""
        call_count = 0
        
        @error_handler.with_retry(max_retries=3, delay=0.01)
        async def test_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIConnectionError(url="test://api")
            return "success"
        
        result = await test_operation()
        assert result == "success"
        assert call_count == 2  # Failed once, succeeded on retry
    
    @pytest.mark.asyncio
    async def test_retry_decorator_exhausted(self, error_handler):
        """Test retry decorator when retries are exhausted."""
        call_count = 0
        
        @error_handler.with_retry(max_retries=2, delay=0.01)
        async def test_operation():
            nonlocal call_count
            call_count += 1
            raise APIConnectionError(url="test://api")
        
        with pytest.raises(APIConnectionError):
            await test_operation()
        
        assert call_count == 3  # Original + 2 retries
    
    @pytest.mark.asyncio
    async def test_retry_decorator_non_retryable(self, error_handler):
        """Test retry decorator with non-retryable exception."""
        call_count = 0
        
        @error_handler.with_retry(max_retries=3, delay=0.01)
        async def test_operation():
            nonlocal call_count
            call_count += 1
            raise APIAuthenticationError()  # Non-retryable
        
        with pytest.raises(APIAuthenticationError):
            await test_operation()
        
        assert call_count == 1  # No retries for non-retryable error
    
    @pytest.mark.asyncio
    async def test_fallback_decorator(self, error_handler):
        """Test fallback decorator."""
        @error_handler.with_fallback(fallback_value="fallback_result")
        async def failing_operation():
            raise APIConnectionError(url="test://api")
        
        result = await failing_operation()
        assert result == "fallback_result"
    
    @pytest.mark.asyncio
    async def test_error_context_decorator(self, error_handler):
        """Test error context enhancement decorator."""
        @error_handler.with_error_context(
            operation="test_operation",
            sport="nba",
            endpoint="/players"
        )
        async def test_operation():
            raise ValueError("Test error")
        
        with pytest.raises(DomainException) as exc_info:
            await test_operation()
        
        exception = exc_info.value
        assert exception.context is not None
        assert exception.context.operation == "test_operation"
        assert exception.context.sport == "nba"
        assert exception.context.endpoint == "/players"
    
    @pytest.mark.asyncio
    async def test_error_boundary_context_manager(self, error_handler):
        """Test error boundary context manager."""
        # Test with error suppression
        async with error_handler.error_boundary(
            operation="test_boundary",
            fallback_result="boundary_fallback",
            suppress_errors=True
        ):
            raise ValueError("Test error")
        
        # Should not raise an exception
    
    def test_failure_statistics(self, error_handler):
        """Test failure statistics tracking."""
        error_handler._record_failure("test.operation", ValueError("test"), 3)
        
        stats = error_handler.get_failure_stats()
        assert "test.operation" in stats
        assert stats["test.operation"]["failures"] == 1
        assert stats["test.operation"]["total_attempts"] == 3
        
        # Test reset
        error_handler.reset_stats()
        stats = error_handler.get_failure_stats()
        assert len(stats) == 0


class TestErrorHandlingDecorators:
    """Test the convenience decorators for error handling."""
    
    @pytest.mark.asyncio
    async def test_api_error_handling_decorator(self):
        """Test the combined API error handling decorator."""
        call_count = 0
        
        @with_api_error_handling(max_retries=2, delay=0.01, fallback_value="api_fallback")
        async def api_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APITimeoutError(timeout=30.0)
            return "api_success"
        
        result = await api_operation()
        assert result == "api_success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_api_error_handling_with_fallback(self):
        """Test API error handling with fallback on exhausted retries."""
        @with_api_error_handling(max_retries=1, delay=0.01, fallback_value="api_fallback")
        async def failing_api_operation():
            raise APIConnectionError(url="test://api")
        
        result = await failing_api_operation()
        assert result == "api_fallback"
    
    @pytest.mark.asyncio
    async def test_domain_error_handling_decorator(self):
        """Test domain error handling decorator."""
        @with_domain_error_handling(fallback_value="domain_fallback")
        async def domain_operation():
            raise ValueError("Unexpected domain error")
        
        result = await domain_operation()
        assert result == "domain_fallback"
    
    @pytest.mark.asyncio
    async def test_domain_error_handling_preserves_hoophead_exceptions(self):
        """Test that domain error handling preserves HoopHead exceptions."""
        @with_domain_error_handling(fallback_value="domain_fallback")
        async def domain_operation():
            raise PlayerNotFoundError(player_id=123, sport="nba")
        
        with pytest.raises(PlayerNotFoundError):
            await domain_operation()


class TestAPIClientErrorIntegration:
    """Test error handling integration with API client."""
    
    @pytest.mark.asyncio
    async def test_simulated_api_errors(self):
        """Test various API error scenarios."""
        from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport
        
        # Test with mock to simulate different error conditions
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock 401 response
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with BallDontLieClient() as client:
                with pytest.raises(APIAuthenticationError):
                    await client._make_request(Sport.NBA, "teams")
            
            # Mock 404 response
            mock_response.status = 404
            async with BallDontLieClient() as client:
                with pytest.raises(APINotFoundError):
                    await client._make_request(Sport.NBA, "invalid_endpoint")
            
            # Mock 429 response
            mock_response.status = 429
            mock_response.headers = {'Retry-After': '60'}
            async with BallDontLieClient() as client:
                with pytest.raises(APIRateLimitError) as exc_info:
                    await client._make_request(Sport.NBA, "teams")
                
                assert exc_info.value.retry_after == 60
            
            # Mock 500 response
            mock_response.status = 500
            mock_response.json = AsyncMock(return_value={"error": "Internal server error"})
            async with BallDontLieClient() as client:
                with pytest.raises(APIServerError) as exc_info:
                    await client._make_request(Sport.NBA, "teams")
                
                assert exc_info.value.status_code == 500


if __name__ == "__main__":
    """Run error handling tests."""
    async def run_async_tests():
        test_instance = TestErrorHandler()
        error_handler = ErrorHandler(default_retries=2, default_delay=0.1)
        
        print("🧪 Running Error Handling Tests...")
        print("=" * 50)
        
        try:
            print("\n1. Testing Exception Hierarchy...")
            exception_tests = TestExceptionHierarchy()
            exception_tests.test_base_exception_creation()
            exception_tests.test_api_exception_with_status_code()
            exception_tests.test_domain_exceptions()
            exception_tests.test_error_context_serialization()
            print("✅ Exception hierarchy tests passed")
            
            print("\n2. Testing Error Handler...")
            await test_instance.test_retry_decorator_success(error_handler)
            await test_instance.test_fallback_decorator(error_handler)
            print("✅ Error handler tests passed")
            
            print("\n3. Testing Error Decorators...")
            decorator_tests = TestErrorHandlingDecorators()
            await decorator_tests.test_api_error_handling_decorator()
            await decorator_tests.test_domain_error_handling_decorator()
            print("✅ Error decorator tests passed")
            
            print("\n" + "=" * 50)
            print("🎉 All error handling tests passed!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
    
    # Run the tests
    asyncio.run(run_async_tests()) 