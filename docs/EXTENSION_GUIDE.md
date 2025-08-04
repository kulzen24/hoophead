# HoopHead Extension Guide

## 🚀 **Extending the Optimized Architecture**

This guide shows how to extend HoopHead's newly optimized architecture to add new sports, services, cache layers, and functionality while maintaining consistency and leveraging existing components.

---

## 📋 **Quick Start: Adding a New Service**

### **1. Create a New Service (Example: GameService)**

```python
# backend/src/domain/services/game_service.py
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from core.utils import LoggerFactory
from core.exceptions import GameNotFoundError
from core.error_handler import with_domain_error_handling

from .base_service import BaseService, BaseSearchCriteria, ServiceListResponse
from ..models.base import SportType
from ..models.game import Game

logger = LoggerFactory.get_logger(__name__)

@dataclass
class GameSearchCriteria(BaseSearchCriteria):
    """Extended search criteria for games."""
    date: Optional[str] = None
    team_id: Optional[int] = None
    season: Optional[int] = None
    status: Optional[str] = None

class GameService(BaseService[Game]):
    """Game service inheriting optimized base functionality."""
    
    def __init__(self, api_client):
        super().__init__(api_client, Game)
    
    def get_api_endpoint(self) -> str:
        return "games"
    
    def create_search_criteria(self, **kwargs) -> GameSearchCriteria:
        return GameSearchCriteria(**kwargs)
    
    def _extract_search_params(self, criteria: GameSearchCriteria) -> Dict[str, Any]:
        params = super()._extract_search_params(criteria)
        
        if criteria.date:
            params['dates[]'] = criteria.date
        if criteria.team_id:
            params['team_ids[]'] = criteria.team_id
        if criteria.season:
            params['seasons[]'] = criteria.season
            
        return params
    
    def _apply_client_filters(self, results: List[Game], criteria: GameSearchCriteria) -> List[Game]:
        filtered = results
        
        if criteria.status:
            status_lower = criteria.status.lower()
            filtered = [
                game for game in filtered
                if game.status and status_lower in game.status.lower()
            ]
        
        return filtered
    
    # Add game-specific methods
    async def get_live_games(self, sport: SportType) -> List[Game]:
        """Get currently live games."""
        criteria = GameSearchCriteria(sport=sport, status="live")
        response = await self.search(criteria)
        return response.data if response.success else []
    
    async def get_games_by_date(self, sport: SportType, date: str) -> List[Game]:
        """Get games for a specific date."""
        criteria = GameSearchCriteria(sport=sport, date=date)
        response = await self.search(criteria)
        return response.data if response.success else []
```

### **2. Register the New Service**

```python
# backend/src/domain/services/__init__.py
from .game_service import GameService, GameSearchCriteria

__all__ = [
    "PlayerService",
    "TeamService", 
    "GameService",  # Add new service
    "StatsService",
    "SearchService",
    # Add search criteria
    "GameSearchCriteria"
]
```

---

## 🎯 **Adding a New Sport**

### **1. Extend SportType Enum**

```python
# backend/src/domain/models/base.py
class SportType(str, Enum):
    NBA = "nba"
    NFL = "nfl"      # Add new sport
    MLB = "mlb"      # Add new sport
    NHL = "nhl"      # Add new sport
    SOCCER = "soccer" # Add new sport
```

### **2. Update API Client**

```python
# backend/src/adapters/external/ball_dont_lie_client.py
from enum import Enum

class Sport(str, Enum):
    NBA = "nba"
    NFL = "nfl"      # Add corresponding API sport
    MLB = "mlb"
    NHL = "nhl"
    SOCCER = "soccer"
```

### **3. Create Sport-Specific Models (if needed)**

```python
# backend/src/domain/models/nfl_player.py
from dataclasses import dataclass
from typing import Optional
from .player import Player

@dataclass 
class NFLPlayer(Player):
    """NFL-specific player extensions."""
    jersey_number: Optional[int] = None
    college: Optional[str] = None
    years_pro: Optional[int] = None
    
    @classmethod
    def from_api_response(cls, api_data: Dict[str, Any], sport: SportType) -> 'NFLPlayer':
        # NFL-specific parsing logic
        player_data = api_data.get('data', {})
        
        return cls(
            id=str(player_data.get('id', '')),
            sport=sport,
            first_name=player_data.get('first_name', ''),
            last_name=player_data.get('last_name', ''),
            jersey_number=player_data.get('jersey_number'),
            college=player_data.get('college'),
            years_pro=player_data.get('years_pro'),
            # ... other fields
            raw_data=api_data
        )
```

