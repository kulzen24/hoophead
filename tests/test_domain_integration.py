"""
Integration tests for domain services with Ball Don't Lie API.
"""

import pytest
import asyncio
import sys
import os

# Add backend src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport
from domain.models.base import SportType
from domain.services.player_service import PlayerService, PlayerSearchCriteria
from domain.services.team_service import TeamService, TeamSearchCriteria
from domain.services.search_service import SearchService


@pytest.mark.asyncio
class TestDomainIntegration:
    """Test domain services with real API client."""
    
    async def test_player_service_integration(self):
        """Test PlayerService with real API calls."""
        async with BallDontLieClient() as client:
            player_service = PlayerService(client)
            
            # Test search players
            criteria = PlayerSearchCriteria(name="James", sport=SportType.NBA)
            players = await player_service.search_players(criteria)
            
            assert isinstance(players, list)
            print(f"Found {len(players)} players with 'James' in NBA")
            
            if players:
                player = players[0]
                assert hasattr(player, 'first_name')
                assert hasattr(player, 'last_name')
                assert hasattr(player, 'sport')
                assert player.sport == SportType.NBA
                print(f"Sample player: {player.full_name} ({player.position})")
    
    async def test_team_service_integration(self):
        """Test TeamService with real API calls."""
        async with BallDontLieClient() as client:
            team_service = TeamService(client)
            
            # Test get all teams
            nba_teams = await team_service.get_all_teams(SportType.NBA)
            
            assert isinstance(nba_teams, list)
            assert len(nba_teams) > 0
            print(f"Found {len(nba_teams)} NBA teams")
            
            if nba_teams:
                team = nba_teams[0]
                assert hasattr(team, 'name')
                assert hasattr(team, 'full_name')
                assert hasattr(team, 'sport')
                assert team.sport == SportType.NBA
                print(f"Sample team: {team.display_name} ({team.team_code})")
                
            # Test search teams
            criteria = TeamSearchCriteria(name="Lakers", sport=SportType.NBA)
            lakers = await team_service.search_teams(criteria)
            
            assert isinstance(lakers, list)
            print(f"Found {len(lakers)} teams matching 'Lakers'")
    
    async def test_search_service_integration(self):
        """Test unified SearchService."""
        async with BallDontLieClient() as client:
            search_service = SearchService(client)
            
            # Test unified search
            result = await search_service.search_all("Lakers", SportType.NBA)
            
            assert hasattr(result, 'players')
            assert hasattr(result, 'teams')
            assert hasattr(result, 'games')
            assert hasattr(result, 'total_results')
            
            print(f"Unified search for 'Lakers': {result.total_results} total results")
            print(f"  - Players: {len(result.players)}")
            print(f"  - Teams: {len(result.teams)}")
            print(f"  - Games: {len(result.games)}")
            
            # Test player search by name
            players = await search_service.search_players_by_name("James", SportType.NBA)
            assert isinstance(players, list)
            print(f"Player search for 'James': {len(players)} results")
    
    async def test_cross_sport_functionality(self):
        """Test domain services work across different sports."""
        async with BallDontLieClient() as client:
            team_service = TeamService(client)
            
            # Test multiple sports
            sports_teams = {}
            for sport in [SportType.NBA, SportType.NHL]:
                teams = await team_service.get_all_teams(sport)
                sports_teams[sport] = len(teams)
                print(f"{sport.value.upper()}: {len(teams)} teams")
            
            # Verify we got teams for multiple sports
            assert len(sports_teams) > 0
            for sport, count in sports_teams.items():
                assert count > 0, f"No teams found for {sport}"


def test_domain_models_creation():
    """Test domain models can be created from sample API data."""
    from domain.models.player import Player
    from domain.models.team import Team
    from domain.models.game import Game
    
    # Sample NBA player data (based on actual API structure)
    player_data = {
        'id': 237,
        'first_name': 'LeBron',
        'last_name': 'James',
        'position': 'F',
        'height': '6-8',
        'weight': '250',
        'jersey_number': '6',
        'college': 'St. Vincent-St. Mary HS (OH)',
        'country': 'USA',
        'draft_year': 2003,
        'draft_round': 1,
        'draft_number': 1,
        'team': {
            'id': 14,
            'abbreviation': 'LAL',
            'city': 'Los Angeles',
            'conference': 'West',
            'division': 'Pacific',
            'full_name': 'Los Angeles Lakers',
            'name': 'Lakers'
        }
    }
    
    # Test Player creation
    player = Player.from_api_response({'data': player_data}, SportType.NBA)
    assert player.first_name == 'LeBron'
    assert player.last_name == 'James'
    assert player.full_name == 'LeBron James'
    assert player.height == '6-8'
    assert player.height_inches == 80  # 6*12 + 8
    assert player.weight_pounds == 250
    assert player.sport == SportType.NBA
    
    # Sample team data
    team_data = {
        'id': 14,
        'abbreviation': 'LAL',
        'city': 'Los Angeles',
        'conference': 'West',
        'division': 'Pacific',
        'full_name': 'Los Angeles Lakers',
        'name': 'Lakers'
    }
    
    # Test Team creation
    team = Team.from_api_response({'data': team_data}, SportType.NBA)
    assert team.name == 'Lakers'
    assert team.full_name == 'Los Angeles Lakers'
    assert team.city == 'Los Angeles'
    assert team.team_code == 'LAL'
    assert team.sport == SportType.NBA
    
    print("✅ Domain models creation test passed")


if __name__ == "__main__":
    """Run integration tests."""
    async def run_tests():
        test_instance = TestDomainIntegration()
        
        print("🧪 Running Domain Integration Tests...")
        print("=" * 50)
        
        try:
            print("\n1. Testing PlayerService...")
            await test_instance.test_player_service_integration()
            
            print("\n2. Testing TeamService...")
            await test_instance.test_team_service_integration()
            
            print("\n3. Testing SearchService...")
            await test_instance.test_search_service_integration()
            
            print("\n4. Testing Cross-Sport Functionality...")
            await test_instance.test_cross_sport_functionality()
            
            print("\n5. Testing Domain Models...")
            test_domain_models_creation()
            
            print("\n" + "=" * 50)
            print("🎉 All domain integration tests passed!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
    
    # Run the tests
    asyncio.run(run_tests()) 