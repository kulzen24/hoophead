"""
Local file caching system for historical sports data.
Complements Redis cache with persistent storage for historical queries.
"""
import os
import json
import gzip
import pickle
import hashlib
import logging
import aiofiles
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import asyncio

# Import our Sport enum and error handling
try:
    from backend.src.adapters.cache.redis_client import Sport
except ImportError:
    class Sport(str, Enum):
        NBA = "nba"
        MLB = "mlb" 
        NFL = "nfl"
        NHL = "nhl"
        EPL = "epl"

try:
    from core.exceptions import CacheException, CacheSerializationError
except ImportError:
    class CacheException(Exception): pass
    class CacheSerializationError(Exception): pass

logger = logging.getLogger(__name__)


@dataclass
class FileCacheEntry:
    """Structure for file cached data with metadata."""
    data: Any
    timestamp: str
    sport: str
    endpoint: str
    params_hash: str
    access_count: int = 0
    last_accessed: str = ""
    file_size: int = 0
    compressed: bool = False
    tier_priority: int = 1


class FileCacheStrategy(str, Enum):
    """Cache strategies for different data types."""
    HISTORICAL = "historical"  # Long-term storage, rarely invalidated
    SEASONAL = "seasonal"      # Season-long data, invalidated yearly
    DAILY = "daily"           # Daily data, invalidated daily
    TRANSIENT = "transient"   # Short-term backup for Redis misses


