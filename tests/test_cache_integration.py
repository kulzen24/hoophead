#!/usr/bin/env python3
"""
Comprehensive test for Redis cache integration with Ball Don't Lie API.
Tests caching layers, TTL strategies, and cache performance.
"""
import asyncio
import os
import sys
import time
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

from src.adapters.external.ball_dont_lie_client import BallDontLieClient, Sport
from src.adapters.cache.redis_client import CacheManager


async def test_cache_integration():
    """Test Redis cache integration with Ball Don't Lie API."""
    
    api_key = os.getenv("BALLDONTLIE_API_KEY")
    if not api_key:
        print("❌ BALLDONTLIE_API_KEY environment variable required")
        return
    
    print("🧪 Testing Redis Cache Integration with Ball Don't Lie API\n")
    
    # Test with cache enabled
    print("1. Testing with cache ENABLED:")
    async with BallDontLieClient(api_key, enable_cache=True) as client:
        print(f"   Cache enabled: {client.cache_enabled}")
        
        # First request (cache miss)
        print("   Making first request (should be cache MISS)...")
        start_time = time.time()
        response1 = await client.get_teams(Sport.NBA)
        first_time = time.time() - start_time
        
        if response1.success:
            meta = response1.meta or {}
            print(f"   ✅ Success - Teams: {len(response1.data.get('data', []))}")
            print(f"   📊 Cached: {meta.get('cached', False)}")
            print(f"   ⏱️  Time: {first_time:.2f}s")
        else:
            print(f"   ❌ Failed: {response1.error}")
            return
        
        # Second request (cache hit)
        print("   Making second request (should be cache HIT)...")
        start_time = time.time()
        response2 = await client.get_teams(Sport.NBA)
        second_time = time.time() - start_time
        
        if response2.success:
            meta = response2.meta or {}
            print(f"   ✅ Success - Teams: {len(response2.data.get('data', []))}")
            print(f"   📊 Cached: {meta.get('cached', False)}")
            print(f"   ⏱️  Time: {second_time:.2f}s")
            print(f"   🚀 Speed improvement: {(first_time/second_time):.1f}x faster")
        else:
            print(f"   ❌ Failed: {response2.error}")
    
    print()
    
    # Test with cache disabled
    print("2. Testing with cache DISABLED:")
    async with BallDontLieClient(api_key, enable_cache=False) as client:
        print(f"   Cache enabled: {client.cache_enabled}")
        
        start_time = time.time()
        response3 = await client.get_teams(Sport.NBA)
        no_cache_time = time.time() - start_time
        
        if response3.success:
            meta = response3.meta or {}
            print(f"   ✅ Success - Teams: {len(response3.data.get('data', []))}")
            print(f"   📊 Cached: {meta.get('cached', False)}")
            print(f"   ⏱️  Time: {no_cache_time:.2f}s")
        else:
            print(f"   ❌ Failed: {response3.error}")
    
    print()
    
    # Test multi-sport caching
    print("3. Testing multi-sport caching:")
    async with BallDontLieClient(api_key, enable_cache=True) as client:
        sports_to_test = [Sport.NBA, Sport.MLB, Sport.NFL, Sport.NHL]
        
        print("   First round (cache misses)...")
        start_time = time.time()
        results1 = {}
        for sport in sports_to_test:
            response = await client.get_teams(sport)
            results1[sport] = response
            if response.success:
                print(f"   ✅ {sport.value.upper()}: {len(response.data.get('data', []))} teams")
            else:
                print(f"   ⚠️  {sport.value.upper()}: {response.error}")
        first_round_time = time.time() - start_time
        
        print("   Second round (cache hits)...")
        start_time = time.time()
        results2 = {}
        for sport in sports_to_test:
            response = await client.get_teams(sport)
            results2[sport] = response
        second_round_time = time.time() - start_time
        
        print(f"   ⏱️  First round time: {first_round_time:.2f}s")
        print(f"   ⏱️  Second round time: {second_round_time:.2f}s")
        print(f"   🚀 Multi-sport cache speedup: {(first_round_time/second_round_time):.1f}x")
        
        # Check cache statistics
        cache_stats = await client.get_cache_stats()
        if cache_stats.get("cache_enabled", False):
            print(f"   📈 Cache stats: {cache_stats.get('total_keys', 0)} total keys")
            for sport, data in cache_stats.get('by_sport', {}).items():
                print(f"      - {sport.upper()}: {data['total']} cached items")
    
    print()
    
    # Test cache invalidation
    print("4. Testing cache invalidation:")
    async with BallDontLieClient(api_key, enable_cache=True) as client:
        # Cache a request
        print("   Caching NBA teams...")
        response = await client.get_teams(Sport.NBA)
        if response.success:
            meta = response.meta or {}
            print(f"   ✅ Cached: {meta.get('cached', False)}")
        
        # Invalidate cache
        print("   Invalidating NBA cache...")
        await client.invalidate_sport_cache(Sport.NBA)
        
        # Request again (should be cache miss)
        print("   Requesting NBA teams again (should be cache MISS)...")
        response = await client.get_teams(Sport.NBA)
        if response.success:
            meta = response.meta or {}
            print(f"   ✅ Cached after invalidation: {meta.get('cached', False)}")
    
    print()
    
    # Test cache with search parameters
    print("5. Testing cache with search parameters:")
    async with BallDontLieClient(api_key, enable_cache=True) as client:
        # Search for different players (different cache keys)
        searches = ["curry", "james", "mcdavid"]
        
        for search_term in searches:
            print(f"   Searching for '{search_term}'...")
            
            # First search (cache miss)
            start_time = time.time()
            response1 = await client.get_players(Sport.NBA, search=search_term)
            first_time = time.time() - start_time
            
            # Second search (cache hit)  
            start_time = time.time()
            response2 = await client.get_players(Sport.NBA, search=search_term)
            second_time = time.time() - start_time
            
            if response1.success and response2.success:
                meta1 = response1.meta or {}
                meta2 = response2.meta or {}
                print(f"   ✅ {search_term}: First cached: {meta1.get('cached', False)}, Second cached: {meta2.get('cached', False)}")
                print(f"      Cache speedup: {(first_time/second_time):.1f}x")
    
    print("\n🎉 Cache integration tests complete!")


