"""
Statistics domain models for multi-sport platform.
Based on actual Ball Don't Lie API data structures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, List, Union
from datetime import datetime
import re

from .base import BaseEntity, SportType, SportSpecificData


class StatType(str, Enum):
    """Types of statistics available."""
    GAME = "game"  # Individual game stats
    SEASON = "season"  # Season aggregates
    CAREER = "career"  # Career totals
    AVERAGE = "average"  # Per-game averages


@dataclass
class UnifiedStats:
    """
    Unified statistics structure that works across all sports.
    Normalizes different sports' stats to comparable metrics.
    """
    # Basic performance metrics
    games_played: int = 0
    points_scored: float = 0.0  # Points/Goals/Runs scored
    assists: float = 0.0
    rebounds: float = 0.0  # Rebounds/Catches/Saves (as applicable)
    
    # Efficiency metrics
    field_goal_percentage: Optional[float] = None
    free_throw_percentage: Optional[float] = None
    
    # Defensive metrics
    steals: float = 0.0
    blocks: float = 0.0
    
    # Usage metrics
    minutes_played: Optional[str] = None  # API format: "37:24"
    turnovers: float = 0.0
    personal_fouls: float = 0.0
    
    def get_minutes_as_float(self) -> float:
        """Convert minutes string to decimal minutes."""
        if not self.minutes_played:
            return 0.0
        
        # Parse format like "37:24"
        match = re.match(r'(\d+):(\d+)', self.minutes_played)
        if match:
            minutes, seconds = match.groups()
            return int(minutes) + int(seconds) / 60
        return 0.0


@dataclass
class GameStatsDetail(BaseEntity):
    """
    Detailed game statistics for a player in a specific game.
    Based on actual Ball Don't Lie API stats structure.
    """
    # Player and context information
    player_id: Optional[int] = None
    player_first_name: Optional[str] = None
    player_last_name: Optional[str] = None
    player_position: Optional[str] = None
    
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    team_abbreviation: Optional[str] = None
    
    game_id: Optional[int] = None
    game_date: Optional[str] = None
    game_season: Optional[int] = None
    
    # Core basketball stats (from API)
    min: Optional[str] = None  # Minutes played as "37:24"
    
    # Shooting stats
    fgm: int = 0  # Field goals made
    fga: int = 0  # Field goals attempted  
    fg_pct: Optional[float] = None  # Field goal percentage
    
    fg3m: int = 0  # 3-pointers made
    fg3a: int = 0  # 3-pointers attempted
    fg3_pct: Optional[float] = None  # 3-point percentage
    
    ftm: int = 0  # Free throws made
    fta: int = 0  # Free throws attempted
    ft_pct: Optional[float] = None  # Free throw percentage
    
    # Rebounding stats
    oreb: int = 0  # Offensive rebounds
    dreb: int = 0  # Defensive rebounds
    reb: int = 0   # Total rebounds
    
    # Other stats
    ast: int = 0       # Assists
    stl: int = 0       # Steals
    blk: int = 0       # Blocks
    turnover: int = 0  # Turnovers
    pf: int = 0        # Personal fouls
    pts: int = 0       # Points scored
    
    # Sport-specific data
    sport_specific: SportSpecificData = field(default_factory=lambda: SportSpecificData(SportType.NBA))
    
    @property
    def player_full_name(self) -> str:
        """Get player's full name."""
        if self.player_first_name and self.player_last_name:
            return f"{self.player_first_name} {self.player_last_name}"
        return "Unknown Player"
    
    @property
    def minutes_as_float(self) -> float:
        """Convert minutes string to decimal minutes."""
        if not self.min:
            return 0.0
        
        # Parse format like "37:24"
        match = re.match(r'(\d+):(\d+)', self.min)
        if match:
            minutes, seconds = match.groups()
            return int(minutes) + int(seconds) / 60
        return 0.0
    
    @property
    def true_shooting_percentage(self) -> Optional[float]:
        """Calculate true shooting percentage."""
        if self.fga == 0 and self.fta == 0:
            return None
        
        total_attempts = self.fga + (0.44 * self.fta)
        if total_attempts == 0:
            return None
        
        return self.pts / (2 * total_attempts)
    
    @property
    def effective_field_goal_percentage(self) -> Optional[float]:
        """Calculate effective field goal percentage."""
        if self.fga == 0:
            return None
        
        return (self.fgm + (0.5 * self.fg3m)) / self.fga
    
    def to_unified_stats(self) -> UnifiedStats:
        """Convert to unified stats format."""
        return UnifiedStats(
            games_played=1,  # This is for one game
            points_scored=float(self.pts),
            assists=float(self.ast),
            rebounds=float(self.reb),
            field_goal_percentage=self.fg_pct,
            free_throw_percentage=self.ft_pct,
            steals=float(self.stl),
            blocks=float(self.blk),
            minutes_played=self.min,
            turnovers=float(self.turnover),
            personal_fouls=float(self.pf)
        )
    
    @classmethod
    def from_api_response(cls, api_data: Dict[str, Any], sport: SportType) -> 'GameStatsDetail':
        """Create GameStatsDetail from Ball Don't Lie API response."""
        # Handle different API response structures
        if 'data' in api_data and isinstance(api_data['data'], list) and api_data['data']:
            stats_data = api_data['data'][0]  # Take first stat
        elif 'data' in api_data and isinstance(api_data['data'], dict):
            stats_data = api_data['data']
        else:
            stats_data = api_data
        
        # Extract player information from nested object
        player_data = stats_data.get('player', {})
        player_id = player_data.get('id')
        player_first_name = player_data.get('first_name')
        player_last_name = player_data.get('last_name')
        player_position = player_data.get('position')
        
        # Extract team information from nested object
        team_data = stats_data.get('team', {})
        team_id = team_data.get('id')
        team_name = team_data.get('full_name')
        team_abbreviation = team_data.get('abbreviation') or team_data.get('tricode')
        
        # Extract game information from nested object
        game_data = stats_data.get('game', {})
        game_id = game_data.get('id')
        game_date = game_data.get('date')
        game_season = game_data.get('season')
        
        # Create sport-specific data container
        sport_specific = SportSpecificData(sport, stats_data.copy())
        
        return cls(
            id=str(stats_data.get('id', '')),
            sport=sport,
            player_id=player_id,
            player_first_name=player_first_name,
            player_last_name=player_last_name,
            player_position=player_position,
            team_id=team_id,
            team_name=team_name,
            team_abbreviation=team_abbreviation,
            game_id=game_id,
            game_date=game_date,
            game_season=game_season,
            min=stats_data.get('min'),
            fgm=stats_data.get('fgm', 0),
            fga=stats_data.get('fga', 0),
            fg_pct=stats_data.get('fg_pct'),
            fg3m=stats_data.get('fg3m', 0),
            fg3a=stats_data.get('fg3a', 0),
            fg3_pct=stats_data.get('fg3_pct'),
            ftm=stats_data.get('ftm', 0),
            fta=stats_data.get('fta', 0),
            ft_pct=stats_data.get('ft_pct'),
            oreb=stats_data.get('oreb', 0),
            dreb=stats_data.get('dreb', 0),
            reb=stats_data.get('reb', 0),
            ast=stats_data.get('ast', 0),
            stl=stats_data.get('stl', 0),
            blk=stats_data.get('blk', 0),
            turnover=stats_data.get('turnover', 0),
            pf=stats_data.get('pf', 0),
            pts=stats_data.get('pts', 0),
            sport_specific=sport_specific,
            raw_data=api_data
        )


