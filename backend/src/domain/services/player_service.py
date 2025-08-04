"""
Player domain service for orchestrating player data retrieval and transformation.
Refactored to use BaseService for common functionality.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from core.utils import LoggerFactory, APIResponseProcessor
from core.exceptions import PlayerNotFoundError, InvalidSearchCriteriaError
from core.error_handler import with_domain_error_handling

from .base_service import BaseService, BaseSearchCriteria, ServiceListResponse
from ..models.base import SportType
from ..models.player import Player, PlayerStats, PlayerPosition
from ..models.statistics import GameStatsDetail, SeasonStats

logger = LoggerFactory.get_logger(__name__)


@dataclass
class PlayerSearchCriteria(BaseSearchCriteria):
    """Extended search criteria for players."""
    name: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    position: Optional[PlayerPosition] = None
    season: Optional[int] = None


class PlayerService(BaseService[Player]):
    """
    Domain service for player-related operations.
    Inherits common functionality from BaseService.
    """
    
    def __init__(self, api_client):
        """Initialize with API client dependency."""
        super().__init__(api_client, Player)
    
    def get_api_endpoint(self) -> str:
        """Get the API endpoint name for players."""
        return "players"
    
    def create_search_criteria(self, **kwargs) -> PlayerSearchCriteria:
        """Create player search criteria from keyword arguments."""
        return PlayerSearchCriteria(**kwargs)
    
    def _extract_search_params(self, criteria: PlayerSearchCriteria) -> Dict[str, Any]:
        """Extract API parameters from player search criteria."""
        params = super()._extract_search_params(criteria)
        
        # Add player-specific parameters
        if criteria.team_id:
            params['team_ids[]'] = criteria.team_id
        
        return params
    
    def _apply_client_filters(self, results: List[Player], criteria: PlayerSearchCriteria) -> List[Player]:
        """Apply client-side filters for player-specific criteria."""
        filtered = results
        
        # Filter by team name if specified
        if criteria.team_name:
            team_name_lower = criteria.team_name.lower()
            filtered = [
                player for player in filtered
                if player.team_name and team_name_lower in player.team_name.lower()
            ]
        
        # Filter by position if specified
        if criteria.position:
            filtered = [
                player for player in filtered
                if player.position == criteria.position
            ]
        
        # Filter by active status
        if criteria.active_only:
            # Assume players without team_id are inactive
            filtered = [
                player for player in filtered
                if player.team_id is not None
            ]
        
        return filtered
    
    # Convenience methods with backward compatibility
    async def get_player_by_id(self, player_id: int, sport: SportType) -> Optional[Player]:
        """Retrieve a player by ID and sport."""
        return await self.get_by_id(player_id, sport)
    
    async def search_players(self, criteria: PlayerSearchCriteria) -> ServiceListResponse[Player]:
        """Search players using criteria."""
        return await self.search(criteria)
    
    @with_domain_error_handling(fallback_value=[], suppress_hoophead_errors=True)
    async def get_player_stats(
        self, 
        player_id: int, 
        sport: SportType, 
        season: Optional[int] = None,
        game_ids: Optional[List[int]] = None
    ) -> List[PlayerStats]:
        """
        Retrieve player statistics for specific games or season.
        
        Args:
            player_id: Player's unique ID
            sport: Sport type
            season: Optional season filter
            game_ids: Optional specific game IDs
            
        Returns:
            List of PlayerStats objects
        """
        try:
            params = {"player_ids[]": player_id}
            if season:
                params["seasons[]"] = season
            if game_ids:
                params["game_ids[]"] = game_ids
            
            response = await self.api_client.get_stats(sport=sport, **params)
            
            if response.success and response.data.get('data'):
                stats_data = APIResponseProcessor.extract_data(response.data)
                
                return [
                    PlayerStats.from_api_response({'data': stat_data}, sport)
                    for stat_data in stats_data
                ]
                
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving player stats for {player_id}: {e}")
            raise PlayerNotFoundError(f"Failed to retrieve stats for player {player_id}")
    
    @with_domain_error_handling(fallback_value=[], suppress_hoophead_errors=True)
    async def get_player_season_stats(
        self, 
        player_id: int, 
        sport: SportType, 
        season: int
    ) -> List[SeasonStats]:
        """
        Retrieve aggregated season statistics for a player.
        
        Args:
            player_id: Player's unique ID
            sport: Sport type
            season: Season year
            
        Returns:
            List of SeasonStats objects
        """
        try:
            # Get all stats for the season
            player_stats = await self.get_player_stats(player_id, sport, season)
            
            if not player_stats:
                return []
            
            # Aggregate into season stats
            # This is a simplified aggregation - extend as needed
            season_stats = SeasonStats(
                player_id=player_id,
                season=season,
                games_played=len(player_stats),
                total_points=sum(stat.points for stat in player_stats if stat.points),
                total_assists=sum(stat.assists for stat in player_stats if stat.assists),
                total_rebounds=sum(stat.rebounds for stat in player_stats if stat.rebounds)
            )
            
            return [season_stats]
            
        except Exception as e:
            logger.error(f"Error aggregating season stats for player {player_id}: {e}")
            return []
    
    @with_domain_error_handling(fallback_value=[], suppress_hoophead_errors=True)
    async def get_team_roster(self, team_id: int, sport: SportType) -> List[Player]:
        """
        Retrieve all players for a specific team.
        
        Args:
            team_id: Team's unique ID
            sport: Sport type
            
        Returns:
            List of Player objects on the team
        """
        criteria = PlayerSearchCriteria(
            sport=sport,
            team_id=team_id,
            active_only=True
        )
        
        response = await self.search(criteria)
        return response.data if response.success else []
    
    async def compare_players(
        self, 
        player_ids: List[int], 
        sport: SportType, 
        season: Optional[int] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        Compare statistics between multiple players.
        
        Args:
            player_ids: List of player IDs to compare
            sport: Sport type
            season: Optional season to compare
            
        Returns:
            Dictionary mapping player_id to their stats summary
        """
        comparison = {}
        
        for player_id in player_ids:
            try:
                player = await self.get_player_by_id(player_id, sport)
                if player:
                    stats = await self.get_player_stats(player_id, sport, season)
                    
                    # Calculate summary statistics
                    comparison[player_id] = {
                        'player_name': f"{player.first_name} {player.last_name}",
                        'team': player.team_name or 'Free Agent',
                        'position': player.position.value if player.position else 'Unknown',
                        'games_played': len(stats),
                        'avg_points': sum(s.points for s in stats if s.points) / len(stats) if stats else 0,
                        'avg_assists': sum(s.assists for s in stats if s.assists) / len(stats) if stats else 0,
                        'avg_rebounds': sum(s.rebounds for s in stats if s.rebounds) / len(stats) if stats else 0
                    }
                
            except Exception as e:
                logger.warning(f"Failed to get stats for player {player_id}: {e}")
                comparison[player_id] = {'error': str(e)}
        
        return comparison
    
    async def get_popular_players(self, sport: SportType, limit: int = 10) -> List[Player]:
        """
        Get popular/featured players for a sport.
        This is a simplified implementation - extend with actual popularity metrics.
        
        Args:
            sport: Sport type
            limit: Maximum number of players to return
            
        Returns:
            List of popular Player objects
        """
        # For now, just return the first N players
        # In a real implementation, this would use popularity metrics
        all_players = await self.get_all(sport)
        return all_players[:limit]


# Export the service
__all__ = ['PlayerService', 'PlayerSearchCriteria'] 