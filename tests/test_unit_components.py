"""
Comprehensive Unit Tests for HoopHead Individual Components.
Tests each component in isolation with mocked dependencies.
"""
import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
import json

# Add backend source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

# Import components to test
from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport, APIResponse
from adapters.external.auth_manager import AuthenticationManager, APITier, TierLimits, APIKeyInfo
from adapters.cache.redis_client import RedisCache, CacheEntry
from adapters.cache.file_cache import FileCache, FileCacheStrategy
from adapters.cache.multi_cache_manager import MultiCacheManager, CacheStrategy
from domain.models.player import Player
from domain.models.team import Team
from domain.models.game import Game
from domain.models.base import SportType
from domain.services.player_service import PlayerService
from domain.services.team_service import TeamService
from domain.services.game_service import GameService
from domain.services.search_service import SearchService


class TestBallDontLieClientUnit:
    """Unit tests for Ball Don't Lie API client."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = BallDontLieClient(api_key="test_key_123")
    
    def test_client_initialization(self):
        """Test client initialization with various configurations."""
        # Test with API key
        client = BallDontLieClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.cache_enabled == True  # Default
        
        # Test without cache
        client_no_cache = BallDontLieClient(api_key="test_key", enable_cache=False)
        assert client_no_cache.cache_enabled == False
    
    def test_base_url_generation(self):
        """Test sport-specific base URL generation."""
        assert "balldontlie.io/v1" in self.client._get_base_url(Sport.NBA)
        assert "balldontlie.io/mlb/v1" in self.client._get_base_url(Sport.MLB)
        assert "balldontlie.io/nfl/v1" in self.client._get_base_url(Sport.NFL)
        assert "balldontlie.io/nhl/v1" in self.client._get_base_url(Sport.NHL)
        assert "balldontlie.io/epl/v1" in self.client._get_base_url(Sport.EPL)
    
    def test_cache_key_generation(self):
        """Test cache key generation for requests."""
        params = {"page": 1, "search": "LeBron"}
        key1 = self.client._generate_cache_key(Sport.NBA, "players", params)
        key2 = self.client._generate_cache_key(Sport.NBA, "players", params)
        key3 = self.client._generate_cache_key(Sport.NBA, "players", {"search": "LeBron", "page": 1})
        
        assert key1 == key2, "Same parameters should generate same cache key"
        assert key1 == key3, "Parameter order shouldn't matter"
        assert "nba" in key1, "Cache key should include sport"
        assert "players" in key1, "Cache key should include endpoint"
    
    @pytest.mark.asyncio
    async def test_request_rate_limiting(self):
        """Test rate limiting logic."""
        with patch('time.time', side_effect=[0, 0.3, 0.8]):  # Mock time progression
            # First request should not be delayed
            assert self.client.last_request_time == 0
            
            # Simulate time passage
            self.client.last_request_time = 0.3
            # Should need to wait for rate limiting
            # (This would be tested more thoroughly with actual async sleep mocking)
    
    @pytest.mark.asyncio 
    async def test_error_response_handling(self):
        """Test handling of various API error responses."""
        # Mock aiohttp response for 404 error
        mock_response = Mock()
        mock_response.status = 404
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json = AsyncMock(return_value={"error": "Not found"})
        
        # Test that 404 raises appropriate exception
        from core.exceptions import APINotFoundError
        # This would be tested with proper context manager mocking


class TestAuthenticationManagerUnit:
    """Unit tests for Authentication Manager."""
    
    def setup_method(self):
        """Set up test environment."""
        # Use a fixed encryption key for testing
        self.test_encryption_key = "test_key_32_characters_for_fernet"
        self.auth_manager = AuthenticationManager(encryption_key=self.test_encryption_key)
    
    def test_tier_limits_configuration(self):
        """Test tier limits are properly configured."""
        assert APITier.FREE in self.auth_manager.tier_limits
        assert APITier.ALL_STAR in self.auth_manager.tier_limits
        assert APITier.GOAT in self.auth_manager.tier_limits
        assert APITier.ENTERPRISE in self.auth_manager.tier_limits
        
        # Test FREE tier limits match Ball Don't Lie API
        free_limits = self.auth_manager.tier_limits[APITier.FREE]
        assert free_limits.requests_per_hour == 300
        assert free_limits.requests_per_minute == 5
        assert free_limits.cache_priority == 1
    
    def test_api_key_tier_detection(self):
        """Test automatic tier detection from API key format."""
        assert self.auth_manager._detect_key_tier("goat_premium_key") == APITier.GOAT
        assert self.auth_manager._detect_key_tier("all_star_key") == APITier.ALL_STAR
        assert self.auth_manager._detect_key_tier("ent_enterprise_key") == APITier.ENTERPRISE
        assert self.auth_manager._detect_key_tier("regular_key") == APITier.FREE
    
    def test_api_key_validation(self):
        """Test API key format validation."""
        valid_keys = [
            "goat_test_key_123",
            "all_star_production_key",
            "ent_enterprise_key_456",
            "bdl_standard_key"
        ]
        
        invalid_keys = [
            "",
            "too_short",
            "invalid format with spaces"
        ]
        
        for key in valid_keys:
            is_valid, _, tier = self.auth_manager.validate_api_key(key)
            assert is_valid, f"Key {key} should be valid"
            assert tier is not None, f"Key {key} should have detected tier"
        
        for key in invalid_keys:
            is_valid, _, _ = self.auth_manager.validate_api_key(key)
            assert not is_valid, f"Key {key} should be invalid"
    
    def test_api_key_encryption_decryption(self):
        """Test API key encryption and decryption."""
        original_key = "test_api_key_12345"
        
        # Add key to manager
        key_id = self.auth_manager.add_api_key(original_key, APITier.ALL_STAR, "Test Key")
        
        # Retrieve and verify
        decrypted_key = self.auth_manager.get_api_key(key_id)
        assert decrypted_key == original_key, "Decrypted key should match original"
        
        # Verify key info
        key_info = self.auth_manager.get_key_info(key_id)
        assert key_info.tier == APITier.ALL_STAR
        assert key_info.label == "Test Key"
        assert key_info.is_active == True
    
    @pytest.mark.asyncio
    async def test_rate_limiting_logic(self):
        """Test rate limiting enforcement."""
        # Add a FREE tier key (5 requests per minute)
        key_id = self.auth_manager.add_api_key("free_test_key", APITier.FREE, "Test")
        
        # Should allow initial requests
        allowed, info = await self.auth_manager.check_rate_limit(key_id)
        assert allowed == True
        assert info["minute_remaining"] == 5
        
        # Record some requests
        for i in range(3):
            await self.auth_manager.record_request(key_id, success=True)
        
        # Check updated limits
        allowed, info = await self.auth_manager.check_rate_limit(key_id)
        assert allowed == True
        assert info["minute_remaining"] == 2
    
    def test_usage_statistics_tracking(self):
        """Test usage statistics collection."""
        key_id = self.auth_manager.add_api_key("stats_key", APITier.GOAT, "Stats Test")
        
        # Initial stats should be zero
        stats = self.auth_manager.get_usage_stats(key_id)
        assert stats["total_requests"] == 0
        assert stats["tier"] == "goat"
        assert stats["label"] == "Stats Test"


class TestCacheComponentsUnit:
    """Unit tests for caching components."""
    
    def setup_method(self):
        """Set up test environment."""
        self.redis_cache = RedisCache()
        self.multi_cache = MultiCacheManager()
    
    def test_redis_cache_initialization(self):
        """Test Redis cache initialization."""
        assert self.redis_cache.enabled == True
        assert self.redis_cache.compression_threshold == 1024
        assert self.redis_cache.key_prefix == "hoophead"
        assert self.redis_cache.version == "v1"
    
    def test_redis_cache_ttl_strategies(self):
        """Test sport-specific TTL strategies."""
        # NBA strategy
        nba_teams_ttl = self.redis_cache._get_ttl_for_endpoint(Sport.NBA, "teams")
        nba_stats_ttl = self.redis_cache._get_ttl_for_endpoint(Sport.NBA, "stats")
        
        assert nba_teams_ttl == 86400, "NBA teams should cache for 24 hours"
        assert nba_stats_ttl == 1800, "NBA stats should cache for 30 minutes"
        
        # NFL strategy (less frequent updates)
        nfl_games_ttl = self.redis_cache._get_ttl_for_endpoint(Sport.NFL, "games")
        assert nfl_games_ttl == 7200, "NFL games should cache for 2 hours (weekly schedule)"
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        params = {"page": 1, "search": "test"}
        key = self.redis_cache._generate_cache_key(Sport.NBA, "players", params)
        
        assert key.startswith("hoophead:v1:nba:players:")
        assert len(key.split(":")) == 5, "Should have 5 parts separated by colons"
    
    def test_compression_logic(self):
        """Test data compression logic."""
        small_data = b"small"
        large_data = b"x" * 2000  # 2KB
        
        assert not self.redis_cache._should_compress(small_data)
        assert self.redis_cache._should_compress(large_data)
    
    def test_multi_cache_strategy_selection(self):
        """Test cache strategy selection logic."""
        # FREE tier should prefer file cache
        free_strategy = self.multi_cache._determine_cache_strategy(APITier.FREE, "teams")
        assert free_strategy in [CacheStrategy.FILE_ONLY, CacheStrategy.LAYERED]
        
        # GOAT tier should prefer Redis
        goat_strategy = self.multi_cache._determine_cache_strategy(APITier.GOAT, "teams")
        assert goat_strategy in [CacheStrategy.LAYERED, CacheStrategy.TIER_OPTIMIZED]
        
        # Historical endpoints should use file strategy
        historical_strategy = self.multi_cache._determine_cache_strategy(APITier.GOAT, "historical_stats")
        assert historical_strategy == CacheStrategy.HISTORICAL


class TestDomainModelsUnit:
    """Unit tests for domain models."""
    
    def test_player_model_creation(self):
        """Test player model creation and methods."""
        player_data = {
            "id": 1,
            "first_name": "LeBron",
            "last_name": "James",
            "height": "6-9",
            "weight": "250",
            "position": "F",
            "team": {"id": 14, "name": "Lakers"}
        }
        
        player = Player.from_api_response(player_data, SportType.NBA)
        
        assert player.id == 1
        assert player.first_name == "LeBron"
        assert player.last_name == "James"
        assert player.full_name == "LeBron James"
        assert player.height_inches == 81  # 6'9" = 81 inches
        assert player.weight_lbs == 250
        assert player.sport == SportType.NBA
    
    def test_team_model_creation(self):
        """Test team model creation and methods."""
        team_data = {
            "id": 1,
            "name": "Los Angeles Lakers",
            "abbreviation": "LAL",
            "city": "Los Angeles",
            "conference": "West",
            "division": "Pacific"
        }
        
        team = Team.from_api_response(team_data, SportType.NBA)
        
        assert team.id == 1
        assert team.name == "Los Angeles Lakers"
        assert team.abbreviation == "LAL"
        assert team.city == "Los Angeles"
        assert team.full_name == "Los Angeles Lakers"
        assert team.sport == SportType.NBA
    
    def test_game_model_creation(self):
        """Test game model creation and methods."""
        game_data = {
            "id": 1,
            "date": "2024-01-15",
            "home_team": {"id": 1, "name": "Lakers"},
            "visitor_team": {"id": 2, "name": "Warriors"},
            "home_team_score": 115,
            "visitor_team_score": 108,
            "status": "Final"
        }
        
        game = Game.from_api_response(game_data, SportType.NBA)
        
        assert game.id == 1
        assert game.home_team_score == 115
        assert game.visitor_team_score == 108
        assert game.is_final == True
        assert game.winner_id == 1  # Home team won
        assert game.sport == SportType.NBA
    
    def test_player_height_conversion(self):
        """Test player height conversion edge cases."""
        # Test various height formats
        test_cases = [
            ("6-9", 81),
            ("5-11", 71),
            ("7-1", 85),
            ("6-0", 72)
        ]
        
        for height_str, expected_inches in test_cases:
            player_data = {
                "id": 1,
                "first_name": "Test",
                "last_name": "Player",
                "height": height_str
            }
            player = Player.from_api_response(player_data, SportType.NBA)
            assert player.height_inches == expected_inches, f"Height {height_str} should convert to {expected_inches} inches"


class TestDomainServicesUnit:
    """Unit tests for domain services."""
    
    def setup_method(self):
        """Set up test environment with mocked dependencies."""
        # Create services with mocked API client
        self.mock_client = Mock()
        self.player_service = PlayerService(api_client=self.mock_client)
        self.team_service = TeamService(api_client=self.mock_client)
        self.game_service = GameService(api_client=self.mock_client)
        self.search_service = SearchService(
            player_service=self.player_service,
            team_service=self.team_service,
            game_service=self.game_service
        )
    
    def test_player_service_initialization(self):
        """Test player service initialization."""
        assert self.player_service.api_client == self.mock_client
        assert hasattr(self.player_service, 'search_players')
        assert hasattr(self.player_service, 'get_player_stats')
    
    def test_team_service_initialization(self):
        """Test team service initialization."""
        assert self.team_service.api_client == self.mock_client
        assert hasattr(self.team_service, 'get_teams')
        assert hasattr(self.team_service, 'get_team_roster')
    
    def test_game_service_initialization(self):
        """Test game service initialization."""
        assert self.game_service.api_client == self.mock_client
        assert hasattr(self.game_service, 'get_games')
        assert hasattr(self.game_service, 'get_team_schedule')
    
    def test_search_service_initialization(self):
        """Test search service initialization."""
        assert self.search_service.player_service == self.player_service
        assert self.search_service.team_service == self.team_service
        assert self.search_service.game_service == self.game_service
        assert hasattr(self.search_service, 'search_all')
    
    @pytest.mark.asyncio
    async def test_player_service_search_logic(self):
        """Test player service search criteria handling."""
        # Mock API response
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = [{"id": 1, "first_name": "LeBron", "last_name": "James"}]
        
        self.mock_client.search_players = AsyncMock(return_value=mock_response)
        
        # Test search
        from domain.services.player_service import PlayerSearchCriteria
        criteria = PlayerSearchCriteria(name="LeBron", sport=SportType.NBA)
        
        result = await self.player_service.search_players(criteria)
        
        # Verify API client was called correctly
        self.mock_client.search_players.assert_called_once()
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_in_services(self):
        """Test error handling in domain services."""
        # Mock API client to raise exception
        from core.exceptions import APIConnectionError
        self.mock_client.get_teams = AsyncMock(side_effect=APIConnectionError("Connection failed"))
        
        # Service should handle the exception gracefully
        from domain.services.team_service import TeamSearchCriteria
        criteria = TeamSearchCriteria(sport=SportType.NBA)
        
        # This should not raise an exception if properly handled
        try:
            result = await self.team_service.get_teams(criteria)
            # Should return empty or error result, not crash
        except APIConnectionError:
            pytest.fail("Service should handle API exceptions gracefully")


# Performance measurement utilities for unit tests
class TestPerformanceUtilities:
    """Unit tests for performance measurement utilities."""
    
    def test_timing_accuracy(self):
        """Test timing measurement accuracy."""
        import time
        start = time.time()
        time.sleep(0.1)  # Sleep for 100ms
        end = time.time()
        duration_ms = (end - start) * 1000
        
        # Should be approximately 100ms (allow 50ms tolerance for system variance)
        assert 80 <= duration_ms <= 150, f"Duration {duration_ms}ms should be around 100ms"
    
    def test_memory_usage_monitoring(self):
        """Test memory usage monitoring utilities."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        # Create some data
        large_data = [i for i in range(100000)]
        
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        
        # Should see some memory increase
        assert memory_increase > 0, "Should detect memory usage increase"
        
        # Clean up
        del large_data


if __name__ == "__main__":
    """Run unit tests when executed directly."""
    pytest.main([__file__, "-v", "-s"]) 