"""
Player domain models for multi-sport platform.
Updated to match actual Ball Don't Lie API data structures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, List, Union
from datetime import datetime, date
import re

from .base import BaseEntity, SportType, SportSpecificData, UnifiedMetrics


class PlayerPosition(str, Enum):
    """
    Unified player positions across all sports.
    Maps sport-specific positions to common categories.
    """
    # Common positions
    FORWARD = "forward"
    GUARD = "guard" 
    CENTER = "center"
    DEFENDER = "defender"
    MIDFIELDER = "midfielder"
    STRIKER = "striker"
    GOALKEEPER = "goalkeeper"
    
    # Sport-specific mappings
    # Basketball
    POINT_GUARD = "point_guard"
    SHOOTING_GUARD = "shooting_guard"
    SMALL_FORWARD = "small_forward"
    POWER_FORWARD = "power_forward"
    
    # Football/Soccer
    LEFT_BACK = "left_back"
    RIGHT_BACK = "right_back"
    CENTER_BACK = "center_back"
    DEFENSIVE_MIDFIELDER = "defensive_midfielder"
    CENTRAL_MIDFIELDER = "central_midfielder"
    ATTACKING_MIDFIELDER = "attacking_midfielder"
    LEFT_WING = "left_wing"
    RIGHT_WING = "right_wing"
    
    # American Football
    QUARTERBACK = "quarterback"
    RUNNING_BACK = "running_back"
    WIDE_RECEIVER = "wide_receiver"
    TIGHT_END = "tight_end"
    OFFENSIVE_LINE = "offensive_line"
    DEFENSIVE_LINE = "defensive_line"
    LINEBACKER = "linebacker"
    CORNERBACK = "cornerback"
    SAFETY = "safety"
    
    # Baseball
    PITCHER = "pitcher"
    CATCHER = "catcher"
    FIRST_BASE = "first_base"
    SECOND_BASE = "second_base"
    THIRD_BASE = "third_base"
    SHORTSTOP = "shortstop"
    OUTFIELD = "outfield"
    
    # Hockey
    LEFT_WING_HOCKEY = "left_wing_hockey"
    RIGHT_WING_HOCKEY = "right_wing_hockey"
    CENTER_HOCKEY = "center_hockey"
    DEFENSEMAN = "defenseman"
    GOALTENDER = "goaltender"
    
    @classmethod
    def from_sport_position(cls, position: str, sport: SportType) -> 'PlayerPosition':
        """Convert sport-specific position string to unified PlayerPosition."""
        position_lower = position.lower().replace(' ', '_').replace('-', '_')
        
        # Sport-specific mapping logic
        sport_mappings = {
            SportType.NBA: {
                'pg': cls.POINT_GUARD,
                'point_guard': cls.POINT_GUARD,
                'sg': cls.SHOOTING_GUARD,
                'shooting_guard': cls.SHOOTING_GUARD,
                'sf': cls.SMALL_FORWARD,
                'small_forward': cls.SMALL_FORWARD,
                'pf': cls.POWER_FORWARD,
                'power_forward': cls.POWER_FORWARD,
                'c': cls.CENTER,
                'center': cls.CENTER,
                'g': cls.GUARD,
                'guard': cls.GUARD,
                'f': cls.FORWARD,
                'forward': cls.FORWARD,
            },
            SportType.EPL: {
                'gk': cls.GOALKEEPER,
                'goalkeeper': cls.GOALKEEPER,
                'def': cls.DEFENDER,
                'defender': cls.DEFENDER,
                'mid': cls.MIDFIELDER,
                'midfielder': cls.MIDFIELDER,
                'fwd': cls.STRIKER,
                'forward': cls.STRIKER,
                'striker': cls.STRIKER,
            },
            SportType.NFL: {
                'qb': cls.QUARTERBACK,
                'quarterback': cls.QUARTERBACK,
                'rb': cls.RUNNING_BACK,
                'running_back': cls.RUNNING_BACK,
                'wr': cls.WIDE_RECEIVER,
                'wide_receiver': cls.WIDE_RECEIVER,
                'te': cls.TIGHT_END,
                'tight_end': cls.TIGHT_END,
            },
            SportType.MLB: {
                'p': cls.PITCHER,
                'pitcher': cls.PITCHER,
                'c': cls.CATCHER,
                'catcher': cls.CATCHER,
                '1b': cls.FIRST_BASE,
                'first_base': cls.FIRST_BASE,
                '2b': cls.SECOND_BASE,
                'second_base': cls.SECOND_BASE,
                '3b': cls.THIRD_BASE,
                'third_base': cls.THIRD_BASE,
                'ss': cls.SHORTSTOP,
                'shortstop': cls.SHORTSTOP,
                'of': cls.OUTFIELD,
                'outfield': cls.OUTFIELD,
            },
            SportType.NHL: {
                'lw': cls.LEFT_WING_HOCKEY,
                'left_wing': cls.LEFT_WING_HOCKEY,
                'rw': cls.RIGHT_WING_HOCKEY,
                'right_wing': cls.RIGHT_WING_HOCKEY,
                'c': cls.CENTER_HOCKEY,
                'center': cls.CENTER_HOCKEY,
                'd': cls.DEFENSEMAN,
                'defenseman': cls.DEFENSEMAN,
                'g': cls.GOALTENDER,
                'goaltender': cls.GOALTENDER,
            }
        }
        
        # Try sport-specific mapping first
        if sport in sport_mappings:
            mapped = sport_mappings[sport].get(position_lower)
            if mapped:
                return mapped
        
        # Fallback to direct enum lookup
        try:
            return cls(position_lower)
        except ValueError:
            # Default fallback based on sport
            if sport == SportType.NBA:
                return cls.GUARD
            elif sport == SportType.EPL:
                return cls.MIDFIELDER
            elif sport == SportType.NFL:
                return cls.WIDE_RECEIVER
            elif sport == SportType.MLB:
                return cls.OUTFIELD
            elif sport == SportType.NHL:
                return cls.CENTER_HOCKEY
            else:
                return cls.FORWARD


@dataclass
class PlayerStats:
    """
    Unified player statistics across all sports.
    Sport-specific stats are stored in the sport_specific field.
    """
    # Common stats across sports
    games_played: int = 0
    games_started: int = 0
    minutes_played: float = 0.0
    
    # Scoring/Offensive stats (normalized)
    points_scored: float = 0.0  # Points, Goals, Runs, etc.
    assists: float = 0.0
    
    # Defensive stats  
    defensive_actions: float = 0.0  # Steals, Tackles, Saves, etc.
    
    # Efficiency metrics
    shooting_percentage: Optional[float] = None
    success_rate: Optional[float] = None  # General success metric
    
    # Season context
    season: Optional[str] = None
    season_type: str = "regular"  # regular, playoffs, etc.
    
    # Unified metrics for cross-sport comparison
    unified_metrics: UnifiedMetrics = field(default_factory=UnifiedMetrics)
    
    # Sport-specific statistics
    sport_specific: SportSpecificData = field(default_factory=lambda: SportSpecificData(SportType.NBA))
    
    def normalize_to_per_game(self) -> 'PlayerStats':
        """Normalize all stats to per-game averages."""
        if self.games_played == 0:
            return self
        
        normalized = PlayerStats(
            games_played=self.games_played,
            games_started=self.games_started,
            minutes_played=self.minutes_played / self.games_played,
            points_scored=self.points_scored / self.games_played,
            assists=self.assists / self.games_played,
            defensive_actions=self.defensive_actions / self.games_played,
            shooting_percentage=self.shooting_percentage,
            success_rate=self.success_rate,
            season=self.season,
            season_type=self.season_type,
            unified_metrics=self.unified_metrics,
            sport_specific=self.sport_specific
        )
        return normalized


@dataclass
class Player(BaseEntity):
    """
    Unified player model across all sports.
    Based on actual Ball Don't Lie API data structure.
    """
    # Basic information (from API)
    first_name: str = ""
    last_name: str = ""
    
    # Physical attributes (API format)
    height: Optional[str] = None  # API format: "6-6", "5-11", etc.
    weight: Optional[str] = None  # API format: "190", "220", etc.
    
    # Team and position information
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    team_abbreviation: Optional[str] = None
    team_city: Optional[str] = None
    team_conference: Optional[str] = None
    team_division: Optional[str] = None
    position: Optional[PlayerPosition] = None
    jersey_number: Optional[str] = None  # API returns as string
    
    # Career information (from API)
    college: Optional[str] = None
    country: Optional[str] = None
    draft_year: Optional[int] = None
    draft_round: Optional[int] = None
    draft_number: Optional[int] = None
    
    # Current season stats
    current_stats: Optional[PlayerStats] = None
    
    # Career stats summary
    career_stats: Optional[PlayerStats] = None
    
    # Sport-specific data
    sport_specific: SportSpecificData = field(default_factory=lambda: SportSpecificData(SportType.NBA))
    
    @property
    def full_name(self) -> str:
        """Get player's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def height_inches(self) -> Optional[int]:
        """Convert height string to total inches."""
        if not self.height:
            return None
        
        # Parse format like "6-6", "5-11" 
        match = re.match(r'(\d+)-(\d+)', self.height)
        if match:
            feet, inches = match.groups()
            return int(feet) * 12 + int(inches)
        return None
    
    @property
    def weight_pounds(self) -> Optional[int]:
        """Convert weight string to integer."""
        if not self.weight:
            return None
        try:
            return int(self.weight)
        except (ValueError, TypeError):
            return None
    
    @property
    def height_formatted(self) -> str:
        """Get formatted height string."""
        return self.height or "N/A"
    
    @classmethod
    def from_api_response(cls, api_data: Dict[str, Any], sport: SportType) -> 'Player':
        """Create Player from Ball Don't Lie API response."""
        # Handle different API response structures
        if 'data' in api_data and isinstance(api_data['data'], list) and api_data['data']:
            player_data = api_data['data'][0]  # Take first player
        elif 'data' in api_data and isinstance(api_data['data'], dict):
            player_data = api_data['data']
        else:
            player_data = api_data
        
        # Extract common fields with fallbacks
        first_name = player_data.get('first_name', '')
        last_name = player_data.get('last_name', '')
        
        # Position handling
        position = None
        if 'position' in player_data:
            position = PlayerPosition.from_sport_position(player_data['position'], sport)
        
        # Team information (handle nested team object)
        team_data = player_data.get('team', {})
        
        # Handle different team field naming conventions across sports
        team_abbreviation = None
        team_conference = None
        team_division = None
        
        if team_data:
            # Standard fields
            team_abbreviation = team_data.get('abbreviation') or team_data.get('tricode')
            team_conference = team_data.get('conference') or team_data.get('conference_name')
            team_division = team_data.get('division') or team_data.get('division_name')
        
        # Create sport-specific data container
        sport_specific = SportSpecificData(sport, player_data.copy())
        
        return cls(
            id=str(player_data.get('id', '')),
            sport=sport,
            first_name=first_name,
            last_name=last_name,
            height=player_data.get('height'),  # Keep as API string format
            weight=player_data.get('weight'),  # Keep as API string format
            team_id=team_data.get('id') if team_data else None,
            team_name=team_data.get('full_name') if team_data else None,
            team_abbreviation=team_abbreviation,
            team_city=team_data.get('city') if team_data else None,
            team_conference=team_conference,
            team_division=team_division,
            position=position,
            jersey_number=player_data.get('jersey_number'),  # Keep as string
            college=player_data.get('college'),
            country=player_data.get('country'),
            draft_year=player_data.get('draft_year'),
            draft_round=player_data.get('draft_round'),
            draft_number=player_data.get('draft_number'),
            sport_specific=sport_specific,
            raw_data=api_data
        ) 