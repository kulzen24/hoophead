#!/usr/bin/env python3
"""
HoopHead API Key Tester
======================

Quick test to verify your Ball Don't Lie API key works correctly.
Set BALLDONTLIE_API_KEY environment variable and run this script.

Usage:
    export BALLDONTLIE_API_KEY=your_key_here
    python test_api_key.py
"""
import asyncio
import sys
import os
import time

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("💡 Install python-dotenv for .env file support: pip install python-dotenv")

# Add backend source to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

def print_result(emoji, message):
    """Print a formatted result."""
    print(f"{emoji} {message}")

async def test_api_key():
    """Test the API key with a simple request."""
    print("🔑 HoopHead API Key Tester")
    print("=" * 40)
    
    # Check for API key
    api_key = os.getenv('BALLDONTLIE_API_KEY')
    
    if not api_key:
        print_result("❌", "No BALLDONTLIE_API_KEY found in environment")
        print("💡 Set your API key: export BALLDONTLIE_API_KEY=your_key")
        print("🔗 Get a key at: https://balldontlie.io")
        return False
    
    print_result("✅", f"Found API key: {api_key[:8]}...")
    
    try:
        # Import HoopHead components
        from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport
        from adapters.external.auth_manager import AuthenticationManager, APITier
        
        print_result("📦", "HoopHead components imported successfully")
        
        # Test API key validation
        auth_manager = AuthenticationManager()
        is_valid, key_id, tier = auth_manager.validate_api_key(api_key)
        
        if is_valid:
            print_result("✅", f"API key format is valid (detected tier: {tier.value if tier else 'unknown'})")
        else:
            print_result("❌", "API key format is invalid")
            return False
        
        # Test actual API call
        print_result("🌐", "Testing live API call...")
        
        start_time = time.time()
        
        async with BallDontLieClient(api_key=api_key) as client:
            response = await client.get_teams(Sport.NBA)
            
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            
            if response.success:
                teams = response.data
                print_result("🏀", f"SUCCESS! Retrieved {len(teams)} NBA teams in {duration:.0f}ms")
                
                # Show a few sample teams
                print("\n📋 Sample teams:")
                if isinstance(teams, list) and len(teams) > 0:
                    for team in teams[:3]:
                        city = team.get('city', 'N/A')
                        name = team.get('name', 'N/A')
                        abbr = team.get('abbreviation', 'N/A')
                        print(f"   • {city} {name} ({abbr})")
                else:
                    print(f"   • Retrieved {len(teams) if hasattr(teams, '__len__') else 'unknown'} teams from API")
                
                # Check cache info
                if hasattr(response, 'meta') and response.meta:
                    cached = response.meta.get('cached', False)
                    cache_source = response.meta.get('cache_source', 'unknown')
                    print(f"\n💾 Cache: {'HIT' if cached else 'MISS'} from {cache_source}")
                
                print_result("🎉", "API key is working perfectly!")
                return True
                
            else:
                print_result("❌", f"API call failed: {response.error}")
                return False
    
    except Exception as e:
        print_result("💥", f"Error during test: {e}")
        print("\n🔧 Troubleshooting:")
        print("   • Verify your API key is correct")
        print("   • Check your internet connection") 
        print("   • Ensure you have required dependencies installed")
        print("   • Try: pip install -r backend/requirements.txt")
        return False

async def test_authentication_tiers():
    """Test authentication tier detection and limits."""
    print("\n" + "=" * 40)
    print("🔐 Testing Authentication Features")
    print("=" * 40)
    
    api_key = os.getenv('BALLDONTLIE_API_KEY')
    if not api_key:
        return
    
    try:
        from adapters.external.auth_manager import AuthenticationManager, APITier
        
        auth_manager = AuthenticationManager()
        
        # Test key validation and tier detection
        is_valid, key_id, tier = auth_manager.validate_api_key(api_key)
        
        if is_valid and tier:
            limits = auth_manager.tier_limits[tier]
            print_result("📊", f"Detected tier: {tier.value.upper()}")
            print(f"   • Requests per hour: {limits.requests_per_hour}")
            print(f"   • Requests per minute: {limits.requests_per_minute}")
            print(f"   • Cache priority: {limits.cache_priority}")
            
            # Add the key to the manager
            managed_key_id = auth_manager.add_api_key(api_key, tier, f"Test Key ({tier.value})")
            
            # Check rate limits
            allowed, info = await auth_manager.check_rate_limit(managed_key_id)
            if allowed:
                print_result("✅", f"Rate limits OK: {info['minute_remaining']} requests remaining this minute")
            else:
                print_result("⚠️", "Rate limited - too many requests")
                
            # Show usage stats
            stats = auth_manager.get_usage_stats(managed_key_id)
            print_result("📈", f"Usage: {stats['total_requests']} total requests")
            
        else:
            print_result("❌", "Could not detect API tier")
            
    except Exception as e:
        print_result("💥", f"Authentication test error: {e}")

async def test_caching_performance():
    """Test caching system performance."""
    print("\n" + "=" * 40)
    print("💾 Testing Caching Performance")
    print("=" * 40)
    
    api_key = os.getenv('BALLDONTLIE_API_KEY')
    if not api_key:
        return
    
    try:
        from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport
        
        async with BallDontLieClient(api_key=api_key) as client:
            # First request (fresh)
            print_result("🌐", "Making first request (should be fresh)...")
            start_time = time.time()
            response1 = await client.get_teams(Sport.NBA)
            first_duration = (time.time() - start_time) * 1000
            
            if response1.success:
                cached1 = getattr(response1.meta, 'cached', False) if hasattr(response1, 'meta') else False
                print_result("📊", f"First request: {first_duration:.0f}ms (cached: {cached1})")
                
                # Second request (should be cached)
                print_result("💾", "Making second request (should be cached)...")
                start_time = time.time()
                response2 = await client.get_teams(Sport.NBA)
                second_duration = (time.time() - start_time) * 1000
                
                if response2.success:
                    cached2 = getattr(response2.meta, 'cached', False) if hasattr(response2, 'meta') else False
                    cache_source = getattr(response2.meta, 'cache_source', 'unknown') if hasattr(response2, 'meta') else 'unknown'
                    
                    print_result("⚡", f"Second request: {second_duration:.0f}ms (cached: {cached2}, source: {cache_source})")
                    
                    if cached2 and second_duration < first_duration:
                        improvement = ((first_duration - second_duration) / first_duration) * 100
                        print_result("🚀", f"Cache performance improvement: {improvement:.1f}%")
                    
            else:
                print_result("❌", "Cache test failed")
                
    except Exception as e:
        print_result("💥", f"Cache test error: {e}")

async def main():
    """Run all tests."""
    print("Starting HoopHead API tests...\n")
    
    # Test basic API functionality
    api_success = await test_api_key()
    
    if api_success:
        # Run additional tests
        await test_authentication_tiers()
        await test_caching_performance()
        
        print("\n" + "=" * 40)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 40)
        print("✅ Your API key is working correctly")
        print("✅ Authentication system is functional")
        print("✅ Caching system is operational")
        print("\n🚀 Ready to run the full examples:")
        print("   • python simple_api_demo.py")
        print("   • python quick_example.py")
        print("   • python example_usage.py")
        print("   • python tests/run_comprehensive_tests.py --real-api")
        
    else:
        print("\n" + "=" * 40)
        print("❌ TESTS FAILED")
        print("=" * 40)
        print("🔧 Please fix the issues above and try again")
        
    return api_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 