#!/usr/bin/env python3
"""
HoopHead Multi-Sport API Platform - Usage Examples
==================================================

This script demonstrates how to use the HoopHead API client to query
NBA, NFL, MLB, NHL, and EPL data with authentication, caching, and
error handling.

Usage:
    python example_usage.py
    
    # With real API (requires BALLDONTLIE_API_KEY environment variable)
    BALLDONTLIE_API_KEY=your_api_key_here python example_usage.py
"""

import asyncio
import os
import sys
from typing import List

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("💡 Install python-dotenv for .env file support: pip install python-dotenv")

# Add backend source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Import the HoopHead platform components
from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport, APIResponse
from adapters.external.auth_manager import AuthenticationManager, APITier
from domain.services.player_service import PlayerService, PlayerSearchCriteria
from domain.services.team_service import TeamService, TeamSearchCriteria
from domain.services.game_service import GameService, GameSearchCriteria
from domain.services.search_service import SearchService
from domain.models.base import SportType

# Color coding for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}🏀 {text}{Colors.ENDC}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


async def example_1_basic_api_client():
    """Example 1: Basic API client usage with environment API key."""
    print_header("Example 1: Basic API Client Usage")
    
    try:
        # Get API key from environment 
        api_key = os.getenv('BALLDONTLIE_API_KEY')
        
        if not api_key:
            print_warning("No BALLDONTLIE_API_KEY found - skipping live API example")
            print_info("Set environment variable to test with real data")
            return
            
        # Create client with real API key
        async with BallDontLieClient(api_key=api_key) as client:
            print_info("Fetching NBA teams...")
            
            # Get NBA teams
            teams_response = await client.get_teams(Sport.NBA)
            
            if teams_response.success:
                print_success(f"Found {len(teams_response.data)} NBA teams")
                
                # Show first 5 teams
                for team in teams_response.data[:5]:
                    name = team.get('name', 'Unknown')
                    city = team.get('city', 'Unknown')
                    print(f"   🏀 {city} {name}")
                
                # Check if response was cached
                if hasattr(teams_response, 'meta') and teams_response.meta.get('cached'):
                    cache_source = teams_response.meta.get('cache_source', 'unknown')
                    print_info(f"Response served from {cache_source} cache")
                else:
                    print_info("Fresh API response")
            else:
                print_error("Failed to fetch NBA teams")
    
    except Exception as e:
        print_error(f"Error in basic client example: {e}")


async def example_2_authentication_and_tiers():
    """Example 2: Authentication manager and API tiers."""
    print_header("Example 2: Authentication & API Tiers")
    
    try:
        # Initialize authentication manager
        auth_manager = AuthenticationManager()
        
        # Add different tier API keys for demonstration
        free_key_id = auth_manager.add_api_key("bdl_demo_free_" + os.urandom(8).hex(), APITier.FREE, "Demo Free Key")
        allstar_key_id = auth_manager.add_api_key("bdl_demo_allstar_" + os.urandom(8).hex(), APITier.ALL_STAR, "Demo All-Star Key")
        
        print_success("Added demonstration API keys")
        
        # Show tier information
        for tier in [APITier.FREE, APITier.ALL_STAR, APITier.GOAT, APITier.ENTERPRISE]:
            limits = auth_manager.tier_limits[tier]
            print(f"   📊 {tier.value.upper()}: {limits.requests_per_hour}/hour, {limits.requests_per_minute}/min")
        
        # Check rate limits
        print_info("Checking rate limits...")
        
        for key_id, tier_name in [(free_key_id, "FREE"), (allstar_key_id, "ALL-STAR")]:
            allowed, info = await auth_manager.check_rate_limit(key_id)
            if allowed:
                print_success(f"{tier_name} tier: {info['minute_remaining']} requests remaining this minute")
            else:
                print_warning(f"{tier_name} tier: Rate limited")
        
        # Show usage statistics
        print_info("Usage statistics:")
        for key_id, tier_name in [(free_key_id, "FREE"), (allstar_key_id, "ALL-STAR")]:
            stats = auth_manager.get_usage_stats(key_id)
            print(f"   📈 {tier_name}: {stats['total_requests']} total requests")
    
    except Exception as e:
        print_error(f"Error in authentication example: {e}")


