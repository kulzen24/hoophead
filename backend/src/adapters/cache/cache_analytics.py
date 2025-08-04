"""
Unified cache analytics module for HoopHead platform.
Consolidates all cache analytics functionality to eliminate duplication.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from core.utils import LoggerFactory, CacheKeyBuilder

logger = LoggerFactory.get_logger(__name__)


@dataclass
class CacheMetrics:
    """Standardized cache metrics structure."""
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    cache_size: int = 0
    storage_usage: int = 0  # in bytes
    
    def calculate_rates(self):
        """Calculate hit and miss rates."""
        if self.total_requests > 0:
            self.hit_rate = self.hits / self.total_requests
            self.miss_rate = self.misses / self.total_requests
        else:
            self.hit_rate = 0.0
            self.miss_rate = 0.0


@dataclass
class CachePerformance:
    """Cache performance statistics."""
    avg_response_time: float = 0.0  # in milliseconds
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    
    def update_from_times(self, response_times: List[float]):
        """Update performance metrics from response time list."""
        if not response_times:
            return
            
        response_times.sort()
        self.avg_response_time = sum(response_times) / len(response_times)
        self.min_response_time = response_times[0]
        self.max_response_time = response_times[-1]
        
        # Calculate percentiles
        if len(response_times) >= 20:  # Only calculate percentiles for reasonable sample sizes
            p95_index = int(0.95 * len(response_times))
            p99_index = int(0.99 * len(response_times))
            self.p95_response_time = response_times[p95_index]
            self.p99_response_time = response_times[p99_index]


@dataclass
class ComponentAnalytics:
    """Analytics for a specific cache component."""
    component_name: str
    metrics: CacheMetrics
    performance: CachePerformance
    last_updated: datetime
    error_count: int = 0
    error_rate: float = 0.0
    
    def calculate_error_rate(self):
        """Calculate error rate based on total requests."""
        if self.metrics.total_requests > 0:
            self.error_rate = self.error_count / self.metrics.total_requests
        else:
            self.error_rate = 0.0


class CacheAnalyticsManager:
    """
    Unified cache analytics manager.
    Collects and aggregates analytics from all cache components.
    """
    
    def __init__(self):
        """Initialize analytics manager."""
        self.components = {}
        self.response_times = {}
        self.start_time = datetime.utcnow()
    
    def register_component(self, component_name: str):
        """Register a cache component for analytics tracking."""
        if component_name not in self.components:
            self.components[component_name] = ComponentAnalytics(
                component_name=component_name,
                metrics=CacheMetrics(),
                performance=CachePerformance(),
                last_updated=datetime.utcnow()
            )
            self.response_times[component_name] = []
    
    def record_hit(self, component_name: str, response_time: float = 0.0):
        """Record a cache hit for a component."""
        self._ensure_component(component_name)
        
        analytics = self.components[component_name]
        analytics.metrics.hits += 1
        analytics.metrics.total_requests += 1
        analytics.metrics.calculate_rates()
        analytics.last_updated = datetime.utcnow()
        
        if response_time > 0:
            self.response_times[component_name].append(response_time)
    
    def record_miss(self, component_name: str, response_time: float = 0.0):
        """Record a cache miss for a component."""
        self._ensure_component(component_name)
        
        analytics = self.components[component_name]
        analytics.metrics.misses += 1
        analytics.metrics.total_requests += 1
        analytics.metrics.calculate_rates()
        analytics.last_updated = datetime.utcnow()
        
        if response_time > 0:
            self.response_times[component_name].append(response_time)
    
    def record_error(self, component_name: str):
        """Record an error for a component."""
        self._ensure_component(component_name)
        
        analytics = self.components[component_name]
        analytics.error_count += 1
        analytics.calculate_error_rate()
        analytics.last_updated = datetime.utcnow()
    
    def update_cache_size(self, component_name: str, size: int, storage_usage: int = 0):
        """Update cache size metrics for a component."""
        self._ensure_component(component_name)
        
        analytics = self.components[component_name]
        analytics.metrics.cache_size = size
        analytics.metrics.storage_usage = storage_usage
        analytics.last_updated = datetime.utcnow()
    
    def update_performance(self, component_name: str):
        """Update performance metrics for a component."""
        self._ensure_component(component_name)
        
        if component_name in self.response_times:
            response_times = self.response_times[component_name]
            if response_times:
                analytics = self.components[component_name]
                analytics.performance.update_from_times(response_times.copy())
                
                # Keep only recent response times (last 1000 requests)
                if len(response_times) > 1000:
                    self.response_times[component_name] = response_times[-1000:]
    
    def get_component_analytics(self, component_name: str) -> Optional[ComponentAnalytics]:
        """Get analytics for a specific component."""
        if component_name in self.components:
            self.update_performance(component_name)
            return self.components[component_name]
        return None
    
    def get_all_analytics(self) -> Dict[str, ComponentAnalytics]:
        """Get analytics for all components."""
        # Update performance for all components
        for component_name in self.components:
            self.update_performance(component_name)
        
        return self.components.copy()
    
    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics across all components."""
        all_analytics = self.get_all_analytics()
        
        # Calculate aggregate metrics
        total_hits = sum(analytics.metrics.hits for analytics in all_analytics.values())
        total_misses = sum(analytics.metrics.misses for analytics in all_analytics.values())
        total_requests = sum(analytics.metrics.total_requests for analytics in all_analytics.values())
        total_errors = sum(analytics.error_count for analytics in all_analytics.values())
        total_cache_size = sum(analytics.metrics.cache_size for analytics in all_analytics.values())
        total_storage = sum(analytics.metrics.storage_usage for analytics in all_analytics.values())
        
        # Calculate overall rates
        overall_hit_rate = (total_hits / total_requests) if total_requests > 0 else 0.0
        overall_error_rate = (total_errors / total_requests) if total_requests > 0 else 0.0
        
        # Calculate performance aggregates
        all_response_times = []
        for response_times in self.response_times.values():
            all_response_times.extend(response_times)
        
        overall_performance = CachePerformance()
        if all_response_times:
            overall_performance.update_from_times(all_response_times)
        
        uptime = datetime.utcnow() - self.start_time
        
        return {
            'summary': {
                'total_components': len(all_analytics),
                'total_hits': total_hits,
                'total_misses': total_misses,
                'total_requests': total_requests,
                'overall_hit_rate': overall_hit_rate,
                'total_errors': total_errors,
                'overall_error_rate': overall_error_rate,
                'total_cache_size': total_cache_size,
                'total_storage_usage': total_storage,
                'uptime_seconds': uptime.total_seconds()
            },
            'performance': asdict(overall_performance),
            'components': {
                name: {
                    'metrics': asdict(analytics.metrics),
                    'performance': asdict(analytics.performance),
                    'error_count': analytics.error_count,
                    'error_rate': analytics.error_rate,
                    'last_updated': analytics.last_updated.isoformat()
                }
                for name, analytics in all_analytics.items()
            },
            'health_indicators': self._calculate_health_indicators(all_analytics),
            'recommendations': self._generate_recommendations(all_analytics)
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall cache health status."""
        all_analytics = self.get_all_analytics()
        health_indicators = self._calculate_health_indicators(all_analytics)
        
        # Determine overall health
        healthy_components = sum(1 for status in health_indicators.values() if status == 'healthy')
        total_components = len(all_analytics)
        
        if total_components == 0:
            overall_health = 'unknown'
        elif healthy_components == total_components:
            overall_health = 'healthy'
        elif healthy_components >= total_components * 0.7:
            overall_health = 'degraded'
        else:
            overall_health = 'unhealthy'
        
        return {
            'overall_health': overall_health,
            'healthy_components': healthy_components,
            'total_components': total_components,
            'component_health': health_indicators
        }
    
    def _ensure_component(self, component_name: str):
        """Ensure component is registered for analytics."""
        if component_name not in self.components:
            self.register_component(component_name)
    
    def _calculate_health_indicators(self, analytics: Dict[str, ComponentAnalytics]) -> Dict[str, str]:
        """Calculate health indicators for each component."""
        health_indicators = {}
        
        for name, component_analytics in analytics.items():
            metrics = component_analytics.metrics
            
            # Health criteria
            hit_rate_threshold = 0.7  # 70% hit rate
            error_rate_threshold = 0.05  # 5% error rate
            response_time_threshold = 100.0  # 100ms average response time
            
            # Check health criteria
            good_hit_rate = metrics.hit_rate >= hit_rate_threshold
            low_error_rate = component_analytics.error_rate <= error_rate_threshold
            good_response_time = component_analytics.performance.avg_response_time <= response_time_threshold
            
            # Determine health status
            healthy_checks = sum([good_hit_rate, low_error_rate, good_response_time])
            
            if healthy_checks >= 3:
                health_indicators[name] = 'healthy'
            elif healthy_checks >= 2:
                health_indicators[name] = 'degraded'
            else:
                health_indicators[name] = 'unhealthy'
        
        return health_indicators
    
    def _generate_recommendations(self, analytics: Dict[str, ComponentAnalytics]) -> List[str]:
        """Generate optimization recommendations based on analytics."""
        recommendations = []
        
        for name, component_analytics in analytics.items():
            metrics = component_analytics.metrics
            performance = component_analytics.performance
            
            # Hit rate recommendations
            if metrics.hit_rate < 0.5:
                recommendations.append(f"{name}: Consider increasing cache TTL or reviewing cache key strategy")
            
            # Error rate recommendations
            if component_analytics.error_rate > 0.1:
                recommendations.append(f"{name}: High error rate detected, investigate connection issues")
            
            # Performance recommendations
            if performance.avg_response_time > 50.0:
                recommendations.append(f"{name}: High average response time, consider optimizing cache backend")
            
            # Storage recommendations
            if metrics.storage_usage > 500 * 1024 * 1024:  # 500MB
                recommendations.append(f"{name}: High storage usage, consider implementing cache eviction policies")
        
        return recommendations
    
    def reset_component_analytics(self, component_name: str):
        """Reset analytics for a specific component."""
        if component_name in self.components:
            self.components[component_name] = ComponentAnalytics(
                component_name=component_name,
                metrics=CacheMetrics(),
                performance=CachePerformance(),
                last_updated=datetime.utcnow()
            )
            self.response_times[component_name] = []
    
    def reset_all_analytics(self):
        """Reset analytics for all components."""
        for component_name in list(self.components.keys()):
            self.reset_component_analytics(component_name)
        
        self.start_time = datetime.utcnow()


# Global analytics manager instance
analytics_manager = CacheAnalyticsManager()


# Convenience functions for backward compatibility
async def get_cache_stats() -> Dict[str, Any]:
    """Get comprehensive cache statistics (unified across all components)."""
    return analytics_manager.get_comprehensive_analytics()


async def get_cache_analytics() -> Dict[str, Any]:
    """Alias for get_cache_stats for backward compatibility."""
    return await get_cache_stats()


async def get_comprehensive_analytics() -> Dict[str, Any]:
    """Get comprehensive analytics (unified across all components)."""
    return analytics_manager.get_comprehensive_analytics()


# Export main classes and functions
__all__ = [
    'CacheAnalyticsManager',
    'CacheMetrics', 
    'CachePerformance',
    'ComponentAnalytics',
    'analytics_manager',
    'get_cache_stats',
    'get_cache_analytics', 
    'get_comprehensive_analytics'
] 