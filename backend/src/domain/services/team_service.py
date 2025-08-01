"""
Team domain service for orchestrating team data retrieval and operations.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..models.base import SportType
from ..models.team import Team, TeamStats
from ..models.player import Player

logger = logging.getLogger(__name__)


@dataclass
class TeamSearchCriteria:
    """Criteria for searching teams across sports."""
    name: Optional[str] = None
    city: Optional[str] = None
    conference: Optional[str] = None
    division: Optional[str] = None
    sport: Optional[SportType] = None


class TeamService:
    """
    Domain service for team-related operations.
    Orchestrates data retrieval, transformation, and business logic.
    """
    
    def __init__(self, api_client):
        """Initialize with API client dependency."""
        self.api_client = api_client
        
    async def get_team_by_id(self, team_id: int, sport: SportType) -> Optional[Team]:
        """
        Retrieve a team by ID and sport.
        
        Args:
            team_id: Team's unique ID
            sport: Sport type to search in
            
        Returns:
            Team object or None if not found
        """
        try:
            response = await self.api_client.get_teams(sport=sport, use_cache=True)
            
            if response.success and response.data.get('data'):
                teams_data = response.data['data']
                
                # Find team with matching ID
                for team_data in teams_data:
                    if team_data.get('id') == team_id:
                        return Team.from_api_response({'data': team_data}, sport)
                        
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving team {team_id} for {sport}: {e}")
            return None
    
    async def get_all_teams(self, sport: SportType) -> List[Team]:
        """
        Get all teams for a specific sport.
        
        Args:
            sport: Sport type
            
        Returns:
            List of all teams in the sport
        """
        try:
            response = await self.api_client.get_teams(sport=sport, use_cache=True)
            
            if not response.success or not response.data.get('data'):
                return []
                
            teams = []
            for team_data in response.data['data']:
                team = Team.from_api_response({'data': team_data}, sport)
                teams.append(team)
                
            return teams
            
        except Exception as e:
            logger.error(f"Error retrieving teams for {sport}: {e}")
            return []
    
    async def search_teams(self, criteria: TeamSearchCriteria) -> List[Team]:
        """
        Search for teams based on criteria.
        
        Args:
            criteria: Search criteria
            
        Returns:
            List of matching teams
        """
        teams = []
        
        try:
            # Determine which sports to search
            sports_to_search = [criteria.sport] if criteria.sport else list(SportType)
            
            for sport in sports_to_search:
                sport_teams = await self.get_all_teams(sport)
                
                # Filter teams based on criteria
                for team in sport_teams:
                    if self._matches_criteria(team, criteria):
                        teams.append(team)
                        
        except Exception as e:
            logger.error(f"Error searching teams: {e}")
            
        return teams
    
    def _matches_criteria(self, team: Team, criteria: TeamSearchCriteria) -> bool:
        """Check if team matches search criteria."""
        # Name filter (case-insensitive partial match)
        if criteria.name:
            team_names = [team.name, team.full_name, team.city]
            if not any(
                criteria.name.lower() in (name or "").lower() 
                for name in team_names
            ):
                return False
                
        # City filter
        if criteria.city:
            if criteria.city.lower() not in (team.city or "").lower():
                return False
                
        # Conference filter
        if criteria.conference:
            conference = team.league_conference
            if not conference or criteria.conference.lower() not in conference.lower():
                return False
                
        # Division filter
        if criteria.division:
            division = team.league_division
            if not division or criteria.division.lower() not in division.lower():
                return False
                
        return True
    
    async def get_teams_by_conference(self, sport: SportType, conference: str) -> List[Team]:
        """
        Get all teams in a specific conference.
        
        Args:
            sport: Sport type
            conference: Conference name
            
        Returns:
            List of teams in the conference
        """
        try:
            all_teams = await self.get_all_teams(sport)
            
            conference_teams = [
                team for team in all_teams 
                if team.league_conference and conference.lower() in team.league_conference.lower()
            ]
            
            return conference_teams
            
        except Exception as e:
            logger.error(f"Error retrieving teams for conference {conference} in {sport}: {e}")
            return []
    
    async def get_teams_by_division(self, sport: SportType, division: str) -> List[Team]:
        """
        Get all teams in a specific division.
        
        Args:
            sport: Sport type
            division: Division name
            
        Returns:
            List of teams in the division
        """
        try:
            all_teams = await self.get_all_teams(sport)
            
            division_teams = [
                team for team in all_teams 
                if team.league_division and division.lower() in team.league_division.lower()
            ]
            
            return division_teams
            
        except Exception as e:
            logger.error(f"Error retrieving teams for division {division} in {sport}: {e}")
            return []
    
    async def get_team_roster(self, team_id: int, sport: SportType) -> List[Player]:
        """
        Get roster for a specific team.
        
        Args:
            team_id: Team's unique ID
            sport: Sport type
            
        Returns:
            List of players on the team
        """
        try:
            # Import here to avoid circular import
            from .player_service import PlayerService
            
            player_service = PlayerService(self.api_client)
            return await player_service.get_team_roster(team_id, sport)
            
        except Exception as e:
            logger.error(f"Error retrieving roster for team {team_id} in {sport}: {e}")
            return [] 