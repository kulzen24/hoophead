"""
Ball Don't Lie API client for multi-sport statistics retrieval.
Supports NBA, NFL, MLB, and EPL leagues.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import aiohttp
import time
from dataclasses import dataclass

try:
    from backend.config.settings import settings
except ImportError:
    # Fallback for when running standalone
    class MockSettings:
        balldontlie_api_key = ""
        api_request_delay = 0.6
    settings = MockSettings()

logger = logging.getLogger(__name__)

class Sport(str, Enum):
    """Supported sports with their API configurations."""
    NBA = "nba"
    MLB = "mlb"
    NFL = "nfl"
    NHL = "nhl"
    # EPL = "epl"  # Partially working - only games endpoint

# Sport-specific API configurations
SPORT_CONFIGS = {
    Sport.NBA: {
        "base_url": "https://api.balldontlie.io/v1",
        "endpoints": ["teams", "players", "games", "stats"],
        "features": ["player_search", "team_filter", "game_stats"]
    },
    Sport.MLB: {
        "base_url": "https://api.balldontlie.io/mlb/v1",
        "endpoints": ["teams", "players", "games", "stats"],
        "features": ["player_search", "team_filter", "season_stats"]
    },
    Sport.NFL: {
        "base_url": "https://api.balldontlie.io/nfl/v1", 
        "endpoints": ["teams", "players", "games"],
        "features": ["player_search", "team_filter"]
    },
    Sport.NHL: {
        "base_url": "https://api.balldontlie.io/nhl/v1",
        "endpoints": ["teams", "players", "games"],
        "features": ["player_search", "team_filter"]
    }
}

@dataclass
class APIResponse:
    """Standardized API response structure."""
    data: Any
    success: bool
    sport: Sport
    error: Optional[str] = None
    meta: Optional[Dict] = None

class BallDontLieClient:
    """
    Unified client for Ball Don't Lie multi-sport API.
    Supports NBA, MLB, NFL, and NHL with sport-specific methods.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            self.api_key = api_key
        else:
            import os
            self.api_key = getattr(settings, 'balldontlie_api_key', '') or os.getenv('BALLDONTLIE_API_KEY', '')
        
        if not self.api_key:
            raise ValueError("API key is required. Provide it as parameter or set BALLDONTLIE_API_KEY environment variable.")
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0
        self.min_request_interval = getattr(settings, 'api_request_delay', 0.6)
        
    async def __aenter__(self):
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "HoopHead/0.1.0"
        }
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _make_request(self, sport: Sport, endpoint: str, params: Optional[Dict] = None) -> APIResponse:
        """Make rate-limited API request with error handling."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' statement.")
        
        config = SPORT_CONFIGS[sport]
        await self._rate_limit()
        
        url = f"{config['base_url']}/{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                
                if response.status == 401:
                    error_msg = "Authentication failed. Check your API key."
                    logger.error(f"{error_msg} Status: {response.status}")
                    return APIResponse(data=None, success=False, sport=sport, error=error_msg)
                
                elif response.status == 429:
                    error_msg = "Rate limit exceeded"
                    logger.warning(f"{error_msg}. Status: {response.status}")
                    return APIResponse(data=None, success=False, sport=sport, error=error_msg)
                
                elif response.status == 404:
                    error_msg = f"Endpoint not found: {endpoint}"
                    logger.error(f"{error_msg} Status: {response.status}")
                    return APIResponse(data=None, success=False, sport=sport, error=error_msg)
                
                elif response.status != 200:
                    error_msg = f"API request failed with status {response.status}"
                    logger.error(f"{error_msg} for {url}")
                    return APIResponse(data=None, success=False, sport=sport, error=error_msg)
                
                data = await response.json()
                return APIResponse(
                    data=data.get('data', []), 
                    success=True, 
                    sport=sport,
                    meta=data.get('meta')
                )
                
        except asyncio.TimeoutError:
            error_msg = f"Request timeout for {endpoint}"
            logger.error(error_msg)
            return APIResponse(data=None, success=False, sport=sport, error=error_msg)
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"{error_msg} for {endpoint}")
            return APIResponse(data=None, success=False, sport=sport, error=error_msg)

    # Generic sport methods
    async def get_teams(self, sport: Sport, cursor: Optional[int] = None, per_page: int = 25) -> APIResponse:
        """Get teams for any sport."""
        params = {"per_page": per_page}
        if cursor:
            params["cursor"] = cursor
        return await self._make_request(sport, "teams", params)

    async def get_players(self, sport: Sport, cursor: Optional[int] = None, per_page: int = 25, 
                         search: Optional[str] = None) -> APIResponse:
        """Get players for any sport with optional search."""
        params = {"per_page": per_page}
        if cursor:
            params["cursor"] = cursor
        if search:
            params["search"] = search
        return await self._make_request(sport, "players", params)

    async def get_games(self, sport: Sport, cursor: Optional[int] = None, per_page: int = 25,
                       **kwargs) -> APIResponse:
        """Get games for any sport with sport-specific filters."""
        params = {"per_page": per_page}
        if cursor:
            params["cursor"] = cursor
        
        # Add sport-specific parameters
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, list):
                    params[f"{key}[]"] = value
                else:
                    params[key] = value
                    
        return await self._make_request(sport, "games", params)

    # Multi-sport convenience methods
    async def search_players_across_sports(self, search_term: str, 
                                         sports: Optional[List[Sport]] = None) -> Dict[Sport, APIResponse]:
        """Search for players across multiple sports."""
        if sports is None:
            sports = list(Sport)
        
        results = {}
        for sport in sports:
            results[sport] = await self.get_players(sport, search=search_term, per_page=10)
        
        return results

    async def get_all_teams_multi_sport(self, sports: Optional[List[Sport]] = None) -> Dict[Sport, List[Dict]]:
        """Get all teams from multiple sports."""
        if sports is None:
            sports = list(Sport)
        
        results = {}
        
        for sport in sports:
            all_teams = []
            cursor = None
            
            while True:
                response = await self.get_teams(sport, cursor=cursor, per_page=100)
                if not response.success:
                    break
                    
                all_teams.extend(response.data)
                
                # Check if there's more data
                if not response.meta or not response.meta.get('next_cursor'):
                    break
                cursor = response.meta['next_cursor']
            
            results[sport] = all_teams
        
        return results

    # Sport-specific methods for convenience
    
    # NBA Methods
    async def get_nba_teams(self, **kwargs) -> APIResponse:
        """Get NBA teams."""
        return await self.get_teams(Sport.NBA, **kwargs)
    
    async def get_nba_players(self, search: Optional[str] = None, **kwargs) -> APIResponse:
        """Get NBA players with optional search."""
        return await self.get_players(Sport.NBA, search=search, **kwargs)
    
    async def get_nba_games(self, **kwargs) -> APIResponse:
        """Get NBA games with filters."""
        return await self.get_games(Sport.NBA, **kwargs)

    # MLB Methods
    async def get_mlb_teams(self, **kwargs) -> APIResponse:
        """Get MLB teams."""
        return await self.get_teams(Sport.MLB, **kwargs)
    
    async def get_mlb_players(self, search: Optional[str] = None, **kwargs) -> APIResponse:
        """Get MLB players with optional search."""
        return await self.get_players(Sport.MLB, search=search, **kwargs)
    
    async def get_mlb_games(self, **kwargs) -> APIResponse:
        """Get MLB games with filters."""
        return await self.get_games(Sport.MLB, **kwargs)

    # NFL Methods
    async def get_nfl_teams(self, **kwargs) -> APIResponse:
        """Get NFL teams."""
        return await self.get_teams(Sport.NFL, **kwargs)
    
    async def get_nfl_players(self, search: Optional[str] = None, **kwargs) -> APIResponse:
        """Get NFL players with optional search."""
        return await self.get_players(Sport.NFL, search=search, **kwargs)
    
    async def get_nfl_games(self, **kwargs) -> APIResponse:
        """Get NFL games with filters."""
        return await self.get_games(Sport.NFL, **kwargs)

    # NHL Methods
    async def get_nhl_teams(self, **kwargs) -> APIResponse:
        """Get NHL teams."""
        return await self.get_teams(Sport.NHL, **kwargs)
    
    async def get_nhl_players(self, search: Optional[str] = None, **kwargs) -> APIResponse:
        """Get NHL players with optional search.""" 
        return await self.get_players(Sport.NHL, search=search, **kwargs)
    
    async def get_nhl_games(self, **kwargs) -> APIResponse:
        """Get NHL games with filters."""
        return await self.get_games(Sport.NHL, **kwargs)

    # Unified search methods
    async def find_player_by_name(self, name: str, sport: Sport) -> Optional[Dict]:
        """Find a specific player by name in a specific sport."""
        response = await self.get_players(sport, search=name)
        if response.success and response.data:
            return response.data[0]
        return None

    async def find_player_across_sports(self, name: str) -> Dict[Sport, Optional[Dict]]:
        """Find a player across all sports."""
        results = {}
        for sport in Sport:
            player = await self.find_player_by_name(name, sport)
            results[sport] = player
        return results

# Convenience functions for quick testing
async def quick_multi_sport_search(api_key: str, player_name: str) -> Dict[Sport, Optional[Dict]]:
    """Quick function to search for a player across all sports."""
    async with BallDontLieClient(api_key) as client:
        return await client.find_player_across_sports(player_name)

async def quick_teams_all_sports(api_key: str) -> Dict[Sport, List[Dict]]:
    """Quick function to fetch teams from all sports."""
    async with BallDontLieClient(api_key) as client:
        return await client.get_all_teams_multi_sport() 