---

## 🔧 **Adding Custom Cache Layers**

### **1. Create New Cache Implementation**

```python
# backend/src/adapters/cache/database_cache.py
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from core.utils import LoggerFactory, CacheKeyBuilder
from adapters.cache.cache_analytics import analytics_manager

logger = LoggerFactory.get_logger(__name__)

class DatabaseCache:
    """Database-backed cache implementation."""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.component_name = "database_cache"
        
        # Register with analytics
        analytics_manager.register_component(self.component_name)
    
    async def get(self, sport: str, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Get cached data from database."""
        import time
        start_time = time.time()
        
        try:
            cache_key = CacheKeyBuilder.build_key(sport, endpoint, params)
            
            # Database query logic
            result = await self._query_cache(cache_key)
            
            response_time = (time.time() - start_time) * 1000
            
            if result:
                analytics_manager.record_hit(self.component_name, response_time)
                return result
            else:
                analytics_manager.record_miss(self.component_name, response_time)
                return None
                
        except Exception as e:
            logger.error(f"Database cache error: {e}")
            analytics_manager.record_error(self.component_name)
            return None
    
    async def set(self, sport: str, endpoint: str, data: Dict[str, Any], ttl: int = 3600, params: Optional[Dict] = None):
        """Store data in database cache."""
        try:
            cache_key = CacheKeyBuilder.build_key(sport, endpoint, params)
            await self._store_cache(cache_key, data, ttl)
            
        except Exception as e:
            logger.error(f"Database cache store error: {e}")
            analytics_manager.record_error(self.component_name)
    
    async def _query_cache(self, cache_key: str) -> Optional[Dict]:
        """Query cache from database - implement based on your DB."""
        # Example SQL query
        query = "SELECT data, expires_at FROM cache WHERE key = ? AND expires_at > NOW()"
        result = await self.db.fetch_one(query, cache_key)
        
        if result:
            return result['data']
        return None
    
    async def _store_cache(self, cache_key: str, data: Dict, ttl: int):
        """Store cache in database - implement based on your DB."""
        # Example SQL insert
        expires_at = "NOW() + INTERVAL ? SECOND"
        query = "INSERT OR REPLACE INTO cache (key, data, expires_at) VALUES (?, ?, ?)"
        await self.db.execute(query, cache_key, data, ttl)
```

### **2. Integrate with Multi-Cache Manager**

```python
# Update backend/src/adapters/cache/multi_cache_manager.py
from .database_cache import DatabaseCache

class MultiCacheManager:
    def __init__(self, redis_cache=None, file_cache=None, database_cache=None):
        self.redis_cache = redis_cache
        self.file_cache = file_cache
        self.database_cache = database_cache  # Add new cache layer
        
        # Cache hierarchy: Redis -> Database -> File
        self.cache_layers = [
            ("redis", self.redis_cache),
            ("database", self.database_cache),  # Add to hierarchy
            ("file", self.file_cache)
        ]
```

---

## 🧪 **Extending Test Infrastructure**

### **1. Add Custom Test Utilities**

```python
# tests/custom_test_utils.py
from tests.test_utils import TestDataFactory, MockBallDontLieClient

class NFLTestDataFactory(TestDataFactory):
    """NFL-specific test data factory."""
    
    @staticmethod
    def create_nfl_player_data(player_id: int = 1, name: str = "Test Player"):
        base_data = TestDataFactory.create_player_data(player_id, name)
        
        # Add NFL-specific fields
        base_data.update({
            "jersey_number": 99,
            "college": "Test University", 
            "years_pro": 5,
            "contract_status": "active"
        })
        
        return base_data
    
    @staticmethod  
    def create_nfl_game_data(game_id: int = 1):
        base_data = TestDataFactory.create_game_data(game_id)
        
        # Add NFL-specific fields
        base_data.update({
            "quarter": 4,
            "time_remaining": "2:30",
            "weather_conditions": "Clear, 72°F",
            "attendance": 75000
        })
        
        return base_data

class MockNFLAPIClient(MockBallDontLieClient):
    """NFL-specific mock API client."""
    
    async def get_nfl_schedule(self, week=None, **kwargs):
        """Mock NFL schedule method."""
        self.call_count['get_nfl_schedule'] = self.call_count.get('get_nfl_schedule', 0) + 1
        return self.responses.get('get_nfl_schedule', MockAPIResponse())
```