class FileCache:
    """
    Local file caching system for historical sports data.
    Features:
    - Hierarchical directory structure by sport/endpoint/date
    - Automatic compression for large datasets
    - Configurable retention policies
    - Analytics and cleanup routines
    - Tier-based storage prioritization
    """
    
    def __init__(self, cache_dir: str = ".cache/hoophead", max_size_gb: float = 5.0):
        """Initialize file cache with configurable storage."""
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)  # Convert GB to bytes
        self.compression_threshold = 5 * 1024  # 5KB threshold for compression
        
        # Create cache directory structure
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        for sport in Sport:
            (self.cache_dir / sport.value).mkdir(exist_ok=True)
        
        # Retention policies by cache strategy (in days)
        self.retention_policies = {
            FileCacheStrategy.HISTORICAL: 365,  # 1 year
            FileCacheStrategy.SEASONAL: 180,    # 6 months
            FileCacheStrategy.DAILY: 30,        # 1 month
            FileCacheStrategy.TRANSIENT: 7      # 1 week
        }
        
        # File cache analytics
        self.analytics = {
            "total_files": 0,
            "total_size": 0,
            "hit_count": 0,
            "miss_count": 0,
            "by_sport": {},
            "by_strategy": {}
        }
        
        logger.info(f"File cache initialized at {self.cache_dir} with {max_size_gb}GB limit")
    
    def _get_file_path(
        self, 
        sport: Sport, 
        endpoint: str, 
        params: Optional[Dict] = None,
        strategy: FileCacheStrategy = FileCacheStrategy.TRANSIENT
    ) -> Path:
        """Generate hierarchical file path for cache entry."""
        # Create parameters hash for unique identification
        params_str = json.dumps(params or {}, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        # Create hierarchical path: sport/endpoint/strategy/date_params.json
        date_str = datetime.now().strftime("%Y-%m")
        filename = f"{date_str}_{params_hash}.cache"
        
        return self.cache_dir / sport.value / endpoint / strategy.value / filename
    
    def _should_compress(self, data: bytes) -> bool:
        """Determine if data should be compressed."""
        return len(data) > self.compression_threshold
    
    async def _serialize_data(self, entry: FileCacheEntry) -> bytes:
        """Serialize cache entry with optional compression."""
        try:
            # Convert to dict for serialization
            entry_dict = asdict(entry)
            
            # Use pickle for complex data types, JSON for simple ones
            if isinstance(entry.data, (dict, list, str, int, float, bool)):
                serialized = json.dumps(entry_dict).encode('utf-8')
            else:
                serialized = pickle.dumps(entry_dict)
            
            # Compress if data is large
            if self._should_compress(serialized):
                compressed = gzip.compress(serialized)
                entry.compressed = True
                entry.file_size = len(compressed)
                return compressed
            else:
                entry.file_size = len(serialized)
                return serialized
                
        except Exception as e:
            logger.error(f"File cache serialization error: {e}")
            raise CacheSerializationError(f"Failed to serialize cache entry: {e}")
    
    async def _deserialize_data(self, data: bytes, compressed: bool = False) -> FileCacheEntry:
        """Deserialize cache entry with optional decompression."""
        try:
            # Decompress if needed
            if compressed:
                data = gzip.decompress(data)
            
            # Try JSON first, fall back to pickle
            try:
                entry_dict = json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                entry_dict = pickle.loads(data)
            
            return FileCacheEntry(**entry_dict)
            
        except Exception as e:
            logger.error(f"File cache deserialization error: {e}")
            raise CacheSerializationError(f"Failed to deserialize cache entry: {e}")
    
    async def get(
        self, 
        sport: Sport, 
        endpoint: str, 
        params: Optional[Dict] = None,
        strategy: FileCacheStrategy = FileCacheStrategy.TRANSIENT
    ) -> Optional[Any]:
        """Retrieve cached data from file system."""
        file_path = self._get_file_path(sport, endpoint, params, strategy)
        
        if not file_path.exists():
            self.analytics["miss_count"] += 1
            return None
        
        try:
            # Read file asynchronously
            async with aiofiles.open(file_path, 'rb') as f:
                data = await f.read()
            
            # Check if file is compressed by reading metadata
            try:
                # Try to read as compressed first
                entry = await self._deserialize_data(data, compressed=True)
            except:
                # Fall back to uncompressed
                entry = await self._deserialize_data(data, compressed=False)
            
            # Update access tracking
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow().isoformat()
            
            # Write back updated metadata (async fire-and-forget)
            asyncio.create_task(self._update_metadata(file_path, entry))
            
            self.analytics["hit_count"] += 1
            logger.debug(f"File cache hit for {sport.value}:{endpoint} (strategy: {strategy.value})")
            
            return entry.data
            
        except Exception as e:
            logger.error(f"File cache get error for {sport.value}:{endpoint}: {e}")
            self.analytics["miss_count"] += 1
            return None
    
    async def set(
        self, 
        sport: Sport, 
        endpoint: str, 
        data: Any,
        params: Optional[Dict] = None,
        strategy: FileCacheStrategy = FileCacheStrategy.TRANSIENT,
        tier_priority: int = 1
    ) -> bool:
        """Store data in file cache with strategy and tier information."""
        try:
            file_path = self._get_file_path(sport, endpoint, params, strategy)
            
            # Create directory structure
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create cache entry
            params_str = json.dumps(params or {}, sort_keys=True)
            entry = FileCacheEntry(
                data=data,
                timestamp=datetime.utcnow().isoformat(),
                sport=sport.value,
                endpoint=endpoint,
                params_hash=hashlib.md5(params_str.encode()).hexdigest()[:8],
                tier_priority=tier_priority
            )
            
            # Serialize and optionally compress
            serialized_data = await self._serialize_data(entry)
            
            # Write to file asynchronously
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(serialized_data)
            
            # Update analytics
            self.analytics["total_files"] += 1
            self.analytics["total_size"] += entry.file_size
            
            # Update sport-specific analytics
            sport_key = sport.value
            if sport_key not in self.analytics["by_sport"]:
                self.analytics["by_sport"][sport_key] = {"files": 0, "size": 0}
            self.analytics["by_sport"][sport_key]["files"] += 1
            self.analytics["by_sport"][sport_key]["size"] += entry.file_size
            
            # Update strategy-specific analytics
            strategy_key = strategy.value
            if strategy_key not in self.analytics["by_strategy"]:
                self.analytics["by_strategy"][strategy_key] = {"files": 0, "size": 0}
            self.analytics["by_strategy"][strategy_key]["files"] += 1
            self.analytics["by_strategy"][strategy_key]["size"] += entry.file_size
            
            logger.debug(
                f"File cached {sport.value}:{endpoint} "
                f"(strategy: {strategy.value}, size: {entry.file_size}, compressed: {entry.compressed})"
            )
            
            # Check if we need cleanup
            if self.analytics["total_size"] > self.max_size_bytes:
                asyncio.create_task(self._cleanup_old_files())
            
            return True
            
        except Exception as e:
            logger.error(f"File cache set error for {sport.value}:{endpoint}: {e}")
            return False
    
    async def _update_metadata(self, file_path: Path, entry: FileCacheEntry):
        """Update file metadata for access tracking."""
        try:
            serialized_data = await self._serialize_data(entry)
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(serialized_data)
        except Exception as e:
            logger.error(f"Failed to update file cache metadata: {e}")
    
    async def invalidate(
        self, 
        sport: Optional[Sport] = None, 
        endpoint: Optional[str] = None,
        strategy: Optional[FileCacheStrategy] = None
    ):
        """Invalidate cache entries based on criteria."""
        if sport and endpoint and strategy:
            # Specific invalidation
            cache_path = self.cache_dir / sport.value / endpoint / strategy.value
            if cache_path.exists():
                for file_path in cache_path.glob("*.cache"):
                    try:
                        file_path.unlink()
                        logger.debug(f"Invalidated {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to invalidate {file_path}: {e}")
        elif sport:
            # Invalidate all files for a sport
            sport_path = self.cache_dir / sport.value
            if sport_path.exists():
                for file_path in sport_path.rglob("*.cache"):
                    try:
                        file_path.unlink()
                        logger.debug(f"Invalidated {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to invalidate {file_path}: {e}")
        else:
            logger.warning("Invalidation called without specific criteria")
    
    async def _cleanup_old_files(self):
        """Clean up old files based on retention policies and size limits."""
        logger.info("Starting file cache cleanup...")
        
        current_time = datetime.utcnow()
        files_removed = 0
        size_freed = 0
        
        # Get all cache files with metadata
        cache_files = []
        for cache_file in self.cache_dir.rglob("*.cache"):
            try:
                stat = cache_file.stat()
                # Determine strategy from path
                strategy = cache_file.parent.name
                cache_files.append({
                    'path': cache_file,
                    'mtime': datetime.fromtimestamp(stat.st_mtime),
                    'size': stat.st_size,
                    'strategy': strategy
                })
            except Exception as e:
                logger.error(f"Error reading cache file {cache_file}: {e}")
        
        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda x: x['mtime'])
        
        for file_info in cache_files:
            file_path = file_info['path']
            mtime = file_info['mtime']
            file_size = file_info['size']
            strategy = file_info['strategy']
            
            # Check retention policy
            retention_days = self.retention_policies.get(
                FileCacheStrategy(strategy), 
                self.retention_policies[FileCacheStrategy.TRANSIENT]
            )
            
            if (current_time - mtime).days > retention_days:
                try:
                    file_path.unlink()
                    files_removed += 1
                    size_freed += file_size
                    self.analytics["total_size"] -= file_size
                    logger.debug(f"Removed old cache file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to remove old cache file {file_path}: {e}")
            
            # Stop if we're under size limit
            if self.analytics["total_size"] <= self.max_size_bytes * 0.8:  # 80% threshold
                break
        
        logger.info(f"Cache cleanup completed: {files_removed} files removed, {size_freed} bytes freed")
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Get comprehensive cache analytics."""
        # Refresh analytics by scanning directory
        await self._refresh_analytics()
        
        return {
            "file_cache_analytics": self.analytics,
            "retention_policies": self.retention_policies,
            "cache_directory": str(self.cache_dir),
            "max_size_gb": self.max_size_bytes / (1024 * 1024 * 1024),
            "current_size_gb": self.analytics["total_size"] / (1024 * 1024 * 1024),
            "utilization_percent": (self.analytics["total_size"] / self.max_size_bytes) * 100
        }
    
    async def _refresh_analytics(self):
        """Refresh analytics by scanning cache directory."""
        self.analytics = {
            "total_files": 0,
            "total_size": 0,
            "hit_count": self.analytics.get("hit_count", 0),
            "miss_count": self.analytics.get("miss_count", 0),
            "by_sport": {},
            "by_strategy": {}
        }
        
        for cache_file in self.cache_dir.rglob("*.cache"):
            try:
                stat = cache_file.stat()
                file_size = stat.st_size
                
                # Extract sport and strategy from path
                parts = cache_file.relative_to(self.cache_dir).parts
                if len(parts) >= 3:
                    sport = parts[0]
                    strategy = parts[2]
                    
                    self.analytics["total_files"] += 1
                    self.analytics["total_size"] += file_size
                    
                    # Sport analytics
                    if sport not in self.analytics["by_sport"]:
                        self.analytics["by_sport"][sport] = {"files": 0, "size": 0}
                    self.analytics["by_sport"][sport]["files"] += 1
                    self.analytics["by_sport"][sport]["size"] += file_size
                    
                    # Strategy analytics
                    if strategy not in self.analytics["by_strategy"]:
                        self.analytics["by_strategy"][strategy] = {"files": 0, "size": 0}
                    self.analytics["by_strategy"][strategy]["files"] += 1
                    self.analytics["by_strategy"][strategy]["size"] += file_size
                    
            except Exception as e:
                logger.error(f"Error analyzing cache file {cache_file}: {e}")


# Global file cache instance
file_cache = FileCache() 