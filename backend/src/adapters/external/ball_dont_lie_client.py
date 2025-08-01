"""
Ball Don't Lie API client for multi-sport statistics retrieval.
Supports NBA, NFL, MLB, NHL, and EPL leagues with proper routing and caching.
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import aiohttp
import time
from dataclasses import dataclass
import os

try:
    from backend.config.settings import settings
except ImportError:
    # Fallback for when running standalone
    class MockSettings:
        balldontlie_api_key = ""
        api_request_delay = 0.6
        max_retries = 3
        api_user_agent = "HoopHead/0.1.0"
        
        @property
        def sport_base_urls(self):
            return {
                "nba": "https://api.balldontlie.io/v1",
                "mlb": "https://api.balldontlie.io/mlb/v1", 
                "nfl": "https://api.balldontlie.io/nfl/v1",
                "nhl": "https://api.balldontlie.io/nhl/v1",
                "epl": "https://api.balldontlie.io/epl/v1"
            }
    settings = MockSettings()

# Optional Redis cache import
try:
    from backend.src.adapters.cache.redis_client import cache as redis_cache
    REDIS_AVAILABLE = True
except ImportError:
    redis_cache = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class Sport(str, Enum):
    """Supported sports with their API configurations."""
    NBA = "nba"
    MLB = "mlb"
    NFL = "nfl"
    NHL = "nhl"
    EPL = "epl"


@dataclass
class APIResponse:
    """Standardized API response structure."""
    data: Any
    success: bool
    error: Optional[str] = None
    sport: Optional[Sport] = None
    meta: Optional[Dict] = None


class BallDontLieClient:
    """
    Unified multi-sport client for Ball Don't Lie API.
    Handles authentication, rate limiting, caching, and sport-specific routing.
    """
    
    def __init__(self, api_key: Optional[str] = None, enable_cache: bool = True):
        """Initialize the multi-sport API client."""
        # Get API key from parameter, settings, or environment
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = (
                getattr(settings, 'balldontlie_api_key', '') or 
                os.getenv('BALLDONTLIE_API_KEY', '')
            )
        
        if not self.api_key:
            raise ValueError(
                "Ball Don't Lie API key is required. "
                "Provide it as parameter or set BALLDONTLIE_API_KEY environment variable."
            )
        
        # Get sport-specific base URLs from settings
        self.sport_base_urls = getattr(settings, 'sport_base_urls', {
            "nba": "https://api.balldontlie.io/v1",
            "mlb": "https://api.balldontlie.io/mlb/v1",
            "nfl": "https://api.balldontlie.io/nfl/v1", 
            "nhl": "https://api.balldontlie.io/nhl/v1",
            "epl": "https://api.balldontlie.io/epl/v1"
        })
        
        # Configuration from settings
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0
        self.min_request_interval = getattr(settings, 'api_request_delay', 0.6)
        self.max_retries = getattr(settings, 'max_retries', 3)
        self.user_agent = getattr(settings, 'api_user_agent', 'HoopHead/0.1.0')
        
        # Cache configuration
        self.cache_enabled = enable_cache and REDIS_AVAILABLE
        self.cache_ttl = getattr(settings, 'cache_ttl', 3600)
        self.redis_cache = redis_cache if self.cache_enabled else None
        
        if self.cache_enabled:
            logger.info("Redis cache enabled for Ball Don't Lie client")
        else:
            logger.info("Redis cache disabled or unavailable")
        
    async def __aenter__(self):
        """Async context manager entry."""
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": self.user_agent
        }
        
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=timeout
        )
        
        # Initialize Redis cache if enabled
        if self.cache_enabled and self.redis_cache:
            await self.redis_cache.connect()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        
        # Disconnect Redis cache if enabled
        if self.cache_enabled and self.redis_cache:
            await self.redis_cache.disconnect()
    
    def _get_base_url(self, sport: Sport) -> str:
        """Get the base URL for a specific sport."""
        return self.sport_base_urls.get(sport.value, self.sport_base_urls["nba"])
    
    def _generate_cache_key(self, sport: Sport, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate a cache key for the request."""
        params_str = json.dumps(params or {}, sort_keys=True)
        return f"bdl:{sport.value}:{endpoint}:{hash(params_str)}"
    
    async def _make_request(
        self, 
        sport: Sport,
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> APIResponse:
        """Make a rate-limited HTTP request to the sport-specific API with caching."""
        
        # Check cache first if enabled
        if use_cache and self.cache_enabled and self.redis_cache:
            try:
                cached_response = await self.redis_cache.get(sport, endpoint, params)
                if cached_response:
                    logger.debug(f"Cache HIT for {sport.value}:{endpoint}")
                    return cached_response
                else:
                    logger.debug(f"Cache MISS for {sport.value}:{endpoint}")
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
        
        # Get sport-specific base URL
        base_url = self._get_base_url(sport)
        url = f"{base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Making request to {url} (attempt {attempt + 1}) with params: {params}")
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        api_response = APIResponse(
                            data=data,
                            success=True,
                            sport=sport,
                            meta={
                                "cached": False,
                                "request_url": url,
                                "attempt": attempt + 1,
                                **(data.get('meta', {}) if isinstance(data, dict) else {})
                            }
                        )
                        
                        # Cache the successful response if enabled
                        if use_cache and self.cache_enabled and self.redis_cache:
                            try:
                                await self.redis_cache.set(sport, endpoint, api_response, params)
                                logger.debug(f"Cached response for {sport.value}:{endpoint}")
                            except Exception as e:
                                logger.warning(f"Cache write error: {e}")
                        
                        return api_response
                        
                    elif response.status == 401:
                        error_msg = "API key authentication failed"
                        logger.error(f"{error_msg} for {sport.value}")
                        return APIResponse(data=None, success=False, error=error_msg, sport=sport)
                        
                    elif response.status == 429:
                        error_msg = "Rate limit exceeded"
                        logger.warning(f"{error_msg} for {sport.value}, retrying...")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        return APIResponse(data=None, success=False, error=error_msg, sport=sport)
                        
                    elif response.status == 404:
                        error_msg = f"Endpoint {endpoint} not found for {sport.value}"
                        logger.warning(error_msg)
                        return APIResponse(data=None, success=False, error=error_msg, sport=sport)
                        
                    else:
                        error_msg = f"HTTP {response.status} error"
                        logger.error(f"{error_msg} for {sport.value}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(1)
                            continue
                        return APIResponse(data=None, success=False, error=error_msg, sport=sport)
                        
            except asyncio.TimeoutError:
                error_msg = "Request timeout"
                logger.error(f"{error_msg} for {sport.value}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                return APIResponse(data=None, success=False, error=error_msg, sport=sport)
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(f"{error_msg} for {sport.value}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                return APIResponse(data=None, success=False, error=error_msg, sport=sport)
        
        return APIResponse(
            data=None, 
            success=False, 
            error=f"Failed after {self.max_retries} attempts",
            sport=sport
        )
    
    # Sport-specific methods
    async def get_teams(self, sport: Sport, use_cache: bool = True) -> APIResponse:
        """Get all teams for a specific sport."""
        return await self._make_request(sport, "teams", use_cache=use_cache)
    
    async def get_players(self, sport: Sport, search: Optional[str] = None, use_cache: bool = True, **kwargs) -> APIResponse:
        """Get players for a specific sport with optional search."""
        params = {}
        if search:
            params["search"] = search
        params.update(kwargs)
        return await self._make_request(sport, "players", params, use_cache=use_cache)
    
    async def get_games(self, sport: Sport, use_cache: bool = True, **kwargs) -> APIResponse:
        """Get games for a specific sport."""
        return await self._make_request(sport, "games", kwargs, use_cache=use_cache)
    
    async def get_stats(self, sport: Sport, use_cache: bool = True, **kwargs) -> APIResponse:
        """Get stats for a specific sport."""
        return await self._make_request(sport, "stats", kwargs, use_cache=use_cache)
    
    # Cache management methods
    async def invalidate_cache(self, sport: Sport, endpoint: str, params: Optional[Dict] = None):
        """Invalidate specific cache entry."""
        if self.cache_enabled and self.redis_cache:
            await self.redis_cache.invalidate(sport, endpoint, params)
    
    async def invalidate_sport_cache(self, sport: Sport):
        """Invalidate all cache entries for a specific sport."""
        if self.cache_enabled and self.redis_cache:
            await self.redis_cache.invalidate_sport(sport)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.cache_enabled and self.redis_cache:
            return await self.redis_cache.get_cache_stats()
        return {"cache_enabled": False}
    
    # Multi-sport convenience methods
    async def search_players_across_sports(
        self, 
        search_term: str, 
        sports: Optional[List[Sport]] = None,
        use_cache: bool = True
    ) -> Dict[Sport, APIResponse]:
        """Search for players across multiple sports."""
        if sports is None:
            sports = list(Sport)
        
        results = {}
        tasks = []
        
        for sport in sports:
            task = self.get_players(sport, search=search_term, use_cache=use_cache)
            tasks.append((sport, task))
        
        # Execute all searches concurrently
        for sport, task in tasks:
            try:
                result = await task
                results[sport] = result
            except Exception as e:
                logger.error(f"Error searching {sport.value}: {e}")
                results[sport] = APIResponse(
                    data=None, 
                    success=False, 
                    error=str(e),
                    sport=sport
                )
        
        return results
    
    async def get_all_teams(self, use_cache: bool = True) -> Dict[Sport, APIResponse]:
        """Get teams from all sports."""
        results = {}
        tasks = []
        
        for sport in Sport:
            task = self.get_teams(sport, use_cache=use_cache)
            tasks.append((sport, task))
        
        # Execute all requests concurrently
        for sport, task in tasks:
            try:
                result = await task
                results[sport] = result
            except Exception as e:
                logger.error(f"Error getting teams for {sport.value}: {e}")
                results[sport] = APIResponse(
                    data=None,
                    success=False, 
                    error=str(e),
                    sport=sport
                )
        
        return results


# Convenience functions for quick testing
async def quick_player_search(search_term: str, api_key: Optional[str] = None, use_cache: bool = True) -> Dict[Sport, APIResponse]:
    """Quick multi-sport player search."""
    async with BallDontLieClient(api_key, enable_cache=use_cache) as client:
        return await client.search_players_across_sports(search_term, use_cache=use_cache)


async def quick_teams_all_sports(api_key: Optional[str] = None, use_cache: bool = True) -> Dict[Sport, APIResponse]:
    """Quick team fetch for all sports."""
    async with BallDontLieClient(api_key, enable_cache=use_cache) as client:
        return await client.get_all_teams(use_cache=use_cache) 