async def test_redis_direct():
    """Test Redis cache directly without API calls."""
    
    print("🔧 Testing Redis cache directly...\n")
    
    try:
        async with CacheManager() as cache:
            print("   ✅ Redis connection successful")
            
            # Test cache stats
            stats = await cache.get_cache_stats()
            print(f"   📊 Cache stats: {stats}")
            
            # Test manual cache operations
            from src.adapters.external.ball_dont_lie_client import APIResponse, Sport
            
            # Create test response
            test_response = APIResponse(
                data={"test": "data", "teams": [{"id": 1, "name": "Test Team"}]},
                success=True,
                sport=Sport.NBA,
                meta={"test": True}
            )
            
            # Store in cache
            await cache.set(Sport.NBA, "teams", test_response)
            print("   ✅ Test data stored in cache")
            
            # Retrieve from cache
            cached_response = await cache.get(Sport.NBA, "teams")
            if cached_response:
                print(f"   ✅ Test data retrieved from cache: {cached_response.data['test']}")
            else:
                print("   ❌ Failed to retrieve test data from cache")
            
            # Test cache invalidation
            await cache.invalidate(Sport.NBA, "teams")
            print("   ✅ Cache invalidated")
            
            # Try to retrieve again (should be None)
            cached_response = await cache.get(Sport.NBA, "teams")
            if cached_response is None:
                print("   ✅ Cache correctly invalidated")
            else:
                print("   ⚠️  Cache invalidation may not have worked")
            
    except Exception as e:
        print(f"   ❌ Redis test failed: {e}")
        print("   💡 Make sure Redis is running: docker run -d -p 6379:6379 redis:alpine")


async def main():
    """Run all cache integration tests."""
    await test_redis_direct()
    print()
    await test_cache_integration()


if __name__ == "__main__":
    asyncio.run(main()) 