"""
Redis caching client for Ball Don't Lie API responses.
Implements multi-layered caching with TTL, compression, and sport-specific strategies.
"""
import asyncio
import json
import gzip
import logging
import sys
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict
import redis.asyncio as redis
from datetime import datetime, timedelta
from enum import Enum

try:
    from backend.config.settings import settings
except ImportError:
    # Fallback for when running standalone
    class MockSettings:
        redis_url = "redis://localhost:6379/0"
        cache_ttl = 3600
        def redis_connection_kwargs(self):
            return {'host': 'localhost', 'port': 6379, 'db': 0, 'decode_responses': True}
    settings = MockSettings()

# Import our error handling system
sys.path.append('../../core')
try:
    from core.exceptions import (
        CacheException, CacheConnectionError, CacheTimeoutError, 
        CacheSerializationError, ErrorContext
    )
    from core.error_handler import with_api_error_handling
except ImportError:
    # Fallback if import fails
    class CacheException(Exception): pass
    class CacheConnectionError(Exception): pass
    class CacheTimeoutError(Exception): pass
    class CacheSerializationError(Exception): pass
    class ErrorContext: pass
    def with_api_error_handling(*args, **kwargs): return lambda f: f

logger = logging.getLogger(__name__)


class Sport(str, Enum):
    """Supported sports enum (copied to avoid circular import)."""
    NBA = "nba"
    MLB = "mlb"
    NFL = "nfl"
    NHL = "nhl"
    EPL = "epl"


@dataclass
class CacheEntry:
    """Structure for cached data with metadata."""
    data: Any
    timestamp: str
    sport: str
    endpoint: str
    compressed: bool = False
    hit_count: int = 0


