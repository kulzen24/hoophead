# HoopHead API Reference Documentation

## Overview

HoopHead provides a unified, enterprise-grade API for accessing multi-sport statistics from the Ball Don't Lie API. This documentation covers all available endpoints, data models, authentication patterns, and integration examples for NBA, MLB, NFL, NHL, and EPL sports data.

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Core API Client](#core-api-client)
- [Data Models](#data-models)
- [API Methods](#api-methods)
- [Caching System](#caching-system)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Response Formats](#response-formats)
- [Integration Examples](#integration-examples)

## Quick Start

### Installation & Setup

```python
# 1. Set up environment variables
export BALLDONTLIE_API_KEY="your-api-key-here"
export HOOPHEAD_ENCRYPTION_KEY="your-32-character-encryption-key"

# 2. Initialize the client
from backend.src.adapters.external.ball_dont_lie_client import BallDontLieClient, Sport

# Simple initialization
client = BallDontLieClient(api_key="your-api-key")

# Or use environment variable
client = BallDontLieClient()  # Reads from BALLDONTLIE_API_KEY

# With authentication manager for enterprise features
from backend.src.adapters.external.auth_manager import AuthenticationManager, APITier

auth_manager = AuthenticationManager()
key_id = auth_manager.add_api_key("your-api-key", APITier.ALL_STAR, "Production Key")
client = BallDontLieClient(key_id=key_id)
```

### Basic Usage

```python
import asyncio

async def get_nba_teams():
    async with BallDontLieClient() as client:
        # Get all NBA teams
        response = await client.get_teams(Sport.NBA)
        teams = response.data
        
        for team in teams[:5]:  # First 5 teams
            print(f"{team['full_name']} ({team['abbreviation']})")

# Run the example
asyncio.run(get_nba_teams())
```

## Authentication

### API Tiers

HoopHead supports tiered authentication aligned with Ball Don't Lie API pricing:

| Tier | Requests/Hour | Requests/Minute | Concurrent | Features |
|------|---------------|-----------------|------------|----------|
| **FREE** | 300 | 5 | 1 | Teams, players, games |
| **ALL-STAR** | 3,600 | 60 | 2 | + Player stats, injuries |
| **GOAT** | 36,000 | 600 | 5 | + Box scores, standings, odds |
| **Enterprise** | 36,000* | 600* | 10 | + Bulk export, custom features |

### Authentication Methods

#### 1. Direct API Key

```python
client = BallDontLieClient(api_key="your-api-key-here")
```

#### 2. Environment Variable

```python
# Set in .env file: BALLDONTLIE_API_KEY=your-key-here
client = BallDontLieClient()  # Auto-detects from environment
```

#### 3. Authentication Manager (Enterprise)

```python
from backend.src.adapters.external.auth_manager import AuthenticationManager, APITier

# Initialize authentication manager
auth_manager = AuthenticationManager()

# Add multiple API keys with different tiers
key_id_1 = auth_manager.add_api_key("free-tier-key", APITier.FREE, "Development")
key_id_2 = auth_manager.add_api_key("goat-tier-key", APITier.GOAT, "Production")

# Create client with specific key
client = BallDontLieClient(key_id=key_id_2)

# Check usage and tier information
usage_stats = auth_manager.get_usage_stats(key_id_2)
print(f"Requests used: {usage_stats['requests_this_hour']}")
```

### Security Features

- **Encrypted Storage**: API keys stored with Fernet (AES 128) encryption
- **Usage Tracking**: Detailed analytics per API key
- **Rate Limiting**: Automatic enforcement based on tier
- **Key Rotation**: Dynamic key switching without restart

## Core API Client

### BallDontLieClient Class

The main interface for all API operations.

```python
class BallDontLieClient:
    """
    Unified multi-sport client for Ball Don't Lie API.
    Handles authentication, rate limiting, caching, and sport-specific routing.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        enable_cache: bool = True, 
        key_id: Optional[str] = None
    ):
        """
        Initialize the multi-sport API client.
        
        Args:
            api_key: Direct API key (optional if set in environment)
            enable_cache: Enable multi-layered caching (default: True)
            key_id: Use specific key from authentication manager
        """
```

### Supported Sports

```python
from backend.src.adapters.external.ball_dont_lie_client import Sport

# Available sports
Sport.NBA  # National Basketball Association
Sport.MLB  # Major League Baseball  
Sport.NFL  # National Football League
Sport.NHL  # National Hockey League
Sport.EPL  # English Premier League
```

### Context Manager Usage

```python
# Recommended: Use async context manager for automatic resource cleanup
async with BallDontLieClient() as client:
    teams = await client.get_teams(Sport.NBA)
    players = await client.get_players(Sport.NBA, search="LeBron")

# Manual management (remember to close)
client = BallDontLieClient()
try:
    teams = await client.get_teams(Sport.NBA)
finally:
    await client.close()
```

## Data Models

### Sport Types

```python
from backend.src.domain.models.base import SportType

class SportType(str, Enum):
    NBA = "nba"
    MLB = "mlb" 
    NFL = "nfl"
    NHL = "nhl"
    EPL = "epl"
    
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
```

### Base Entity

All domain models inherit from `BaseEntity`:

```python
@dataclass
class BaseEntity(ABC):
    """Base entity class for all domain models with common patterns."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sport: SportType = SportType.NBA
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    raw_data: Optional[Dict[str, Any]] = None  # Original API response
```

### Team Model

```python
@dataclass
class Team(BaseEntity):
    """Unified team model across all sports."""
    # Basic information (from API)
    name: str = ""                    # "Lakers"
    full_name: str = ""              # "Los Angeles Lakers"
    abbreviation: str = ""           # "LAL"
    city: str = ""                   # "Los Angeles"
    
    # League structure
    conference: Optional[str] = None  # "West", "American League", etc.
    division: Optional[str] = None   # "Pacific", "NL West", etc.
    
    # Team statistics
    team_stats: Optional[TeamStats] = None
    
    # Sport-specific data
    sport_specific: SportSpecificData = field(default_factory=lambda: SportSpecificData(SportType.NBA))
```

### Player Model

```python
@dataclass
class Player(BaseEntity):
    """Unified player model across all sports."""
    # Basic information
    first_name: str = ""
    last_name: str = ""
    
    # Physical attributes
    height: Optional[str] = None      # "6-6", "5-11"
    weight: Optional[str] = None      # "190", "220"
    
    # Team and position information
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    team_abbreviation: Optional[str] = None
    position: Optional[PlayerPosition] = None
    jersey_number: Optional[str] = None
    
    # Career information
    college: Optional[str] = None
    country: Optional[str] = None
    draft_year: Optional[int] = None
    draft_round: Optional[int] = None
    draft_number: Optional[int] = None
    
    # Statistics
    current_stats: Optional[PlayerStats] = None
    career_stats: Optional[PlayerStats] = None
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
```

### Game Model

```python
@dataclass
class Game(BaseEntity):
    """Unified game model across all sports."""
    # Basic game information
    date: Optional[str] = None        # "1946-11-01"
    datetime: Optional[str] = None    # "2018-10-17T02:30:00.000Z"
    season: Optional[int] = None      # Season year
    status: str = ""                  # "Final", "In Progress"
    
    # Game structure
    period: Optional[int] = None      # Quarter/Period/Inning
    time: Optional[str] = None        # Time remaining
    postseason: bool = False          # Playoff game
    
    # Team information and scores
    home_team_id: Optional[int] = None
    home_team_score: int = 0
    home_team_name: Optional[str] = None
    home_team_abbreviation: Optional[str] = None
    
    visitor_team_id: Optional[int] = None
    visitor_team_score: int = 0
    visitor_team_name: Optional[str] = None
    visitor_team_abbreviation: Optional[str] = None
    
    @property
    def is_completed(self) -> bool:
        return self.status.lower() in ['final', 'completed', 'finished']
    
    @property
    def point_differential(self) -> int:
        return self.home_team_score - self.visitor_team_score
```

## API Methods

### Teams

#### Get All Teams

```python
async def get_teams(self, sport: Sport) -> APIResponse:
    """
    Retrieve all teams for a specific sport.
    
    Args:
        sport: Sport to get teams for (NBA, MLB, NFL, NHL, EPL)
        
    Returns:
        APIResponse containing list of teams
        
    Example:
        response = await client.get_teams(Sport.NBA)
        teams = response.data['data']  # Ball Don't Lie API wraps data
        
        for team in teams:
            print(f"{team['full_name']} - {team['city']}")
    """
```

#### Usage Examples by Sport

```python
# NBA Teams (30 teams)
nba_teams = await client.get_teams(Sport.NBA)
print(f"Found {len(nba_teams.data['data'])} NBA teams")

# MLB Teams (30 teams)  
mlb_teams = await client.get_teams(Sport.MLB)

# NFL Teams (32 teams)
nfl_teams = await client.get_teams(Sport.NFL)

# NHL Teams (59+ teams including historical)
nhl_teams = await client.get_teams(Sport.NHL)

# EPL Teams (20 teams)
epl_teams = await client.get_teams(Sport.EPL)
```

### Players

#### Get Players with Search

```python
async def get_players(
    self, 
    sport: Sport, 
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 25
) -> APIResponse:
    """
    Retrieve players for a sport with optional search.
    
    Args:
        sport: Sport to search in
        search: Player name search term (optional)
        page: Page number for pagination (default: 1)
        per_page: Results per page (default: 25, max: 100)
        
    Returns:
        APIResponse containing list of players and pagination metadata
    """
```

#### Player Search Examples

```python
# Search for specific player
lebron = await client.get_players(Sport.NBA, search="LeBron")
players = lebron.data['data']
if players:
    player = players[0]
    print(f"Found: {player['first_name']} {player['last_name']}")
    print(f"Team: {player['team']['full_name']}")
    print(f"Position: {player['position']}")

# Get all players (paginated)
all_players = await client.get_players(Sport.NBA, page=1, per_page=100)

# Search across different sports
curry = await client.get_players(Sport.NBA, search="Curry")
mahomes = await client.get_players(Sport.NFL, search="Mahomes") 
ohtani = await client.get_players(Sport.MLB, search="Ohtani")
mcdavid = await client.get_players(Sport.NHL, search="McDavid")
```

### Games

#### Get Games

```python
async def get_games(
    self,
    sport: Sport,
    seasons: Optional[List[int]] = None,
    team_ids: Optional[List[int]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    postseason: Optional[bool] = None,
    page: int = 1,
    per_page: int = 25
) -> APIResponse:
    """
    Retrieve games with flexible filtering options.
    
    Args:
        sport: Sport to get games for
        seasons: List of season years to filter by
        team_ids: List of team IDs to filter by
        start_date: Start date filter (YYYY-MM-DD)
        end_date: End date filter (YYYY-MM-DD)
        postseason: Filter by playoff games (True/False/None)
        page: Page number for pagination
        per_page: Results per page (max: 100)
        
    Returns:
        APIResponse containing list of games and pagination metadata
    """
```

#### Game Query Examples

```python
# Get recent Lakers games
lakers_games = await client.get_games(
    sport=Sport.NBA,
    team_ids=[14],  # Lakers team ID
    seasons=[2023],
    per_page=10
)

# Get playoff games for current season
playoff_games = await client.get_games(
    sport=Sport.NBA,
    seasons=[2023],
    postseason=True
)

# Get games by date range
recent_games = await client.get_games(
    sport=Sport.NBA,
    start_date="2023-12-01",
    end_date="2023-12-31"
)

# Multi-sport game retrieval
nba_games = await client.get_games(Sport.NBA, seasons=[2023])
nfl_games = await client.get_games(Sport.NFL, seasons=[2023])
mlb_games = await client.get_games(Sport.MLB, seasons=[2023])
```

## Caching System

### Multi-Layered Cache Architecture

HoopHead uses a sophisticated multi-layered caching system:

1. **Redis Cache** (Hot Data): Sub-3ms access for frequently requested data
2. **File Cache** (Historical Data): Persistent storage for long-term data
3. **Tier-Based Optimization**: Cache strategy based on API subscription tier

```python
# Cache is automatically enabled, but can be controlled
client = BallDontLieClient(enable_cache=True)  # Default

# Disable cache for real-time data
client = BallDontLieClient(enable_cache=False)
```

### Cache Configuration by Tier

| Tier | Redis Priority | File Priority | TTL Multiplier | Features |
|------|---------------|---------------|----------------|----------|
| **FREE** | Low | High | 1.0x | File-first caching |
| **ALL-STAR** | Medium | Medium | 1.2x | Balanced caching |
| **GOAT** | High | Low | 1.5x | Redis-first, extended TTL |
| **Enterprise** | High | Medium | 1.5x | Full features + analytics |

### Cache Usage Examples

```python
from backend.src.adapters.cache import CacheStrategy

# Get cache statistics
async with BallDontLieClient() as client:
    # Make some requests to populate cache
    teams = await client.get_teams(Sport.NBA)
    players = await client.get_players(Sport.NBA, search="LeBron")
    
    # Check cache performance
    if hasattr(client, 'multi_cache'):
        stats = await client.multi_cache.get_analytics()
        print(f"Cache hit rate: {stats['hit_rate']:.2%}")
        print(f"Average latency: {stats['avg_latency_ms']:.1f}ms")
        print(f"Redis hits: {stats['redis_hits']}")
        print(f"File hits: {stats['file_hits']}")

# Cache warming for popular queries
from backend.src.adapters.cache.cache_warming import warm_popular_queries

# Warm cache with celebrity players
await warm_popular_queries(client, Sport.NBA)
```

## Error Handling

### Exception Hierarchy

HoopHead provides comprehensive error handling with detailed context:

```python
from backend.src.core.exceptions import (
    HoopHeadException,           # Base exception
    APIException,                # API-related errors
    APIConnectionError,          # Network connectivity issues
    APITimeoutError,            # Request timeout
    APIRateLimitError,          # Rate limit exceeded
    APIAuthenticationError,      # Invalid API key
    APINotFoundError,           # Resource not found
    APIServerError,             # Server-side errors
    CacheException,             # Cache-related errors
    DomainException             # Business logic errors
)
```

### Error Handling Examples

```python
import asyncio
from backend.src.core.exceptions import APIRateLimitError, APIAuthenticationError

async def robust_api_call():
    try:
        async with BallDontLieClient() as client:
            response = await client.get_teams(Sport.NBA)
            return response.data
            
    except APIAuthenticationError as e:
        print(f"Authentication failed: {e}")
        print("Check your API key configuration")
        return None
        
    except APIRateLimitError as e:
        print(f"Rate limit exceeded: {e}")
        print(f"Retry after: {e.retry_after} seconds")
        if e.retry_after:
            await asyncio.sleep(e.retry_after)
            # Retry logic here
        return None
        
    except APIConnectionError as e:
        print(f"Connection error: {e}")
        print("Check network connectivity")
        return None
        
    except HoopHeadException as e:
        print(f"HoopHead error: {e}")
        print(f"Error context: {e.context}")
        return None
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Example with error context
try:
    response = await client.get_players(Sport.NBA, search="InvalidPlayer")
except APINotFoundError as e:
    print(f"Resource not found: {e.resource}")
    print(f"Sport: {e.context.sport}")
    print(f"Operation: {e.context.operation}")
```

### Retry and Recovery Patterns

```python
from backend.src.core.error_handler import with_api_error_handling

@with_api_error_handling(max_retries=3, delay=1.0)
async def get_teams_with_retry(client, sport):
    """Automatically retry on transient failures."""
    return await client.get_teams(sport)

# Usage
teams = await get_teams_with_retry(client, Sport.NBA)
```

## Rate Limiting

### Automatic Rate Limiting

HoopHead automatically enforces rate limits based on your API tier:

```python
# Rate limiting is handled automatically
async with BallDontLieClient() as client:
    # These requests are automatically throttled
    for i in range(100):
        try:
            response = await client.get_teams(Sport.NBA)
            print(f"Request {i+1} successful")
        except APIRateLimitError as e:
            print(f"Rate limited. Waiting {e.retry_after} seconds...")
            await asyncio.sleep(e.retry_after)
```

### Rate Limit Information

```python
from backend.src.adapters.external.auth_manager import AuthenticationManager

auth_manager = AuthenticationManager()
key_info = auth_manager.get_key_info(key_id)

print(f"Tier: {key_info.tier.value}")
print(f"Requests per hour: {key_info.tier_limits.requests_per_hour}")
print(f"Requests per minute: {key_info.tier_limits.requests_per_minute}")
print(f"Current usage: {key_info.usage_stats['requests_this_hour']}")
```

## Response Formats

### Standard API Response

All API methods return an `APIResponse` object:

```python
@dataclass
class APIResponse:
    """Standardized API response structure."""
    data: Any                    # Actual response data
    success: bool               # Whether request succeeded
    error: Optional[str] = None # Error message if failed
    sport: Optional[Sport] = None # Sport for the request
    meta: Optional[Dict] = None  # Additional metadata (caching, pagination)
```

### Ball Don't Lie API Data Structure

The Ball Don't Lie API wraps all responses in a `data` field:

```python
# Example response structure
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

### Accessing Response Data

```python
# Get teams
response = await client.get_teams(Sport.NBA)

# Access the actual data
teams_list = response.data['data']  # Ball Don't Lie wraps in 'data'
pagination = response.data['meta']   # Pagination metadata

# Process teams
for team in teams_list:
    print(f"Team: {team['full_name']}")
    print(f"  City: {team['city']}")
    print(f"  Conference: {team['conference']}")
    print(f"  Division: {team['division']}")
```

## Integration Examples

### Web Application Integration

```python
from fastapi import FastAPI, HTTPException
from backend.src.adapters.external.ball_dont_lie_client import BallDontLieClient, Sport

app = FastAPI()

# Initialize client globally or as dependency
client = BallDontLieClient()

@app.get("/api/teams/{sport}")
async def get_teams(sport: str):
    """Get all teams for a sport."""
    try:
        sport_enum = Sport(sport.lower())
        response = await client.get_teams(sport_enum)
        return {
            "teams": response.data['data'],
            "success": True,
            "sport": sport_enum.value
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid sport: {sport}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/players/{sport}")
async def search_players(sport: str, search: str = ""):
    """Search players in a sport."""
    try:
        sport_enum = Sport(sport.lower())
        response = await client.get_players(sport_enum, search=search)
        return {
            "players": response.data['data'],
            "pagination": response.data['meta'],
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Data Analysis Integration

```python
import pandas as pd
from typing import List, Dict, Any

class SportsDataAnalyzer:
    """Data analysis wrapper for HoopHead API."""
    
    def __init__(self, api_key: str):
        self.client = BallDontLieClient(api_key=api_key)
    
    async def get_teams_dataframe(self, sport: Sport) -> pd.DataFrame:
        """Get teams as a pandas DataFrame."""
        response = await self.client.get_teams(sport)
        teams = response.data['data']
        return pd.DataFrame(teams)
    
    async def get_players_dataframe(self, sport: Sport, search: str = "") -> pd.DataFrame:
        """Get players as a pandas DataFrame."""
        all_players = []
        page = 1
        
        while True:
            response = await self.client.get_players(sport, search=search, page=page, per_page=100)
            players = response.data['data']
            
            if not players:
                break
                
            all_players.extend(players)
            
            # Check if there are more pages
            meta = response.data['meta']
            if page >= meta['total_pages']:
                break
            page += 1
        
        return pd.DataFrame(all_players)
    
    async def analyze_conference_distribution(self, sport: Sport) -> Dict[str, int]:
        """Analyze team distribution by conference."""
        df = await self.get_teams_dataframe(sport)
        return df['conference'].value_counts().to_dict()

# Usage
analyzer = SportsDataAnalyzer("your-api-key")
teams_df = await analyzer.get_teams_dataframe(Sport.NBA)
conference_dist = await analyzer.analyze_conference_distribution(Sport.NBA)
```

### CLI Tool Integration

```python
import click
import asyncio
from backend.src.adapters.external.ball_dont_lie_client import BallDontLieClient, Sport

@click.group()
def cli():
    """HoopHead CLI for sports data."""
    pass

@cli.command()
@click.argument('sport', type=click.Choice(['nba', 'mlb', 'nfl', 'nhl', 'epl']))
def teams(sport):
    """Get all teams for a sport."""
    async def get_teams():
        async with BallDontLieClient() as client:
            response = await client.get_teams(Sport(sport))
            teams = response.data['data']
            
            for team in teams:
                click.echo(f"{team['full_name']} ({team['abbreviation']})")
    
    asyncio.run(get_teams())

@cli.command()
@click.argument('sport', type=click.Choice(['nba', 'mlb', 'nfl', 'nhl', 'epl']))
@click.argument('player_name')
def search(sport, player_name):
    """Search for a player."""
    async def search_player():
        async with BallDontLieClient() as client:
            response = await client.get_players(Sport(sport), search=player_name)
            players = response.data['data']
            
            if not players:
                click.echo(f"No players found matching '{player_name}'")
                return
            
            for player in players:
                team_info = f" ({player['team']['abbreviation']})" if player['team'] else ""
                click.echo(f"{player['first_name']} {player['last_name']}{team_info}")
    
    asyncio.run(search_player())

if __name__ == "__main__":
    cli()
```

### Async Batch Processing

```python
import asyncio
from typing import List, Tuple
from backend.src.adapters.external.ball_dont_lie_client import BallDontLieClient, Sport

class BatchProcessor:
    """Batch process multiple API requests efficiently."""
    
    def __init__(self, api_key: str, max_concurrent: int = 5):
        self.client = BallDontLieClient(api_key=api_key)
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def get_all_sports_teams(self) -> Dict[Sport, List[Dict]]:
        """Get teams for all sports concurrently."""
        sports = [Sport.NBA, Sport.MLB, Sport.NFL, Sport.NHL, Sport.EPL]
        
        async def get_sport_teams(sport: Sport) -> Tuple[Sport, List[Dict]]:
            async with self.semaphore:
                response = await self.client.get_teams(sport)
                return sport, response.data['data']
        
        # Execute all requests concurrently
        tasks = [get_sport_teams(sport) for sport in sports]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        teams_by_sport = {}
        for result in results:
            if isinstance(result, Exception):
                print(f"Error: {result}")
                continue
            sport, teams = result
            teams_by_sport[sport] = teams
        
        return teams_by_sport
    
    async def search_players_across_sports(self, name: str) -> Dict[Sport, List[Dict]]:
        """Search for a player across all sports."""
        sports = [Sport.NBA, Sport.MLB, Sport.NFL, Sport.NHL, Sport.EPL]
        
        async def search_in_sport(sport: Sport) -> Tuple[Sport, List[Dict]]:
            async with self.semaphore:
                try:
                    response = await self.client.get_players(sport, search=name)
                    return sport, response.data['data']
                except Exception as e:
                    print(f"Error searching {sport.value}: {e}")
                    return sport, []
        
        tasks = [search_in_sport(sport) for sport in sports]
        results = await asyncio.gather(*tasks)
        
        return {sport: players for sport, players in results if players}

# Usage
async def main():
    processor = BatchProcessor("your-api-key")
    
    # Get all teams across sports
    all_teams = await processor.get_all_sports_teams()
    for sport, teams in all_teams.items():
        print(f"{sport.value}: {len(teams)} teams")
    
    # Search for a player across all sports
    lebron_results = await processor.search_players_across_sports("LeBron")
    for sport, players in lebron_results.items():
        print(f"Found in {sport.value}: {len(players)} players")

asyncio.run(main())
```

## Performance Optimization

### Connection Pooling

```python
# BallDontLieClient automatically uses connection pooling
connector = aiohttp.TCPConnector(
    limit=10,           # Total connection pool size
    limit_per_host=5    # Max connections per host
)

# Client handles this automatically, but you can customize:
client = BallDontLieClient(api_key="your-key")
# Internal: Uses optimized connector settings
```

### Batch Requests for Better Performance

```python
async def get_multiple_teams_efficiently():
    """Get teams for multiple sports efficiently."""
    async with BallDontLieClient() as client:
        # Use asyncio.gather for concurrent requests
        tasks = [
            client.get_teams(Sport.NBA),
            client.get_teams(Sport.MLB),
            client.get_teams(Sport.NFL)
        ]
        
        nba_response, mlb_response, nfl_response = await asyncio.gather(*tasks)
        
        return {
            'nba': nba_response.data['data'],
            'mlb': mlb_response.data['data'],
            'nfl': nfl_response.data['data']
        }
```

### Cache Optimization

```python
# Leverage cache warming for better performance
from backend.src.adapters.cache.cache_warming import CacheWarmer

async def optimize_cache_performance():
    """Pre-warm cache with popular queries."""
    async with BallDontLieClient() as client:
        warmer = CacheWarmer(client)
        
        # Warm cache with celebrity players
        await warmer.warm_popular_players()
        
        # Now subsequent requests will be much faster
        lebron = await client.get_players(Sport.NBA, search="LeBron")  # From cache
        curry = await client.get_players(Sport.NBA, search="Curry")    # From cache
```

---

## Next Steps

- Review [Data Model Documentation](DATA_MODELS.md) for detailed schema information
- Check [Integration Guide](INTEGRATION_GUIDE.md) for advanced integration patterns  
- See [Error Handling Guide](ERROR_HANDLING.md) for comprehensive error management
- Explore [Extension Guide](EXTENSION_GUIDE.md) for adding new sports and features

For technical support or questions, refer to the main [HoopHead Documentation](../README.md). 