"""
Base service class for HoopHead domain services.
Provides common functionality and patterns for all services.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from dataclasses import dataclass

from core.utils import LoggerFactory, APIResponseProcessor, AsyncPatterns, DataValidator
from core.exceptions import DomainException, InvalidSportError
from core.error_handler import with_domain_error_handling

from ..models.base import SportType, BaseEntity

# Type variables for generic service functionality
T = TypeVar('T', bound=BaseEntity)
SearchCriteria = TypeVar('SearchCriteria')

logger = LoggerFactory.get_logger(__name__)


@dataclass
class ServiceResponse(Generic[T]):
    """Standardized response from domain services."""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass 
class ServiceListResponse(Generic[T]):
    """Standardized list response from domain services."""
    success: bool
    data: List[T] = None
    error: Optional[str] = None
    total_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = []
        if self.metadata is None:
            self.metadata = {}
        if self.total_count == 0:
            self.total_count = len(self.data)


class BaseService(ABC, Generic[T]):
    """
    Abstract base class for all domain services.
    Provides common functionality and enforces consistent patterns.
    """
    
    def __init__(self, api_client, entity_class: Type[T]):
        """
        Initialize service with API client and entity class.
        
        Args:
            api_client: API client for external data retrieval
            entity_class: Domain entity class this service manages
        """
        self.api_client = api_client
        self.entity_class = entity_class
        self.logger = LoggerFactory.get_logger(self.__class__.__name__)
    
    @abstractmethod
    def get_api_endpoint(self) -> str:
        """Get the API endpoint name for this service."""
        pass
    
    @abstractmethod
    def create_search_criteria(self, **kwargs) -> SearchCriteria:
        """Create search criteria object from keyword arguments."""
        pass
    
    @with_domain_error_handling(fallback_value=None, suppress_hoophead_errors=True)
    async def get_by_id(self, entity_id: int, sport: SportType) -> Optional[T]:
        """
        Generic method to retrieve entity by ID and sport.
        
        Args:
            entity_id: Entity's unique ID
            sport: Sport type to search in
            
        Returns:
            Entity object or None if not found
        """
        try:
            sport_str = DataValidator.validate_sport_type(sport)
            entity_id = DataValidator.validate_positive_int(entity_id, "entity_id")
            
            # Use the API client method based on endpoint
            api_method = getattr(self.api_client, f"get_{self.get_api_endpoint()}")
            response = await api_method(sport=sport, use_cache=True)
            
            if response.success and response.data.get('data'):
                entities_data = APIResponseProcessor.extract_data(response.data)
                
                # Find entity with matching ID
                for entity_data in entities_data:
                    if entity_data.get('id') == entity_id:
                        return self.entity_class.from_api_response({'data': entity_data}, sport)
                        
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving {self.entity_class.__name__} {entity_id}: {e}")
            raise DomainException(f"Failed to retrieve {self.entity_class.__name__}", original_error=e)
    
    @with_domain_error_handling(fallback_value=[], suppress_hoophead_errors=True)
    async def get_all(self, sport: SportType, **filters) -> List[T]:
        """
        Generic method to retrieve all entities for a sport with optional filters.
        
        Args:
            sport: Sport type to retrieve from
            **filters: Additional filter parameters
            
        Returns:
            List of entity objects
        """
        try:
            sport_str = DataValidator.validate_sport_type(sport)
            
            # Use the API client method based on endpoint
            api_method = getattr(self.api_client, f"get_{self.get_api_endpoint()}")
            response = await api_method(sport=sport, use_cache=True, **filters)
            
            if response.success and response.data.get('data'):
                entities_data = APIResponseProcessor.extract_data(response.data)
                
                entities = []
                for entity_data in entities_data:
                    try:
                        entity = self.entity_class.from_api_response({'data': entity_data}, sport)
                        entities.append(entity)
                    except Exception as e:
                        self.logger.warning(f"Skipping invalid {self.entity_class.__name__} data: {e}")
                        continue
                
                return entities
                
            return []
            
        except Exception as e:
            self.logger.error(f"Error retrieving {self.entity_class.__name__} list: {e}")
            raise DomainException(f"Failed to retrieve {self.entity_class.__name__} list", original_error=e)
    
    @AsyncPatterns.async_retry(max_retries=2, delay=0.5)
    async def search(self, criteria: SearchCriteria) -> ServiceListResponse[T]:
        """
        Generic search method using search criteria.
        
        Args:
            criteria: Search criteria object
            
        Returns:
            ServiceListResponse with search results
        """
        try:
            # Extract search parameters from criteria
            search_params = self._extract_search_params(criteria)
            sport = getattr(criteria, 'sport', SportType.NBA)
            
            # Perform search
            results = await self.get_all(sport, **search_params)
            
            # Apply client-side filtering if needed
            filtered_results = self._apply_client_filters(results, criteria)
            
            return ServiceListResponse(
                success=True,
                data=filtered_results,
                total_count=len(filtered_results),
                metadata={
                    'search_criteria': criteria,
                    'sport': sport.value if hasattr(sport, 'value') else sport
                }
            )
            
        except Exception as e:
            self.logger.error(f"Search failed for {self.entity_class.__name__}: {e}")
            return ServiceListResponse(
                success=False,
                error=str(e),
                metadata={'search_criteria': criteria}
            )
    
    def _extract_search_params(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """
        Extract API parameters from search criteria.
        Override in subclasses for specific criteria handling.
        """
        params = {}
        
        # Common parameter extraction
        if hasattr(criteria, 'name') and criteria.name:
            params['search'] = criteria.name
        
        return params
    
    def _apply_client_filters(self, results: List[T], criteria: SearchCriteria) -> List[T]:
        """
        Apply client-side filters that can't be done at API level.
        Override in subclasses for specific filtering logic.
        """
        return results
    
    async def get_cached_entities(self, sport: SportType, cache_key: str) -> Optional[List[T]]:
        """Get entities from cache if available."""
        try:
            if hasattr(self.api_client, 'get_cached_response'):
                cached_response = await self.api_client.get_cached_response(cache_key)
                if cached_response:
                    entities_data = APIResponseProcessor.extract_data(cached_response)
                    return [
                        self.entity_class.from_api_response({'data': data}, sport)
                        for data in entities_data
                    ]
        except Exception as e:
            self.logger.debug(f"Cache retrieval failed: {e}")
        
        return None
    
    async def invalidate_cache(self, sport: SportType, **params):
        """Invalidate cache for this service's endpoint."""
        try:
            if hasattr(self.api_client, 'invalidate_cache'):
                await self.api_client.invalidate_cache(sport, self.get_api_endpoint(), params)
        except Exception as e:
            self.logger.warning(f"Cache invalidation failed: {e}")
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about this service."""
        return {
            'service_name': self.__class__.__name__,
            'entity_type': self.entity_class.__name__,
            'api_endpoint': self.get_api_endpoint(),
            'supports_caching': hasattr(self.api_client, 'get_cached_response'),
            'supports_search': True
        }


# Common search criteria patterns
@dataclass
class BaseSearchCriteria:
    """Base search criteria with common fields."""
    sport: Optional[SportType] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    active_only: bool = True


# Export commonly used classes
__all__ = [
    'BaseService',
    'ServiceResponse', 
    'ServiceListResponse',
    'BaseSearchCriteria'
] 