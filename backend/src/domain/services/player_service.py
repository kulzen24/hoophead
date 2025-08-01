"""
Player domain service for orchestrating player data retrieval and transformation.
"""

import logging
import sys
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass

# Add core to path for imports
sys.path.append('../../core')
try:
    from core.exceptions import (
        PlayerNotFoundError, InvalidSearchCriteriaError, DomainException, ErrorContext
    )
    from core.error_handler import with_domain_error_handling, error_handler
except ImportError:
    # Fallback if import fails
    class PlayerNotFoundError(Exception): pass
    class InvalidSearchCriteriaError(Exception): pass
    class DomainException(Exception): pass
    def with_domain_error_handling(*args, **kwargs): return lambda f: f

from ..models.base import SportType
from ..models.player import Player, PlayerStats, PlayerPosition
from ..models.statistics import GameStatsDetail, SeasonStats

logger = logging.getLogger(__name__)


@dataclass
class PlayerSearchCriteria:
    """Criteria for searching players across sports."""
    name: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    position: Optional[PlayerPosition] = None
    sport: Optional[SportType] = None
    season: Optional[int] = None
    active_only: bool = True


class PlayerService:
    """
    Domain service for player-related operations.
    Orchestrates data retrieval, transformation, and business logic.
    """
    
    def __init__(self, api_client):
        """Initialize with API client dependency."""
        self.api_client = api_client
        
    @with_domain_error_handling(fallback_value=None, suppress_hoophead_errors=True)
    async def get_player_by_id(self, player_id: int, sport: SportType) -> Optional[Player]:
        """
        Retrieve a player by ID and sport.
        
        Args:
            player_id: Player's unique ID
            sport: Sport type to search in
            
        Returns:
            Player object
            
        Raises:
            PlayerNotFoundError: If player cannot be found
            DomainException: For other unexpected errors
        """
        if not isinstance(player_id, int) or player_id <= 0:
            raise InvalidSearchCriteriaError(
                criteria="player_id",
                reason="Must be a positive integer",
                context=ErrorContext(
                    operation="get_player_by_id",
                    sport=sport.value,
                    parameters={"player_id": player_id}
                )
            )
        
        # Use the API client to get player data
        response = await self.api_client.get_players(
            sport=sport, 
            search=str(player_id),
            use_cache=True
        )
        
        if response.success and response.data.get('data'):
            players_data = response.data['data']
            
            # Find player with matching ID
            for player_data in players_data:
                if player_data.get('id') == player_id:
                    return Player.from_api_response({'data': player_data}, sport)
        
        # If we get here, player was not found
        raise PlayerNotFoundError(
            player_id=player_id,
            sport=sport.value,
            context=ErrorContext(
                operation="get_player_by_id",
                sport=sport.value,
                parameters={"player_id": player_id}
            )
        )
    
    @with_domain_error_handling(fallback_value=[])
    async def search_players(self, criteria: PlayerSearchCriteria) -> List[Player]:
        """
        Search for players based on criteria.
        
        Args:
            criteria: Search criteria
            
        Returns:
            List of matching players
            
        Raises:
            InvalidSearchCriteriaError: If search criteria are invalid
            DomainException: For other unexpected errors
        """
        # Validate search criteria
        if not criteria.name and not criteria.team_id and not criteria.team_name:
            raise InvalidSearchCriteriaError(
                criteria="search_parameters",
                reason="At least one search parameter (name, team_id, or team_name) must be provided",
                context=ErrorContext(
                    operation="search_players",
                    sport=criteria.sport.value if criteria.sport else "all",
                    parameters={"criteria": criteria.__dict__}
                )
            )
        
        players = []
        
        # Determine which sports to search
        sports_to_search = [criteria.sport] if criteria.sport else list(SportType)
        
        for sport in sports_to_search:
            try:
                sport_players = await self._search_players_in_sport(sport, criteria)
                players.extend(sport_players)
            except Exception as e:
                logger.warning(f"Error searching players in {sport}: {e}")
                continue
                
        return players
    
    async def _search_players_in_sport(self, sport: SportType, criteria: PlayerSearchCriteria) -> List[Player]:
        """Search for players in a specific sport."""
        try:
            # Build search parameters
            search_params = {}
            if criteria.name:
                search_params['search'] = criteria.name
            if criteria.team_id:
                search_params['team_ids[]'] = criteria.team_id
                
            response = await self.api_client.get_players(
                sport=sport,
                use_cache=True,
                **search_params
            )
            
            if not response.success or not response.data.get('data'):
                return []
            
            players = []
            for player_data in response.data['data']:
                player = Player.from_api_response({'data': player_data}, sport)
                
                # Apply additional filtering criteria
                if self._matches_criteria(player, criteria):
                    players.append(player)
                    
            return players
            
        except Exception as e:
            logger.error(f"Error searching players in {sport}: {e}")
            return []
    
    def _matches_criteria(self, player: Player, criteria: PlayerSearchCriteria) -> bool:
        """Check if player matches search criteria."""
        # Position filter
        if criteria.position and player.position != criteria.position:
            return False
            
        # Team name filter (case-insensitive partial match)
        if criteria.team_name:
            team_names = [player.team_name, player.team_abbreviation, player.team_city]
            if not any(
                criteria.team_name.lower() in (name or "").lower() 
                for name in team_names
            ):
                return False
                
        return True
    
    async def get_player_stats(
        self, 
        player_id: int, 
        sport: SportType,
        season: Optional[int] = None,
        season_type: str = "regular"
    ) -> List[GameStatsDetail]:
        """
        Get detailed statistics for a player.
        
        Args:
            player_id: Player's unique ID
            sport: Sport type
            season: Specific season (optional)
            season_type: Type of season (regular, playoffs)
            
        Returns:
            List of game statistics
        """
        try:
            # Build stats query parameters
            params = {
                'player_ids[]': player_id,
                'season': season,
                'postseason': season_type == "playoffs"
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            response = await self.api_client.get_stats(
                sport=sport,
                use_cache=True,
                **params
            )
            
            if not response.success or not response.data.get('data'):
                return []
                
            stats = []
            for stat_data in response.data['data']:
                game_stat = GameStatsDetail.from_api_response({'data': stat_data}, sport)
                stats.append(game_stat)
                
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving stats for player {player_id} in {sport}: {e}")
            return []
    
    async def get_player_season_stats(
        self,
        player_id: int,
        sport: SportType,
        season: int,
        season_type: str = "regular"
    ) -> Optional[SeasonStats]:
        """
        Get aggregated season statistics for a player.
        
        Args:
            player_id: Player's unique ID
            sport: Sport type
            season: Season year
            season_type: Type of season
            
        Returns:
            Aggregated season statistics
        """
        try:
            # Get all game stats for the season
            game_stats = await self.get_player_stats(
                player_id=player_id,
                sport=sport,
                season=season,
                season_type=season_type
            )
            
            if not game_stats:
                return None
                
            # Aggregate the stats
            season_stats = self._aggregate_season_stats(game_stats, player_id, season, season_type)
            return season_stats
            
        except Exception as e:
            logger.error(f"Error calculating season stats for player {player_id}: {e}")
            return None
    
    def _aggregate_season_stats(
        self,
        game_stats: List[GameStatsDetail],
        player_id: int,
        season: int,
        season_type: str
    ) -> SeasonStats:
        """Aggregate individual game stats into season totals."""
        season_stats = SeasonStats(
            player_id=player_id,
            season=season,
            season_type=season_type,
            games_played=len(game_stats)
        )
        
        # Sum up all the stats
        for game_stat in game_stats:
            season_stats.total_points += game_stat.pts
            season_stats.total_assists += game_stat.ast
            season_stats.total_rebounds += game_stat.reb
            season_stats.total_steals += game_stat.stl
            season_stats.total_blocks += game_stat.blk
            season_stats.total_turnovers += game_stat.turnover
            
            # Shooting stats
            season_stats.total_fgm += game_stat.fgm
            season_stats.total_fga += game_stat.fga
            season_stats.total_fg3m += game_stat.fg3m
            season_stats.total_fg3a += game_stat.fg3a
            season_stats.total_ftm += game_stat.ftm
            season_stats.total_fta += game_stat.fta
        
        # Calculate averages and percentages
        season_stats.calculate_averages()
        season_stats.calculate_percentages()
        
        return season_stats
    
    async def get_team_roster(self, team_id: int, sport: SportType) -> List[Player]:
        """
        Get all players for a specific team.
        
        Args:
            team_id: Team's unique ID
            sport: Sport type
            
        Returns:
            List of players on the team
        """
        try:
            response = await self.api_client.get_players(
                sport=sport,
                team_ids=[team_id],
                use_cache=True
            )
            
            if not response.success or not response.data.get('data'):
                return []
                
            players = []
            for player_data in response.data['data']:
                player = Player.from_api_response({'data': player_data}, sport)
                players.append(player)
                
            return players
            
        except Exception as e:
            logger.error(f"Error retrieving roster for team {team_id} in {sport}: {e}")
            return []
    
    async def compare_players(self, player_ids: List[int], sport: SportType, season: Optional[int] = None) -> Dict[int, Dict[str, Any]]:
        """
        Compare statistics between multiple players.
        
        Args:
            player_ids: List of player IDs to compare
            sport: Sport type
            season: Specific season for comparison
            
        Returns:
            Dictionary with player stats for comparison
        """
        comparison = {}
        
        try:
            for player_id in player_ids:
                # Get player info
                player = await self.get_player_by_id(player_id, sport)
                if not player:
                    continue
                    
                # Get season stats if season specified
                season_stats = None
                if season:
                    season_stats = await self.get_player_season_stats(player_id, sport, season)
                
                comparison[player_id] = {
                    'player': player,
                    'season_stats': season_stats
                }
                
        except Exception as e:
            logger.error(f"Error comparing players: {e}")
            
        return comparison 