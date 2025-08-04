"""
Common test utilities for HoopHead test suite.
Eliminates duplication across test files and provides standardized test patterns.
"""

import os
import sys
import asyncio
import pytest
from pathlib import Path
from typing import Any, Dict, Optional, List
from unittest.mock import Mock, AsyncMock

# Common path setup that was duplicated across test files
def setup_test_environment():
    """Setup test environment with proper path configuration."""
    try:
        from core.utils import PathManager, EnvironmentManager
        PathManager.setup_backend_path()
        EnvironmentManager.load_env_vars()
    except ImportError:
        # Fallback path setup if utils not available
        backend_path = Path(__file__).parent.parent / "backend" / "src"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))


# Call setup on import
setup_test_environment()


class MockAPIResponse:
    """Mock API response for testing."""
    
    def __init__(self, success: bool = True, data: Optional[Dict] = None, error: Optional[str] = None):
        self.success = success
        self.data = data or {}
        self.error = error
        self.status_code = 200 if success else 400


class MockBallDontLieClient:
    """Mock Ball Don't Lie API client for testing."""
    
    def __init__(self):
        self.responses = {}
        self.call_count = {}
    
    def set_response(self, method: str, response: MockAPIResponse):
        """Set mock response for a specific method."""
        self.responses[method] = response
        self.call_count[method] = 0
    
    async def get_teams(self, sport, **kwargs):
        """Mock get_teams method."""
        self.call_count['get_teams'] = self.call_count.get('get_teams', 0) + 1
        return self.responses.get('get_teams', MockAPIResponse())
    
    async def get_players(self, sport, **kwargs):
        """Mock get_players method."""
        self.call_count['get_players'] = self.call_count.get('get_players', 0) + 1
        return self.responses.get('get_players', MockAPIResponse())
    
    async def get_games(self, sport, **kwargs):
        """Mock get_games method."""
        self.call_count['get_games'] = self.call_count.get('get_games', 0) + 1
        return self.responses.get('get_games', MockAPIResponse())
    
    async def get_stats(self, sport, **kwargs):
        """Mock get_stats method."""
        self.call_count['get_stats'] = self.call_count.get('get_stats', 0) + 1
        return self.responses.get('get_stats', MockAPIResponse())
    
    async def invalidate_cache(self, *args, **kwargs):
        """Mock cache invalidation."""
        pass
    
    async def get_cache_stats(self):
        """Mock cache stats."""
        return {"cache_enabled": True, "hits": 0, "misses": 0}


class MockAuthenticationManager:
    """Mock authentication manager for testing."""
    
    def __init__(self):
        self.api_keys = {}
        self.usage_stats = {}
    
    def add_api_key(self, key: str, tier=None, description: str = "Test Key"):
        """Mock add API key."""
        key_id = f"key_{len(self.api_keys) + 1}"
        self.api_keys[key_id] = {
            'key': key,
            'tier': tier,
            'description': description,
            'active': True
        }
        return key_id
    
    def get_api_key(self, key_id: str):
        """Mock get API key."""
        return self.api_keys.get(key_id, {}).get('key')
    
    def validate_api_key(self, key: str):
        """Mock validate API key."""
        for key_id, key_data in self.api_keys.items():
            if key_data['key'] == key:
                return True, key_id, key_data['tier']
        return False, None, None
    
    async def check_rate_limit(self, key_id: str):
        """Mock rate limit check."""
        return True, {"requests_remaining": 100}
    
    async def record_request(self, key_id: str):
        """Mock request recording."""
        self.usage_stats[key_id] = self.usage_stats.get(key_id, 0) + 1


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_player_data(player_id: int = 1, name: str = "Test Player", team_id: int = 1):
        """Create mock player data."""
        return {
            "id": player_id,
            "first_name": name.split()[0] if " " in name else name,
            "last_name": name.split()[1] if " " in name else "Player",
            "team_id": team_id,
            "team": {
                "id": team_id,
                "name": "Test Team",
                "city": "Test City",
                "abbreviation": "TT"
            },
            "position": "PG",
            "height": "6-0",
            "weight": "180"
        }
    
    @staticmethod
    def create_team_data(team_id: int = 1, name: str = "Test Team", city: str = "Test City"):
        """Create mock team data."""
        return {
            "id": team_id,
            "name": name,
            "city": city,
            "abbreviation": name[:3].upper(),
            "conference": "Eastern",
            "division": "Atlantic"
        }
    
    @staticmethod
    def create_game_data(game_id: int = 1, home_team_id: int = 1, visitor_team_id: int = 2):
        """Create mock game data."""
        return {
            "id": game_id,
            "date": "2023-01-01",
            "home_team": {
                "id": home_team_id,
                "name": "Home Team",
                "city": "Home City"
            },
            "visitor_team": {
                "id": visitor_team_id,
                "name": "Visitor Team", 
                "city": "Visitor City"
            },
            "home_team_score": 100,
            "visitor_team_score": 95,
            "status": "Final"
        }
    
    @staticmethod
    def create_stats_data(player_id: int = 1, game_id: int = 1):
        """Create mock player stats data."""
        return {
            "id": 1,
            "player_id": player_id,
            "game_id": game_id,
            "points": 20,
            "assists": 5,
            "rebounds": 8,
            "steals": 2,
            "blocks": 1,
            "turnovers": 3,
            "fgm": 8,
            "fga": 15,
            "fg3m": 2,
            "fg3a": 5,
            "ftm": 4,
            "fta": 4
        }


