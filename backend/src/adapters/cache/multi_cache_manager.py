"""
Multi-layered cache manager for HoopHead sports API.
Orchestrates Redis (hot data) and file caching (historical data) with tier-based prioritization.
"""
import asyncio
import logging
import time
import hashlib
from typing import Any, Dict, Optional, List, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

# Import cache layers
try:
    from .redis_client import cache as redis_cache, Sport, CacheEntry as RedisCacheEntry
    from .file_cache import file_cache, FileCacheStrategy, FileCacheEntry
    REDIS_AVAILABLE = True
except ImportError:
    redis_cache = None
    file_cache = None
    REDIS_AVAILABLE = False
    class Sport(str, Enum):
        NBA = "nba"
        MLB = "mlb"
        NFL = "nfl"
        NHL = "nhl"
        EPL = "epl"

# Import authentication for tier-based features
try:
    from backend.src.adapters.external.auth_manager import APITier, TierLimits
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    class APITier(str, Enum):
        FREE = "free"
        ALL_STAR = "all-star"
        GOAT = "goat"
        ENTERPRISE = "enterprise"

try:
    from core.exceptions import CacheException, CacheConnectionError
except ImportError:
    class CacheException(Exception): pass
    class CacheConnectionError(Exception): pass

logger = logging.getLogger(__name__)


@dataclass
class CacheHitInfo:
    """Information about cache hit location and performance."""
    hit: bool
    source: str  # 'redis', 'file', 'none'
    latency_ms: float
    data_age_seconds: float
    tier_priority: int = 1


@dataclass 
class CacheWarming:
    """Configuration for cache warming strategies."""
    enabled: bool = True
    popular_queries_limit: int = 100
    warming_schedule_hours: List[int] = None  # Hours to warm cache (0-23)
    min_hit_count: int = 5  # Minimum hits to consider query popular


class CacheStrategy(str, Enum):
    """Cache strategy selection."""
    REDIS_ONLY = "redis_only"           # Fast access, no persistence
    FILE_ONLY = "file_only"             # Persistent, slower access  
    LAYERED = "layered"                 # Redis first, fallback to file
    HISTORICAL = "historical"           # File cache for long-term data
    TIER_OPTIMIZED = "tier_optimized"   # Strategy based on authentication tier


