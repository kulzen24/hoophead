"""
Search domain service for unified search across all sports entities.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass

from ..models.base import SportType
from ..models.player import Player
from ..models.team import Team
from ..models.game import Game
from .player_service import PlayerService, PlayerSearchCriteria
from .team_service import TeamService, TeamSearchCriteria
from .game_service import GameService, GameSearchCriteria

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Unified search result containing different entity types."""
    players: List[Player]
    teams: List[Team]
    games: List[Game]
    total_results: int = 0
    
    def __post_init__(self):
        """Calculate total results."""
        self.total_results = len(self.players) + len(self.teams) + len(self.games)


class SearchService:
    """
    Domain service for unified search operations.
    Provides search capabilities across players, teams, and games.
    """
    
    def __init__(self, api_client):
        """Initialize with API client dependency."""
        self.api_client = api_client
        self.player_service = PlayerService(api_client)
        self.team_service = TeamService(api_client)
        self.game_service = GameService(api_client)
        
    async def search_all(
        self, 
        query: str, 
        sport: Optional[SportType] = None,
        limit_per_type: int = 10
    ) -> SearchResult:
        """
        Search across all entity types with a single query.
        
        Args:
            query: Search term
            sport: Optional sport filter
            limit_per_type: Maximum results per entity type
            
        Returns:
            SearchResult containing players, teams, and games
        """
        try:
            # Create search criteria for each entity type
            player_criteria = PlayerSearchCriteria(name=query, sport=sport)
            team_criteria = TeamSearchCriteria(name=query, sport=sport)
            
            # Perform searches concurrently (could be optimized with asyncio.gather)
            players = await self.player_service.search_players(player_criteria)
            teams = await self.team_service.search_teams(team_criteria)
            
            # Limit results
            players = players[:limit_per_type]
            teams = teams[:limit_per_type]
            
            # Games search is more complex - for now, return empty list
            games = []
            
            return SearchResult(
                players=players,
                teams=teams,
                games=games
            )
            
        except Exception as e:
            logger.error(f"Error in unified search for '{query}': {e}")
            return SearchResult(players=[], teams=[], games=[])
    
    async def search_players_by_name(
        self, 
        name: str, 
        sport: Optional[SportType] = None
    ) -> List[Player]:
        """
        Search for players by name.
        
        Args:
            name: Player name to search for
            sport: Optional sport filter
            
        Returns:
            List of matching players
        """
        criteria = PlayerSearchCriteria(name=name, sport=sport)
        return await self.player_service.search_players(criteria)
    
    async def search_teams_by_name(
        self, 
        name: str, 
        sport: Optional[SportType] = None
    ) -> List[Team]:
        """
        Search for teams by name.
        
        Args:
            name: Team name to search for
            sport: Optional sport filter
            
        Returns:
            List of matching teams
        """
        criteria = TeamSearchCriteria(name=name, sport=sport)
        return await self.team_service.search_teams(criteria)
    
    async def search_by_location(
        self, 
        city: str, 
        sport: Optional[SportType] = None
    ) -> SearchResult:
        """
        Search for teams and players by city/location.
        
        Args:
            city: City name to search for
            sport: Optional sport filter
            
        Returns:
            SearchResult with location-based results
        """
        try:
            # Search teams by city
            team_criteria = TeamSearchCriteria(city=city, sport=sport)
            teams = await self.team_service.search_teams(team_criteria)
            
            # Search players by team city (indirect location search)
            players = []
            for team in teams:
                if team.team_id:
                    team_players = await self.player_service.get_team_roster(team.team_id, team.sport)
                    players.extend(team_players)
            
            return SearchResult(
                players=players,
                teams=teams,
                games=[]
            )
            
        except Exception as e:
            logger.error(f"Error searching by location '{city}': {e}")
            return SearchResult(players=[], teams=[], games=[])
    
    async def get_popular_searches(self, sport: SportType) -> Dict[str, List[str]]:
        """
        Get popular/trending search terms for a sport.
        (This would typically be based on analytics data)
        
        Args:
            sport: Sport type
            
        Returns:
            Dictionary with popular search categories
        """
        # For now, return static popular searches
        # In production, this would be based on actual search analytics
        popular = {
            SportType.NBA: {
                "players": ["LeBron James", "Stephen Curry", "Kevin Durant"],
                "teams": ["Lakers", "Warriors", "Celtics"],
            },
            SportType.NFL: {
                "players": ["Tom Brady", "Aaron Rodgers", "Patrick Mahomes"],
                "teams": ["Patriots", "Chiefs", "Cowboys"],
            },
            SportType.MLB: {
                "players": ["Mike Trout", "Mookie Betts", "Aaron Judge"],
                "teams": ["Yankees", "Dodgers", "Red Sox"],
            },
            SportType.NHL: {
                "players": ["Connor McDavid", "Sidney Crosby", "Alex Ovechkin"],
                "teams": ["Bruins", "Rangers", "Maple Leafs"],
            },
            SportType.EPL: {
                "players": ["Cristiano Ronaldo", "Mohamed Salah", "Kevin De Bruyne"],
                "teams": ["Manchester United", "Liverpool", "Arsenal"],
            }
        }
        
        return popular.get(sport, {"players": [], "teams": []}) 