"""
Cache warming utilities for HoopHead multi-sport API.
Preloads popular queries and maintains hot cache for optimal performance.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

# Import our caching system
try:
    from .multi_cache_manager import multi_cache, Sport, APITier, CacheStrategy
    from .redis_client import Sport as RedisClientSport
except ImportError:
    multi_cache = None
    class Sport(str):
        NBA = "nba"
        MLB = "mlb"
        NFL = "nfl"
        NHL = "nhl"
        EPL = "epl"

# Import Ball Don't Lie client for actual data fetching
try:
    from backend.src.adapters.external.ball_dont_lie_client import BallDontLieClient
    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    BallDontLieClient = None

logger = logging.getLogger(__name__)


@dataclass
class PopularQuery:
    """Definition of a popular query for cache warming."""
    sport: Sport
    endpoint: str
    params: Optional[Dict] = None
    priority: int = 1  # 1=low, 5=high
    tier_relevance: List[str] = None  # Which tiers find this query valuable
    description: str = ""


class CacheWarmingManager:
    """
    Manages cache warming with predefined popular queries and intelligent warming strategies.
    """
    
    def __init__(self):
        """Initialize cache warming manager with popular query definitions."""
        self.popular_queries = self._define_popular_queries()
        self.warming_stats = {
            'total_warming_cycles': 0,
            'queries_warmed': 0,
            'queries_failed': 0,
            'last_warming': None,
            'average_warming_time': 0
        }
        
        logger.info(f"Cache warming manager initialized with {len(self.popular_queries)} popular queries")
    
    def _define_popular_queries(self) -> List[PopularQuery]:
        """Define popular queries that should be cached proactively."""
        queries = []
        
        # NBA Popular Queries
        queries.extend([
            PopularQuery(
                sport=Sport.NBA,
                endpoint="teams",
                params=None,
                priority=5,
                tier_relevance=["free", "all-star", "goat", "enterprise"],
                description="All NBA teams - fundamental data"
            ),
            PopularQuery(
                sport=Sport.NBA,
                endpoint="players",
                params={"search": "LeBron"},
                priority=4,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="LeBron James player search"
            ),
            PopularQuery(
                sport=Sport.NBA,
                endpoint="players",
                params={"search": "Curry"},
                priority=4,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Stephen Curry player search"
            ),
            PopularQuery(
                sport=Sport.NBA,
                endpoint="players",
                params={"search": "Durant"},
                priority=4,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Kevin Durant player search"
            ),
            PopularQuery(
                sport=Sport.NBA,
                endpoint="games",
                params={"seasons": [datetime.now().year]},
                priority=3,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Current season games"
            )
        ])
        
        # NFL Popular Queries
        queries.extend([
            PopularQuery(
                sport=Sport.NFL,
                endpoint="teams",
                params=None,
                priority=5,
                tier_relevance=["free", "all-star", "goat", "enterprise"],
                description="All NFL teams"
            ),
            PopularQuery(
                sport=Sport.NFL,
                endpoint="players",
                params={"search": "Mahomes"},
                priority=4,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Patrick Mahomes player search"
            ),
            PopularQuery(
                sport=Sport.NFL,
                endpoint="players",
                params={"search": "Brady"},
                priority=4,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Tom Brady player search"
            ),
            PopularQuery(
                sport=Sport.NFL,
                endpoint="players",
                params={"search": "Allen"},
                priority=3,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Josh Allen player search"
            )
        ])
        
        # MLB Popular Queries
        queries.extend([
            PopularQuery(
                sport=Sport.MLB,
                endpoint="teams",
                params=None,
                priority=5,
                tier_relevance=["free", "all-star", "goat", "enterprise"],
                description="All MLB teams"
            ),
            PopularQuery(
                sport=Sport.MLB,
                endpoint="players",
                params={"search": "Ohtani"},
                priority=5,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Shohei Ohtani player search"
            ),
            PopularQuery(
                sport=Sport.MLB,
                endpoint="players",
                params={"search": "Judge"},
                priority=4,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Aaron Judge player search"
            ),
            PopularQuery(
                sport=Sport.MLB,
                endpoint="players",
                params={"search": "Trout"},
                priority=4,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Mike Trout player search"
            )
        ])
        
        # NHL Popular Queries
        queries.extend([
            PopularQuery(
                sport=Sport.NHL,
                endpoint="teams",
                params=None,
                priority=5,
                tier_relevance=["free", "all-star", "goat", "enterprise"],
                description="All NHL teams"
            ),
            PopularQuery(
                sport=Sport.NHL,
                endpoint="players",
                params={"search": "McDavid"},
                priority=5,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Connor McDavid player search"
            ),
            PopularQuery(
                sport=Sport.NHL,
                endpoint="players",
                params={"search": "Ovechkin"},
                priority=4,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Alexander Ovechkin player search"
            ),
            PopularQuery(
                sport=Sport.NHL,
                endpoint="players",
                params={"search": "Crosby"},
                priority=4,
                tier_relevance=["all-star", "goat", "enterprise"],
                description="Sidney Crosby player search"
            )
        ])
        
        # EPL Popular Queries (if available)
        queries.extend([
            PopularQuery(
                sport=Sport.EPL,
                endpoint="teams",
                params=None,
                priority=3,
                tier_relevance=["goat", "enterprise"],
                description="All EPL teams"
            )
        ])
        
        return queries
    
    def get_queries_for_tier(self, tier: APITier) -> List[PopularQuery]:
        """Get popular queries relevant for a specific tier."""
        tier_value = tier.value
        relevant_queries = []
        
        for query in self.popular_queries:
            if query.tier_relevance and tier_value in query.tier_relevance:
                relevant_queries.append(query)
        
        # Sort by priority descending
        relevant_queries.sort(key=lambda q: q.priority, reverse=True)
        return relevant_queries
    
    def get_queries_for_sport(self, sport: Sport) -> List[PopularQuery]:
        """Get all popular queries for a specific sport."""
        sport_queries = [q for q in self.popular_queries if q.sport == sport]
        sport_queries.sort(key=lambda q: q.priority, reverse=True)
        return sport_queries
    
    async def warm_tier_specific_cache(
        self, 
        tier: APITier, 
        max_queries: int = 20,
        client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Warm cache with tier-specific popular queries.
        Uses actual API calls to fetch and cache data.
        """
        if not CLIENT_AVAILABLE or not multi_cache:
            logger.warning("Cache warming requires Ball Don't Lie client and multi-cache system")
            return {"status": "failed", "reason": "dependencies_not_available"}
        
        start_time = datetime.utcnow()
        relevant_queries = self.get_queries_for_tier(tier)[:max_queries]
        
        results = {
            "status": "completed",
            "tier": tier.value,
            "total_queries": len(relevant_queries),
            "successful": 0,
            "failed": 0,
            "already_cached": 0,
            "details": []
        }
        
        logger.info(f"Starting cache warming for {tier.value} tier with {len(relevant_queries)} queries")
        
        # Use provided client or create new one
        if client is None:
            async with BallDontLieClient() as api_client:
                results = await self._execute_warming_queries(api_client, relevant_queries, tier, results)
        else:
            results = await self._execute_warming_queries(client, relevant_queries, tier, results)
        
        warming_duration = (datetime.utcnow() - start_time).total_seconds()
        results["duration_seconds"] = warming_duration
        
        # Update stats
        self.warming_stats['total_warming_cycles'] += 1
        self.warming_stats['queries_warmed'] += results['successful']
        self.warming_stats['queries_failed'] += results['failed']
        self.warming_stats['last_warming'] = start_time.isoformat()
        self.warming_stats['average_warming_time'] = (
            (self.warming_stats['average_warming_time'] * (self.warming_stats['total_warming_cycles'] - 1) + warming_duration)
            / self.warming_stats['total_warming_cycles']
        )
        
        logger.info(
            f"Cache warming completed for {tier.value}: "
            f"{results['successful']} successful, {results['failed']} failed, "
            f"{results['already_cached']} already cached in {warming_duration:.2f}s"
        )
        
        return results
    
    async def _execute_warming_queries(
        self, 
        client: Any, 
        queries: List[PopularQuery], 
        tier: APITier, 
        results: Dict
    ) -> Dict:
        """Execute warming queries with the API client."""
        for query in queries:
            try:
                # Check if already cached
                cached_data, hit_info = await multi_cache.get(
                    query.sport, query.endpoint, query.params, tier
                )
                
                if hit_info.hit:
                    results["already_cached"] += 1
                    results["details"].append({
                        "query": f"{query.sport}:{query.endpoint}",
                        "status": "already_cached",
                        "source": hit_info.source
                    })
                    continue
                
                # Fetch data from API based on endpoint
                api_data = None
                if query.endpoint == "teams":
                    api_data = await client.get_teams(query.sport)
                elif query.endpoint == "players":
                    if query.params and "search" in query.params:
                        api_data = await client.search_players(query.sport, query.params["search"])
                    else:
                        api_data = await client.get_players(query.sport)
                elif query.endpoint == "games":
                    api_data = await client.get_games(query.sport, **(query.params or {}))
                
                if api_data and api_data.success:
                    # Store in cache
                    redis_success, file_success = await multi_cache.set(
                        query.sport, query.endpoint, api_data.data, 
                        query.params, tier, api_response=api_data
                    )
                    
                    if redis_success or file_success:
                        results["successful"] += 1
                        results["details"].append({
                            "query": f"{query.sport}:{query.endpoint}",
                            "status": "warmed",
                            "redis": redis_success,
                            "file": file_success
                        })
                    else:
                        results["failed"] += 1
                        results["details"].append({
                            "query": f"{query.sport}:{query.endpoint}",
                            "status": "cache_failed"
                        })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "query": f"{query.sport}:{query.endpoint}",
                        "status": "api_failed"
                    })
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error warming cache for {query.sport}:{query.endpoint}: {e}")
                results["failed"] += 1
                results["details"].append({
                    "query": f"{query.sport}:{query.endpoint}",
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    async def warm_all_sports_basic_data(self, tier: APITier = APITier.FREE) -> Dict[str, Any]:
        """
        Warm cache with basic data for all sports (teams primarily).
        Useful for initial application load.
        """
        logger.info("Starting basic data warming for all sports")
        
        basic_queries = [
            PopularQuery(Sport.NBA, "teams", None, 5, description="NBA teams"),
            PopularQuery(Sport.NFL, "teams", None, 5, description="NFL teams"),
            PopularQuery(Sport.MLB, "teams", None, 5, description="MLB teams"),
            PopularQuery(Sport.NHL, "teams", None, 5, description="NHL teams"),
        ]
        
        if tier in [APITier.GOAT, APITier.ENTERPRISE]:
            basic_queries.append(PopularQuery(Sport.EPL, "teams", None, 3, description="EPL teams"))
        
        start_time = datetime.utcnow()
        results = {
            "status": "completed",
            "total_queries": len(basic_queries),
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        if CLIENT_AVAILABLE:
            async with BallDontLieClient() as client:
                for query in basic_queries:
                    try:
                        api_data = await client.get_teams(query.sport)
                        if api_data and api_data.success:
                            redis_success, file_success = await multi_cache.set(
                                query.sport, query.endpoint, api_data.data,
                                query.params, tier, api_response=api_data
                            )
                            
                            if redis_success or file_success:
                                results["successful"] += 1
                            else:
                                results["failed"] += 1
                        else:
                            results["failed"] += 1
                        
                        await asyncio.sleep(0.2)  # Rate limiting
                        
                    except Exception as e:
                        logger.error(f"Error warming {query.sport} teams: {e}")
                        results["failed"] += 1
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        results["duration_seconds"] = duration
        
        logger.info(f"Basic data warming completed in {duration:.2f}s: {results['successful']} successful, {results['failed']} failed")
        return results
    
    async def get_warming_recommendations(self, tier: APITier) -> Dict[str, Any]:
        """
        Get recommendations for cache warming based on tier and current cache state.
        """
        recommendations = {
            "tier": tier.value,
            "total_available_queries": len(self.get_queries_for_tier(tier)),
            "high_priority": [],
            "medium_priority": [],
            "low_priority": [],
            "warming_stats": self.warming_stats
        }
        
        tier_queries = self.get_queries_for_tier(tier)
        
        for query in tier_queries:
            query_info = {
                "sport": query.sport,
                "endpoint": query.endpoint,
                "params": query.params,
                "description": query.description
            }
            
            if query.priority >= 4:
                recommendations["high_priority"].append(query_info)
            elif query.priority >= 3:
                recommendations["medium_priority"].append(query_info)
            else:
                recommendations["low_priority"].append(query_info)
        
        return recommendations
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """Get cache warming statistics."""
        return {
            "warming_stats": self.warming_stats,
            "total_popular_queries": len(self.popular_queries),
            "queries_by_sport": {
                sport: len(self.get_queries_for_sport(sport))
                for sport in [Sport.NBA, Sport.NFL, Sport.MLB, Sport.NHL, Sport.EPL]
            },
            "queries_by_tier": {
                tier.value: len(self.get_queries_for_tier(tier))
                for tier in [APITier.FREE, APITier.ALL_STAR, APITier.GOAT, APITier.ENTERPRISE]
            }
        }


# Global cache warming manager instance
cache_warmer = CacheWarmingManager() 