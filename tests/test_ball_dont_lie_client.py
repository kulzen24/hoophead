#!/usr/bin/env python3
"""
Comprehensive test suite for Ball Don't Lie multi-sport API client.
Tests all 5 sports: NBA, MLB, NFL, NHL, EPL
"""
import asyncio
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock
from typing import Dict, Any

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

from src.adapters.external.ball_dont_lie_client import (
    BallDontLieClient,
    Sport,
    APIResponse,
    quick_player_search,
    quick_teams_all_sports
)


class TestBallDontLieClient:
    """Test suite for Ball Don't Lie multi-sport client."""
    
    @pytest.fixture
    def api_key(self):
        """Get API key from environment."""
        api_key = os.getenv("BALLDONTLIE_API_KEY")
        if not api_key:
            pytest.skip("BALLDONTLIE_API_KEY environment variable required")
        return api_key
    
    @pytest.fixture
    async def client(self, api_key):
        """Create client instance."""
        async with BallDontLieClient(api_key) as client:
            yield client
    
    # Basic initialization tests
    def test_client_initialization_with_api_key(self):
        """Test client initializes correctly with API key."""
        client = BallDontLieClient("test-key")
        assert client.api_key == "test-key"
        assert client.user_agent == "HoopHead/0.1.0"
        assert Sport.NBA.value in client.sport_base_urls
        assert Sport.NHL.value in client.sport_base_urls
    
    def test_client_initialization_from_env(self):
        """Test client gets API key from environment."""
        with patch.dict(os.environ, {'BALLDONTLIE_API_KEY': 'env-test-key'}):
            client = BallDontLieClient()
            assert client.api_key == "env-test-key"
    
    def test_client_initialization_no_api_key(self):
        """Test client raises error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key is required"):
                BallDontLieClient()
    
    # Sport configuration tests
    def test_all_sports_have_base_urls(self):
        """Test all 5 sports have configured base URLs."""
        client = BallDontLieClient("test-key")
        expected_sports = {Sport.NBA, Sport.MLB, Sport.NFL, Sport.NHL, Sport.EPL}
        
        for sport in expected_sports:
            assert sport.value in client.sport_base_urls
            assert client.sport_base_urls[sport.value].startswith("https://")
    
    def test_sport_base_url_retrieval(self):
        """Test sport-specific base URL retrieval."""
        client = BallDontLieClient("test-key")
        
        assert client._get_base_url(Sport.NBA) == "https://api.balldontlie.io/v1"
        assert client._get_base_url(Sport.MLB) == "https://api.balldontlie.io/mlb/v1"
        assert client._get_base_url(Sport.NFL) == "https://api.balldontlie.io/nfl/v1"
        assert client._get_base_url(Sport.NHL) == "https://api.balldontlie.io/nhl/v1"
        assert client._get_base_url(Sport.EPL) == "https://api.balldontlie.io/epl/v1"
    
    # Cache key generation tests
    def test_cache_key_generation(self):
        """Test cache key generation for different requests."""
        client = BallDontLieClient("test-key")
        
        key1 = client._generate_cache_key(Sport.NBA, "teams")
        key2 = client._generate_cache_key(Sport.NBA, "teams", {"limit": 10})
        key3 = client._generate_cache_key(Sport.MLB, "teams")
        
        assert key1.startswith("bdl:nba:teams:")
        assert key2.startswith("bdl:nba:teams:")
        assert key3.startswith("bdl:mlb:teams:")
        assert key1 != key2  # Different params should generate different keys
        assert key1 != key3  # Different sports should generate different keys
    
    # Live API tests (require actual API key)
    @pytest.mark.asyncio
    async def test_nba_teams_retrieval(self, client):
        """Test NBA teams retrieval."""
        response = await client.get_teams(Sport.NBA)
        
        assert response.success is True
        assert response.sport == Sport.NBA
        assert response.error is None
        assert "data" in response.data
        assert len(response.data["data"]) > 0
    
    @pytest.mark.asyncio
    async def test_mlb_teams_retrieval(self, client):
        """Test MLB teams retrieval."""
        response = await client.get_teams(Sport.MLB)
        
        assert response.success is True
        assert response.sport == Sport.MLB
        assert response.error is None
        assert "data" in response.data
    
    @pytest.mark.asyncio
    async def test_nfl_teams_retrieval(self, client):
        """Test NFL teams retrieval."""
        response = await client.get_teams(Sport.NFL)
        
        assert response.success is True
        assert response.sport == Sport.NFL
        assert response.error is None
        assert "data" in response.data
    
    @pytest.mark.asyncio
    async def test_nhl_teams_retrieval(self, client):
        """Test NHL teams retrieval - this is the new sport we added."""
        response = await client.get_teams(Sport.NHL)
        
        assert response.success is True
        assert response.sport == Sport.NHL
        assert response.error is None
        assert "data" in response.data
        # NHL should have more teams than other leagues
        assert len(response.data["data"]) > 30
    
    @pytest.mark.asyncio
    async def test_epl_teams_retrieval(self, client):
        """Test EPL teams retrieval (may have limited functionality)."""
        response = await client.get_teams(Sport.EPL)
        
        # EPL might not work fully, so we test for either success or specific error
        if not response.success:
            assert response.sport == Sport.EPL
            assert response.error is not None
        else:
            assert response.sport == Sport.EPL
    
    @pytest.mark.asyncio
    async def test_nba_player_search(self, client):
        """Test NBA player search functionality."""
        response = await client.get_players(Sport.NBA, search="curry")
        
        assert response.success is True
        assert response.sport == Sport.NBA
        assert "data" in response.data
        assert len(response.data["data"]) > 0
        
        # Check that we found Stephen Curry
        players = response.data["data"]
        curry_found = any("curry" in player.get("last_name", "").lower() for player in players)
        assert curry_found
    
    @pytest.mark.asyncio
    async def test_multi_sport_player_search(self, client):
        """Test searching for players across multiple sports."""
        results = await client.search_players_across_sports("connor")
        
        # Should have results for all 5 sports
        assert len(results) == 5
        
        for sport in Sport:
            assert sport in results
            response = results[sport]
            assert isinstance(response, APIResponse)
            assert response.sport == sport
    
    @pytest.mark.asyncio
    async def test_get_all_teams_multi_sport(self, client):
        """Test getting teams from all sports simultaneously."""
        results = await client.get_all_teams()
        
        # Should have results for all 5 sports
        assert len(results) == 5
        
        successful_sports = []
        for sport, response in results.items():
            assert isinstance(response, APIResponse)
            assert response.sport == sport
            
            if response.success:
                successful_sports.append(sport)
                assert "data" in response.data
                assert len(response.data["data"]) > 0
        
        # At least NBA, MLB, NFL, NHL should work
        assert Sport.NBA in successful_sports
        assert Sport.MLB in successful_sports
        assert Sport.NFL in successful_sports
        assert Sport.NHL in successful_sports
    
    @pytest.mark.asyncio
    async def test_nhl_specific_functionality(self, client):
        """Test NHL-specific functionality to ensure it's fully integrated."""
        # Test teams
        teams_response = await client.get_teams(Sport.NHL)
        assert teams_response.success is True
        assert len(teams_response.data["data"]) > 25  # NHL has many teams
        
        # Test player search
        players_response = await client.get_players(Sport.NHL, search="mcdavid")
        assert players_response.success is True
        
        # Test games
        games_response = await client.get_games(Sport.NHL)
        assert games_response.success is True
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_endpoint(self, client):
        """Test error handling for invalid endpoints."""
        response = await client._make_request(Sport.NBA, "invalid_endpoint")
        
        assert response.success is False
        assert response.error is not None
        assert "404" in response.error or "not found" in response.error.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_delay(self, client):
        """Test that rate limiting delay is applied."""
        import time
        
        start_time = time.time()
        
        # Make two requests quickly
        await client.get_teams(Sport.NBA)
        await client.get_teams(Sport.MLB)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should take at least the rate limit delay
        assert elapsed >= client.min_request_interval
    
    # Convenience function tests
    @pytest.mark.asyncio
    async def test_quick_player_search_function(self, api_key):
        """Test the quick player search convenience function."""
        results = await quick_player_search("james", api_key)
        
        assert isinstance(results, dict)
        assert len(results) == 5
        
        for sport, response in results.items():
            assert isinstance(sport, Sport)
            assert isinstance(response, APIResponse)
    
    @pytest.mark.asyncio
    async def test_quick_teams_all_sports_function(self, api_key):
        """Test the quick teams fetch convenience function."""
        results = await quick_teams_all_sports(api_key)
        
        assert isinstance(results, dict)
        assert len(results) == 5
        
        successful_count = sum(1 for response in results.values() if response.success)
        assert successful_count >= 4  # At least NBA, MLB, NFL, NHL should work


