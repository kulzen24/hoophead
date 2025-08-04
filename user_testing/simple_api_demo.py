#!/usr/bin/env python3
"""
HoopHead API Usage Demo - Simple Examples
=========================================

This shows you exactly how to use the HoopHead API platform.
Set BALLDONTLIE_API_KEY environment variable to test with real data!
"""
import asyncio
import sys
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("💡 Install python-dotenv for .env file support: pip install python-dotenv")

# Add backend source to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Check for API key
api_key = os.getenv('BALLDONTLIE_API_KEY')
if api_key:
    print(f"✅ Found API key: {api_key[:8]}...")
    print("🌐 Will demonstrate with REAL Ball Don't Lie API data!")
else:
    print("⚠️  No BALLDONTLIE_API_KEY found in environment")
    print("📚 Showing usage patterns only (no live API calls)")
print()

print("🏀 HoopHead Multi-Sport API Platform - Simple Demo")
print("=" * 60)

# Show the basic imports you need
print("\n📚 1. BASIC IMPORTS")
print("=" * 30)

print("""
from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport
from adapters.external.auth_manager import AuthenticationManager, APITier

# Available Sports:
• Sport.NBA  - National Basketball Association
• Sport.NFL  - National Football League  
• Sport.MLB  - Major League Baseball
• Sport.NHL  - National Hockey League
• Sport.EPL  - English Premier League
""")

# Show the basic usage pattern
print("\n🔧 2. BASIC USAGE PATTERN")
print("=" * 30)

print("""
# Step 1: Get your API key from https://balldontlie.io
api_key = "your_ball_dont_lie_api_key_here"

# Step 2: Create the client
async with BallDontLieClient(api_key=api_key) as client:
    
    # Step 3: Make requests
    teams_response = await client.get_teams(Sport.NBA)
    
    # Step 4: Use the data
    if teams_response.success:
        teams = teams_response.data
        print(f"Found {len(teams)} NBA teams!")
        
        for team in teams[:5]:  # Show first 5
            print(f"- {team['city']} {team['name']}")
""")

# Show available methods
print("\n⚡ 3. AVAILABLE METHODS")
print("=" * 30)

methods = [
    ("client.get_teams(sport)", "Get all teams for a sport"),
    ("client.get_players(sport, search='name')", "Search for players by name"),
    ("client.get_games(sport, seasons=[2024])", "Get games for specific seasons"),
    ("client.get_player_stats(sport, player_id)", "Get player statistics"),
]

for method, description in methods:
    print(f"• {method:<35} - {description}")

# Show authentication tiers
print("\n🔐 4. AUTHENTICATION TIERS")
print("=" * 30)

print("""
Ball Don't Lie API has different tiers:

• FREE      - 300 requests/hour, 5/minute
• ALL-STAR  - 3,600 requests/hour, 60/minute  
• GOAT      - 36,000 requests/hour, 600/minute
• ENTERPRISE- 36,000 requests/hour, 600/minute

Higher tiers get better cache priority and performance!
""")

# Show response structure
print("\n📊 5. RESPONSE STRUCTURE")
print("=" * 30)

print("""
All API calls return an APIResponse object:

response = await client.get_teams(Sport.NBA)

response.success    # True if successful
response.data       # List of teams/players/games
response.error      # Error message if failed
response.sport      # Which sport was queried
response.meta       # Cache info, timing, etc.

Example team data:
{
    "id": 1,
    "name": "Lakers", 
    "city": "Los Angeles",
    "abbreviation": "LAL",
    "conference": "West",
    "division": "Pacific"
}
""")

# Show caching features  
print("\n💾 6. INTELLIGENT CACHING")
print("=" * 30)

print("""
HoopHead automatically caches responses for better performance:

• Redis Cache: Hot data, sub-3ms retrieval
• File Cache: Historical data, persistent storage
• Tier-Based: Higher auth tiers get Redis priority
• Automatic: No configuration needed
• Compression: Large responses automatically compressed

Cache info in response.meta:
- cached: True/False
- cache_source: "redis" or "file"  
- cache_latency_ms: How fast the cache was
- data_age_seconds: How old the cached data is
""")

# Show error handling
print("\n🛡️ 7. ERROR HANDLING")
print("=" * 30)

