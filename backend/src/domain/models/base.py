"""
Base domain models and common patterns for multi-sport platform.
"""

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Union, List
from datetime import datetime
import uuid


class SportType(str, Enum):
    """
    Unified sport types matching the API client Sport enum.
    """
    NBA = "nba"
    MLB = "mlb" 
    NFL = "nfl"
    NHL = "nhl"
    EPL = "epl"
    
    @property
    def display_name(self) -> str:
        """Get the full display name for the sport."""
        names = {
            self.NBA: "National Basketball Association",
            self.MLB: "Major League Baseball",
            self.NFL: "National Football League", 
            self.NHL: "National Hockey League",
            self.EPL: "English Premier League"
        }
        return names.get(self, self.value.upper())
    
    @property
    def is_team_sport(self) -> bool:
        """All supported sports are team sports."""
        return True


@dataclass
class BaseEntity(ABC):
    """
    Base entity class for all domain models with common patterns.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sport: SportType = SportType.NBA
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Raw API data for debugging and future use
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization validation and processing."""
        if isinstance(self.sport, str):
            self.sport = SportType(self.sport)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary representation."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [
                    item.to_dict() if hasattr(item, 'to_dict') else item 
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_api_response(cls, api_data: Dict[str, Any], sport: SportType) -> 'BaseEntity':
        """
        Create entity from API response data.
        Should be overridden by subclasses for specific transformation logic.
        """
        raise NotImplementedError("Subclasses must implement from_api_response")


@dataclass
class SportSpecificData:
    """
    Container for sport-specific data that doesn't fit the unified model.
    """
    sport: SportType
    data: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get sport-specific data value."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set sport-specific data value."""
        self.data[key] = value


@dataclass 
class UnifiedMetrics:
    """
    Common metrics that apply across all sports, normalized to comparable scales.
    """
    # Performance metrics (0-100 scale)
    offensive_rating: Optional[float] = None
    defensive_rating: Optional[float] = None
    overall_rating: Optional[float] = None
    
    # Usage and efficiency
    usage_percentage: Optional[float] = None
    efficiency_rating: Optional[float] = None
    
    # Team contribution
    win_shares: Optional[float] = None
    plus_minus: Optional[float] = None
    
    def calculate_overall_rating(self) -> float:
        """Calculate overall rating from available metrics."""
        ratings = [
            r for r in [self.offensive_rating, self.defensive_rating] 
            if r is not None
        ]
        return sum(ratings) / len(ratings) if ratings else 0.0 