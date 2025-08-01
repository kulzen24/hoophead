"""
Game domain models for multi-sport platform.
Based on actual Ball Don't Lie API data structures.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime, date
import re

from .base import BaseEntity, SportType, SportSpecificData


@dataclass
class GameStats:
    """
    Unified game-level statistics across all sports.
    Sport-specific stats are stored in the sport_specific field.
    """
    # Basic game stats
    home_score: int = 0
    visitor_score: int = 0
    total_score: int = 0
    
    # Game flow stats
    periods_played: int = 0
    largest_lead: Optional[int] = None
    lead_changes: Optional[int] = None
    
    # Team performance
    home_shooting_percentage: Optional[float] = None
    visitor_shooting_percentage: Optional[float] = None
    
    # Sport-specific statistics
    sport_specific: SportSpecificData = field(default_factory=lambda: SportSpecificData(SportType.NBA))
    
    @property
    def point_differential(self) -> int:
        """Calculate point differential (home - visitor)."""
        return self.home_score - self.visitor_score
    
    @property
    def winning_team(self) -> str:
        """Get which team won ('home', 'visitor', 'tie')."""
        if self.home_score > self.visitor_score:
            return "home"
        elif self.visitor_score > self.home_score:
            return "visitor"
        else:
            return "tie"


@dataclass
class Game(BaseEntity):
    """
    Unified game model across all sports.
    Based on actual Ball Don't Lie API data structure.
    """
    # Basic game information (from API)
    date: Optional[str] = None  # API format: "1946-11-01"
    datetime: Optional[str] = None  # API format: "2018-10-17T02:30:00.000Z"
    season: Optional[int] = None  # Season year
    status: str = ""  # "Final", "In Progress", etc.
    
    # Game structure
    period: Optional[int] = None  # Current period/quarter/inning
    time: Optional[str] = None  # Time remaining in period
    postseason: bool = False  # Whether this is a playoff game
    
    # Team information and scores
    home_team_id: Optional[int] = None
    home_team_score: int = 0
    home_team_name: Optional[str] = None
    home_team_abbreviation: Optional[str] = None
    
    visitor_team_id: Optional[int] = None
    visitor_team_score: int = 0
    visitor_team_name: Optional[str] = None
    visitor_team_abbreviation: Optional[str] = None
    
    # Game statistics
    game_stats: Optional[GameStats] = None
    
    # Sport-specific data
    sport_specific: SportSpecificData = field(default_factory=lambda: SportSpecificData(SportType.NBA))
    
    @property
    def is_completed(self) -> bool:
        """Check if the game is completed."""
        return self.status.lower() in ['final', 'completed', 'finished']
    
    @property
    def is_live(self) -> bool:
        """Check if the game is currently in progress."""
        return self.status.lower() in ['in progress', 'live', 'active']
    
    @property
    def point_differential(self) -> int:
        """Calculate point differential (home - visitor)."""
        return self.home_team_score - self.visitor_team_score
    
    @property
    def total_score(self) -> int:
        """Calculate total points scored in the game."""
        return self.home_team_score + self.visitor_team_score
    
    @property
    def winning_team_id(self) -> Optional[int]:
        """Get the ID of the winning team."""
        if self.home_team_score > self.visitor_team_score:
            return self.home_team_id
        elif self.visitor_team_score > self.home_team_score:
            return self.visitor_team_id
        return None  # Tie game
    
    @property
    def display_date(self) -> str:
        """Get formatted display date."""
        if self.datetime:
            try:
                dt = datetime.fromisoformat(self.datetime.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')
            except:
                pass
        return self.date or "Unknown Date"
    
    @classmethod
    def from_api_response(cls, api_data: Dict[str, Any], sport: SportType) -> 'Game':
        """Create Game from Ball Don't Lie API response."""
        # Handle different API response structures
        if 'data' in api_data and isinstance(api_data['data'], list) and api_data['data']:
            game_data = api_data['data'][0]  # Take first game
        elif 'data' in api_data and isinstance(api_data['data'], dict):
            game_data = api_data['data']
        else:
            game_data = api_data
        
        # Extract basic game information
        game_id = str(game_data.get('id', ''))
        date = game_data.get('date')
        datetime_str = game_data.get('datetime')
        season = game_data.get('season')
        status = game_data.get('status', '')
        period = game_data.get('period')
        time = game_data.get('time')
        postseason = game_data.get('postseason', False)
        
        # Extract scores
        home_team_score = game_data.get('home_team_score', 0)
        visitor_team_score = game_data.get('visitor_team_score', 0)
        
        # Extract team information from nested objects
        home_team_data = game_data.get('home_team', {})
        visitor_team_data = game_data.get('visitor_team', {})
        
        home_team_id = home_team_data.get('id') if home_team_data else game_data.get('home_team_id')
        visitor_team_id = visitor_team_data.get('id') if visitor_team_data else game_data.get('visitor_team_id')
        
        home_team_name = home_team_data.get('full_name') if home_team_data else None
        visitor_team_name = visitor_team_data.get('full_name') if visitor_team_data else None
        
        home_team_abbreviation = home_team_data.get('abbreviation') or home_team_data.get('tricode') if home_team_data else None
        visitor_team_abbreviation = visitor_team_data.get('abbreviation') or visitor_team_data.get('tricode') if visitor_team_data else None
        
        # Create game stats
        game_stats = GameStats(
            home_score=home_team_score,
            visitor_score=visitor_team_score,
            total_score=home_team_score + visitor_team_score,
            periods_played=period if period else 0,
            sport_specific=SportSpecificData(sport, game_data.copy())
        )
        
        # Create sport-specific data container
        sport_specific = SportSpecificData(sport, game_data.copy())
        
        return cls(
            id=game_id,
            sport=sport,
            date=date,
            datetime=datetime_str,
            season=season,
            status=status,
            period=period,
            time=time,
            postseason=postseason,
            home_team_id=home_team_id,
            home_team_score=home_team_score,
            home_team_name=home_team_name,
            home_team_abbreviation=home_team_abbreviation,
            visitor_team_id=visitor_team_id,
            visitor_team_score=visitor_team_score,
            visitor_team_name=visitor_team_name,
            visitor_team_abbreviation=visitor_team_abbreviation,
            game_stats=game_stats,
            sport_specific=sport_specific,
            raw_data=api_data
        ) 