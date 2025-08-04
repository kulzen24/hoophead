# HoopHead Quick Start Guide

## 🚀 **Get Started in 5 Minutes**

This guide gets you up and running with HoopHead's optimized architecture immediately.

---

## 📋 **Prerequisites**

- Python 3.8+
- Redis (for caching)
- Ball Don't Lie API key

---

## ⚡ **1. Environment Setup**

### **Create `.env` file:**
```bash
# API Configuration
BALLDONTLIE_API_KEY=your_api_key_here

# Cache Configuration  
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_redis_password

# Security
HOOPHEAD_ENCRYPTION_KEY=your_32_character_encryption_key_here
SECRET_KEY=your_secret_key_for_sessions

# Environment
ENVIRONMENT=development
DEBUG=true
```

### **Install Dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

### **Start Redis:**
```bash
redis-server
```

---

## 🎯 **2. Basic Usage Examples**

### **Get NBA Teams:**
```python
import asyncio
from core.utils import EnvironmentManager
from adapters.external.ball_dont_lie_client import BallDontLieClient
from domain.services.team_service import TeamService
from domain.models.base import SportType

# Setup environment
EnvironmentManager.load_env_vars()

async def get_nba_teams():
    # Initialize client and service
    client = BallDontLieClient()
    team_service = TeamService(client)
    
    # Get all NBA teams
    teams = await team_service.get_all_teams(SportType.NBA)
    
    print(f"Found {len(teams)} NBA teams:")
    for team in teams[:5]:  # Show first 5
        print(f"- {team.city} {team.name} ({team.abbreviation})")

# Run the example
asyncio.run(get_nba_teams())
```

### **Search Players:**
```python
from domain.services.player_service import PlayerService, PlayerSearchCriteria

async def search_players():
    client = BallDontLieClient()
    player_service = PlayerService(client)
    
    # Search for players
    criteria = PlayerSearchCriteria(
        name="LeBron",
        sport=SportType.NBA,
        active_only=True
    )
    
    response = await player_service.search(criteria)
    
    if response.success:
        print(f"Found {len(response.data)} players:")
        for player in response.data:
            print(f"- {player.first_name} {player.last_name} ({player.team_name})")

asyncio.run(search_players())
```

### **Get Games by Date:**
```python
from domain.services.game_service import GameService, GameSearchCriteria

async def get_games_today():
    client = BallDontLieClient()
    game_service = GameService(client)
    
    # Get today's games
    from datetime import date
    today = date.today().isoformat()
    
    criteria = GameSearchCriteria(
        sport=SportType.NBA,
        date=today
    )
    
    response = await game_service.search(criteria)
    
    if response.success:
        print(f"Found {len(response.data)} games today:")
        for game in response.data:
            print(f"- {game.home_team_name} vs {game.visitor_team_name}")

asyncio.run(get_games_today())
```

---

## 📊 **3. Monitoring & Analytics**

### **Check Cache Performance:**
```python
from adapters.cache.cache_analytics import analytics_manager

async def check_cache_performance():
    # Get comprehensive analytics
    analytics = analytics_manager.get_comprehensive_analytics()
    
    print("Cache Performance Summary:")
    print(f"- Total Requests: {analytics['summary']['total_requests']}")
    print(f"- Hit Rate: {analytics['summary']['overall_hit_rate']:.2%}")
    print(f"- Components: {analytics['summary']['total_components']}")
    
    # Health status
    health = analytics_manager.get_health_status()
    print(f"- Overall Health: {health['overall_health']}")

asyncio.run(check_cache_performance())
```

### **Get Business Metrics:**
```python
from analytics.business_metrics import business_tracker

def check_business_metrics():
    metrics = business_tracker.get_metrics()
    
    print("Business Metrics:")
    print(f"- Total API Calls: {metrics['business_metrics']['total_api_calls']}")
    print(f"- Unique Users: {metrics['business_metrics']['unique_users']}")
    print(f"- Popular Sports: {metrics['business_metrics']['popular_sports']}")

check_business_metrics()
```

---

## 🧪 **4. Testing Your Code**

### **Create a Simple Test:**
```python
# test_my_feature.py
import pytest
from tests.test_utils import (
    MockBallDontLieClient, TestDataFactory, 
    CommonTestPatterns, assert_api_called
)
from domain.services.team_service import TeamService
from domain.models.base import SportType

class TestTeamFeature:
    def setup_method(self):
        self.mock_client = MockBallDontLieClient()
        self.service = TeamService(self.mock_client)
        self.data_factory = TestDataFactory()
    
    @pytest.mark.asyncio
    async def test_get_team_by_id(self):
        # Setup mock response
        team_data = self.data_factory.create_team_data(team_id=1, name="Lakers")
        self.mock_client.set_response('get_teams', MockAPIResponse(
            success=True,
            data={'data': [team_data]}
        ))
        
        # Test the service
        team = await self.service.get_team_by_id(1, SportType.NBA)
        
        # Assertions
        assert team is not None
        assert team.name == "Lakers"
        assert_api_called(self.mock_client, 'get_teams', times=1)

# Run the test
pytest.run(['test_my_feature.py', '-v'])
```