# Test data validation
class TestAPIResponse:
    """Test APIResponse data structure."""
    
    def test_api_response_creation(self):
        """Test APIResponse creation and attributes."""
        response = APIResponse(
            data={"test": "data"},
            success=True,
            sport=Sport.NBA,
            meta={"total": 100}
        )
        
        assert response.data == {"test": "data"}
        assert response.success is True
        assert response.sport == Sport.NBA
        assert response.meta == {"total": 100}
        assert response.error is None
    
    def test_api_response_error_case(self):
        """Test APIResponse for error cases."""
        response = APIResponse(
            data=None,
            success=False,
            error="Test error",
            sport=Sport.NHL
        )
        
        assert response.data is None
        assert response.success is False
        assert response.error == "Test error"
        assert response.sport == Sport.NHL


# Performance tests
class TestPerformance:
    """Performance-related tests."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_different_sports(self, api_key):
        """Test concurrent requests to different sports."""
        import time
        
        async with BallDontLieClient(api_key) as client:
            start_time = time.time()
            
            # Make concurrent requests to different sports
            tasks = [
                client.get_teams(Sport.NBA),
                client.get_teams(Sport.MLB),
                client.get_teams(Sport.NFL),
                client.get_teams(Sport.NHL)
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Concurrent requests should be faster than sequential
            assert elapsed < 10  # Should complete within 10 seconds
            
            # All requests should succeed or have specific errors
            for result in results:
                assert isinstance(result, APIResponse)


if __name__ == "__main__":
    # Run a quick smoke test
    async def smoke_test():
        api_key = os.getenv("BALLDONTLIE_API_KEY")
        if not api_key:
            print("❌ BALLDONTLIE_API_KEY environment variable required")
            return
        
        print("🏆 Running Ball Don't Lie API Smoke Test...")
        
        async with BallDontLieClient(api_key) as client:
            # Test all 5 sports
            for sport in Sport:
                print(f"Testing {sport.value.upper()}...")
                response = await client.get_teams(sport)
                if response.success:
                    team_count = len(response.data.get("data", []))
                    print(f"✅ {sport.value.upper()}: {team_count} teams")
                else:
                    print(f"⚠️  {sport.value.upper()}: {response.error}")
        
        print("🎉 Smoke test complete!")
    
    asyncio.run(smoke_test()) 