### **2. Create Performance Benchmarks**

```python
# tests/test_performance_benchmarks.py
import pytest
from tests.test_utils import PerformanceTimer, assert_response_time
from domain.services.game_service import GameService

class TestGameServicePerformance:
    """Performance tests for GameService."""
    
    @pytest.mark.asyncio
    async def test_get_live_games_performance(self, mock_api_client):
        """Test live games retrieval performance."""
        service = GameService(mock_api_client)
        timer = PerformanceTimer()
        
        timer.start()
        await service.get_live_games(SportType.NBA)
        timer.stop()
        
        # Assert response time under 100ms
        assert_response_time(timer, max_time_ms=100)
    
    @pytest.mark.asyncio
    async def test_bulk_game_retrieval_performance(self, mock_api_client):
        """Test bulk game retrieval performance."""
        service = GameService(mock_api_client)
        
        # Test multiple concurrent requests
        import asyncio
        
        timer = PerformanceTimer()
        timer.start()
        
        tasks = [
            service.get_games_by_date(SportType.NBA, f"2023-01-{day:02d}")
            for day in range(1, 11)  # 10 concurrent requests
        ]
        
        await asyncio.gather(*tasks)
        timer.stop()
        
        # Assert total time under 500ms for 10 requests
        assert_response_time(timer, max_time_ms=500)
```

---

## 🔌 **Creating Custom Middleware**

### **1. Add Authentication Middleware**

```python
# backend/src/middleware/auth_middleware.py
from core.utils import LoggerFactory, EnvironmentManager
from core.exceptions import APIAuthenticationError

logger = LoggerFactory.get_logger(__name__)

class AuthMiddleware:
    """Authentication middleware for API requests."""
    
    def __init__(self):
        self.required_headers = ['Authorization', 'X-API-Key']
    
    async def process_request(self, request, handler):
        """Process incoming request for authentication."""
        try:
            # Check for required authentication headers
            auth_header = request.headers.get('Authorization')
            api_key = request.headers.get('X-API-Key')
            
            if not auth_header and not api_key:
                raise APIAuthenticationError("Missing authentication credentials")
            
            # Validate credentials
            if api_key:
                await self._validate_api_key(api_key)
            elif auth_header:
                await self._validate_bearer_token(auth_header)
            
            # Continue to handler
            return await handler(request)
            
        except APIAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            raise APIAuthenticationError("Authentication validation failed")
    
    async def _validate_api_key(self, api_key: str):
        """Validate API key."""
        # Implement your API key validation logic
        pass
    
    async def _validate_bearer_token(self, auth_header: str):
        """Validate Bearer token."""
        # Implement your token validation logic  
        pass
```

### **2. Add Rate Limiting Middleware**

```python
# backend/src/middleware/rate_limit_middleware.py
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

from core.utils import LoggerFactory
from core.exceptions import APIRateLimitError

logger = LoggerFactory.get_logger(__name__)

class RateLimitMiddleware:
    """Rate limiting middleware."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_counts = defaultdict(list)
        self.cleanup_interval = 300  # 5 minutes
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_old_requests())
    
    async def process_request(self, request, handler):
        """Process request with rate limiting."""
        client_id = self._get_client_id(request)
        current_time = datetime.utcnow()
        
        # Clean old requests for this client
        cutoff_time = current_time - timedelta(minutes=1)
        self.request_counts[client_id] = [
            req_time for req_time in self.request_counts[client_id]
            if req_time > cutoff_time
        ]
        
        # Check rate limit
        if len(self.request_counts[client_id]) >= self.requests_per_minute:
            raise APIRateLimitError(
                f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
            )
        
        # Record this request
        self.request_counts[client_id].append(current_time)
        
        # Continue to handler
        return await handler(request)
    
    def _get_client_id(self, request) -> str:
        """Get client identifier from request."""
        # Use API key, IP address, or other identifier
        return (
            request.headers.get('X-API-Key') or
            request.headers.get('X-Forwarded-For') or
            request.remote_addr or
            'unknown'
        )
    
    async def _cleanup_old_requests(self):
        """Periodic cleanup of old request records."""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            
            for client_id in list(self.request_counts.keys()):
                self.request_counts[client_id] = [
                    req_time for req_time in self.request_counts[client_id]
                    if req_time > cutoff_time
                ]
                
                # Remove empty entries
                if not self.request_counts[client_id]:
                    del self.request_counts[client_id]
```