async def example_3_multi_sport_queries():
    """Example 3: Multi-sport data queries."""
    print_header("Example 3: Multi-Sport Data Queries")
    
    try:
        # Create client with authentication (uses environment API key if available)
        api_key = os.getenv('BALLDONTLIE_API_KEY')
        if api_key:
            print_info(f"Using real API key: {api_key[:8]}...")
        else:
            print_warning("No API key found - using mock data")
        
        async with BallDontLieClient(api_key=api_key) as client:
            
            # Query each sport
            sports_to_test = [
                (Sport.NBA, "🏀 NBA"),
                (Sport.NFL, "🏈 NFL"), 
                (Sport.MLB, "⚾ MLB"),
                (Sport.NHL, "🏒 NHL"),
                (Sport.EPL, "⚽ EPL")
            ]
            
            for sport, emoji_name in sports_to_test:
                print_info(f"Querying {emoji_name} teams...")
                
                try:
                    teams_response = await client.get_teams(sport)
                    if teams_response.success:
                        team_count = len(teams_response.data)
                        print_success(f"{emoji_name}: {team_count} teams found")
                        
                        # Show a sample team
                        if teams_response.data:
                            sample_team = teams_response.data[0]
                            team_name = sample_team.get('name', 'Unknown')
                            print(f"   📝 Sample: {team_name}")
                    else:
                        print_warning(f"{emoji_name}: No data available")
                
                except Exception as e:
                    print_error(f"{emoji_name}: {e}")
    
    except Exception as e:
        print_error(f"Error in multi-sport example: {e}")


async def example_4_domain_services():
    """Example 4: Using domain services for business logic."""
    print_header("Example 4: Domain Services & Business Logic")
    
    try:
        # Initialize services
        api_key = os.getenv('BALLDONTLIE_API_KEY')
        async with BallDontLieClient(api_key=api_key) as client:
            
            # Create domain services
            player_service = PlayerService(api_client=client)
            team_service = TeamService(api_client=client)
            search_service = SearchService(
                player_service=player_service,
                team_service=team_service,
                game_service=GameService(api_client=client)
            )
            
            print_info("Domain services initialized")
            
            # Example: Search for LeBron James
            print_info("Searching for LeBron James...")
            
            criteria = PlayerSearchCriteria(
                name="LeBron",
                sport=SportType.NBA
            )
            
            players = await player_service.search_players(criteria)
            if players:
                print_success(f"Found {len(players)} players matching 'LeBron'")
                for player in players[:3]:  # Show first 3
                    print(f"   👤 {player.full_name} - {player.position}")
            else:
                print_warning("No players found matching 'LeBron'")
            
            # Example: Get Lakers team info
            print_info("Searching for Lakers...")
            
            team_criteria = TeamSearchCriteria(
                name="Lakers",
                sport=SportType.NBA
            )
            
            teams = await team_service.get_teams(team_criteria)
            if teams:
                lakers = teams[0]
                print_success(f"Found team: {lakers.full_name}")
                print(f"   🏠 City: {lakers.city}")
                print(f"   📝 Abbreviation: {lakers.abbreviation}")
            else:
                print_warning("No teams found matching 'Lakers'")
    
    except Exception as e:
        print_error(f"Error in domain services example: {e}")


async def example_5_cache_performance():
    """Example 5: Cache performance demonstration."""
    print_header("Example 5: Cache Performance Demo")
    
    try:
        api_key = os.getenv('BALLDONTLIE_API_KEY')
        async with BallDontLieClient(api_key=api_key) as client:
            
            # First request (should be fresh)
            print_info("Making first request to NBA teams...")
            import time
            
            start_time = time.time()
            response1 = await client.get_teams(Sport.NBA)
            end_time = time.time()
            
            first_duration = (end_time - start_time) * 1000
            
            if response1.success:
                print_success(f"First request: {first_duration:.2f}ms")
                if hasattr(response1, 'meta'):
                    cached = response1.meta.get('cached', False)
                    print_info(f"Cached: {cached}")
            
            # Second request (should be cached)
            print_info("Making second request (should be cached)...")
            
            start_time = time.time()
            response2 = await client.get_teams(Sport.NBA)
            end_time = time.time()
            
            second_duration = (end_time - start_time) * 1000
            
            if response2.success:
                print_success(f"Second request: {second_duration:.2f}ms")
                if hasattr(response2, 'meta'):
                    cached = response2.meta.get('cached', False)
                    cache_source = response2.meta.get('cache_source', 'unknown')
                    print_info(f"Cached: {cached} (source: {cache_source})")
                
                # Show performance improvement
                if first_duration > 0 and second_duration > 0:
                    improvement = ((first_duration - second_duration) / first_duration) * 100
                    print_success(f"Cache performance improvement: {improvement:.1f}%")
    
    except Exception as e:
        print_error(f"Error in cache performance example: {e}")


