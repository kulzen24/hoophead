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

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class League(str, Enum):
    """Supported leagues."""
    NBA = "nba"
    NFL = "nfl"
    MLB = "mlb"
    EPL = "epl"


@dataclass
class APIResponse:
    """Standardized API response structure."""
    data: Any
    success: bool
    error: Optional[str] = None
    league: Optional[League] = None


class BallDontLieClient:
    """
    Unified client for Ball Don't Lie API across all supported sports.
    Handles authentication, rate limiting, and sport-specific endpoints.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = settings.balldontlie_api_base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0
        self.min_request_interval = settings.api_request_delay
        
    async def __aenter__(self):
        """Async context manager entry."""
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "SportsMind/0.1.0"
        }
        
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        league: Optional[League] = None
    ) -> APIResponse:
        """Make a rate-limited HTTP request to the API."""
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
        
        try:
            url = f"{self.base_url}/{endpoint}"
            logger.info(f"Making request to {url} with params: {params}")
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return APIResponse(
                        data=data,
                        success=True,
                        league=league
                    )
                elif response.status == 401:
                    error_msg = "API key authentication failed"
                    logger.error(error_msg)
                    return APIResponse(
                        data=None,
                        success=False,
                        error=error_msg,
                        league=league
                    )
                elif response.status == 429:
                    error_msg = "Rate limit exceeded"
                    logger.warning(error_msg)
                    return APIResponse(
                        data=None,
                        success=False,
                        error=error_msg,
                        league=league
                    )
                else:
                    error_msg = f"API request failed with status {response.status}"
                    logger.error(error_msg)
                    return APIResponse(
                        data=None,
                        success=False,
                        error=error_msg,
                        league=league
                    )
                    
        except asyncio.TimeoutError:
            error_msg = "Request timeout"
            logger.error(error_msg)
            return APIResponse(
                data=None,
                success=False,
                error=error_msg,
                league=league
            )
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return APIResponse(
                data=None,
                success=False,
                error=error_msg,
                league=league
            )
    
    # NBA Endpoints
    async def get_nba_teams(self) -> APIResponse:
        """Get all NBA teams."""
        return await self._make_request("nba/teams", league=League.NBA)
    
    async def get_nba_players(
        self, 
        search: Optional[str] = None,
        team_ids: Optional[List[int]] = None
    ) -> APIResponse:
        """Get NBA players with optional filtering."""
        params = {}
        if search:
            params["search"] = search
        if team_ids:
            params["team_ids[]"] = team_ids
            
        return await self._make_request("nba/players", params, League.NBA)
    
    async def get_nba_games(
        self,
        dates: Optional[List[str]] = None,
        team_ids: Optional[List[int]] = None,
        season: Optional[int] = None
    ) -> APIResponse:
        """Get NBA games with optional filtering."""
        params = {}
        if dates:
            params["dates[]"] = dates
        if team_ids:
            params["team_ids[]"] = team_ids
        if season:
            params["season"] = season
            
        return await self._make_request("nba/games", params, League.NBA)
    
    async def get_nba_stats(
        self,
        player_ids: Optional[List[int]] = None,
        team_ids: Optional[List[int]] = None,
        dates: Optional[List[str]] = None
    ) -> APIResponse:
        """Get NBA statistics."""
        params = {}
        if player_ids:
            params["player_ids[]"] = player_ids
        if team_ids:
            params["team_ids[]"] = team_ids
        if dates:
            params["dates[]"] = dates
            
        return await self._make_request("nba/stats", params, League.NBA)
    
    # NFL Endpoints
    async def get_nfl_teams(self) -> APIResponse:
        """Get all NFL teams."""
        return await self._make_request("nfl/teams", league=League.NFL)
    
    async def get_nfl_players(
        self,
        search: Optional[str] = None,
        team_ids: Optional[List[int]] = None
    ) -> APIResponse:
        """Get NFL players with optional filtering."""
        params = {}
        if search:
            params["search"] = search
        if team_ids:
            params["team_ids[]"] = team_ids
            
        return await self._make_request("nfl/players", params, League.NFL)
    
    async def get_nfl_games(
        self,
        dates: Optional[List[str]] = None,
        team_ids: Optional[List[int]] = None,
        season: Optional[int] = None
    ) -> APIResponse:
        """Get NFL games with optional filtering."""
        params = {}
        if dates:
            params["dates[]"] = dates
        if team_ids:
            params["team_ids[]"] = team_ids
        if season:
            params["season"] = season
            
        return await self._make_request("nfl/games", params, League.NFL)
    
    # MLB Endpoints
    async def get_mlb_teams(self) -> APIResponse:
        """Get all MLB teams."""
        return await self._make_request("mlb/teams", league=League.MLB)
    
    async def get_mlb_players(
        self,
        search: Optional[str] = None,
        team_ids: Optional[List[int]] = None
    ) -> APIResponse:
        """Get MLB players with optional filtering."""
        params = {}
        if search:
            params["search"] = search
        if team_ids:
            params["team_ids[]"] = team_ids
            
        return await self._make_request("mlb/players", params, League.MLB)
    
    # EPL Endpoints
    async def get_epl_teams(self) -> APIResponse:
        """Get all EPL teams/clubs."""
        return await self._make_request("epl/teams", league=League.EPL)
    
    async def get_epl_players(
        self,
        search: Optional[str] = None,
        team_ids: Optional[List[int]] = None
    ) -> APIResponse:
        """Get EPL players with optional filtering."""
        params = {}
        if search:
            params["search"] = search
        if team_ids:
            params["team_ids[]"] = team_ids
            
        return await self._make_request("epl/players", params, League.EPL)
    
    # Unified Multi-Sport Methods
    async def search_players_across_leagues(
        self, 
        search_term: str,
        leagues: Optional[List[League]] = None
    ) -> Dict[League, APIResponse]:
        """Search for players across multiple leagues."""
        if leagues is None:
            leagues = [League.NBA, League.NFL, League.MLB, League.EPL]
        
        results = {}
        
        for league in leagues:
            if league == League.NBA:
                results[league] = await self.get_nba_players(search=search_term)
            elif league == League.NFL:
                results[league] = await self.get_nfl_players(search=search_term)
            elif league == League.MLB:
                results[league] = await self.get_mlb_players(search=search_term)
            elif league == League.EPL:
                results[league] = await self.get_epl_players(search=search_term)
        
        return results
    
    async def get_all_teams(self) -> Dict[League, APIResponse]:
        """Get teams from all supported leagues."""
        results = {}
        
        tasks = [
            (League.NBA, self.get_nba_teams()),
            (League.NFL, self.get_nfl_teams()),
            (League.MLB, self.get_mlb_teams()),
            (League.EPL, self.get_epl_teams())
        ]
        
        for league, task in tasks:
            results[league] = await task
        
        return results


# Convenience functions for quick access
async def quick_player_search(api_key: str, player_name: str) -> Dict[League, APIResponse]:
    """Quick function to search for a player across all leagues."""
    async with BallDontLieClient(api_key) as client:
        return await client.search_players_across_leagues(player_name)


async def quick_teams_fetch(api_key: str) -> Dict[League, APIResponse]:
    """Quick function to fetch teams from all leagues."""
    async with BallDontLieClient(api_key) as client:
        return await client.get_all_teams() 