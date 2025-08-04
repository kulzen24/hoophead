#!/usr/bin/env python3
"""
Quick HoopHead API Example - Get NBA Teams
==========================================

This is the simplest way to use HoopHead to query NBA team data.
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

from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport
from adapters.external.auth_manager import AuthenticationManager, APITier


async def simple_nba_teams_example():
    """Simple example: Get NBA teams with authentication."""
    print("🏀 HoopHead Quick Example - NBA Teams\n")
    
    # Check for real API key first
    api_key = os.getenv('BALLDONTLIE_API_KEY')
    
    if api_key:
        print(f"✅ Using real API key: {api_key[:8]}...")
        print("🌐 Will fetch REAL NBA team data!\n")
    else:
        print("⚠️  No BALLDONTLIE_API_KEY found in environment")
        print("📚 To get real data: export BALLDONTLIE_API_KEY=your_key")
        print("🔗 Get key at: https://balldontlie.io\n")
        return  # Skip this example if no real key
    
    # Use the API client with real key
    async with BallDontLieClient(api_key=api_key) as client:
        print("🔍 Fetching NBA teams...")
        
        # Get NBA teams
        response = await client.get_teams(Sport.NBA)
        
        if response.success:
            teams_data = response.data
            
            # Handle the API response format - extract the actual teams list
            if isinstance(teams_data, dict) and 'data' in teams_data:
                teams = teams_data['data']
            else:
                teams = teams_data
            
            print(f"✅ Successfully retrieved {len(teams)} NBA teams!\n")
            
            # Show first 10 teams as examples
            print("📋 First 10 NBA Teams:")
            print("-" * 50)
            
            for i, team in enumerate(teams[:10], 1):
                city = team.get('city', 'N/A')
                name = team.get('name', 'N/A')
                abbreviation = team.get('abbreviation', 'N/A')
                conference = team.get('conference', 'N/A')
                print(f"{i:2d}. {city} {name} ({abbreviation}) - {conference}")
            
            # Show cache info if available
            if hasattr(response, 'meta') and response.meta:
                cached = response.meta.get('cached', False)
                if cached:
                    cache_source = response.meta.get('cache_source', 'unknown')
                    print(f"\n💾 Response served from {cache_source} cache")
                else:
                    print(f"\n🌐 Fresh API response")
        else:
            print("❌ Failed to fetch NBA teams")
    
    print(f"\n🎉 Example complete! Here's how the code works:")
    print("   1. Set up AuthenticationManager and add an API key")
    print("   2. Create BallDontLieClient with the key")
    print("   3. Call client.get_teams(Sport.NBA)")
    print("   4. Process the response data")


async def simple_player_search_example():
    """Simple example: Search for a specific player."""
    print("\n" + "="*60)
    print("🔍 Bonus Example - Player Search")
    print("="*60)
    
    # Check for real API key
    api_key = os.getenv('BALLDONTLIE_API_KEY')
    
    if not api_key:
        print("⚠️  Skipping player search - no API key found")
        return
    
    async with BallDontLieClient(api_key=api_key) as client:
        print("🔍 Searching for 'LeBron'...")
        
        # Search for LeBron using the get_players method with search parameter
        response = await client.get_players(Sport.NBA, search="LeBron")
        
        if response.success and response.data:
            players_data = response.data
            
            # Handle the API response format - extract the actual players list
            if isinstance(players_data, dict) and 'data' in players_data:
                players = players_data['data']
            else:
                players = players_data
            
            print(f"✅ Found {len(players)} players matching 'LeBron':\n")
            
            for player in players:
                first_name = player.get('first_name', '')
                last_name = player.get('last_name', '')
                height = player.get('height', 'N/A')
                position = player.get('position', 'N/A')
                team = player.get('team', {})
                team_name = team.get('name', 'N/A') if team else 'N/A'
                
                print(f"   👤 {first_name} {last_name}")
                print(f"      Height: {height}, Position: {position}")
                print(f"      Team: {team_name}\n")
        else:
            print("⚠️  No players found or search failed")


async def main():
    """Run the quick examples."""
    await simple_nba_teams_example()
    await simple_player_search_example()
    
    print("\n" + "="*60)
    print("🚀 Ready to build your own queries?")
    print("="*60)
    print("📚 Available Sports:")
    print("   • Sport.NBA  - National Basketball Association")
    print("   • Sport.NFL  - National Football League") 
    print("   • Sport.MLB  - Major League Baseball")
    print("   • Sport.NHL  - National Hockey League")
    print("   • Sport.EPL  - English Premier League")
    
    print("\n🔧 Available Methods:")
    print("   • client.get_teams(sport)              - Get all teams")
    print("   • client.search_players(sport, query)  - Search players")
    print("   • client.get_games(sport, seasons)     - Get games")
    print("   • client.get_player_stats(sport, ...)  - Get player stats")
    
    print("\n💡 Pro Tips:")
    print("   • Higher authentication tiers get better cache priority")
    print("   • Responses are automatically cached for performance")
    print("   • All methods return APIResponse objects with .success and .data")
    print("   • Error handling is built-in with graceful fallbacks")
    
    print("\n🎯 Next Steps:")
    print("   1. Get a real Ball Don't Lie API key: https://balldontlie.io")
    print("   2. Set environment variable: export BALLDONTLIE_API_KEY=your_key")
    print("   3. Run: python quick_example.py")
    print("   4. Explore the comprehensive test suite: python tests/run_comprehensive_tests.py")


if __name__ == "__main__":
    asyncio.run(main()) 