@dataclass
class SeasonStats:
    """
    Aggregated statistics for a player over a season.
    """
    # Context
    player_id: Optional[int] = None
    team_id: Optional[int] = None
    season: Optional[int] = None
    season_type: str = "regular"  # regular, playoffs, etc.
    
    # Aggregated stats
    games_played: int = 0
    games_started: int = 0
    
    # Totals
    total_points: int = 0
    total_assists: int = 0
    total_rebounds: int = 0
    total_steals: int = 0
    total_blocks: int = 0
    total_turnovers: int = 0
    
    # Shooting totals
    total_fgm: int = 0
    total_fga: int = 0
    total_fg3m: int = 0
    total_fg3a: int = 0
    total_ftm: int = 0
    total_fta: int = 0
    
    # Calculated averages
    ppg: Optional[float] = None  # Points per game
    apg: Optional[float] = None  # Assists per game
    rpg: Optional[float] = None  # Rebounds per game
    
    # Calculated percentages
    fg_percentage: Optional[float] = None
    fg3_percentage: Optional[float] = None
    ft_percentage: Optional[float] = None
    
    def calculate_averages(self) -> None:
        """Calculate per-game averages from totals."""
        if self.games_played > 0:
            self.ppg = self.total_points / self.games_played
            self.apg = self.total_assists / self.games_played
            self.rpg = self.total_rebounds / self.games_played
    
    def calculate_percentages(self) -> None:
        """Calculate shooting percentages from totals."""
        if self.total_fga > 0:
            self.fg_percentage = self.total_fgm / self.total_fga
        
        if self.total_fg3a > 0:
            self.fg3_percentage = self.total_fg3m / self.total_fg3a
        
        if self.total_fta > 0:
            self.ft_percentage = self.total_ftm / self.total_fta 