async def example_6_error_handling():
    """Example 6: Error handling and resilience."""
    print_header("Example 6: Error Handling & Resilience")
    
    try:
        # Get real API key for testing
        api_key = os.getenv('BALLDONTLIE_API_KEY')
        
        if api_key:
            # Test with invalid API key 
            print_info("Testing with invalid API key...")
            
            try:
                async with BallDontLieClient(api_key="invalid_key_123") as client:
                    response = await client.get_teams(Sport.NBA)
                    if response.success:
                        print_success("Request succeeded despite invalid key (fallback working)")
                    else:
                        print_warning("Request failed as expected with invalid key")
            except Exception as e:
                print_info(f"Exception handled gracefully: {type(e).__name__}")
        else:
            print_warning("No API key found - skipping error handling tests")
            
        # Test rate limiting with auth manager
        print_info("Testing authentication manager rate limiting...")
        
        auth_manager = AuthenticationManager()
        key_id = auth_manager.add_api_key("bdl_rate_limit_" + os.urandom(8).hex(), APITier.FREE, "Rate Limit Test")
        
        # Simulate rate limit exhaustion
        for i in range(6):  # FREE tier allows 5/minute
            await auth_manager.record_request(key_id, success=True)
        
        allowed, info = await auth_manager.check_rate_limit(key_id)
        if not allowed:
            print_success("Rate limiting working correctly - requests blocked")
        else:
            print_warning("Rate limiting may not be working properly")
    
    except Exception as e:
        print_error(f"Error in error handling example: {e}")


async def main():
    """Run all examples."""
    print_header("HoopHead Multi-Sport API Platform - Usage Examples")
    print(f"{Colors.OKCYAN}🚀 Welcome to HoopHead! Here are some practical examples:{Colors.ENDC}")
    
    # Check for API key
    api_key = os.getenv('BALLDONTLIE_API_KEY')
    if api_key:
        print_success(f"Real API key detected: {api_key[:8]}...")
        print_info("Examples will use real Ball Don't Lie API data")
    else:
        print_warning("No API key found in BALLDONTLIE_API_KEY environment variable")
        print_info("Examples will use mock data and demonstrate functionality")
    
    # Run examples
    examples = [
        example_1_basic_api_client,
        example_2_authentication_and_tiers,
        example_3_multi_sport_queries,
        example_4_domain_services,
        example_5_cache_performance,
        example_6_error_handling
    ]
    
    for i, example in enumerate(examples, 1):
        try:
            await example()
        except Exception as e:
            print_error(f"Example {i} failed: {e}")
        
        # Add separator
        if i < len(examples):
            print(f"\n{'-' * 60}")
    
    # Final summary
    print_header("Summary")
    print(f"{Colors.OKGREEN}🎉 Examples completed! Here's what you've seen:{Colors.ENDC}")
    print("   • Basic API client usage with caching")
    print("   • Authentication tiers and rate limiting")
    print("   • Multi-sport data queries (NBA, NFL, MLB, NHL, EPL)")
    print("   • Domain services for business logic")
    print("   • Cache performance improvements")
    print("   • Error handling and system resilience")
    
    print(f"\n{Colors.OKCYAN}🔧 To get started with your own code:{Colors.ENDC}")
    print("   1. Set BALLDONTLIE_API_KEY environment variable")
    print("   2. Import: from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport")
    print("   3. Use: async with BallDontLieClient(api_key='your_key') as client:")
    print("   4. Query: response = await client.get_teams(Sport.NBA)")
    
    print(f"\n{Colors.BOLD}Happy coding! 🏀🏈⚾🏒⚽{Colors.ENDC}")


if __name__ == "__main__":
    """Run examples when executed directly."""
    asyncio.run(main()) 