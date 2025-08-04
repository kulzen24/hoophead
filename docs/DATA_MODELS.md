# HoopHead Data Models Documentation

## Overview

HoopHead uses a unified data model architecture that works across all supported sports (NBA, MLB, NFL, NHL, EPL). This documentation covers all data structures, their relationships, and provides examples for each model type.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Base Models](#base-models)
- [Sport Types](#sport-types)
- [Team Models](#team-models)
- [Player Models](#player-models)
- [Game Models](#game-models)
- [Statistics Models](#statistics-models)
- [Response Formats](#response-formats)
- [Model Relationships](#model-relationships)
- [Usage Examples](#usage-examples)

## Architecture Overview

### Design Principles

1. **Unified Schema**: Same data structure across all sports
2. **Extensible**: Sport-specific data through `sport_specific` fields
3. **API-First**: Models match Ball Don't Lie API response structure
4. **Type Safety**: Full TypeScript/Python type annotations
5. **Backwards Compatible**: Raw API data preserved in `raw_data` field

### Model Hierarchy

```
BaseEntity (Abstract)
├── Team
├── Player  
├── Game
└── GameStatsDetail

Standalone Models:
├── TeamStats
├── PlayerStats
├── GameStats
├── UnifiedStats
└── SeasonStats
```

## Base Models

### BaseEntity

The foundation for all domain models with common patterns:

```python
@dataclass
class BaseEntity(ABC):
    """Base entity class for all domain models with common patterns."""
    
    # Core identifiers
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sport: SportType = SportType.NBA
    
    # Timestamps
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
        # Handles enum conversion, datetime serialization, nested objects
    
    @classmethod
    def from_api_response(cls, api_data: Dict[str, Any], sport: SportType) -> 'BaseEntity':
        """Create entity from API response data."""
        # Override in subclasses for specific transformation logic
```

**Common Properties:**
- `id`: Unique identifier (UUID)
- `sport`: SportType enum value
- `created_at`/`updated_at`: Automatic timestamps
- `raw_data`: Original API response for debugging

### SportSpecificData

Container for sport-specific attributes that don't fit the unified schema:

```python
@dataclass
class SportSpecificData:
    """Container for sport-specific attributes."""
    sport: SportType
    data: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get sport-specific attribute."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set sport-specific attribute."""
        self.data[key] = value
```

## Sport Types

### SportType Enum

```python
class SportType(str, Enum):
    """Unified sport types matching the API client Sport enum."""
    NBA = "nba"  # National Basketball Association
    MLB = "mlb"  # Major League Baseball
    NFL = "nfl"  # National Football League
    NHL = "nhl"  # National Hockey League
    EPL = "epl"  # English Premier League
    
    @property
    def display_name(self) -> str:
        """Get the full display name for the sport."""
        return {
            SportType.NBA: "National Basketball Association",
            SportType.MLB: "Major League Baseball",
            SportType.NFL: "National Football League", 
            SportType.NHL: "National Hockey League",
            SportType.EPL: "English Premier League"
        }[self]
    
    @property
    def is_team_sport(self) -> bool:
        """All supported sports are team sports."""
        return True
    
    @property
    def typical_season_length(self) -> int:
        """Typical number of games in a regular season."""
        return {
            SportType.NBA: 82,
            SportType.MLB: 162,
            SportType.NFL: 17,
            SportType.NHL: 82,
            SportType.EPL: 38
        }[self]
```

### Sport-Specific Characteristics

| Sport | Teams | Season Length | Conferences | Typical Positions |
|-------|-------|---------------|-------------|-------------------|
| **NBA** | 30 | 82 games | East/West | PG, SG, SF, PF, C |
| **MLB** | 30 | 162 games | American/National | P, C, 1B, 2B, 3B, SS, OF |
| **NFL** | 32 | 17 games | AFC/NFC | QB, RB, WR, TE, OL, DL, LB, DB |
| **NHL** | 32+ | 82 games | East/West | G, D, LW, C, RW |
| **EPL** | 20 | 38 games | None | GK, DF, MF, FW |

## Team Models

### Team

Main team entity with comprehensive information:

```python
@dataclass
class Team(BaseEntity):
    """Unified team model across all sports."""
    
    # Basic information (from Ball Don't Lie API)
    name: str = ""                      # "Lakers"
    full_name: str = ""                 # "Los Angeles Lakers"
    abbreviation: str = ""              # "LAL"
    city: str = ""                      # "Los Angeles"
    
    # League structure
    conference: Optional[str] = None     # "West", "American League"
    division: Optional[str] = None       # "Pacific", "AL West"
    
    # Team colors and branding
    primary_color: Optional[str] = None  # "#552583" (Lakers purple)
    secondary_color: Optional[str] = None # "#FDB927" (Lakers gold)
    
    # Stadium/Arena information
    venue_name: Optional[str] = None     # "Crypto.com Arena"
    venue_city: Optional[str] = None     # "Los Angeles"
    venue_capacity: Optional[int] = None # 20000
    
    # Team statistics (current season)
    team_stats: Optional[TeamStats] = None
    
    # Sport-specific data
    sport_specific: SportSpecificData = field(default_factory=lambda: SportSpecificData(SportType.NBA))
    
    @property
    def display_name(self) -> str:
        """Get display name (full_name or name)."""
        return self.full_name or self.name
    
    @property
    def location_abbreviation(self) -> str:
        """Get location with abbreviation."""
        return f"{self.city} {self.abbreviation}" if self.city and self.abbreviation else self.abbreviation
```

### TeamStats

Statistical information for teams:

```python
@dataclass
class TeamStats:
    """Team statistics across different sports."""
    
    # Win/Loss record
    wins: int = 0
    losses: int = 0
    ties: int = 0                        # For NFL/EPL
    overtime_losses: int = 0             # For NHL
    
    # Scoring statistics
    points_for: float = 0.0              # Points/goals scored
    points_against: float = 0.0          # Points/goals allowed
    
    # Advanced metrics (sport-specific)
    win_percentage: Optional[float] = None
    point_differential: Optional[float] = None
    home_record: Optional[str] = None    # "20-10"
    away_record: Optional[str] = None    # "15-15"
    
    # League standings
    conference_rank: Optional[int] = None
    division_rank: Optional[int] = None
    playoff_position: Optional[str] = None # "Wild Card", "Division Leader"
    
    # Season information
    season: Optional[int] = None
    last_updated: Optional[datetime] = None
    
    @property
    def total_games(self) -> int:
        """Total games played."""
        return self.wins + self.losses + self.ties
    
    @property
    def win_percentage_calculated(self) -> float:
        """Calculate win percentage."""
        total = self.total_games
        if total == 0:
            return 0.0
        return self.wins / total
    
    @property
    def points_per_game(self) -> float:
        """Average points per game."""
        total = self.total_games
        return self.points_for / total if total > 0 else 0.0
```

### Team JSON Schema

```json
{
  "type": "object",
  "properties": {
    "id": {"type": "string"},
    "sport": {"enum": ["nba", "mlb", "nfl", "nhl", "epl"]},
    "name": {"type": "string"},
    "full_name": {"type": "string"},
    "abbreviation": {"type": "string", "maxLength": 5},
    "city": {"type": "string"},
    "conference": {"type": ["string", "null"]},
    "division": {"type": ["string", "null"]},
    "team_stats": {
      "type": ["object", "null"],
      "properties": {
        "wins": {"type": "integer", "minimum": 0},
        "losses": {"type": "integer", "minimum": 0},
        "ties": {"type": "integer", "minimum": 0},
        "points_for": {"type": "number"},
        "points_against": {"type": "number"}
      }
    },
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"}
  },
  "required": ["id", "sport", "name", "abbreviation"]
}
```

## Player Models

### Player

Comprehensive player model with career information:

```python
@dataclass
class Player(BaseEntity):
    """Unified player model across all sports."""
    
    # Basic information (from Ball Don't Lie API)
    first_name: str = ""
    last_name: str = ""
    
    # Physical attributes (API format)
    height: Optional[str] = None         # "6-6", "5-11" (feet-inches)
    weight: Optional[str] = None         # "190", "220" (pounds)
    
    # Team and position information
    team_id: Optional[int] = None
    team_name: Optional[str] = None      # "Los Angeles Lakers"
    team_abbreviation: Optional[str] = None # "LAL"
    team_city: Optional[str] = None      # "Los Angeles"
    team_conference: Optional[str] = None # "West"
    team_division: Optional[str] = None  # "Pacific"
    
    position: Optional[PlayerPosition] = None
    jersey_number: Optional[str] = None  # API returns as string
    
    # Career information (from Ball Don't Lie API)
    college: Optional[str] = None        # "UCLA"
    country: Optional[str] = None        # "USA"
    draft_year: Optional[int] = None     # 2003
    draft_round: Optional[int] = None    # 1
    draft_number: Optional[int] = None   # 1
    
    # Player status
    active: bool = True
    rookie: bool = False
    
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
        except ValueError:
            return None
    
    @property
    def draft_position_display(self) -> Optional[str]:
        """Get formatted draft position."""
        if self.draft_year and self.draft_round and self.draft_number:
            return f"{self.draft_year} Round {self.draft_round}, Pick {self.draft_number}"
        return None
```

### PlayerPosition

Position enumeration that adapts to different sports:

```python
class PlayerPosition(str, Enum):
    """Unified player positions across sports."""
    
    # Basketball (NBA)
    POINT_GUARD = "PG"
    SHOOTING_GUARD = "SG" 
    SMALL_FORWARD = "SF"
    POWER_FORWARD = "PF"
    CENTER = "C"
    GUARD = "G"           # Generic guard
    FORWARD = "F"         # Generic forward
    
    # Baseball (MLB)
    PITCHER = "P"
    CATCHER = "C"
    FIRST_BASE = "1B"
    SECOND_BASE = "2B"
    THIRD_BASE = "3B"
    SHORTSTOP = "SS"
    OUTFIELD = "OF"
    LEFT_FIELD = "LF"
    CENTER_FIELD = "CF"
    RIGHT_FIELD = "RF"
    DESIGNATED_HITTER = "DH"
    
    # Football (NFL)
    QUARTERBACK = "QB"
    RUNNING_BACK = "RB"
    WIDE_RECEIVER = "WR"
    TIGHT_END = "TE"
    OFFENSIVE_LINE = "OL"
    DEFENSIVE_LINE = "DL"
    LINEBACKER = "LB"
    DEFENSIVE_BACK = "DB"
    KICKER = "K"
    PUNTER = "P"
    
    # Hockey (NHL)
    GOALIE = "G"
    DEFENSEMAN = "D"
    LEFT_WING = "LW"
    CENTER_HOCKEY = "C"
    RIGHT_WING = "RW"
    
    # Soccer (EPL)
    GOALKEEPER = "GK"
    DEFENDER = "DF"
    MIDFIELDER = "MF"
    FORWARD = "FW"
    
    @classmethod
    def for_sport(cls, sport: SportType) -> List['PlayerPosition']:
        """Get valid positions for a specific sport."""
        sport_positions = {
            SportType.NBA: [cls.POINT_GUARD, cls.SHOOTING_GUARD, cls.SMALL_FORWARD, cls.POWER_FORWARD, cls.CENTER],
            SportType.MLB: [cls.PITCHER, cls.CATCHER, cls.FIRST_BASE, cls.SECOND_BASE, cls.THIRD_BASE, 
                          cls.SHORTSTOP, cls.LEFT_FIELD, cls.CENTER_FIELD, cls.RIGHT_FIELD, cls.DESIGNATED_HITTER],
            SportType.NFL: [cls.QUARTERBACK, cls.RUNNING_BACK, cls.WIDE_RECEIVER, cls.TIGHT_END, 
                          cls.OFFENSIVE_LINE, cls.DEFENSIVE_LINE, cls.LINEBACKER, cls.DEFENSIVE_BACK],
            SportType.NHL: [cls.GOALIE, cls.DEFENSEMAN, cls.LEFT_WING, cls.CENTER_HOCKEY, cls.RIGHT_WING],
            SportType.EPL: [cls.GOALKEEPER, cls.DEFENDER, cls.MIDFIELDER, cls.FORWARD]
        }
        return sport_positions.get(sport, [])
```

### PlayerStats

Unified statistics model that adapts to different sports:

```python
@dataclass
class PlayerStats:
    """Unified player statistics across sports."""
    
    # Basic game statistics
    games_played: int = 0
    games_started: int = 0
    minutes_played: Optional[float] = None  # Total or per game
    
    # Scoring (sport-agnostic)
    points: Optional[float] = None          # Points/Goals/Touchdowns
    assists: Optional[float] = None         # Assists (when applicable)
    
    # Sport-specific primary stats
    sport_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Advanced metrics
    efficiency_rating: Optional[float] = None
    plus_minus: Optional[float] = None
    
    # Season information
    season: Optional[int] = None
    season_type: str = "Regular Season"    # "Regular Season", "Playoffs"
    
    # Stat calculation metadata
    per_game: bool = False                 # Whether stats are per-game averages
    last_updated: Optional[datetime] = None
    
    def normalize_to_per_game(self) -> 'PlayerStats':
        """Convert total stats to per-game averages."""
        if self.per_game or self.games_played == 0:
            return self
        
        normalized = PlayerStats(
            games_played=self.games_played,
            games_started=self.games_started,
            minutes_played=self.minutes_played / self.games_played if self.minutes_played else None,
            points=self.points / self.games_played if self.points else None,
            assists=self.assists / self.games_played if self.assists else None,
            per_game=True,
            season=self.season,
            season_type=self.season_type,
            sport_stats=self.sport_stats
        )
        return normalized
    
    @classmethod
    def for_nba_player(cls, **kwargs) -> 'PlayerStats':
        """Create NBA-specific player stats."""
        return cls(
            sport_stats={
                'field_goals_made': kwargs.get('fg_made', 0),
                'field_goals_attempted': kwargs.get('fg_attempted', 0),
                'three_pointers_made': kwargs.get('three_pm', 0),
                'three_pointers_attempted': kwargs.get('three_pa', 0),
                'free_throws_made': kwargs.get('ft_made', 0),
                'free_throws_attempted': kwargs.get('ft_attempted', 0),
                'rebounds': kwargs.get('rebounds', 0),
                'offensive_rebounds': kwargs.get('oreb', 0),
                'defensive_rebounds': kwargs.get('dreb', 0),
                'steals': kwargs.get('steals', 0),
                'blocks': kwargs.get('blocks', 0),
                'turnovers': kwargs.get('turnovers', 0),
                'personal_fouls': kwargs.get('fouls', 0)
            },
            **{k: v for k, v in kwargs.items() if k not in ['fg_made', 'fg_attempted', 'three_pm', 'three_pa', 'ft_made', 'ft_attempted', 'rebounds', 'oreb', 'dreb', 'steals', 'blocks', 'turnovers', 'fouls']}
        )
```

## Game Models

### Game

Complete game information including teams, scores, and status:

```python
@dataclass
class Game(BaseEntity):
    """Unified game model across all sports."""
    
    # Basic game information (from Ball Don't Lie API)
    date: Optional[str] = None           # "1946-11-01"
    datetime: Optional[str] = None       # "2018-10-17T02:30:00.000Z"
    season: Optional[int] = None         # Season year (2023)
    status: str = ""                     # "Final", "In Progress", "Scheduled"
    
    # Game structure
    period: Optional[int] = None         # Current quarter/period/inning
    time: Optional[str] = None           # Time remaining in period
    postseason: bool = False             # Whether this is a playoff game
    
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
    
    # Weather (for outdoor sports)
    weather_conditions: Optional[str] = None
    temperature: Optional[int] = None
    
    # Venue information
    venue_name: Optional[str] = None
    venue_capacity: Optional[int] = None
    attendance: Optional[int] = None
    
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
    def is_scheduled(self) -> bool:
        """Check if the game is scheduled for the future."""
        return self.status.lower() in ['scheduled', 'upcoming', 'not started']
    
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
        if not self.is_completed:
            return None
        
        if self.home_team_score > self.visitor_team_score:
            return self.home_team_id
        elif self.visitor_team_score > self.home_team_score:
            return self.visitor_team_id
        else:
            return None  # Tie game
    
    @property
    def game_summary(self) -> str:
        """Get a summary string for the game."""
        home = self.home_team_abbreviation or "Home"
        visitor = self.visitor_team_abbreviation or "Visitor"
        
        if self.is_completed:
            return f"{visitor} {self.visitor_team_score} - {self.home_team_score} {home} (Final)"
        elif self.is_live:
            return f"{visitor} {self.visitor_team_score} - {self.home_team_score} {home} ({self.status})"
        else:
            return f"{visitor} @ {home} ({self.status})"
```

### GameStats

Game-level statistics and advanced metrics:

```python
@dataclass
class GameStats:
    """Game-level statistics across sports."""
    
    # Basic game flow
    lead_changes: int = 0
    times_tied: int = 0
    largest_lead_home: int = 0
    largest_lead_visitor: int = 0
    
    # Pace and efficiency
    pace: Optional[float] = None         # Possessions per game
    efficiency_home: Optional[float] = None
    efficiency_visitor: Optional[float] = None
    
    # Team statistics
    home_team_stats: Dict[str, Any] = field(default_factory=dict)
    visitor_team_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Player performances (top performers)
    leading_scorer: Optional[Dict[str, Any]] = None
    leading_rebounder: Optional[Dict[str, Any]] = None
    leading_assister: Optional[Dict[str, Any]] = None
    
    # Game notes
    overtime_periods: int = 0
    ejections: List[str] = field(default_factory=list)
    technical_fouls: int = 0
    
    @property
    def was_close_game(self) -> bool:
        """Determine if the game was close (within 5 points)."""
        return abs(self.largest_lead_home - self.largest_lead_visitor) <= 5
    
    @property
    def total_lead_changes(self) -> int:
        """Total lead changes and ties."""
        return self.lead_changes + self.times_tied
```

## Statistics Models

### UnifiedStats

Base statistics structure that adapts to any sport:

```python
@dataclass
class UnifiedStats:
    """Base statistics structure adaptable to any sport."""
    
    # Temporal information
    season: int
    season_type: str = "Regular Season"   # "Regular Season", "Playoffs", "Preseason"
    date_range: Optional[Tuple[str, str]] = None
    
    # Entity information
    entity_id: str                        # Player ID, Team ID, etc.
    entity_type: str                      # "player", "team", "game"
    sport: SportType
    
    # Core statistics (sport-agnostic)
    games: int = 0
    wins: int = 0
    losses: int = 0
    
    # Statistical data (flexible structure)
    stats: Dict[str, Union[int, float]] = field(default_factory=dict)
    
    # Advanced metrics
    advanced_stats: Dict[str, float] = field(default_factory=dict)
    
    # Percentiles and rankings
    percentiles: Dict[str, float] = field(default_factory=dict)
    rankings: Dict[str, int] = field(default_factory=dict)
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.utcnow)
    source: str = "ball_dont_lie_api"
    
    def get_stat(self, stat_name: str) -> Optional[Union[int, float]]:
        """Get a specific statistic."""
        return self.stats.get(stat_name)
    
    def set_stat(self, stat_name: str, value: Union[int, float]) -> None:
        """Set a specific statistic."""
        self.stats[stat_name] = value
    
    def get_percentile(self, stat_name: str) -> Optional[float]:
        """Get percentile ranking for a statistic."""
        return self.percentiles.get(stat_name)
    
    def calculate_efficiency(self) -> Optional[float]:
        """Calculate general efficiency metric (sport-specific implementation)."""
        # Override in sport-specific subclasses
        return None
```

### StatType

Enumeration of different statistical types:

```python
class StatType(str, Enum):
    """Types of statistics for classification."""
    
    TOTAL = "total"       # Season/career totals
    AVERAGE = "average"   # Per-game averages
    RATE = "rate"         # Rate statistics (per 100 possessions, etc.)
    PERCENTAGE = "percentage"  # Shooting percentages, win percentage
    ADVANCED = "advanced" # Advanced metrics (PER, WAR, etc.)
    RANKING = "ranking"   # League/position rankings
```

## Response Formats

### Ball Don't Lie API Response Structure

All API responses follow this format:

```json
{
  "data": [
    {
      "id": 1,
      "abbreviation": "ATL",
      "city": "Atlanta",
      "conference": "East",
      "division": "Southeast",
      "full_name": "Atlanta Hawks",
      "name": "Hawks"
    }
  ],
  "meta": {
    "total_pages": 1,
    "current_page": 1,
    "next_page": null,
    "per_page": 30,
    "total_count": 30
  }
}
```

### HoopHead APIResponse

Internal response wrapper:

```python
@dataclass
class APIResponse:
    """Standardized API response structure."""
    data: Any                    # Raw Ball Don't Lie response
    success: bool               # Request success status
    error: Optional[str] = None # Error message if failed
    sport: Optional[Sport] = None # Sport context
    meta: Optional[Dict] = None  # Cache info, timing, etc.
    
    @property
    def entities(self) -> List[Dict]:
        """Extract entity list from data."""
        if isinstance(self.data, dict) and 'data' in self.data:
            return self.data['data']
        elif isinstance(self.data, list):
            return self.data
        else:
            return []
    
    @property
    def pagination(self) -> Optional[Dict]:
        """Extract pagination metadata."""
        if isinstance(self.data, dict) and 'meta' in self.data:
            return self.data['meta']
        return None
```

## Model Relationships

### Entity Relationship Diagram

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Team     │    │   Player    │    │    Game     │
│             │    │             │    │             │
│ • id        │───►│ • team_id   │    │ • home_team │
│ • name      │    │ • name      │    │ • visitor   │
│ • conference│    │ • position  │◄───│ • scores    │
│ • division  │    │ • stats     │    │ • status    │
│ • stats     │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ TeamStats   │    │PlayerStats  │    │ GameStats   │
│             │    │             │    │             │
│ • wins/loss │    │ • points    │    │ • pace      │
│ • scoring   │    │ • assists   │    │ • efficiency│
│ • rankings  │    │ • sport_    │    │ • lead      │
│             │    │   specific  │    │   changes   │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Relationships

1. **Team ↔ Player**: One-to-Many
   - A team has multiple players
   - A player belongs to one team (at a time)
   - Connected via `player.team_id`

2. **Team ↔ Game**: Many-to-Many
   - A team plays multiple games
   - A game involves two teams (home/visitor)
   - Connected via `game.home_team_id` and `game.visitor_team_id`

3. **Player ↔ Stats**: One-to-Many
   - A player has stats across multiple seasons
   - Stats belong to one player
   - Connected via foreign key relationships

4. **Game ↔ Stats**: One-to-One
   - Each game has associated statistics
   - Connected via `game.game_stats`

## Usage Examples

### Creating Models from API Data

```python
from backend.src.domain.models import Team, Player, Game, SportType

# Create team from API response
api_team_data = {
    "id": 1,
    "abbreviation": "ATL",
    "city": "Atlanta", 
    "conference": "East",
    "division": "Southeast",
    "full_name": "Atlanta Hawks",
    "name": "Hawks"
}

team = Team(
    id=str(api_team_data["id"]),
    sport=SportType.NBA,
    name=api_team_data["name"],
    full_name=api_team_data["full_name"],
    abbreviation=api_team_data["abbreviation"],
    city=api_team_data["city"],
    conference=api_team_data["conference"],
    division=api_team_data["division"],
    raw_data=api_team_data
)

print(f"Team: {team.display_name}")
print(f"Location: {team.location_abbreviation}")
```

### Model Serialization

```python
# Convert model to dictionary
team_dict = team.to_dict()

# Convert to JSON
import json
team_json = json.dumps(team_dict, default=str)

# Create model from dictionary
team_restored = Team(**team_dict)
```

### Sport-Specific Customization

```python
# Add sport-specific data
nba_team = Team(
    name="Lakers",
    full_name="Los Angeles Lakers",
    sport=SportType.NBA
)

# Add NBA-specific data
nba_team.sport_specific.set("salary_cap", 136021000)
nba_team.sport_specific.set("luxury_tax_threshold", 165294000)
nba_team.sport_specific.set("arena_capacity", 20000)

# Retrieve sport-specific data
salary_cap = nba_team.sport_specific.get("salary_cap")
print(f"Salary cap: ${salary_cap:,}")
```

### Complex Queries and Analysis

```python
from typing import List
from backend.src.domain.models import Player, PlayerStats

def analyze_team_roster(players: List[Player]) -> Dict[str, Any]:
    """Analyze a team's roster composition."""
    
    analysis = {
        "total_players": len(players),
        "positions": {},
        "international_players": 0,
        "rookies": 0,
        "average_height": 0,
        "average_weight": 0,
        "colleges": set()
    }
    
    total_height = 0
    total_weight = 0
    height_count = 0
    weight_count = 0
    
    for player in players:
        # Position analysis
        if player.position:
            pos = player.position.value
            analysis["positions"][pos] = analysis["positions"].get(pos, 0) + 1
        
        # International players
        if player.country and player.country.upper() != "USA":
            analysis["international_players"] += 1
        
        # Rookies
        if player.rookie:
            analysis["rookies"] += 1
        
        # Physical attributes
        if player.height_inches:
            total_height += player.height_inches
            height_count += 1
        
        if player.weight_pounds:
            total_weight += player.weight_pounds
            weight_count += 1
        
        # Colleges
        if player.college:
            analysis["colleges"].add(player.college)
    
    # Calculate averages
    if height_count > 0:
        avg_height_inches = total_height / height_count
        analysis["average_height"] = f"{avg_height_inches // 12:.0f}'-{avg_height_inches % 12:.0f}\""
    
    if weight_count > 0:
        analysis["average_weight"] = f"{total_weight / weight_count:.0f} lbs"
    
    analysis["colleges"] = len(analysis["colleges"])
    
    return analysis

# Usage
roster_analysis = analyze_team_roster(lakers_players)
print(f"Total players: {roster_analysis['total_players']}")
print(f"International players: {roster_analysis['international_players']}")
print(f"Average height: {roster_analysis['average_height']}")
```

### Model Validation

```python
from typing import Optional
import re

def validate_player_data(player: Player) -> List[str]:
    """Validate player data and return list of issues."""
    issues = []
    
    # Name validation
    if not player.first_name.strip():
        issues.append("First name is required")
    if not player.last_name.strip():
        issues.append("Last name is required")
    
    # Height validation (if provided)
    if player.height:
        if not re.match(r'^\d+-\d+$', player.height):
            issues.append(f"Invalid height format: {player.height} (expected: 6-6)")
    
    # Weight validation
    if player.weight:
        try:
            weight = int(player.weight)
            if weight < 100 or weight > 400:
                issues.append(f"Weight seems unrealistic: {weight} lbs")
        except ValueError:
            issues.append(f"Invalid weight format: {player.weight}")
    
    # Jersey number validation
    if player.jersey_number:
        try:
            num = int(player.jersey_number)
            if num < 0 or num > 99:
                issues.append(f"Invalid jersey number: {num}")
        except ValueError:
            issues.append(f"Jersey number must be numeric: {player.jersey_number}")
    
    # Position validation
    if player.position:
        valid_positions = PlayerPosition.for_sport(player.sport)
        if player.position not in valid_positions:
            issues.append(f"Invalid position {player.position} for {player.sport.value}")
    
    return issues

# Usage
validation_issues = validate_player_data(lebron)
if validation_issues:
    print("Validation issues found:")
    for issue in validation_issues:
        print(f"  - {issue}")
else:
    print("Player data is valid")
```

---

## Next Steps

- Review [API Reference](API_REFERENCE.md) for detailed API usage
- Check [Integration Guide](INTEGRATION_GUIDE.md) for implementation patterns
- See [Error Handling Guide](ERROR_HANDLING.md) for robust error management
- Explore [Extension Guide](EXTENSION_GUIDE.md) for adding custom functionality

For technical support, refer to the main [HoopHead Documentation](../README.md). 