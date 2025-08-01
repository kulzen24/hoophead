"""
Ball Don't Lie API Authentication Manager.
Handles API key validation, tiered access management, and rate limiting.
"""
import os
import time
import hashlib
import json
import logging
from typing import Dict, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
import asyncio

logger = logging.getLogger(__name__)


class APITier(str, Enum):
    """API access tiers with different rate limits and features."""
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class TierLimits:
    """Rate limits and features for each API tier."""
    requests_per_hour: int
    requests_per_minute: int
    concurrent_requests: int
    cache_priority: int
    features: list


@dataclass
class APIKeyInfo:
    """Information about an API key including tier and usage tracking."""
    key_id: str
    tier: APITier
    encrypted_key: str
    created_at: str
    last_used: str
    requests_count: int = 0
    hourly_requests: int = 0
    hourly_reset_time: float = 0
    minute_requests: int = 0
    minute_reset_time: float = 0
    is_active: bool = True
    label: Optional[str] = None


class AuthenticationManager:
    """
    Manages Ball Don't Lie API keys with tiered access and rate limiting.
    Features:
    - Multiple API key support with tiers
    - Encrypted key storage
    - Per-tier rate limiting
    - Usage tracking and analytics
    - Key rotation and validation
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize authentication manager."""
        # Get or generate encryption key
        self.encryption_key = encryption_key or os.getenv('HOOPHEAD_ENCRYPTION_KEY')
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
            logger.warning("Generated new encryption key. Set HOOPHEAD_ENCRYPTION_KEY environment variable for persistence.")
        
        self.cipher = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
        
        # Tier configurations with limits per Ball Don't Lie API documentation
        self.tier_limits = {
            APITier.FREE: TierLimits(
                requests_per_hour=100,
                requests_per_minute=10,
                concurrent_requests=1,
                cache_priority=1,
                features=["basic_stats", "teams", "players"]
            ),
            APITier.PRO: TierLimits(
                requests_per_hour=1000,
                requests_per_minute=50,
                concurrent_requests=3,
                cache_priority=2,
                features=["basic_stats", "teams", "players", "advanced_stats", "historical_data"]
            ),
            APITier.PREMIUM: TierLimits(
                requests_per_hour=5000,
                requests_per_minute=200,
                concurrent_requests=5,
                cache_priority=3,
                features=["basic_stats", "teams", "players", "advanced_stats", "historical_data", "real_time"]
            ),
            APITier.ENTERPRISE: TierLimits(
                requests_per_hour=50000,
                requests_per_minute=1000,
                concurrent_requests=10,
                cache_priority=4,
                features=["basic_stats", "teams", "players", "advanced_stats", "historical_data", "real_time", "bulk_export"]
            )
        }
        
        # In-memory key storage (in production, use proper secret management)
        self.api_keys: Dict[str, APIKeyInfo] = {}
        self.default_key_id: Optional[str] = None
        
        # Load existing keys from environment/storage
        self._load_api_keys()
    
    def _generate_key_id(self, api_key: str) -> str:
        """Generate a unique identifier for an API key."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    def _encrypt_key(self, api_key: str) -> str:
        """Encrypt an API key for secure storage."""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def _decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt an API key from storage."""
        return self.cipher.decrypt(encrypted_key.encode()).decode()
    
    def _load_api_keys(self):
        """Load API keys from environment variables and storage."""
        # Load primary API key from environment
        primary_key = os.getenv('BALLDONTLIE_API_KEY')
        if primary_key:
            tier = self._detect_key_tier(primary_key)
            self.add_api_key(
                api_key=primary_key,
                tier=tier,
                label="Primary",
                set_as_default=True
            )
        
        # Load additional keys from HOOPHEAD_API_KEYS environment variable (JSON format)
        additional_keys_json = os.getenv('HOOPHEAD_API_KEYS')
        if additional_keys_json:
            try:
                additional_keys = json.loads(additional_keys_json)
                for key_config in additional_keys:
                    self.add_api_key(
                        api_key=key_config['key'],
                        tier=APITier(key_config.get('tier', 'free')),
                        label=key_config.get('label', 'Additional')
                    )
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error loading additional API keys: {e}")
    
    def _detect_key_tier(self, api_key: str) -> APITier:
        """Detect API key tier based on key format or prefix."""
        # This is a simplified detection - in reality, you'd validate with the API
        if api_key.startswith('ent_'):
            return APITier.ENTERPRISE
        elif api_key.startswith('prem_'):
            return APITier.PREMIUM
        elif api_key.startswith('pro_'):
            return APITier.PRO
        else:
            return APITier.FREE
    
    def add_api_key(
        self, 
        api_key: str, 
        tier: APITier = APITier.FREE,
        label: Optional[str] = None,
        set_as_default: bool = False
    ) -> str:
        """Add a new API key to the manager."""
        key_id = self._generate_key_id(api_key)
        encrypted_key = self._encrypt_key(api_key)
        current_time = time.time()
        
        key_info = APIKeyInfo(
            key_id=key_id,
            tier=tier,
            encrypted_key=encrypted_key,
            created_at=str(current_time),
            last_used=str(current_time),
            label=label
        )
        
        self.api_keys[key_id] = key_info
        
        if set_as_default or not self.default_key_id:
            self.default_key_id = key_id
        
        logger.info(f"Added API key {key_id} with tier {tier.value}")
        return key_id
    
    def remove_api_key(self, key_id: str) -> bool:
        """Remove an API key from the manager."""
        if key_id in self.api_keys:
            del self.api_keys[key_id]
            if self.default_key_id == key_id:
                self.default_key_id = next(iter(self.api_keys.keys())) if self.api_keys else None
            logger.info(f"Removed API key {key_id}")
            return True
        return False
    
    def get_api_key(self, key_id: Optional[str] = None) -> Optional[str]:
        """Get decrypted API key by ID (or default if None)."""
        if not key_id:
            key_id = self.default_key_id
        
        if not key_id or key_id not in self.api_keys:
            return None
        
        key_info = self.api_keys[key_id]
        if not key_info.is_active:
            return None
        
        return self._decrypt_key(key_info.encrypted_key)
    
    def get_key_info(self, key_id: Optional[str] = None) -> Optional[APIKeyInfo]:
        """Get API key information."""
        if not key_id:
            key_id = self.default_key_id
        
        if not key_id or key_id not in self.api_keys:
            return None
        
        return self.api_keys[key_id]
    
    def get_tier_limits(self, key_id: Optional[str] = None) -> Optional[TierLimits]:
        """Get rate limits for an API key's tier."""
        key_info = self.get_key_info(key_id)
        if not key_info:
            return None
        
        return self.tier_limits.get(key_info.tier)
    
    async def check_rate_limit(self, key_id: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits.
        Returns (allowed, rate_limit_info)
        """
        key_info = self.get_key_info(key_id)
        if not key_info:
            return False, {"error": "Invalid API key"}
        
        tier_limits = self.tier_limits[key_info.tier]
        current_time = time.time()
        
        # Reset counters if time windows have passed
        if current_time >= key_info.hourly_reset_time:
            key_info.hourly_requests = 0
            key_info.hourly_reset_time = current_time + 3600  # Next hour
        
        if current_time >= key_info.minute_reset_time:
            key_info.minute_requests = 0
            key_info.minute_reset_time = current_time + 60  # Next minute
        
        # Check limits
        hour_allowed = key_info.hourly_requests < tier_limits.requests_per_hour
        minute_allowed = key_info.minute_requests < tier_limits.requests_per_minute
        
        rate_limit_info = {
            "tier": key_info.tier.value,
            "hourly_remaining": max(0, tier_limits.requests_per_hour - key_info.hourly_requests),
            "minute_remaining": max(0, tier_limits.requests_per_minute - key_info.minute_requests),
            "hourly_reset": key_info.hourly_reset_time,
            "minute_reset": key_info.minute_reset_time,
            "concurrent_limit": tier_limits.concurrent_requests
        }
        
        return hour_allowed and minute_allowed, rate_limit_info
    
    async def record_request(self, key_id: Optional[str] = None, success: bool = True):
        """Record a request against rate limits."""
        key_info = self.get_key_info(key_id)
        if not key_info:
            return
        
        key_info.requests_count += 1
        key_info.hourly_requests += 1
        key_info.minute_requests += 1
        key_info.last_used = str(time.time())
        
        logger.debug(f"Recorded request for key {key_info.key_id}: "
                    f"hourly={key_info.hourly_requests}, minute={key_info.minute_requests}")
    
    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[str], Optional[APITier]]:
        """
        Validate an API key format and return key_id and tier if valid.
        Returns (is_valid, key_id, tier)
        """
        if not api_key or len(api_key) < 10:
            return False, None, None
        
        # Find existing key
        key_id = self._generate_key_id(api_key)
        if key_id in self.api_keys:
            key_info = self.api_keys[key_id]
            return key_info.is_active, key_id, key_info.tier
        
        # For new keys, do basic validation
        # In production, you'd validate against Ball Don't Lie API
        if api_key.startswith(('bdl_', 'sk_', 'pk_', 'ent_', 'pro_', 'prem_')):
            tier = self._detect_key_tier(api_key)
            return True, None, tier
        
        return False, None, None
    
    def get_usage_stats(self, key_id: Optional[str] = None) -> Dict[str, Any]:
        """Get usage statistics for an API key."""
        key_info = self.get_key_info(key_id)
        if not key_info:
            return {}
        
        tier_limits = self.tier_limits[key_info.tier]
        
        return {
            "key_id": key_info.key_id,
            "label": key_info.label,
            "tier": key_info.tier.value,
            "total_requests": key_info.requests_count,
            "hourly_requests": key_info.hourly_requests,
            "minute_requests": key_info.minute_requests,
            "hourly_limit": tier_limits.requests_per_hour,
            "minute_limit": tier_limits.requests_per_minute,
            "hourly_remaining": max(0, tier_limits.requests_per_hour - key_info.hourly_requests),
            "minute_remaining": max(0, tier_limits.requests_per_minute - key_info.minute_requests),
            "created_at": key_info.created_at,
            "last_used": key_info.last_used,
            "is_active": key_info.is_active,
            "features": tier_limits.features
        }
    
    def list_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """List all API keys with their usage statistics."""
        return {
            key_id: self.get_usage_stats(key_id) 
            for key_id in self.api_keys.keys()
        }
    
    def set_default_key(self, key_id: str) -> bool:
        """Set the default API key."""
        if key_id in self.api_keys:
            self.default_key_id = key_id
            logger.info(f"Set default API key to {key_id}")
            return True
        return False
    
    def deactivate_key(self, key_id: str) -> bool:
        """Deactivate an API key without removing it."""
        if key_id in self.api_keys:
            self.api_keys[key_id].is_active = False
            logger.info(f"Deactivated API key {key_id}")
            return True
        return False
    
    def activate_key(self, key_id: str) -> bool:
        """Reactivate an API key."""
        if key_id in self.api_keys:
            self.api_keys[key_id].is_active = True
            logger.info(f"Activated API key {key_id}")
            return True
        return False


# Global authentication manager instance
auth_manager = AuthenticationManager() 