class RedisCache:
    """
    Redis-based caching system for Ball Don't Lie API responses.
    Features:
    - Sport-specific TTL strategies
    - Automatic compression for large responses
    - Cache hit tracking and analytics
    - Intelligent cache invalidation
    - Connection pooling and error handling
    """
    
    def __init__(self):
        """Initialize Redis cache with connection pooling."""
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
        self.enabled = True
        
        # Sport-specific cache TTL strategies (in seconds)
        self.sport_ttl_strategies = {
            Sport.NBA: {
                'teams': 86400,      # Teams change rarely (24 hours)
                'players': 21600,    # Players change occasionally (6 hours)  
                'games': 3600,       # Games change frequently (1 hour)
                'stats': 1800,       # Stats change very frequently (30 min)
                'default': 3600
            },
            Sport.MLB: {
                'teams': 86400,      # Teams stable (24 hours)
                'players': 21600,    # Player trades happen (6 hours)
                'games': 3600,       # Game results update (1 hour)
                'stats': 1800,       # Stats very dynamic (30 min)
                'default': 3600
            },
            Sport.NFL: {
                'teams': 86400,      # Teams very stable (24 hours)
                'players': 43200,    # Less frequent trades (12 hours)
                'games': 7200,       # Weekly games (2 hours)
                'stats': 3600,       # Weekly stats (1 hour)
                'default': 7200
            },
            Sport.NHL: {
                'teams': 86400,      # Teams stable (24 hours)
                'players': 21600,    # Trade deadline activity (6 hours)
                'games': 3600,       # Frequent games (1 hour)
                'stats': 1800,       # High-frequency stats (30 min)
                'default': 3600
            },
            Sport.EPL: {
                'teams': 86400,      # Teams stable (24 hours)
                'players': 43200,    # Transfer windows (12 hours)
                'games': 7200,       # Weekly games (2 hours)
                'stats': 3600,       # Match day stats (1 hour)
                'default': 7200
            }
        }
        
        # Compression threshold (bytes)
        self.compression_threshold = 1024  # 1KB
        
        # Cache key prefixes
        self.key_prefix = "hoophead"
        self.version = "v1"
    
    async def connect(self) -> bool:
        """Establish Redis connection with error handling."""
        try:
            # Get connection parameters from settings
            conn_kwargs = settings.redis_connection_kwargs
            
            # Create connection pool
            self.connection_pool = redis.ConnectionPool(**conn_kwargs)
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis cache connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.enabled = False
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.aclose()
            logger.info("Redis cache disconnected")
    
    def _generate_cache_key(self, sport: Sport, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate a hierarchical cache key."""
        params_str = json.dumps(params or {}, sort_keys=True)
        params_hash = str(hash(params_str))
        return f"{self.key_prefix}:{self.version}:{sport.value}:{endpoint}:{params_hash}"
    
    def _get_ttl_for_endpoint(self, sport: Sport, endpoint: str) -> int:
        """Get sport and endpoint specific TTL."""
        sport_strategy = self.sport_ttl_strategies.get(sport, {})
        return sport_strategy.get(endpoint, sport_strategy.get('default', 3600))
    
    def _should_compress(self, data: bytes) -> bool:
        """Determine if data should be compressed."""
        return len(data) > self.compression_threshold
    
    def _compress_data(self, data: str) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(data.encode('utf-8'))
    
    def _decompress_data(self, data: bytes) -> str:
        """Decompress gzip data."""
        return gzip.decompress(data).decode('utf-8')
    
    async def get(self, sport: Sport, endpoint: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Retrieve cached API response (returns APIResponse-like object)."""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_cache_key(sport, endpoint, params)
            
            # Get cached entry
            cached_data = await self.redis_client.get(cache_key)
            if not cached_data:
                return None
            
            # Handle compressed data
            if isinstance(cached_data, bytes):
                cached_data = self._decompress_data(cached_data)
            
            # Deserialize cache entry
            entry_dict = json.loads(cached_data)
            entry = CacheEntry(**entry_dict)
            
            # Increment hit counter
            entry.hit_count += 1
            await self._update_hit_count(cache_key, entry)
            
            # Return APIResponse-like structure (to avoid circular import)
            api_response = {
                "data": entry.data,
                "success": True,
                "sport": Sport(entry.sport),
                "meta": {"cached": True, "timestamp": entry.timestamp, "hits": entry.hit_count}
            }
            
            logger.debug(f"Cache hit for {sport.value}:{endpoint} (hits: {entry.hit_count})")
            
            # Import here to avoid circular dependency
            try:
                from backend.src.adapters.external.ball_dont_lie_client import APIResponse
                return APIResponse(**api_response)
            except ImportError:
                return api_response
            
        except Exception as e:
            logger.error(f"Cache get error for {sport.value}:{endpoint}: {e}")
            return None
    
    async def set(
        self, 
        sport: Sport, 
        endpoint: str, 
        api_response: Any,  # APIResponse object 
        params: Optional[Dict] = None
    ) -> bool:
        """Store API response in cache."""
        if not self.enabled or not self.redis_client:
            return False
            
        # Check if response is successful (handle both dict and object)
        success = getattr(api_response, 'success', api_response.get('success', False)) if hasattr(api_response, 'get') or hasattr(api_response, 'success') else False
        if not success:
            return False
        
        try:
            cache_key = self._generate_cache_key(sport, endpoint, params)
            
            # Extract data from response (handle both dict and object)
            response_data = getattr(api_response, 'data', api_response.get('data', {})) if hasattr(api_response, 'get') or hasattr(api_response, 'data') else {}
            
            # Create cache entry
            entry = CacheEntry(
                data=response_data,
                timestamp=datetime.utcnow().isoformat(),
                sport=sport.value,
                endpoint=endpoint,
                compressed=False,
                hit_count=0
            )
            
            # Serialize entry
            entry_json = json.dumps(asdict(entry))
            
            # Compress if data is large
            if self._should_compress(entry_json.encode('utf-8')):
                cached_data = self._compress_data(entry_json)
                entry.compressed = True
            else:
                cached_data = entry_json
            
            # Get TTL for this endpoint
            ttl = self._get_ttl_for_endpoint(sport, endpoint)
            
            # Store in cache
            await self.redis_client.setex(cache_key, ttl, cached_data)
            
            logger.debug(f"Cached {sport.value}:{endpoint} for {ttl}s (compressed: {entry.compressed})")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for {sport.value}:{endpoint}: {e}")
            return False
    
    async def _update_hit_count(self, cache_key: str, entry: CacheEntry):
        """Update hit count for analytics."""
        try:
            # Update the entry with new hit count
            entry_json = json.dumps(asdict(entry))
            
            if entry.compressed:
                cached_data = self._compress_data(entry_json)
            else:
                cached_data = entry_json
            
            # Get remaining TTL
            ttl = await self.redis_client.ttl(cache_key)
            if ttl > 0:
                await self.redis_client.setex(cache_key, ttl, cached_data)
                
        except Exception as e:
            logger.error(f"Hit count update error: {e}")
    
    async def invalidate(self, sport: Sport, endpoint: str, params: Optional[Dict] = None):
        """Invalidate specific cache entry."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            cache_key = self._generate_cache_key(sport, endpoint, params)
            await self.redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for {sport.value}:{endpoint}")
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
    
    async def invalidate_sport(self, sport: Sport):
        """Invalidate all cache entries for a specific sport."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            pattern = f"{self.key_prefix}:{self.version}:{sport.value}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for {sport.value}")
                
        except Exception as e:
            logger.error(f"Sport cache invalidation error: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and analytics."""
        if not self.enabled or not self.redis_client:
            return {}
        
        try:
            stats = {
                "total_keys": 0,
                "by_sport": {},
                "memory_usage": "N/A",
                "hit_rates": {}
            }
            
            # Get all cache keys
            pattern = f"{self.key_prefix}:{self.version}:*"
            keys = await self.redis_client.keys(pattern)
            stats["total_keys"] = len(keys)
            
            # Analyze by sport
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 4:
                    sport = parts[2]
                    endpoint = parts[3]
                    
                    if sport not in stats["by_sport"]:
                        stats["by_sport"][sport] = {"endpoints": {}, "total": 0}
                    
                    if endpoint not in stats["by_sport"][sport]["endpoints"]:
                        stats["by_sport"][sport]["endpoints"][endpoint] = 0
                    
                    stats["by_sport"][sport]["endpoints"][endpoint] += 1
                    stats["by_sport"][sport]["total"] += 1
            
            # Get memory info if available
            try:
                info = await self.redis_client.info("memory")
                stats["memory_usage"] = info.get("used_memory_human", "N/A")
            except:
                pass
            
            return stats
            
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {}
    
    async def clear_all(self):
        """Clear all cache entries (use with caution)."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            pattern = f"{self.key_prefix}:{self.version}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.warning(f"Cleared {len(keys)} cache entries")
                
        except Exception as e:
            logger.error(f"Cache clear error: {e}")


# Global cache instance
cache = RedisCache()


# Context manager for cache lifecycle
class CacheManager:
    """Context manager for Redis cache operations."""
    
    async def __aenter__(self):
        """Connect to Redis on entry."""
        await cache.connect()
        return cache
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from Redis on exit."""
        await cache.disconnect() 