### **Performance Testing:**
```python
from tests.test_utils import PerformanceTimer, assert_response_time

async def test_performance():
    timer = PerformanceTimer()
    
    timer.start()
    # Your code here
    await team_service.get_all_teams(SportType.NBA)
    timer.stop()
    
    # Assert response time under 100ms
    assert_response_time(timer, max_time_ms=100)
    print(f"✅ Response time: {timer.elapsed_ms:.2f}ms")

asyncio.run(test_performance())
```

---

## 🔧 **5. Common Patterns**

### **Error Handling:**
```python
from core.exceptions import TeamNotFoundError, APIConnectionError
from core.error_handler import with_domain_error_handling

@with_domain_error_handling(fallback_value=None)
async def safe_get_team(team_id: int):
    try:
        return await team_service.get_team_by_id(team_id, SportType.NBA)
    except TeamNotFoundError:
        print(f"Team {team_id} not found")
        return None
    except APIConnectionError:
        print("API connection failed")
        return None
```

### **Caching:**
```python
# Caching is automatic, but you can control it:
async def get_fresh_data():
    # Force fresh data (bypass cache)
    teams = await client.get_teams(sport=SportType.NBA, use_cache=False)
    
    # Invalidate cache when needed
    await team_service.invalidate_cache(SportType.NBA)
```

### **Logging:**
```python
from core.utils import LoggerFactory

# Get a configured logger
logger = LoggerFactory.get_logger(__name__)

async def my_function():
    logger.info("Starting operation")
    try:
        # Your code
        logger.debug("Operation details")
    except Exception as e:
        logger.error(f"Operation failed: {e}")
```

---

## 🚀 **6. Production Deployment**

### **Health Check Endpoint:**
```python
from health.health_checker import health_checker

async def health_check():
    health = await health_checker.get_health_status()
    return health

# Use in your web framework (FastAPI, Flask, etc.)
@app.get("/health")
async def get_health():
    return await health_check()
```

### **Configuration:**
```python
from config.dynamic_config import dynamic_config

# Get configuration values
cache_ttl = dynamic_config.get('cache.default_ttl', 3600)
api_timeout = dynamic_config.get('api.timeout', 30)

# Update configuration at runtime
dynamic_config.set('cache.default_ttl', 7200)
```

---

## 📚 **7. Next Steps**

### **Explore Advanced Features:**
1. **Custom Services** - See [Extension Guide](./EXTENSION_GUIDE.md#adding-a-new-service)
2. **New Sports** - See [Extension Guide](./EXTENSION_GUIDE.md#adding-a-new-sport) 
3. **Custom Caching** - See [Extension Guide](./EXTENSION_GUIDE.md#adding-custom-cache-layers)
4. **Middleware** - See [Extension Guide](./EXTENSION_GUIDE.md#creating-custom-middleware)

### **Documentation:**
- [API Reference](./API_REFERENCE.md) - Complete API documentation
- [Data Models](./DATA_MODELS.md) - Entity relationships and schemas
- [Integration Guide](./INTEGRATION_GUIDE.md) - Step-by-step integration
- [Error Handling](./ERROR_HANDLING.md) - Exception hierarchy and patterns

### **Run Complete Test Suite:**
```bash
cd tests
python run_comprehensive_tests.py
```

---

## 🎯 **Common Issues & Solutions**

### **Redis Connection Issues:**
```python
# Check Redis connectivity
from adapters.cache.redis_client import HoopHeadRedisCache

try:
    cache = HoopHeadRedisCache()
    await cache.ping()
    print("✅ Redis connected")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
```

### **API Key Issues:**
```python
# Validate API key
from adapters.external.auth_manager import AuthenticationManager

auth_manager = AuthenticationManager()
is_valid, key_id, tier = auth_manager.validate_api_key("your_api_key")

if is_valid:
    print(f"✅ API key valid (Tier: {tier})")
else:
    print("❌ Invalid API key")
```

### **Performance Issues:**
```python
# Check component performance
analytics = analytics_manager.get_comprehensive_analytics()

# Look for recommendations
recommendations = analytics['recommendations']
for rec in recommendations:
    print(f"💡 {rec}")
```

---

## 🎉 **You're Ready!**

You now have everything you need to start building with HoopHead's optimized architecture. The system provides:

- ✅ **Automatic caching** with performance monitoring
- ✅ **Type-safe services** with consistent error handling  
- ✅ **Comprehensive testing** utilities
- ✅ **Production-ready** monitoring and health checks
- ✅ **Easy extension** patterns for new features

**Happy coding!** 🚀

---

*Need help? Check the [Extension Guide](./EXTENSION_GUIDE.md) for advanced patterns or create an issue.* 