---

## 📊 **Adding Custom Analytics**

### **1. Create Business Metrics Tracker**

```python
# backend/src/analytics/business_metrics.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List

from core.utils import LoggerFactory
from adapters.cache.cache_analytics import analytics_manager

logger = LoggerFactory.get_logger(__name__)

@dataclass
class BusinessMetrics:
    """Business-specific metrics."""
    total_api_calls: int = 0
    unique_users: int = 0
    popular_sports: Dict[str, int] = None
    peak_usage_hours: List[int] = None
    
    def __post_init__(self):
        if self.popular_sports is None:
            self.popular_sports = {}
        if self.peak_usage_hours is None:
            self.peak_usage_hours = []

class BusinessMetricsTracker:
    """Track business-specific metrics."""
    
    def __init__(self):
        self.metrics = BusinessMetrics()
        self.hourly_usage = [0] * 24  # 24 hours
        self.user_sessions = set()
        
        # Register with cache analytics
        analytics_manager.register_component("business_metrics")
    
    def track_api_call(self, user_id: str, sport: str, endpoint: str):
        """Track API call for business metrics."""
        try:
            self.metrics.total_api_calls += 1
            self.user_sessions.add(user_id)
            
            # Track sport popularity
            if sport not in self.metrics.popular_sports:
                self.metrics.popular_sports[sport] = 0
            self.metrics.popular_sports[sport] += 1
            
            # Track hourly usage
            current_hour = datetime.utcnow().hour
            self.hourly_usage[current_hour] += 1
            
            # Update peak hours (top 3 hours)
            peak_hours = sorted(
                range(24), 
                key=lambda h: self.hourly_usage[h], 
                reverse=True
            )[:3]
            self.metrics.peak_usage_hours = peak_hours
            
            logger.debug(f"Tracked API call: {user_id} -> {sport}/{endpoint}")
            
        except Exception as e:
            logger.error(f"Business metrics tracking error: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current business metrics."""
        self.metrics.unique_users = len(self.user_sessions)
        
        return {
            'business_metrics': {
                'total_api_calls': self.metrics.total_api_calls,
                'unique_users': self.metrics.unique_users,
                'popular_sports': dict(sorted(
                    self.metrics.popular_sports.items(),
                    key=lambda x: x[1],
                    reverse=True
                )),
                'peak_usage_hours': self.metrics.peak_usage_hours,
                'hourly_distribution': self.hourly_usage
            },
            'cache_analytics': analytics_manager.get_comprehensive_analytics()
        }

# Global instance
business_tracker = BusinessMetricsTracker()
```

### **2. Integrate with Existing Services**

```python
# Update your services to track business metrics
from analytics.business_metrics import business_tracker

class PlayerService(BaseService[Player]):
    async def get_by_id(self, entity_id: int, sport: SportType, user_id: str = None) -> Optional[Player]:
        # Track business metrics
        if user_id:
            business_tracker.track_api_call(user_id, sport.value, "players")
        
        return await super().get_by_id(entity_id, sport)
```

---

## 🚀 **Deployment Extensions**

### **1. Health Check Endpoint**

```python
# backend/src/health/health_checker.py
from typing import Dict, Any
import asyncio

from core.utils import LoggerFactory
from adapters.cache.cache_analytics import analytics_manager
from analytics.business_metrics import business_tracker

logger = LoggerFactory.get_logger(__name__)

class HealthChecker:
    """Comprehensive health checking."""
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        
        # Check cache health
        cache_health = analytics_manager.get_health_status()
        
        # Check API connectivity
        api_health = await self._check_api_connectivity()
        
        # Check database connectivity (if applicable)
        db_health = await self._check_database_connectivity()
        
        # Get business metrics
        business_metrics = business_tracker.get_metrics()
        
        # Determine overall health
        all_healthy = all([
            cache_health['overall_health'] == 'healthy',
            api_health['status'] == 'healthy',
            db_health['status'] == 'healthy'
        ])
        
        overall_status = 'healthy' if all_healthy else 'degraded'
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'cache': cache_health,
                'api': api_health,
                'database': db_health
            },
            'metrics': business_metrics,
            'uptime': self._get_uptime()
        }
    
    async def _check_api_connectivity(self) -> Dict[str, Any]:
        """Check external API connectivity."""
        try:
            # Test API connection with timeout
            async with asyncio.timeout(5.0):
                # Make a simple API call to test connectivity
                from adapters.external.ball_dont_lie_client import BallDontLieClient
                client = BallDontLieClient()
                await client.get_teams(sport="nba", use_cache=False)
            
            return {'status': 'healthy', 'response_time': '<5s'}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    async def _check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity."""
        # Implement based on your database setup
        return {'status': 'healthy', 'connection': 'active'}
    
    def _get_uptime(self) -> str:
        """Get system uptime."""
        # Calculate uptime based on when health checker was initialized
        uptime_delta = datetime.utcnow() - getattr(self, 'start_time', datetime.utcnow())
        return str(uptime_delta)

# Global health checker
health_checker = HealthChecker()
```

