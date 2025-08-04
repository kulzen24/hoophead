"""
Team domain service for orchestrating team data retrieval and operations.
Refactored to use BaseService for common functionality.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from core.utils import LoggerFactory, APIResponseProcessor
from core.exceptions import TeamNotFoundError, InvalidSearchCriteriaError
from core.error_handler import with_domain_error_handling

from .base_service import BaseService, BaseSearchCriteria, ServiceListResponse
from ..models.base import SportType
from ..models.team import Team, TeamStats
from ..models.player import Player

logger = LoggerFactory.get_logger(__name__)


@dataclass
class TeamSearchCriteria(BaseSearchCriteria):
    """Extended search criteria for teams."""
    name: Optional[str] = None
    city: Optional[str] = None
    conference: Optional[str] = None
    division: Optional[str] = None


class TeamService(BaseService[Team]):
    """
    Domain service for team-related operations.
    Inherits common functionality from BaseService.
    """
    
    def __init__(self, api_client):
        """Initialize with API client dependency."""
        super().__init__(api_client, Team)
        
    def get_api_endpoint(self) -> str:
        """Get the API endpoint name for teams."""
        return "teams"
    
    def create_search_criteria(self, **kwargs) -> TeamSearchCriteria:
        """Create team search criteria from keyword arguments."""
        return TeamSearchCriteria(**kwargs)
    
    def _extract_search_params(self, criteria: TeamSearchCriteria) -> Dict[str, Any]:
        """Extract API parameters from team search criteria."""
        params = super()._extract_search_params(criteria)
        
        # Teams API typically doesn't have search filters at API level
        # Most filtering will be done client-side
        return params
    
    def _apply_client_filters(self, results: List[Team], criteria: TeamSearchCriteria) -> List[Team]:
        """Apply client-side filters for team-specific criteria."""
        filtered = results
        
        # Filter by city if specified
        if criteria.city:
            city_lower = criteria.city.lower()
            filtered = [
                team for team in filtered
                if team.city and city_lower in team.city.lower()
            ]
        
        # Filter by conference if specified
        if criteria.conference:
            conference_lower = criteria.conference.lower()
            filtered = [
                team for team in filtered
                if team.conference and conference_lower in team.conference.lower()
            ]
        
        # Filter by division if specified
        if criteria.division:
            division_lower = criteria.division.lower()
            filtered = [
                team for team in filtered
                if team.division and division_lower in team.division.lower()
            ]
        
        return filtered
    
    # Convenience methods with backward compatibility
    async def get_team_by_id(self, team_id: int, sport: SportType) -> Optional[Team]:
        """Retrieve a team by ID and sport."""
        return await self.get_by_id(team_id, sport)
    
    async def get_all_teams(self, sport: SportType) -> List[Team]:
        """Get all teams for a specific sport."""
        return await self.get_all(sport)
    
    async def search_teams(self, criteria: TeamSearchCriteria) -> ServiceListResponse[Team]:
        """Search teams using criteria."""
        return await self.search(criteria)
    
    @with_domain_error_handling(fallback_value=[], suppress_hoophead_errors=True)
    async def get_teams_by_conference(self, sport: SportType, conference: str) -> List[Team]:
        """
        Get all teams in a specific conference.
        
        Args:
            sport: Sport type
            conference: Conference name (e.g., "Eastern", "Western")
            
        Returns:
            List of Team objects in the conference
        """
        criteria = TeamSearchCriteria(
            sport=sport,
            conference=conference
        )
        
        response = await self.search(criteria)
        return response.data if response.success else []
    
    @with_domain_error_handling(fallback_value=[], suppress_hoophead_errors=True)
    async def get_teams_by_division(self, sport: SportType, division: str) -> List[Team]:
        """
        Get all teams in a specific division.
        
        Args:
            sport: Sport type
            division: Division name (e.g., "Atlantic", "Pacific")
            
        Returns:
            List of Team objects in the division
        """
        criteria = TeamSearchCriteria(
            sport=sport,
            division=division
        )
        
        response = await self.search(criteria)
        return response.data if response.success else []
    
    @with_domain_error_handling(fallback_value=[], suppress_hoophead_errors=True)
    async def get_team_roster(self, team_id: int, sport: SportType) -> List[Player]:
        """
        Get the roster (all players) for a specific team.
        
        Args:
            team_id: Team's unique ID
            sport: Sport type
            
        Returns:
            List of Player objects on the team roster
        """
        try:
            # Import PlayerService to avoid circular imports
            from .player_service import PlayerService, PlayerSearchCriteria
            
            # Create player service instance
            player_service = PlayerService(self.api_client)
            
            # Search for players on this team
            criteria = PlayerSearchCriteria(
                sport=sport,
                team_id=team_id,
                active_only=True
            )
            
            response = await player_service.search(criteria)
            return response.data if response.success else []
            
        except Exception as e:
            logger.error(f"Error retrieving roster for team {team_id}: {e}")
            return []
    
    @with_domain_error_handling(fallback_value=None, suppress_hoophead_errors=True)
    async def get_team_stats(self, team_id: int, sport: SportType, season: Optional[int] = None) -> Optional[TeamStats]:
        """
        Get team statistics for a specific season.
        
        Args:
            team_id: Team's unique ID
            sport: Sport type
            season: Optional season filter
            
        Returns:
            TeamStats object or None if not found
        """
        try:
            params = {"team_ids[]": team_id}
            if season:
                params["seasons[]"] = season
            
            response = await self.api_client.get_stats(sport=sport, **params)
            
            if response.success and response.data.get('data'):
                stats_data = APIResponseProcessor.extract_data(response.data)
                
                if stats_data:
                    # Assuming first result is for our team
                    team_stat_data = stats_data[0]
                    return TeamStats.from_api_response({'data': team_stat_data}, sport)
                    
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving team stats for {team_id}: {e}")
            return None
    
    async def get_conference_standings(self, sport: SportType, conference: str, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get standings for all teams in a conference.
        
        Args:
            sport: Sport type
            conference: Conference name
            season: Optional season filter
            
        Returns:
            List of team standings with wins, losses, etc.
        """
        try:
            teams = await self.get_teams_by_conference(sport, conference)
            standings = []
            
            for team in teams:
                team_stats = await self.get_team_stats(team.id, sport, season)
                
                standings.append({
                    'team_id': team.id,
                    'team_name': team.name,
                    'team_city': team.city,
                    'wins': team_stats.wins if team_stats else 0,
                    'losses': team_stats.losses if team_stats else 0,
                    'win_percentage': team_stats.win_percentage if team_stats else 0.0,
                    'conference': team.conference,
                    'division': team.division
                })
            
            # Sort by win percentage (descending)
            standings.sort(key=lambda x: x['win_percentage'], reverse=True)
            
            return standings
            
        except Exception as e:
            logger.error(f"Error retrieving conference standings for {conference}: {e}")
            return []
    
    async def get_division_standings(self, sport: SportType, division: str, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get standings for all teams in a division.
        
        Args:
            sport: Sport type
            division: Division name
            season: Optional season filter
            
        Returns:
            List of team standings with wins, losses, etc.
        """
        try:
            teams = await self.get_teams_by_division(sport, division)
            standings = []
            
            for team in teams:
                team_stats = await self.get_team_stats(team.id, sport, season)
                
                standings.append({
                    'team_id': team.id,
                    'team_name': team.name,
                    'team_city': team.city,
                    'wins': team_stats.wins if team_stats else 0,
                    'losses': team_stats.losses if team_stats else 0,
                    'win_percentage': team_stats.win_percentage if team_stats else 0.0,
                    'conference': team.conference,
                    'division': team.division
                })
            
            # Sort by win percentage (descending)
            standings.sort(key=lambda x: x['win_percentage'], reverse=True)
            
            return standings
            
        except Exception as e:
            logger.error(f"Error retrieving division standings for {division}: {e}")
            return []
    
    async def compare_teams(self, team_ids: List[int], sport: SportType, season: Optional[int] = None) -> Dict[int, Dict[str, Any]]:
        """
        Compare statistics between multiple teams.
        
        Args:
            team_ids: List of team IDs to compare
            sport: Sport type
            season: Optional season to compare
            
        Returns:
            Dictionary mapping team_id to their stats summary
        """
        comparison = {}
        
        for team_id in team_ids:
            try:
                team = await self.get_team_by_id(team_id, sport)
                if team:
                    stats = await self.get_team_stats(team_id, sport, season)
                    
                    comparison[team_id] = {
                        'team_name': f"{team.city} {team.name}",
                        'conference': team.conference or 'Unknown',
                        'division': team.division or 'Unknown',
                        'wins': stats.wins if stats else 0,
                        'losses': stats.losses if stats else 0,
                        'win_percentage': stats.win_percentage if stats else 0.0,
                        'abbreviation': team.abbreviation or team.name[:3].upper()
                    }
                
            except Exception as e:
                logger.warning(f"Failed to get stats for team {team_id}: {e}")
                comparison[team_id] = {'error': str(e)}
        
        return comparison
    
    async def get_popular_teams(self, sport: SportType, limit: int = 10) -> List[Team]:
        """
        Get popular/featured teams for a sport.
        This is a simplified implementation - extend with actual popularity metrics.
        
        Args:
            sport: Sport type
            limit: Maximum number of teams to return
            
        Returns:
            List of popular Team objects
        """
        # For now, just return the first N teams
        # In a real implementation, this would use popularity metrics
        all_teams = await self.get_all(sport)
        return all_teams[:limit]


# Export the service
__all__ = ['TeamService', 'TeamSearchCriteria'] 