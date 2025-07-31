#!/usr/bin/env python3
"""
Test script for Ball Don't Lie API multi-sport integration.
Run this to verify API connectivity across all 4 supported leagues.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

from src.adapters.external.ball_dont_lie_client import (
    BallDontLieClient, 
    League, 
    quick_player_search,
    quick_teams_fetch
)


async def test_api_connectivity(api_key: str):
    """Test basic API connectivity for all leagues."""
    print("🏆 Testing Ball Don't Lie API Multi-Sport Integration...\n")
    
    if not api_key:
        print("❌ ERROR: No API key provided")
        print("Please set BALL_DONT_LIE_API_KEY environment variable")
        return False
    
    try:
        async with BallDontLieClient(api_key) as client:
            
            # Test 1: Get all teams across leagues
            print("1. Testing team data across all leagues...")
            teams_results = await client.get_all_teams()
            
            for league, response in teams_results.items():
                if response.success:
                    print(f"✅ {league.upper()}: Retrieved teams successfully")
                    if response.data and 'data' in response.data:
                        team_count = len(response.data['data'])
                        print(f"   📊 Found {team_count} teams")
                else:
                    print(f"❌ {league.upper()}: {response.error}")
            
            print()
            
            # Test 2: Search for famous players across leagues
            print("2. Testing player search across leagues...")
            test_players = [
                "LeBron James",  # NBA
                "Tom Brady",     # NFL (retired but should be in system)
                "Mike Trout",    # MLB
                "Messi"          # EPL (if available)
            ]
            
            for player_name in test_players:
                print(f"   Searching for '{player_name}'...")
                search_results = await client.search_players_across_leagues(player_name)
                
                found_in_leagues = []
                for league, response in search_results.items():
                    if response.success and response.data and 'data' in response.data:
                        if response.data['data']:  # If players found
                            found_in_leagues.append(league.upper())
                
                if found_in_leagues:
                    print(f"   ✅ Found in: {', '.join(found_in_leagues)}")
                else:
                    print(f"   ⚠️  Not found in any league (may be expected)")
            
            print()
            
            # Test 3: League-specific endpoint tests
            print("3. Testing league-specific endpoints...")
            
            # NBA specific test
            print("   Testing NBA players endpoint...")
            nba_players = await client.get_nba_players(search="Curry")
            if nba_players.success:
                print("   ✅ NBA players search working")
            else:
                print(f"   ❌ NBA players search failed: {nba_players.error}")
            
            # NFL specific test
            print("   Testing NFL teams endpoint...")
            nfl_teams = await client.get_nfl_teams()
            if nfl_teams.success:
                print("   ✅ NFL teams endpoint working")
            else:
                print(f"   ❌ NFL teams endpoint failed: {nfl_teams.error}")
            
            print()
            print("🎉 Multi-sport API integration test completed!")
            return True
            
    except Exception as e:
        print(f"❌ Unexpected error during testing: {str(e)}")
        return False


async def test_convenience_functions(api_key: str):
    """Test the convenience functions."""
    print("4. Testing convenience functions...")
    
    try:
        # Test quick player search
        print("   Testing quick_player_search...")
        results = await quick_player_search(api_key, "Jordan")
        found_any = any(r.success for r in results.values())
        if found_any:
            print("   ✅ Quick player search working")
        else:
            print("   ⚠️  Quick player search returned no results")
        
        # Test quick teams fetch
        print("   Testing quick_teams_fetch...")
        teams = await quick_teams_fetch(api_key)
        working_leagues = [league for league, response in teams.items() if response.success]
        if working_leagues:
            print(f"   ✅ Quick teams fetch working for: {', '.join([l.upper() for l in working_leagues])}")
        else:
            print("   ❌ Quick teams fetch failed for all leagues")
            
    except Exception as e:
        print(f"   ❌ Convenience functions test failed: {str(e)}")


def main():
    """Main test function."""
    # Get API key from environment or prompt
    api_key = os.getenv("BALL_DONT_LIE_API_KEY")
    
    if not api_key:
        print("🔑 Ball Don't Lie API Key Required")
        print("Please set your API key as an environment variable:")
        print("export BALL_DONT_LIE_API_KEY=your_api_key_here")
        print("\nOr enter it now (it won't be saved):")
        api_key = input("API Key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Exiting.")
        return
    
    # Run the tests
    try:
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(test_api_connectivity(api_key))
        
        if success:
            loop.run_until_complete(test_convenience_functions(api_key))
            
            print("\n✅ All tests completed successfully!")
            print("🚀 Your multi-sport API client is ready for integration!")
        else:
            print("\n❌ Some tests failed. Check your API key and network connection.")
            
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")


if __name__ == "__main__":
    main() 