### **2. Configuration Management**

```python
# backend/src/config/dynamic_config.py
from typing import Dict, Any, Optional
import json
from pathlib import Path

from core.utils import LoggerFactory, EnvironmentManager

logger = LoggerFactory.get_logger(__name__)

class DynamicConfig:
    """Dynamic configuration management."""
    
    def __init__(self, config_path: str = "config/dynamic.json"):
        self.config_path = Path(config_path)
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = self._get_default_config()
                self.save_config()
                
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = self._get_default_config()
    
    def save_config(self):
        """Save configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        self.save_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'cache': {
                'default_ttl': 3600,
                'max_size': 10000,
                'enable_analytics': True
            },
            'api': {
                'timeout': 30,
                'max_retries': 3,
                'rate_limit': 100
            },
            'features': {
                'enable_caching': True,
                'enable_analytics': True,
                'enable_rate_limiting': True
            }
        }

# Global configuration
dynamic_config = DynamicConfig()
```

---

## 📚 **Best Practices for Extensions**

### **1. Follow the Established Patterns**

✅ **DO:**
- Inherit from `BaseService` for all new services
- Use `LoggerFactory.get_logger(__name__)` for logging
- Register components with `analytics_manager`
- Use `PathManager` for import handling
- Follow the established error handling patterns

❌ **DON'T:**
- Create manual `sys.path` manipulation
- Duplicate functionality that exists in base classes
- Skip error handling decorators
- Ignore the analytics system

### **2. Maintain Type Safety**

```python
# Use proper type hints and generics
from typing import TypeVar, Generic, List, Optional
T = TypeVar('T', bound=BaseEntity)

class CustomService(BaseService[T]):
    def custom_method(self, entity_id: int) -> Optional[T]:
        # Implementation with proper typing
        pass
```

### **3. Test Your Extensions**

```python
# Always create comprehensive tests
class TestCustomService:
    def test_initialization(self, mock_api_client):
        CommonTestPatterns.test_service_initialization(CustomService, mock_api_client)
    
    async def test_custom_functionality(self, async_test_setup):
        # Test your custom functionality
        pass
```

### **4. Document Your Extensions**

- Add docstrings to all new classes and methods
- Update the relevant `__init__.py` files
- Create examples showing how to use new functionality
- Update this extension guide with new patterns

---

## 🎯 **Common Extension Scenarios**

### **Adding Real-time Features**
```python
# Use WebSockets with the existing analytics framework
from adapters.cache.cache_analytics import analytics_manager

class WebSocketManager:
    def __init__(self):
        analytics_manager.register_component("websocket")
    
    async def broadcast_update(self, data):
        analytics_manager.record_hit("websocket")
        # Implementation
```

### **Adding External Integrations**
```python
# Create new adapters following the established pattern
class TwitterIntegration:
    def __init__(self):
        self.logger = LoggerFactory.get_logger(__name__)
        EnvironmentManager.load_env_vars()
```

### **Adding Background Jobs**
```python
# Use the async patterns and error handling
from core.utils import AsyncPatterns

class BackgroundJobManager:
    @AsyncPatterns.async_retry(max_retries=3)
    async def process_job(self, job_data):
        # Implementation with automatic retry
        pass
```

---

## 🚀 **Ready to Extend!**

The optimized HoopHead architecture is designed for easy extension. Every new component you add will automatically benefit from:

- ✅ **Centralized logging and error handling**
- ✅ **Performance monitoring and analytics**
- ✅ **Consistent testing patterns**
- ✅ **Type safety and validation**
- ✅ **Optimized caching and response handling**

**Happy coding!** 🎉 