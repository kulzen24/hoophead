"""
Team domain models for multi-sport platform.
Based on actual Ball Don't Lie API data structures.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime

from .base import BaseEntity, SportType, SportSpecificData


@dataclass
class TeamStats:
    """
    Unified team statistics across all sports.
    Sport-specific stats are stored in the sport_specific field.
    """
    # Basic season stats
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    win_percentage: Optional[float] = None
    
    # Scoring stats (normalized)
    points_for: float = 0.0  # Points scored
    points_against: float = 0.0  # Points allowed
    point_differential: float = 0.0
    
    # Season context
    season: Optional[str] = None
    season_type: str = "regular"  # regular, playoffs, etc.
    
    # Sport-specific statistics
    sport_specific: SportSpecificData = field(default_factory=lambda: SportSpecificData(SportType.NBA))
    
    def calculate_win_percentage(self) -> float:
        """Calculate win percentage from wins and losses."""
        total_games = self.wins + self.losses
        if total_games == 0:
            return 0.0
        return self.wins / total_games


@dataclass
class Team(BaseEntity):
    """
    Unified team model across all sports.
    Based on actual Ball Don't Lie API data structure.
    """
    # Basic information (from API)
    name: str = ""  # Team name (e.g., "Hawks")
    full_name: str = ""  # Full team name (e.g., "Atlanta Hawks")
    city: str = ""  # Team city (e.g., "Atlanta")
    
    # Team identifiers - handle different naming conventions across sports
    abbreviation: Optional[str] = None  # NBA/NFL/MLB: "ATL"
    tricode: Optional[str] = None  # NHL: "QUE"
    
    # League structure - handle different naming conventions
    conference: Optional[str] = None  # NBA/NFL: "East", "West"
    conference_name: Optional[str] = None  # NHL: "Eastern", "Western", "Defunct"
    division: Optional[str] = None  # NBA/NFL: "Southeast", "Pacific"
    division_name: Optional[str] = None  # NHL: "Atlantic", "Metropolitan", "Historical"
    
    # Additional team information
    founded_year: Optional[int] = None
    home_venue: Optional[str] = None
    
    # Current season stats
    current_stats: Optional[TeamStats] = None
    
    # All-time/franchise stats
    franchise_stats: Optional[TeamStats] = None
    
    # Sport-specific data
    sport_specific: SportSpecificData = field(default_factory=lambda: SportSpecificData(SportType.NBA))
    
    @property
    def display_name(self) -> str:
        """Get the best display name for the team."""
        return self.full_name or f"{self.city} {self.name}".strip() or self.name
    
    @property
    def team_code(self) -> str:
        """Get the team's abbreviation/tricode."""
        return self.abbreviation or self.tricode or ""
    
    @property
    def league_conference(self) -> Optional[str]:
        """Get conference name regardless of sport naming convention."""
        return self.conference or self.conference_name
    
    @property
    def league_division(self) -> Optional[str]:
        """Get division name regardless of sport naming convention."""
        return self.division or self.division_name
    
    @classmethod
    def from_api_response(cls, api_data: Dict[str, Any], sport: SportType) -> 'Team':
        """Create Team from Ball Don't Lie API response."""
        # Handle different API response structures
        if 'data' in api_data and isinstance(api_data['data'], list) and api_data['data']:
            team_data = api_data['data'][0]  # Take first team
        elif 'data' in api_data and isinstance(api_data['data'], dict):
            team_data = api_data['data']
        else:
            team_data = api_data
        
        # Handle different field naming conventions across sports
        name = team_data.get('name', '')
        full_name = team_data.get('full_name', '')
        city = team_data.get('city', '')
        
        # Abbreviation/tricode handling
        abbreviation = team_data.get('abbreviation')
        tricode = team_data.get('tricode')
        
        # Conference/division handling for different sports
        conference = team_data.get('conference')
        conference_name = team_data.get('conference_name')
        division = team_data.get('division')
        division_name = team_data.get('division_name')
        
        # Create sport-specific data container
        sport_specific = SportSpecificData(sport, team_data.copy())
        
        return cls(
            id=str(team_data.get('id', '')),
            sport=sport,
            name=name,
            full_name=full_name,
            city=city,
            abbreviation=abbreviation,
            tricode=tricode,
            conference=conference,
            conference_name=conference_name,
            division=division,
            division_name=division_name,
            sport_specific=sport_specific,
            raw_data=api_data
        )
    
    def get_roster(self) -> List['Player']:
        """
        Get current roster for this team.
        To be implemented with data retrieval service.
        """
        # This will be implemented in the domain service layer
        raise NotImplementedError("Roster retrieval to be implemented in domain service")
    
    def get_schedule(self, season: Optional[str] = None) -> List['Game']:
        """
        Get team's schedule for a given season.
        To be implemented with data retrieval service.
        """
        # This will be implemented in the domain service layer
        raise NotImplementedError("Schedule retrieval to be implemented in domain service") 