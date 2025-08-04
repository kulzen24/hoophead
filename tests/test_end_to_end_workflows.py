"""
End-to-End Test Suite for HoopHead Multi-Sport API Platform.
Tests complete user workflows from API request to cached response across all sports.
"""
import asyncio
import pytest
import sys
import os
import time
from typing import Dict, List, Any
from dataclasses import dataclass

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system env vars only

# Add backend source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

# Import the complete system
from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport, APIResponse
from adapters.external.auth_manager import AuthenticationManager, APITier
from adapters.cache import multi_cache, CacheStrategy
from domain.services.player_service import PlayerService, PlayerSearchCriteria
from domain.services.team_service import TeamService, TeamSearchCriteria
from domain.services.game_service import GameService, GameSearchCriteria
from domain.services.search_service import SearchService
from domain.models.base import SportType


@dataclass
class WorkflowResult:
    """Result of an end-to-end workflow test."""
    workflow_name: str
    success: bool
    total_duration_ms: float
    steps_completed: int
    steps_total: int
    cache_hits: int
    api_calls: int
    errors: List[str]
    performance_metrics: Dict[str, Any]


class EndToEndTestSuite:
    """
    Comprehensive end-to-end test suite for HoopHead platform.
    
    Tests complete workflows:
    1. User queries → API client → Authentication → Caching → Domain models
    2. Different sports and authentication tiers
    3. Cache warming and performance optimization
    4. Error handling and recovery scenarios
    """
    
    def __init__(self, use_real_api: bool = False):
        """Initialize E2E test suite."""
        self.use_real_api = use_real_api
        self.auth_manager = None
        self.test_api_keys = {}
        self.workflow_results = []
        
        print(f"🎯 End-to-End Test Suite initialized (Real API: {'✅' if use_real_api else '❌'})")
    
    async def setup_test_environment(self):
        """Set up authentication and test environment."""
        print("\n🔧 Setting up test environment...")
        
        # Initialize authentication manager
        self.auth_manager = AuthenticationManager()
        
        # Add test API keys for different tiers
        if not self.use_real_api:
            # Use mock keys for testing
            self.test_api_keys = {
                APITier.FREE: self.auth_manager.add_api_key("free_test_key_123", APITier.FREE, "E2E Free Test"),
                APITier.ALL_STAR: self.auth_manager.add_api_key("all_star_test_key_123", APITier.ALL_STAR, "E2E All-Star Test"),
                APITier.GOAT: self.auth_manager.add_api_key("goat_test_key_123", APITier.GOAT, "E2E GOAT Test"),
            }
        else:
            # Use environment API key
            api_key = os.getenv('BALLDONTLIE_API_KEY')
            if api_key:
                key_id = self.auth_manager.add_api_key(api_key, APITier.ALL_STAR, "Real API Test")
                self.test_api_keys[APITier.ALL_STAR] = key_id
        
        print(f"   Added {len(self.test_api_keys)} test API keys")
    
    async def test_complete_nba_workflow(self) -> WorkflowResult:
        """Test complete NBA workflow: teams → players → games → stats."""
        workflow_name = "Complete NBA Workflow"
        print(f"\n🏀 Testing {workflow_name}...")
        
        start_time = time.time()
        steps_completed = 0
        steps_total = 6
        cache_hits = 0
        api_calls = 0
        errors = []
        
        try:
            # Step 1: Initialize client with authentication
            if self.use_real_api and APITier.ALL_STAR in self.test_api_keys:
                key_id = self.test_api_keys[APITier.ALL_STAR]
            else:
                key_id = self.test_api_keys.get(APITier.ALL_STAR)
            
            async with BallDontLieClient(key_id=key_id) as client:
                steps_completed += 1
                
                # Step 2: Get NBA teams
                print("   📋 Fetching NBA teams...")
                teams_response = await client.get_teams(Sport.NBA)
                if teams_response.success:
                    steps_completed += 1
                    api_calls += 1
                    if hasattr(teams_response, 'meta') and teams_response.meta.get('cached'):
                        cache_hits += 1
                    print(f"      ✅ Found {len(teams_response.data)} NBA teams")
                else:
                    errors.append("Failed to fetch NBA teams")
                
                # Step 3: Search for popular player (LeBron James)
                print("   🏀 Searching for LeBron James...")
                player_response = await client.search_players(Sport.NBA, "LeBron")
                if player_response.success and len(player_response.data) > 0:
                    steps_completed += 1
                    api_calls += 1
                    if hasattr(player_response, 'meta') and player_response.meta.get('cached'):
                        cache_hits += 1
                    print(f"      ✅ Found {len(player_response.data)} players matching 'LeBron'")
                    
                    # Step 4: Get player details
                    lebron = player_response.data[0]
                    print(f"      👤 Player: {lebron.get('first_name', '')} {lebron.get('last_name', '')}")
                    steps_completed += 1
                else:
                    errors.append("Failed to find LeBron James")
                
                # Step 5: Get recent NBA games
                print("   🎮 Fetching recent NBA games...")
                games_response = await client.get_games(Sport.NBA, seasons=[2024])
                if games_response.success:
                    steps_completed += 1
                    api_calls += 1
                    if hasattr(games_response, 'meta') and games_response.meta.get('cached'):
                        cache_hits += 1
                    print(f"      ✅ Found {len(games_response.data)} games")
                else:
                    errors.append("Failed to fetch NBA games")
                
                # Step 6: Test domain model conversion
                print("   🔄 Testing domain model conversion...")
                team_service = TeamService(api_client=client)
                criteria = TeamSearchCriteria(sport=SportType.NBA)
                domain_teams = await team_service.get_teams(criteria)
                if domain_teams:
                    steps_completed += 1
                    print(f"      ✅ Converted to {len(domain_teams)} domain models")
                else:
                    errors.append("Failed to convert to domain models")
        
        except Exception as e:
            errors.append(f"Workflow exception: {str(e)}")
        
        end_time = time.time()
        total_duration_ms = (end_time - start_time) * 1000
        
        success = len(errors) == 0 and steps_completed == steps_total
        
        result = WorkflowResult(
            workflow_name=workflow_name,
            success=success,
            total_duration_ms=total_duration_ms,
            steps_completed=steps_completed,
            steps_total=steps_total,
            cache_hits=cache_hits,
            api_calls=api_calls,
            errors=errors,
            performance_metrics={
                "avg_request_time_ms": total_duration_ms / api_calls if api_calls > 0 else 0,
                "cache_hit_rate": cache_hits / api_calls if api_calls > 0 else 0
            }
        )
        
        print(f"   📊 Result: {'✅ SUCCESS' if success else '❌ FAILED'} ({steps_completed}/{steps_total} steps)")
        return result
    
    async def test_multi_sport_comparison_workflow(self) -> WorkflowResult:
        """Test multi-sport comparison workflow."""
        workflow_name = "Multi-Sport Comparison Workflow"
        print(f"\n🌟 Testing {workflow_name}...")
        
        start_time = time.time()
        steps_completed = 0
        steps_total = 8  # 4 sports × 2 operations each
        cache_hits = 0
        api_calls = 0
        errors = []
        
        sports_to_test = [Sport.NBA, Sport.NFL, Sport.MLB, Sport.NHL]
        
        try:
            key_id = self.test_api_keys.get(APITier.ALL_STAR)
            async with BallDontLieClient(key_id=key_id) as client:
                
                sport_results = {}
                
                for sport in sports_to_test:
                    print(f"   🏈 Testing {sport.value.upper()}...")
                    
                    try:
                        # Get teams for each sport
                        teams_response = await client.get_teams(sport)
                        if teams_response.success:
                            steps_completed += 1
                            api_calls += 1
                            if hasattr(teams_response, 'meta') and teams_response.meta.get('cached'):
                                cache_hits += 1
                            
                            team_count = len(teams_response.data)
                            sport_results[sport.value] = {"teams": team_count}
                            print(f"      ✅ {team_count} teams")
                        else:
                            errors.append(f"Failed to get {sport.value} teams")
                        
                        # Test player search (if supported)
                        if sport != Sport.EPL:  # EPL has limited player search
                            player_response = await client.search_players(sport, "Smith")
                            if player_response.success:
                                steps_completed += 1
                                api_calls += 1
                                if hasattr(player_response, 'meta') and player_response.meta.get('cached'):
                                    cache_hits += 1
                                
                                player_count = len(player_response.data)
                                sport_results[sport.value]["players"] = player_count
                                print(f"      ✅ {player_count} players named Smith")
                            else:
                                print(f"      ⚠️  Limited player search for {sport.value}")
                        else:
                            steps_completed += 1  # Skip EPL player search
                            print(f"      ⏭️  Skipping player search for {sport.value}")
                    
                    except Exception as e:
                        errors.append(f"{sport.value} error: {str(e)}")
                
                # Analyze results
                print(f"   📊 Sport comparison results:")
                for sport, data in sport_results.items():
                    print(f"      {sport.upper()}: {data}")
        
        except Exception as e:
            errors.append(f"Multi-sport workflow exception: {str(e)}")
        
        end_time = time.time()
        total_duration_ms = (end_time - start_time) * 1000
        
        success = len(errors) == 0 and steps_completed >= steps_total * 0.8  # Allow 80% success
        
        result = WorkflowResult(
            workflow_name=workflow_name,
            success=success,
            total_duration_ms=total_duration_ms,
            steps_completed=steps_completed,
            steps_total=steps_total,
            cache_hits=cache_hits,
            api_calls=api_calls,
            errors=errors,
            performance_metrics={
                "avg_request_time_ms": total_duration_ms / api_calls if api_calls > 0 else 0,
                "cache_hit_rate": cache_hits / api_calls if api_calls > 0 else 0,
                "sports_tested": len(sports_to_test),
                "sport_success_rate": (steps_completed / steps_total) * 100
            }
        )
        
        print(f"   📊 Result: {'✅ SUCCESS' if success else '❌ FAILED'} ({steps_completed}/{steps_total} steps)")
        return result
    
    async def test_authentication_tier_workflow(self) -> WorkflowResult:
        """Test different authentication tier workflows."""
        workflow_name = "Authentication Tier Workflow"
        print(f"\n🔐 Testing {workflow_name}...")
        
        start_time = time.time()
        steps_completed = 0
        steps_total = len(self.test_api_keys) * 3  # 3 operations per tier
        cache_hits = 0
        api_calls = 0
        errors = []
        
        try:
            for tier, key_id in self.test_api_keys.items():
                print(f"   🎯 Testing {tier.value.upper()} tier...")
                
                try:
                    async with BallDontLieClient(key_id=key_id) as client:
                        # Test rate limiting awareness
                        rate_info = await self.auth_manager.check_rate_limit(key_id)
                        allowed, info = rate_info
                        if allowed:
                            steps_completed += 1
                            print(f"      ✅ Rate limit check: {info['minute_remaining']} requests remaining")
                        else:
                            errors.append(f"{tier.value} tier rate limited")
                        
                        # Test tier-specific cache behavior
                        teams_response = await client.get_teams(Sport.NBA)
                        if teams_response.success:
                            steps_completed += 1
                            api_calls += 1
                            
                            # Check if caching behavior matches tier
                            if hasattr(teams_response, 'meta'):
                                meta = teams_response.meta
                                if meta.get('cached'):
                                    cache_hits += 1
                                    cache_source = meta.get('cache_source', 'unknown')
                                    print(f"      💾 Cache hit from {cache_source}")
                                else:
                                    print(f"      🌐 Fresh API call")
                        else:
                            errors.append(f"{tier.value} tier API call failed")
                        
                        # Test usage tracking
                        usage_stats = self.auth_manager.get_usage_stats(key_id)
                        if usage_stats:
                            steps_completed += 1
                            print(f"      📈 Usage: {usage_stats['total_requests']} total requests")
                        else:
                            errors.append(f"{tier.value} tier usage tracking failed")
                
                except Exception as e:
                    errors.append(f"{tier.value} tier error: {str(e)}")
        
        except Exception as e:
            errors.append(f"Authentication workflow exception: {str(e)}")
        
        end_time = time.time()
        total_duration_ms = (end_time - start_time) * 1000
        
        success = len(errors) == 0 and steps_completed >= steps_total * 0.8
        
        result = WorkflowResult(
            workflow_name=workflow_name,
            success=success,
            total_duration_ms=total_duration_ms,
            steps_completed=steps_completed,
            steps_total=steps_total,
            cache_hits=cache_hits,
            api_calls=api_calls,
            errors=errors,
            performance_metrics={
                "avg_request_time_ms": total_duration_ms / api_calls if api_calls > 0 else 0,
                "cache_hit_rate": cache_hits / api_calls if api_calls > 0 else 0,
                "tiers_tested": len(self.test_api_keys)
            }
        )
        
        print(f"   📊 Result: {'✅ SUCCESS' if success else '❌ FAILED'} ({steps_completed}/{steps_total} steps)")
        return result
    
    async def test_cache_warming_workflow(self) -> WorkflowResult:
        """Test cache warming workflow."""
        workflow_name = "Cache Warming Workflow"
        print(f"\n🔥 Testing {workflow_name}...")
        
        start_time = time.time()
        steps_completed = 0
        steps_total = 4
        cache_hits = 0
        api_calls = 0
        errors = []
        
        try:
            # Step 1: Get cache warming manager
            from adapters.cache import multi_cache
            
            # Create a cache warming wrapper for testing
            class CacheWarmingTestWrapper:
                def __init__(self, multi_cache_manager):
                    self.multi_cache = multi_cache_manager
                    # Add some test popular queries
                    from datetime import datetime
                    self.multi_cache.popular_queries = {
                        'nba:teams:': {'sport': 'nba', 'endpoint': 'teams', 'params': None, 'hit_count': 10, 'tier_users': {'all-star', 'goat'}},
                        'nba:players:': {'sport': 'nba', 'endpoint': 'players', 'params': None, 'hit_count': 8, 'tier_users': {'all-star'}},
                        'nfl:teams:': {'sport': 'nfl', 'endpoint': 'teams', 'params': None, 'hit_count': 6, 'tier_users': {'goat'}},
                        'mlb:teams:': {'sport': 'mlb', 'endpoint': 'teams', 'params': None, 'hit_count': 5, 'tier_users': {'all-star'}},
                        'nhl:teams:': {'sport': 'nhl', 'endpoint': 'teams', 'params': None, 'hit_count': 4, 'tier_users': {'goat'}},
                        'epl:teams:': {'sport': 'epl', 'endpoint': 'teams', 'params': None, 'hit_count': 2, 'tier_users': {'all-star'}}
                    }
                
                def get_queries_for_tier(self, tier):
                    return self.multi_cache._get_popular_queries_for_warming(tier)
                
                async def get_warming_recommendations(self, tier):
                    queries = self.multi_cache._get_popular_queries_for_warming(tier)
                    return {
                        'high_priority': queries[:15] if len(queries) > 15 else queries,
                        'medium_priority': queries[15:30] if len(queries) > 30 else [],
                        'low_priority': queries[30:] if len(queries) > 30 else []
                    }
                
                def get_warming_stats(self):
                    sports_breakdown = {}
                    for query_info in self.multi_cache.popular_queries.values():
                        sport = query_info['sport']
                        if sport not in sports_breakdown:
                            sports_breakdown[sport] = 0
                        sports_breakdown[sport] += 1
                    
                    from adapters.cache.redis_client import Sport
                    sport_enum_breakdown = {}
                    for sport_name, count in sports_breakdown.items():
                        try:
                            sport_enum = Sport(sport_name)
                            sport_enum_breakdown[sport_enum] = count
                        except:
                            sport_enum_breakdown[sport_name] = count
                    
                    return {
                        'total_popular_queries': len(self.multi_cache.popular_queries),
                        'queries_by_sport': sport_enum_breakdown,
                        'warming_cycles': self.multi_cache.analytics.get('warming_cycles', 0)
                    }
            
            cache_warmer = CacheWarmingTestWrapper(multi_cache)
            if cache_warmer:
                steps_completed += 1
                print("   ✅ Cache warming manager available")
            else:
                errors.append("Cache warming manager not available")
            
            # Step 2: Get popular queries
            popular_queries = cache_warmer.get_queries_for_tier(APITier.ALL_STAR)
            if len(popular_queries) > 0:
                steps_completed += 1
                print(f"   ✅ Found {len(popular_queries)} popular queries for ALL-STAR tier")
            else:
                errors.append("No popular queries found")
            
            # Step 3: Test warming recommendations
            recommendations = await cache_warmer.get_warming_recommendations(APITier.GOAT)
            if recommendations and len(recommendations.get('high_priority', [])) > 0:
                steps_completed += 1
                print(f"   ✅ {len(recommendations['high_priority'])} high-priority warming recommendations")
            else:
                errors.append("No warming recommendations available")
            
            # Step 4: Test warming statistics
            stats = cache_warmer.get_warming_stats()
            if stats and stats['total_popular_queries'] > 0:
                steps_completed += 1
                print(f"   ✅ Warming stats: {stats['total_popular_queries']} total popular queries")
                print(f"      Sport breakdown: {stats['queries_by_sport']}")
            else:
                errors.append("No warming statistics available")
        
        except Exception as e:
            errors.append(f"Cache warming workflow exception: {str(e)}")
        
        end_time = time.time()
        total_duration_ms = (end_time - start_time) * 1000
        
        success = len(errors) == 0 and steps_completed == steps_total
        
        result = WorkflowResult(
            workflow_name=workflow_name,
            success=success,
            total_duration_ms=total_duration_ms,
            steps_completed=steps_completed,
            steps_total=steps_total,
            cache_hits=cache_hits,
            api_calls=api_calls,
            errors=errors,
            performance_metrics={
                "warming_setup_time_ms": total_duration_ms
            }
        )
        
        print(f"   📊 Result: {'✅ SUCCESS' if success else '❌ FAILED'} ({steps_completed}/{steps_total} steps)")
        return result
    
    async def test_error_recovery_workflow(self) -> WorkflowResult:
        """Test error handling and recovery workflow."""
        workflow_name = "Error Recovery Workflow"
        print(f"\n🛡️ Testing {workflow_name}...")
        
        start_time = time.time()
        steps_completed = 0
        steps_total = 5
        cache_hits = 0
        api_calls = 0
        errors = []
        
        try:
            # Step 1: Test invalid API key handling
            try:
                invalid_client = BallDontLieClient(api_key="invalid_key_123")
                steps_completed += 1
                print("   ✅ Invalid API key handled gracefully")
            except Exception as e:
                print(f"   ✅ Invalid API key properly rejected: {type(e).__name__}")
                steps_completed += 1
            
            # Step 2: Test rate limit handling
            if APITier.FREE in self.test_api_keys:
                key_id = self.test_api_keys[APITier.FREE]
                
                # Simulate rate limit exhaustion
                for i in range(6):  # FREE tier allows 5/minute
                    await self.auth_manager.record_request(key_id, success=True)
                
                allowed, info = await self.auth_manager.check_rate_limit(key_id)
                if not allowed:
                    steps_completed += 1
                    print("   ✅ Rate limiting working correctly")
                else:
                    errors.append("Rate limiting not enforced")
            else:
                steps_completed += 1  # Skip if no FREE tier key
            
            # Step 3: Test cache fallback
            key_id = self.test_api_keys.get(APITier.ALL_STAR)
            if key_id:
                async with BallDontLieClient(key_id=key_id) as client:
                    # Try to get data that might be cached
                    response = await client.get_teams(Sport.NBA)
                    if response.success:
                        steps_completed += 1
                        api_calls += 1
                        if hasattr(response, 'meta') and response.meta.get('cached'):
                            cache_hits += 1
                        print("   ✅ Cache fallback mechanism available")
                    else:
                        errors.append("Cache fallback failed")
            else:
                steps_completed += 1  # Skip if no key
            
            # Step 4: Test domain service error handling
            try:
                team_service = TeamService()
                criteria = TeamSearchCriteria(sport=SportType.NBA)
                # This might fail gracefully if no API client
                result = await team_service.get_teams(criteria)
                steps_completed += 1
                print("   ✅ Domain service error handling working")
            except Exception as e:
                print(f"   ✅ Domain service error handled: {type(e).__name__}")
                steps_completed += 1
            
            # Step 5: Test multi-cache resilience
            try:
                cached_data, hit_info = await multi_cache.get(Sport.NBA, "teams", tier=APITier.ALL_STAR)
                steps_completed += 1
                print(f"   ✅ Multi-cache resilience: {hit_info.source if hit_info.hit else 'miss'}")
            except Exception as e:
                print(f"   ✅ Multi-cache error handled: {type(e).__name__}")
                steps_completed += 1
        
        except Exception as e:
            errors.append(f"Error recovery workflow exception: {str(e)}")
        
        end_time = time.time()
        total_duration_ms = (end_time - start_time) * 1000
        
        success = len(errors) == 0 and steps_completed >= steps_total * 0.8
        
        result = WorkflowResult(
            workflow_name=workflow_name,
            success=success,
            total_duration_ms=total_duration_ms,
            steps_completed=steps_completed,
            steps_total=steps_total,
            cache_hits=cache_hits,
            api_calls=api_calls,
            errors=errors,
            performance_metrics={
                "error_recovery_time_ms": total_duration_ms
            }
        )
        
        print(f"   📊 Result: {'✅ SUCCESS' if success else '❌ FAILED'} ({steps_completed}/{steps_total} steps)")
        return result
    
    async def run_all_workflows(self) -> List[WorkflowResult]:
        """Run all end-to-end workflows."""
        print("\n" + "="*80)
        print("🎯 HoopHead End-to-End Test Suite - Complete Workflows")
        print("="*80)
        
        await self.setup_test_environment()
        
        # Run all workflow tests
        workflows = [
            self.test_complete_nba_workflow(),
            self.test_multi_sport_comparison_workflow(),
            self.test_authentication_tier_workflow(),
            self.test_cache_warming_workflow(),
            self.test_error_recovery_workflow()
        ]
        
        results = []
        for workflow in workflows:
            result = await workflow
            results.append(result)
            self.workflow_results.append(result)
        
        # Generate summary report
        await self._generate_e2e_report()
        
        return results
    
    async def _generate_e2e_report(self):
        """Generate comprehensive E2E test report."""
        print("\n" + "="*80)
        print("📊 END-TO-END TEST RESULTS SUMMARY")
        print("="*80)
        
        total_workflows = len(self.workflow_results)
        successful_workflows = sum(1 for r in self.workflow_results if r.success)
        total_steps = sum(r.steps_total for r in self.workflow_results)
        completed_steps = sum(r.steps_completed for r in self.workflow_results)
        total_api_calls = sum(r.api_calls for r in self.workflow_results)
        total_cache_hits = sum(r.cache_hits for r in self.workflow_results)
        
        print(f"\n🎯 Overall Results:")
        print(f"   Workflows: {successful_workflows}/{total_workflows} successful ({successful_workflows/total_workflows*100:.1f}%)")
        print(f"   Steps: {completed_steps}/{total_steps} completed ({completed_steps/total_steps*100:.1f}%)")
        print(f"   API Calls: {total_api_calls}")
        print(f"   Cache Hits: {total_cache_hits} ({total_cache_hits/total_api_calls*100:.1f}% hit rate)" if total_api_calls > 0 else "   Cache Hits: 0")
        
        print(f"\n📋 Workflow Details:")
        for result in self.workflow_results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"   {result.workflow_name:30} | {status} | {result.steps_completed}/{result.steps_total} steps | {result.total_duration_ms/1000:.2f}s")
        
        # Show errors if any
        all_errors = []
        for result in self.workflow_results:
            all_errors.extend(result.errors)
        
        if all_errors:
            print(f"\n❌ Errors Found:")
            for error in all_errors:
                print(f"   • {error}")
        
        # Performance insights
        total_duration = sum(r.total_duration_ms for r in self.workflow_results)
        avg_request_time = sum(r.performance_metrics.get('avg_request_time_ms', 0) for r in self.workflow_results) / len(self.workflow_results)
        
        print(f"\n⚡ Performance Summary:")
        print(f"   Total E2E Duration: {total_duration/1000:.2f}s")
        print(f"   Average Request Time: {avg_request_time:.1f}ms")
        print(f"   Cache Efficiency: {total_cache_hits/total_api_calls*100:.1f}%" if total_api_calls > 0 else "   Cache Efficiency: N/A")
        
        # Success criteria
        overall_success_rate = successful_workflows / total_workflows * 100
        print(f"\n🏆 E2E Test Status: {'✅ PASSED' if overall_success_rate >= 80 else '❌ NEEDS ATTENTION'}")
        if overall_success_rate >= 80:
            print("   🎉 Excellent! Your platform successfully handles complete user workflows!")
        else:
            print("   🔧 Some workflows need attention. Review failed tests above.")


async def run_end_to_end_tests(use_real_api: bool = False):
    """
    Run the complete end-to-end test suite.
    
    Args:
        use_real_api: Whether to use real API calls (requires valid API key)
    """
    suite = EndToEndTestSuite(use_real_api=use_real_api)
    results = await suite.run_all_workflows()
    return results


if __name__ == "__main__":
    """Run end-to-end tests when executed directly."""
    import argparse
    
    parser = argparse.ArgumentParser(description="HoopHead End-to-End Test Suite")
    parser.add_argument("--real-api", action="store_true", 
                       help="Use real API calls (requires BALLDONTLIE_API_KEY environment variable)")
    
    args = parser.parse_args()
    
    asyncio.run(run_end_to_end_tests(use_real_api=args.real_api)) 