"""
Ball Don't Lie API client for multi-sport statistics retrieval.
Supports NBA, NFL, MLB, NHL, and EPL leagues with proper routing and caching.
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
import aiohttp
import time
from dataclasses import dataclass
import os

# Add import for our new error handling system
import sys
sys.path.append('/'.join(__file__.split('/')[:-4]))

from core.exceptions import (
    APIConnectionError, APITimeoutError, APIRateLimitError, 
    APIAuthenticationError, APINotFoundError, APIServerError, 
    APIResponseError, ErrorContext
)
from core.error_handler import with_api_error_handling, error_handler

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

# Import authentication manager
try:
    from .auth_manager import auth_manager, APITier, AuthenticationManager
    AUTH_MANAGER_AVAILABLE = True
except ImportError:
    # Fallback if auth manager is not available
    auth_manager = None
    AUTH_MANAGER_AVAILABLE = False
    class APITier:
        FREE = "free"

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
    
    def __init__(self, api_key: Optional[str] = None, enable_cache: bool = True, key_id: Optional[str] = None):
        """Initialize the multi-sport API client with enhanced authentication."""
        # Use authentication manager if available
        if AUTH_MANAGER_AVAILABLE and auth_manager:
            if api_key:
                # Validate and potentially add new API key
                is_valid, existing_key_id, tier = auth_manager.validate_api_key(api_key)
                if not is_valid:
                    raise ValueError(f"Invalid Ball Don't Lie API key format: {api_key[:10]}...")
                
                if not existing_key_id:
                    # Add new key to manager
                    self.key_id = auth_manager.add_api_key(api_key, tier or APITier.FREE)
                else:
                    self.key_id = existing_key_id
            else:
                # Use provided key_id or default
                self.key_id = key_id
                if not self.key_id:
                    # Get default key from manager
                    self.api_key = auth_manager.get_api_key()
                    self.key_id = auth_manager.default_key_id
                    if not self.api_key:
                        raise ValueError(
                            "No valid API key available. "
                            "Add a key using auth_manager.add_api_key() or set BALLDONTLIE_API_KEY environment variable."
                        )
                else:
                    # Get key by ID
                    self.api_key = auth_manager.get_api_key(self.key_id)
                    if not self.api_key:
                        raise ValueError(f"API key with ID {self.key_id} not found or inactive.")
            
            # Get current API key for requests
            self.api_key = auth_manager.get_api_key(self.key_id)
            self.auth_manager = auth_manager
            self.tier_info = auth_manager.get_key_info(self.key_id)
            logger.info(f"Initialized client with {self.tier_info.tier.value if self.tier_info else 'unknown'} tier API key")
        else:
            # Fallback to original behavior
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
            
            self.key_id = None
            self.auth_manager = None
            self.tier_info = None
        
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
        
        # Check tier-based rate limits if authentication manager is available
        if self.auth_manager:
            allowed, rate_limit_info = await self.auth_manager.check_rate_limit(self.key_id)
            if not allowed:
                error_msg = f"Rate limit exceeded for {self.tier_info.tier.value if self.tier_info else 'unknown'} tier"
                raise APIRateLimitError(
                    retry_after=min(
                        rate_limit_info.get('minute_reset', 60) - time.time(),
                        rate_limit_info.get('hourly_reset', 3600) - time.time()
                    ),
                    context=ErrorContext(
                        operation="rate_limit_check",
                        rate_limit_info=rate_limit_info,
                        key_id=self.key_id
                    )
                )
            
            logger.debug(f"Rate limit check passed: {rate_limit_info}")
        
        # Check cache first if enabled (with tier-based cache priority)
        if use_cache and self.cache_enabled and self.redis_cache:
            try:
                cached_response = await self.redis_cache.get(sport, endpoint, params)
                if cached_response:
                    logger.debug(f"Cache HIT for {sport.value}:{endpoint}")
                    # Still record the "request" for usage tracking
                    if self.auth_manager:
                        await self.auth_manager.record_request(self.key_id, success=True)
                    return cached_response
                else:
                    logger.debug(f"Cache MISS for {sport.value}:{endpoint}")
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        # Tier-based rate limiting (more sophisticated than simple delay)
        if self.auth_manager and self.tier_info:
            # Use tier-specific rate limiting
            tier_limits = self.auth_manager.get_tier_limits(self.key_id)
            if tier_limits:
                # Calculate dynamic delay based on tier
                base_delay = 60.0 / tier_limits.requests_per_minute  # Minimum time between requests
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                if time_since_last < base_delay:
                    await asyncio.sleep(base_delay - time_since_last)
        else:
            # Fallback to original rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
        
        # Get sport-specific base URL
        base_url = self._get_base_url(sport)
        url = f"{base_url}/{endpoint.lstrip('/')}"
        
        # Create error context for detailed error tracking
        context = ErrorContext(
            operation="api_request",
            sport=sport.value,
            endpoint=endpoint,
            parameters=params,
            user_agent=self.user_agent
        )
        
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
                        
                        # Record successful request in authentication manager
                        if self.auth_manager:
                            await self.auth_manager.record_request(self.key_id, success=True)
                        
                        # Cache the successful response if enabled
                        if use_cache and self.cache_enabled and self.redis_cache:
                            try:
                                await self.redis_cache.set(sport, endpoint, api_response, params)
                                logger.debug(f"Cached response for {sport.value}:{endpoint}")
                            except Exception as e:
                                logger.warning(f"Cache write error: {e}")
                        
                        return api_response
                        
                    elif response.status == 401:
                        # Record failed authentication in manager
                        if self.auth_manager:
                            await self.auth_manager.record_request(self.key_id, success=False)
                        raise APIAuthenticationError(context=context)
                        
                    elif response.status == 429:
                        retry_after = response.headers.get('Retry-After')
                        retry_seconds = int(retry_after) if retry_after else None
                        if attempt < self.max_retries - 1:
                            sleep_time = retry_seconds or (2 ** attempt)
                            logger.warning(f"Rate limit hit for {sport.value}, retrying in {sleep_time}s...")
                            await asyncio.sleep(sleep_time)
                            continue
                        raise APIRateLimitError(retry_after=retry_seconds, context=context)
                        
                    elif response.status == 404:
                        raise APINotFoundError(resource=f"{sport.value}:{endpoint}", context=context)
                        
                    else:
                        # Handle other HTTP errors
                        response_data = None
                        try:
                            response_data = await response.json()
                        except:
                            pass
                        
                        if 500 <= response.status < 600:
                            # Server errors - retryable
                            if attempt < self.max_retries - 1:
                                logger.warning(f"Server error {response.status} for {sport.value}, retrying...")
                                await asyncio.sleep(1)
                                continue
                            raise APIServerError(
                                status_code=response.status,
                                response_data=response_data,
                                context=context
                            )
                        else:
                            # Client errors - not retryable
                            raise APIServerError(
                                status_code=response.status,
                                response_data=response_data,
                                context=context
                            )
                        
            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request timeout for {sport.value}, retrying...")
                    await asyncio.sleep(1)
                    continue
                raise APITimeoutError(timeout=30.0, context=context)
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Unexpected error for {sport.value}: {e}, retrying...")
                    await asyncio.sleep(1)
                    continue
                raise APIConnectionError(url=url, context=context, original_error=e)
        
        # This should not be reached due to the exceptions above, but safety fallback
        raise APIConnectionError(
            url=url, 
            context=context, 
            original_error=Exception(f"Failed after {self.max_retries} attempts")
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
    
    # Authentication and usage management methods
    def get_authentication_info(self) -> Dict[str, Any]:
        """Get current authentication information and usage stats."""
        if not self.auth_manager:
            return {"auth_manager_enabled": False}
        
        return {
            "auth_manager_enabled": True,
            "current_key_id": self.key_id,
            "usage_stats": self.auth_manager.get_usage_stats(self.key_id),
            "all_keys": self.auth_manager.list_api_keys()
        }
    
    def switch_api_key(self, key_id: str) -> bool:
        """Switch to a different API key."""
        if not self.auth_manager:
            logger.warning("Authentication manager not available")
            return False
        
        new_key = self.auth_manager.get_api_key(key_id)
        if not new_key:
            logger.error(f"API key {key_id} not found or inactive")
            return False
        
        self.key_id = key_id
        self.api_key = new_key
        self.tier_info = self.auth_manager.get_key_info(key_id)
        
        logger.info(f"Switched to API key {key_id} ({self.tier_info.tier.value if self.tier_info else 'unknown'} tier)")
        return True
    
    def add_api_key(self, api_key: str, tier: Optional[str] = None, label: Optional[str] = None) -> Optional[str]:
        """Add a new API key to the authentication manager."""
        if not self.auth_manager:
            logger.warning("Authentication manager not available")
            return None
        
        try:
            tier_enum = APITier(tier) if tier else APITier.FREE
            key_id = self.auth_manager.add_api_key(api_key, tier_enum, label)
            logger.info(f"Added new API key {key_id} with tier {tier_enum.value}")
            return key_id
        except Exception as e:
            logger.error(f"Error adding API key: {e}")
            return None
    
    async def validate_current_key(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate the current API key by making a test request."""
        try:
            # Make a simple test request (get NBA teams with minimal params)
            test_response = await self.get_teams(Sport.NBA, use_cache=False)
            
            validation_result = {
                "valid": test_response.success,
                "key_id": self.key_id,
                "tier": self.tier_info.tier.value if self.tier_info else "unknown",
                "test_endpoint": "teams",
                "response_meta": test_response.meta
            }
            
            if self.auth_manager:
                validation_result["usage_stats"] = self.auth_manager.get_usage_stats(self.key_id)
            
            return test_response.success, validation_result
            
        except APIAuthenticationError:
            return False, {
                "valid": False,
                "error": "Authentication failed - API key may be invalid or expired",
                "key_id": self.key_id
            }
        except Exception as e:
            return False, {
                "valid": False,
                "error": f"Validation failed: {str(e)}",
                "key_id": self.key_id
            }
    
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
async def quick_player_search(search_term: str, api_key: Optional[str] = None, key_id: Optional[str] = None, use_cache: bool = True) -> Dict[Sport, APIResponse]:
    """Quick multi-sport player search with enhanced authentication."""
    async with BallDontLieClient(api_key, enable_cache=use_cache, key_id=key_id) as client:
        return await client.search_players_across_sports(search_term, use_cache=use_cache)


async def quick_teams_all_sports(api_key: Optional[str] = None, key_id: Optional[str] = None, use_cache: bool = True) -> Dict[Sport, APIResponse]:
    """Quick team fetch for all sports with enhanced authentication."""
    async with BallDontLieClient(api_key, enable_cache=use_cache, key_id=key_id) as client:
        return await client.get_all_teams(use_cache=use_cache)


async def validate_api_key_quick(api_key: str) -> Tuple[bool, Dict[str, Any]]:
    """Quick API key validation test."""
    try:
        async with BallDontLieClient(api_key, enable_cache=False) as client:
            return await client.validate_current_key()
    except Exception as e:
        return False, {"valid": False, "error": str(e)} 