"""
Statistics domain service for orchestrating stats data operations.
"""

import logging
from typing import List, Optional, Dict, Any
from ..models.base import SportType
from ..models.statistics import GameStatsDetail, SeasonStats

logger = logging.getLogger(__name__)


class StatsService:
    """
    Domain service for statistics-related operations.
    Orchestrates stats retrieval, aggregation, and analysis.
    """
    
    def __init__(self, api_client):
        """Initialize with API client dependency."""
        self.api_client = api_client
        
    async def get_game_stats(
        self, 
        sport: SportType, 
        **filters
    ) -> List[GameStatsDetail]:
        """
        Get game statistics with optional filters.
        
        Args:
            sport: Sport type
            **filters: Additional filters (player_ids, team_ids, game_ids, etc.)
            
        Returns:
            List of game statistics
        """
        try:
            response = await self.api_client.get_stats(
                sport=sport,
                use_cache=True,
                **filters
            )
            
            if not response.success or not response.data.get('data'):
                return []
                
            stats = []
            for stat_data in response.data['data']:
                game_stat = GameStatsDetail.from_api_response({'data': stat_data}, sport)
                stats.append(game_stat)
                
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving stats for {sport}: {e}")
            return [] 