class MultiCacheManager:
    """
    Multi-layered cache manager with tier-based optimization.
    
    Features:
    - Redis for hot data (fast access)
    - File cache for historical data (persistent storage)
    - Tier-based cache prioritization
    - Cache warming for popular queries
    - Smart invalidation strategies
    - Comprehensive analytics
    """
    
    def __init__(self, warming_config: Optional[CacheWarming] = None):
        """Initialize multi-layered cache manager."""
        self.redis_cache = redis_cache
        self.file_cache = file_cache
        self.enabled = REDIS_AVAILABLE or file_cache is not None
        
        # Cache warming configuration
        self.warming_config = warming_config or CacheWarming()
        if self.warming_config.warming_schedule_hours is None:
            # Default warming at 6 AM, 12 PM, 6 PM
            self.warming_config.warming_schedule_hours = [6, 12, 18]
        
        # Popular queries tracking
        self.popular_queries: Dict[str, Dict] = {}
        self.query_access_log: List[Dict] = []
        
        # Tier-based strategies
        self.tier_strategies = {
            APITier.FREE: {
                'redis_priority': False,
                'file_cache_enabled': True,
                'warming_enabled': False,
                'ttl_multiplier': 1.0
            },
            APITier.ALL_STAR: {
                'redis_priority': True,
                'file_cache_enabled': True,
                'warming_enabled': True,
                'ttl_multiplier': 1.2
            },
            APITier.GOAT: {
                'redis_priority': True,
                'file_cache_enabled': True,
                'warming_enabled': True,
                'ttl_multiplier': 1.5
            },
            APITier.ENTERPRISE: {
                'redis_priority': True,
                'file_cache_enabled': True,
                'warming_enabled': True,
                'ttl_multiplier': 2.0
            }
        }
        
        # Analytics
        self.analytics = {
            'total_requests': 0,
            'redis_hits': 0,
            'file_hits': 0,
            'cache_misses': 0,
            'tier_breakdown': {},
            'average_latency_ms': 0,
            'warming_cycles': 0
        }
        
        logger.info(f"Multi-cache manager initialized (Redis: {self.redis_cache is not None}, File: {self.file_cache is not None})")
    
    def _generate_query_key(self, sport: Sport, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate a consistent query key for tracking."""
        params_str = str(sorted((params or {}).items()))
        return f"{sport.value}:{endpoint}:{hashlib.md5(params_str.encode()).hexdigest()[:8]}"
    
    def _determine_cache_strategy(
        self, 
        tier: Optional[APITier] = None,
        endpoint: Optional[str] = None,
        force_strategy: Optional[CacheStrategy] = None
    ) -> CacheStrategy:
        """Determine optimal cache strategy based on tier and data type."""
        if force_strategy:
            return force_strategy
        
        # Historical data endpoints should use file cache
        historical_endpoints = {'historical_stats', 'season_stats', 'career_stats', 'archives'}
        if endpoint and any(hist in endpoint for hist in historical_endpoints):
            return CacheStrategy.HISTORICAL
        
        # Tier-based strategy selection
        if tier and AUTH_AVAILABLE:
            tier_config = self.tier_strategies.get(tier, self.tier_strategies[APITier.FREE])
            if tier_config['redis_priority']:
                return CacheStrategy.LAYERED
            else:
                return CacheStrategy.FILE_ONLY
        
        # Default to layered if both caches available
        if self.redis_cache and self.file_cache:
            return CacheStrategy.LAYERED
        elif self.redis_cache:
            return CacheStrategy.REDIS_ONLY
        elif self.file_cache:
            return CacheStrategy.FILE_ONLY
        
        # Fallback (should not happen if caches are available)
        return CacheStrategy.REDIS_ONLY
    
    def _get_file_cache_strategy(self, endpoint: str) -> FileCacheStrategy:
        """Map API endpoint to file cache strategy."""
        if 'historical' in endpoint or 'career' in endpoint:
            return FileCacheStrategy.HISTORICAL
        elif 'season' in endpoint:
            return FileCacheStrategy.SEASONAL
        elif 'daily' in endpoint or 'today' in endpoint:
            return FileCacheStrategy.DAILY
        else:
            return FileCacheStrategy.TRANSIENT
    
    async def get(
        self, 
        sport: Sport, 
        endpoint: str, 
        params: Optional[Dict] = None,
        tier: Optional[APITier] = None,
        strategy: Optional[CacheStrategy] = None
    ) -> Tuple[Optional[Any], CacheHitInfo]:
        """
        Retrieve data from multi-layered cache with tier-based optimization.
        Returns (data, hit_info) tuple.
        """
        start_time = time.time()
        query_key = self._generate_query_key(sport, endpoint, params)
        
        # Track query for popularity analysis
        self._track_query_access(query_key, sport, endpoint, params, tier)
        
        # Determine cache strategy
        cache_strategy = self._determine_cache_strategy(tier, endpoint, strategy)
        tier_priority = getattr(tier, 'value', 1) if tier else 1
        
        # Update analytics
        self.analytics['total_requests'] += 1
        if tier:
            tier_key = tier.value
            if tier_key not in self.analytics['tier_breakdown']:
                self.analytics['tier_breakdown'][tier_key] = {'requests': 0, 'hits': 0}
            self.analytics['tier_breakdown'][tier_key]['requests'] += 1
        
        # Try cache layers based on strategy
        if cache_strategy in [CacheStrategy.REDIS_ONLY, CacheStrategy.LAYERED, CacheStrategy.TIER_OPTIMIZED]:
            # Try Redis first
            if self.redis_cache:
                try:
                    redis_data = await self.redis_cache.get(sport, endpoint, params)
                    if redis_data:
                        latency_ms = (time.time() - start_time) * 1000
                        self.analytics['redis_hits'] += 1
                        if tier:
                            self.analytics['tier_breakdown'][tier.value]['hits'] += 1
                        
                        # Calculate data age from metadata
                        data_age = 0
                        if hasattr(redis_data, 'meta') and redis_data.meta and 'timestamp' in redis_data.meta:
                            cache_time = datetime.fromisoformat(redis_data.meta['timestamp'])
                            data_age = (datetime.utcnow() - cache_time).total_seconds()
                        
                        return redis_data.data if hasattr(redis_data, 'data') else redis_data, CacheHitInfo(
                            hit=True,
                            source='redis',
                            latency_ms=latency_ms,
                            data_age_seconds=data_age,
                            tier_priority=tier_priority
                        )
                except Exception as e:
                    logger.error(f"Redis cache error: {e}")
        
        # Try file cache (for LAYERED, FILE_ONLY, or HISTORICAL strategies)
        if cache_strategy in [CacheStrategy.FILE_ONLY, CacheStrategy.LAYERED, CacheStrategy.HISTORICAL]:
            if self.file_cache:
                try:
                    file_strategy = self._get_file_cache_strategy(endpoint)
                    file_data = await self.file_cache.get(sport, endpoint, params, file_strategy)
                    if file_data:
                        latency_ms = (time.time() - start_time) * 1000
                        self.analytics['file_hits'] += 1
                        if tier:
                            self.analytics['tier_breakdown'][tier.value]['hits'] += 1
                        
                        # For file cache, data age is harder to determine precisely
                        # We'll use a rough estimate
                        data_age = 300  # Assume 5 minutes average age for file cache
                        
                        return file_data, CacheHitInfo(
                            hit=True,
                            source='file',
                            latency_ms=latency_ms,
                            data_age_seconds=data_age,
                            tier_priority=tier_priority
                        )
                except Exception as e:
                    logger.error(f"File cache error: {e}")
        
        # Cache miss
        latency_ms = (time.time() - start_time) * 1000
        self.analytics['cache_misses'] += 1
        
        return None, CacheHitInfo(
            hit=False,
            source='none',
            latency_ms=latency_ms,
            data_age_seconds=0,
            tier_priority=tier_priority
        )
    
    async def set(
        self, 
        sport: Sport, 
        endpoint: str, 
        data: Any,
        params: Optional[Dict] = None,
        tier: Optional[APITier] = None,
        strategy: Optional[CacheStrategy] = None,
        api_response: Optional[Any] = None
    ) -> Tuple[bool, bool]:
        """
        Store data in appropriate cache layers.
        Returns (redis_success, file_success) tuple.
        """
        cache_strategy = self._determine_cache_strategy(tier, endpoint, strategy)
        tier_priority = getattr(tier, 'value', 1) if tier else 1
        
        redis_success = False
        file_success = False
        
        # Store in Redis for hot data
        if cache_strategy in [CacheStrategy.REDIS_ONLY, CacheStrategy.LAYERED, CacheStrategy.TIER_OPTIMIZED]:
            if self.redis_cache:
                try:
                    # Use the API response if provided, otherwise create a mock response
                    response_obj = api_response or {
                        'data': data,
                        'success': True,
                        'sport': sport,
                        'meta': {'cached': False, 'timestamp': datetime.utcnow().isoformat()}
                    }
                    redis_success = await self.redis_cache.set(sport, endpoint, response_obj, params)
                except Exception as e:
                    logger.error(f"Redis cache set error: {e}")
        
        # Store in file cache for persistence
        if cache_strategy in [CacheStrategy.FILE_ONLY, CacheStrategy.LAYERED, CacheStrategy.HISTORICAL]:
            if self.file_cache:
                try:
                    file_strategy = self._get_file_cache_strategy(endpoint)
                    file_success = await self.file_cache.set(
                        sport, endpoint, data, params, file_strategy, tier_priority
                    )
                except Exception as e:
                    logger.error(f"File cache set error: {e}")
        
        return redis_success, file_success
    
    def _track_query_access(
        self, 
        query_key: str, 
        sport: Sport, 
        endpoint: str, 
        params: Optional[Dict], 
        tier: Optional[APITier]
    ):
        """Track query access for popularity analysis."""
        current_time = datetime.utcnow()
        
        # Update popular queries tracking
        if query_key not in self.popular_queries:
            self.popular_queries[query_key] = {
                'sport': sport.value,
                'endpoint': endpoint,
                'params': params,
                'hit_count': 0,
                'first_access': current_time.isoformat(),
                'last_access': current_time.isoformat(),
                'tier_users': set()
            }
        
        query_info = self.popular_queries[query_key]
        query_info['hit_count'] += 1
        query_info['last_access'] = current_time.isoformat()
        if tier:
            query_info['tier_users'].add(tier.value)
        
        # Keep recent access log (limit size)
        self.query_access_log.append({
            'query_key': query_key,
            'timestamp': current_time.isoformat(),
            'tier': tier.value if tier else 'unknown'
        })
        
        # Trim access log to last 10000 entries
        if len(self.query_access_log) > 10000:
            self.query_access_log = self.query_access_log[-10000:]
    
    async def warm_cache(self, tier: Optional[APITier] = None, force: bool = False):
        """
        Warm cache with popular queries.
        Can be tier-specific or global.
        """
        if not self.warming_config.enabled and not force:
            logger.debug("Cache warming is disabled")
            return
        
        current_hour = datetime.now().hour
        if not force and current_hour not in self.warming_config.warming_schedule_hours:
            logger.debug(f"Cache warming not scheduled for hour {current_hour}")
            return
        
        logger.info(f"Starting cache warming (tier: {tier.value if tier else 'all'})")
        warming_start = time.time()
        
        # Get popular queries to warm
        popular_queries = self._get_popular_queries_for_warming(tier)
        
        warmed_count = 0
        for query_info in popular_queries:
            try:
                sport = Sport(query_info['sport'])
                endpoint = query_info['endpoint']
                params = query_info['params']
                
                # Check if already cached (don't re-warm)
                cached_data, hit_info = await self.get(sport, endpoint, params, tier)
                if not hit_info.hit:
                    # Data not in cache, this would be a good candidate for warming
                    # In a real implementation, you'd fetch from API here
                    logger.debug(f"Would warm cache for {sport.value}:{endpoint}")
                
                warmed_count += 1
                
            except Exception as e:
                logger.error(f"Error warming cache for query: {e}")
        
        warming_duration = time.time() - warming_start
        self.analytics['warming_cycles'] += 1
        
        logger.info(
            f"Cache warming completed: {warmed_count} queries processed in {warming_duration:.2f}s"
        )
    
    def _get_popular_queries_for_warming(self, tier: Optional[APITier] = None) -> List[Dict]:
        """Get list of popular queries for cache warming."""
        # Filter queries by tier if specified
        candidates = []
        for query_key, query_info in self.popular_queries.items():
            if query_info['hit_count'] >= self.warming_config.min_hit_count:
                if tier is None or tier.value in query_info.get('tier_users', set()):
                    candidates.append(query_info)
        
        # Sort by hit count descending
        candidates.sort(key=lambda x: x['hit_count'], reverse=True)
        
        # Return top N queries
        return candidates[:self.warming_config.popular_queries_limit]
    
    async def invalidate(
        self, 
        sport: Optional[Sport] = None, 
        endpoint: Optional[str] = None,
        params: Optional[Dict] = None,
        strategy: Optional[CacheStrategy] = None
    ):
        """
        Invalidate cache entries across layers.
        """
        logger.info(f"Invalidating cache for sport: {sport}, endpoint: {endpoint}")
        
        # Determine which caches to invalidate
        if strategy is None:
            # Invalidate both layers by default
            redis_invalidate = True
            file_invalidate = True
        elif strategy == CacheStrategy.REDIS_ONLY:
            redis_invalidate = True
            file_invalidate = False
        elif strategy == CacheStrategy.FILE_ONLY:
            redis_invalidate = False
            file_invalidate = True
        else:
            redis_invalidate = True
            file_invalidate = True
        
        # Invalidate Redis cache
        if redis_invalidate and self.redis_cache:
            try:
                if sport and endpoint:
                    await self.redis_cache.invalidate(sport, endpoint, params)
                elif sport:
                    await self.redis_cache.invalidate_sport(sport)
                else:
                    logger.warning("Redis cache invalidation requires at least sport parameter")
            except Exception as e:
                logger.error(f"Redis cache invalidation error: {e}")
        
        # Invalidate file cache
        if file_invalidate and self.file_cache:
            try:
                file_strategy = self._get_file_cache_strategy(endpoint) if endpoint else None
                await self.file_cache.invalidate(sport, endpoint, file_strategy)
            except Exception as e:
                logger.error(f"File cache invalidation error: {e}")
    
    async def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics from all cache layers."""
        analytics = {
            'multi_cache_manager': self.analytics,
            'popular_queries': len(self.popular_queries),
            'warming_config': {
                'enabled': self.warming_config.enabled,
                'schedule_hours': self.warming_config.warming_schedule_hours,
                'min_hit_count': self.warming_config.min_hit_count
            }
        }
        
        # Add Redis analytics
        if self.redis_cache:
            try:
                redis_stats = await self.redis_cache.get_cache_stats()
                analytics['redis_cache'] = redis_stats
            except Exception as e:
                logger.error(f"Error getting Redis analytics: {e}")
        
        # Add file cache analytics
        if self.file_cache:
            try:
                file_stats = await self.file_cache.get_analytics()
                analytics['file_cache'] = file_stats
            except Exception as e:
                logger.error(f"Error getting file cache analytics: {e}")
        
        return analytics
    
    async def cleanup_all_caches(self):
        """Perform cleanup on all cache layers."""
        logger.info("Starting comprehensive cache cleanup")
        
        # File cache cleanup (Redis cleanup is automatic via TTL)
        if self.file_cache:
            try:
                await self.file_cache._cleanup_old_files()
            except Exception as e:
                logger.error(f"File cache cleanup error: {e}")
        
        # Clean up popular queries tracking (keep only recent data)
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(days=30)  # Keep 30 days of history
        
        queries_to_remove = []
        for query_key, query_info in self.popular_queries.items():
            last_access = datetime.fromisoformat(query_info['last_access'])
            if last_access < cutoff_time:
                queries_to_remove.append(query_key)
        
        for query_key in queries_to_remove:
            del self.popular_queries[query_key]
        
        logger.info(f"Cache cleanup completed, removed {len(queries_to_remove)} old queries")


# Global multi-cache manager instance
multi_cache = MultiCacheManager() 