class AsyncTestCase:
    """Base class for async test cases with common setup."""
    
    def setup_method(self):
        """Setup method called before each test."""
        self.api_client = MockBallDontLieClient()
        self.auth_manager = MockAuthenticationManager()
        self.data_factory = TestDataFactory()
    
    def teardown_method(self):
        """Teardown method called after each test."""
        # Clean up any resources if needed
        pass
    
    async def async_setup(self):
        """Async setup for tests that need it."""
        pass
    
    async def async_teardown(self):
        """Async teardown for tests that need it."""
        pass


def create_mock_service_response(success: bool = True, data: Any = None, error: str = None):
    """Create a mock service response."""
    from domain.services.base_service import ServiceListResponse
    
    return ServiceListResponse(
        success=success,
        data=data or [],
        error=error,
        total_count=len(data) if data else 0
    )


def assert_api_called(mock_client: MockBallDontLieClient, method: str, times: int = 1):
    """Assert that an API method was called a specific number of times."""
    actual_calls = mock_client.call_count.get(method, 0)
    assert actual_calls == times, f"Expected {method} to be called {times} times, but was called {actual_calls} times"


def create_test_environment_vars():
    """Create test environment variables."""
    test_env_vars = {
        'BALLDONTLIE_API_KEY': 'test_api_key_123',
        'REDIS_URL': 'redis://localhost:6379/1',  # Use different DB for tests
        'HOOPHEAD_ENCRYPTION_KEY': 'test_encryption_key_32_chars_long',
        'DEBUG': 'true',
        'ENVIRONMENT': 'test'
    }
    
    for key, value in test_env_vars.items():
        os.environ[key] = value
    
    return test_env_vars


def cleanup_test_environment_vars(env_vars: Dict[str, str]):
    """Clean up test environment variables."""
    for key in env_vars.keys():
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def mock_api_client():
    """Pytest fixture for mock API client."""
    return MockBallDontLieClient()


@pytest.fixture
def mock_auth_manager():
    """Pytest fixture for mock authentication manager."""
    return MockAuthenticationManager()


@pytest.fixture
def test_data_factory():
    """Pytest fixture for test data factory."""
    return TestDataFactory()


@pytest.fixture
def test_env_vars():
    """Pytest fixture for test environment variables."""
    env_vars = create_test_environment_vars()
    yield env_vars
    cleanup_test_environment_vars(env_vars)


@pytest.fixture
async def async_test_setup():
    """Pytest fixture for async test setup."""
    test_case = AsyncTestCase()
    test_case.setup_method()
    await test_case.async_setup()
    yield test_case
    await test_case.async_teardown()
    test_case.teardown_method()


class PerformanceTimer:
    """Simple performance timer for tests."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start the timer."""
        import time
        self.start_time = time.time()
    
    def stop(self):
        """Stop the timer."""
        import time
        self.end_time = time.time()
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return self.elapsed * 1000


def assert_response_time(timer: PerformanceTimer, max_time_ms: float):
    """Assert that response time is below threshold."""
    assert timer.elapsed_ms <= max_time_ms, f"Response time {timer.elapsed_ms:.2f}ms exceeded limit of {max_time_ms}ms"


# Common test patterns
class CommonTestPatterns:
    """Common test patterns used across test suites."""
    
    @staticmethod
    async def test_service_initialization(service_class, api_client):
        """Test service initialization pattern."""
        service = service_class(api_client)
        assert service.api_client == api_client
        assert hasattr(service, 'get_api_endpoint')
        assert hasattr(service, 'create_search_criteria')
    
    @staticmethod
    async def test_service_get_by_id(service, entity_id: int, sport, expected_entity):
        """Test get by ID pattern."""
        result = await service.get_by_id(entity_id, sport)
        if expected_entity:
            assert result is not None
            assert result.id == entity_id
        else:
            assert result is None
    
    @staticmethod
    async def test_service_get_all(service, sport, expected_count: int):
        """Test get all pattern."""
        results = await service.get_all(sport)
        assert isinstance(results, list)
        assert len(results) == expected_count
    
    @staticmethod
    async def test_service_search(service, criteria, expected_count: int):
        """Test search pattern."""
        response = await service.search(criteria)
        assert response.success
        assert len(response.data) == expected_count
        assert response.total_count == expected_count


# Export commonly used classes and functions
__all__ = [
    'setup_test_environment',
    'MockAPIResponse',
    'MockBallDontLieClient', 
    'MockAuthenticationManager',
    'TestDataFactory',
    'AsyncTestCase',
    'PerformanceTimer',
    'CommonTestPatterns',
    'create_mock_service_response',
    'assert_api_called',
    'assert_response_time',
    'create_test_environment_vars',
    'cleanup_test_environment_vars'
] 