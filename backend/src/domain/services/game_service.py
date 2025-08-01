"""
Game domain service for orchestrating game data retrieval and operations.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, date

from ..models.base import SportType
from ..models.game import Game, GameStats
from ..models.team import Team

logger = logging.getLogger(__name__)


@dataclass
class GameSearchCriteria:
    """Criteria for searching games across sports."""
    team_id: Optional[int] = None
    opponent_id: Optional[int] = None
    date: Optional[str] = None
    season: Optional[int] = None
    postseason: Optional[bool] = None
    status: Optional[str] = None
    sport: Optional[SportType] = None


class GameService:
    """
    Domain service for game-related operations.
    Orchestrates data retrieval, transformation, and business logic.
    """
    
    def __init__(self, api_client):
        """Initialize with API client dependency."""
        self.api_client = api_client
        
    async def get_game_by_id(self, game_id: int, sport: SportType) -> Optional[Game]:
        """
        Retrieve a game by ID and sport.
        
        Args:
            game_id: Game's unique ID
            sport: Sport type to search in
            
        Returns:
            Game object or None if not found
        """
        try:
            response = await self.api_client.get_games(sport=sport, use_cache=True)
            
            if response.success and response.data.get('data'):
                games_data = response.data['data']
                
                # Find game with matching ID
                for game_data in games_data:
                    if game_data.get('id') == game_id:
                        return Game.from_api_response({'data': game_data}, sport)
                        
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving game {game_id} for {sport}: {e}")
            return None
    
    async def get_games(self, sport: SportType, **filters) -> List[Game]:
        """
        Get games for a specific sport with optional filters.
        
        Args:
            sport: Sport type
            **filters: Additional filters (season, team_ids, dates, etc.)
            
        Returns:
            List of games matching criteria
        """
        try:
            response = await self.api_client.get_games(
                sport=sport,
                use_cache=True,
                **filters
            )
            
            if not response.success or not response.data.get('data'):
                return []
                
            games = []
            for game_data in response.data['data']:
                game = Game.from_api_response({'data': game_data}, sport)
                games.append(game)
                
            return games
            
        except Exception as e:
            logger.error(f"Error retrieving games for {sport}: {e}")
            return []
    
    async def search_games(self, criteria: GameSearchCriteria) -> List[Game]:
        """
        Search for games based on criteria.
        
        Args:
            criteria: Search criteria
            
        Returns:
            List of matching games
        """
        games = []
        
        try:
            # Determine which sports to search
            sports_to_search = [criteria.sport] if criteria.sport else list(SportType)
            
            for sport in sports_to_search:
                # Build filters from criteria
                filters = {}
                if criteria.season:
                    filters['season'] = criteria.season
                if criteria.team_id:
                    filters['team_ids[]'] = criteria.team_id
                if criteria.date:
                    filters['dates[]'] = criteria.date
                if criteria.postseason is not None:
                    filters['postseason'] = criteria.postseason
                
                sport_games = await self.get_games(sport, **filters)
                
                # Apply additional filtering
                for game in sport_games:
                    if self._matches_criteria(game, criteria):
                        games.append(game)
                        
        except Exception as e:
            logger.error(f"Error searching games: {e}")
            
        return games
    
    def _matches_criteria(self, game: Game, criteria: GameSearchCriteria) -> bool:
        """Check if game matches search criteria."""
        # Status filter
        if criteria.status:
            if criteria.status.lower() not in game.status.lower():
                return False
                
        # Opponent filter (check if specified team is playing against opponent)
        if criteria.team_id and criteria.opponent_id:
            teams_in_game = {game.home_team_id, game.visitor_team_id}
            if not (criteria.team_id in teams_in_game and criteria.opponent_id in teams_in_game):
                return False
                
        return True
    
    async def get_team_games(
        self, 
        team_id: int, 
        sport: SportType, 
        season: Optional[int] = None,
        postseason: bool = False
    ) -> List[Game]:
        """
        Get all games for a specific team.
        
        Args:
            team_id: Team's unique ID
            sport: Sport type
            season: Specific season (optional)
            postseason: Include playoff games
            
        Returns:
            List of games for the team
        """
        try:
            filters = {
                'team_ids[]': team_id,
                'postseason': postseason
            }
            if season:
                filters['season'] = season
                
            return await self.get_games(sport, **filters)
            
        except Exception as e:
            logger.error(f"Error retrieving games for team {team_id} in {sport}: {e}")
            return []
    
    async def get_games_by_date(self, sport: SportType, date: str) -> List[Game]:
        """
        Get all games on a specific date.
        
        Args:
            sport: Sport type
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of games on the date
        """
        try:
            return await self.get_games(sport, dates=[date])
            
        except Exception as e:
            logger.error(f"Error retrieving games for {sport} on {date}: {e}")
            return []
    
    async def get_recent_games(self, sport: SportType, limit: int = 10) -> List[Game]:
        """
        Get most recent games for a sport.
        
        Args:
            sport: Sport type
            limit: Maximum number of games to return
            
        Returns:
            List of recent games
        """
        try:
            # Get games and sort by date (most recent first)
            games = await self.get_games(sport)
            
            # Sort by date descending
            games.sort(key=lambda g: g.date or "", reverse=True)
            
            return games[:limit]
            
        except Exception as e:
            logger.error(f"Error retrieving recent games for {sport}: {e}")
            return []
    
    async def get_live_games(self, sport: SportType) -> List[Game]:
        """
        Get currently live/in-progress games.
        
        Args:
            sport: Sport type
            
        Returns:
            List of live games
        """
        try:
            all_games = await self.get_games(sport)
            
            # Filter for live games
            live_games = [game for game in all_games if game.is_live]
            
            return live_games
            
        except Exception as e:
            logger.error(f"Error retrieving live games for {sport}: {e}")
            return [] 