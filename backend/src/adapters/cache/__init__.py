"""
Cache adapters for HoopHead multi-sport API.
Provides multi-layered caching with Redis (hot data) and file system (historical data).
"""

from .redis_client import RedisCache, cache, CacheManager, CacheEntry
from .file_cache import FileCache, file_cache, FileCacheEntry, FileCacheStrategy
from .multi_cache_manager import (
    MultiCacheManager, 
    multi_cache, 
    CacheStrategy, 
    CacheHitInfo, 
    CacheWarming
)

__all__ = [
    # Redis caching
    "RedisCache", 
    "cache", 
    "CacheManager", 
    "CacheEntry",
    
    # File caching
    "FileCache", 
    "file_cache", 
    "FileCacheEntry", 
    "FileCacheStrategy",
    
    # Multi-layered caching
    "MultiCacheManager", 
    "multi_cache", 
    "CacheStrategy", 
    "CacheHitInfo", 
    "CacheWarming"
] 