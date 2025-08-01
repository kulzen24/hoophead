"""
Cache adapters for HoopHead multi-sport API.
Provides Redis-based caching with sport-specific strategies.
"""

from .redis_client import RedisCache, cache, CacheManager, CacheEntry

__all__ = ["RedisCache", "cache", "CacheManager", "CacheEntry"] 