print("""
Built-in error handling with graceful fallbacks:

try:
    response = await client.get_teams(Sport.NBA)
    if response.success:
        # Process data
        teams = response.data
    else:
        print(f"Error: {response.error}")
        
except APIRateLimitError:
    print("Rate limited - try again later")
except APIConnectionError:
    print("Connection failed - check internet")
except Exception as e:
    print(f"Other error: {e}")

Errors are handled gracefully with detailed context.
""")

# Show domain services
print("\n🏗️ 8. DOMAIN SERVICES (Advanced)")
print("=" * 30)

print("""
Use domain services for business logic:

from domain.services.player_service import PlayerService, PlayerSearchCriteria
from domain.services.team_service import TeamService, TeamSearchCriteria
from domain.models.base import SportType

# Initialize services
player_service = PlayerService(api_client=client)
team_service = TeamService(api_client=client)

# Search with criteria
criteria = PlayerSearchCriteria(name="LeBron", sport=SportType.NBA)
players = await player_service.search_players(criteria)

# Get domain models with business logic
for player in players:
    print(f"{player.full_name} - {player.height_inches} inches")
""")

# Show testing
print("\n🧪 9. COMPREHENSIVE TESTING")
print("=" * 30)

print("""
Run the test suite to validate everything:

# Run all tests
python tests/run_comprehensive_tests.py

# Run specific test categories  
python tests/run_comprehensive_tests.py --no-e2e --no-performance

# Run with real API (requires BALLDONTLIE_API_KEY)
BALLDONTLIE_API_KEY=your_key python tests/run_comprehensive_tests.py --real-api

# Generate coverage report
python tests/run_comprehensive_tests.py --coverage-threshold 90
""")

# Final getting started
print("\n🚀 10. GETTING STARTED")
print("=" * 30)

print("""
Ready to start? Here's your checklist:

1. ✅ Get API key: https://balldontlie.io
2. ✅ Set environment: export BALLDONTLIE_API_KEY=your_key  
3. ✅ Install dependencies: pip install -r backend/requirements.txt
4. ✅ Run example: python simple_api_demo.py
5. ✅ Try real queries: Modify the examples above
6. ✅ Run tests: python tests/run_comprehensive_tests.py --real-api

🎯 Pro Tips:
• Start with NBA (most reliable data)
• Use higher auth tiers for better performance  
• Check response.meta for cache statistics
• Run tests regularly to catch issues early
• Use domain services for complex business logic

Happy coding! 🏀🏈⚾🏒⚽
""")

async def live_api_demo():
    """Run a live API demonstration if key is available."""
    if not api_key:
        return
        
    print("\n🔴 LIVE API DEMONSTRATION")
    print("=" * 30)
    
    try:
        from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport
        
        async with BallDontLieClient(api_key=api_key) as client:
            print("🔍 Making real API call to get NBA teams...")
            
            response = await client.get_teams(Sport.NBA)
            
            if response.success:
                teams_data = response.data
                
                # Handle the API response format - extract the actual teams list
                if isinstance(teams_data, dict) and 'data' in teams_data:
                    teams = teams_data['data']
                else:
                    teams = teams_data
                
                print(f"✅ SUCCESS! Retrieved {len(teams)} NBA teams")
                
                print("\n📋 Sample teams:")
                for team in teams[:5]:
                    city = team.get('city', 'N/A')
                    name = team.get('name', 'N/A') 
                    abbr = team.get('abbreviation', 'N/A')
                    print(f"   🏀 {city} {name} ({abbr})")
                
                # Show cache info
                if hasattr(response, 'meta') and response.meta:
                    cached = response.meta.get('cached', False)
                    cache_source = response.meta.get('cache_source', 'unknown')
                    latency = response.meta.get('cache_latency_ms', 'unknown')
                    print(f"\n💾 Cache: {'HIT' if cached else 'MISS'} from {cache_source} ({latency}ms)")
                else:
                    print(f"\n🌐 Fresh API response")
                    
            else:
                print(f"❌ API call failed: {response.error}")
                
    except Exception as e:
        print(f"❌ Error during live demo: {e}")
        print("💡 Tip: Verify your API key is valid at https://balldontlie.io")


async def main():
    """Run the demo and optionally the live API test."""
    await live_api_demo()


print("\n" + "=" * 60)
print("🎉 Demo complete! You're ready to build amazing sports apps!")
print("=" * 60)

# Run live demo if this file is executed directly
if __name__ == "__main__" and api_key:
    print(f"\n🚀 Running live API demonstration...")
    asyncio.run(main()) 