"""
Integration tests for Ball Don't Lie API authentication and key management.
Tests the new tiered authentication system, rate limiting, and secure key storage.
"""
import asyncio
import os
import pytest
import logging
from typing import Dict, Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system env vars only

# Set up test environment
from test_utils import setup_test_environment
setup_test_environment()

try:
    from adapters.external.auth_manager import AuthenticationManager, APITier
    from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport, validate_api_key_quick
except ImportError as e:
    print(f"Import error: {e}")
    print("Run this test from the project root or ensure PYTHONPATH includes backend/src")
    sys.exit(1)

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestAuthenticationManager:
    """Test the authentication manager functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Use a proper base64-encoded test encryption key (32 bytes)
        from cryptography.fernet import Fernet
        self.test_key = Fernet.generate_key().decode()
        self.auth_manager = AuthenticationManager(encryption_key=self.test_key)
    
    def test_add_and_retrieve_api_key(self):
        """Test adding and retrieving API keys."""
        # Test API key
        test_api_key = "bdl_test_key_12345678901234567890"
        
        # Add key
        key_id = self.auth_manager.add_api_key(
            test_api_key, 
            APITier.ALL_STAR, 
            "Test Key"
        )
        
        assert key_id is not None
        assert len(key_id) == 16  # SHA256 hash truncated to 16 chars
        
        # Retrieve key
        retrieved_key = self.auth_manager.get_api_key(key_id)
        assert retrieved_key == test_api_key
        
        # Check key info
        key_info = self.auth_manager.get_key_info(key_id)
        assert key_info is not None
        assert key_info.tier == APITier.ALL_STAR
        assert key_info.label == "Test Key"
        assert key_info.is_active is True
    
    def test_tier_limits(self):
        """Test tier-based rate limiting."""
        # Add keys with different tiers
        free_key = self.auth_manager.add_api_key("free_key_123", APITier.FREE)
        allstar_key = self.auth_manager.add_api_key("all_star_key_123", APITier.ALL_STAR)
        
        # Check tier limits
        free_limits = self.auth_manager.get_tier_limits(free_key)
        allstar_limits = self.auth_manager.get_tier_limits(allstar_key)
        
        assert free_limits.requests_per_hour == 300
        assert allstar_limits.requests_per_hour == 3600
        assert allstar_limits.requests_per_minute > free_limits.requests_per_minute
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # Add a test key
        test_key = self.auth_manager.add_api_key("rate_test_key", APITier.FREE)
        
        # Check initial rate limit (should be allowed)
        allowed, info = await self.auth_manager.check_rate_limit(test_key)
        assert allowed is True
        assert info["hourly_remaining"] == 300
        assert info["minute_remaining"] == 5
        
        # Record some requests (Free tier allows 5/min, so record 3 to stay under limit)
        for i in range(3):
            await self.auth_manager.record_request(test_key)
        
        # Check updated limits
        allowed, info = await self.auth_manager.check_rate_limit(test_key)
        assert allowed is True
        assert info["hourly_remaining"] == 297
        assert info["minute_remaining"] == 2
    
    def test_key_validation(self):
        """Test API key validation."""
        # Valid key formats
        valid_keys = [
            "bdl_valid_key_123456789",
            "sk_test_123456789",
            "goat_premium_key_123",
            "all_star_tier_key_456",
            "ent_enterprise_key_789"
        ]
        
        for key in valid_keys:
            is_valid, key_id, tier = self.auth_manager.validate_api_key(key)
            assert is_valid is True
            assert tier is not None
        
        # Invalid key formats
        invalid_keys = [
            "short",
            "",
            "invalid_format",
            None
        ]
        
        for key in invalid_keys:
            if key is not None:
                is_valid, key_id, tier = self.auth_manager.validate_api_key(key)
                assert is_valid is False
    
    def test_usage_statistics(self):
        """Test usage statistics tracking."""
        # Add a test key
        key_id = self.auth_manager.add_api_key("stats_test_key", APITier.ALL_STAR, "Statistics Test")
        
        # Get initial stats
        stats = self.auth_manager.get_usage_stats(key_id)
        assert stats["total_requests"] == 0
        assert stats["tier"] == "all-star"
        assert stats["label"] == "Statistics Test"
        
        # Record some usage
        asyncio.run(self.auth_manager.record_request(key_id))
        
        # Check updated stats
        stats = self.auth_manager.get_usage_stats(key_id)
        assert stats["total_requests"] == 1


class TestBallDontLieClientAuthentication:
    """Test the enhanced Ball Don't Lie client with authentication."""
    
    @pytest.mark.skipif(
        not os.getenv('BALLDONTLIE_API_KEY'),
        reason="Requires BALLDONTLIE_API_KEY environment variable"
    )
    async def test_client_with_auth_manager(self):
        """Test client initialization with authentication manager."""
        # This test requires a real API key
        api_key = os.getenv('BALLDONTLIE_API_KEY')
        
        async with BallDontLieClient(api_key, enable_cache=False) as client:
            # Check authentication info
            auth_info = client.get_authentication_info()
            
            assert auth_info["auth_manager_enabled"] is True
            assert "current_key_id" in auth_info
            assert "usage_stats" in auth_info
            
            # Validate the key
            is_valid, validation_result = await client.validate_current_key()
            logger.info(f"Key validation result: {validation_result}")
            
            # Note: Validation might fail if API key is invalid, but test structure should work
            assert "valid" in validation_result
            assert "key_id" in validation_result
    
    def test_client_fallback_without_auth_manager(self):
        """Test client fallback when authentication manager is not available."""
        # Test with mock environment (no real API key needed for this test)
        import backend.src.adapters.external.ball_dont_lie_client as bdl_module
        
        # Temporarily disable auth manager
        original_auth_available = bdl_module.AUTH_MANAGER_AVAILABLE
        bdl_module.AUTH_MANAGER_AVAILABLE = False
        
        try:
            # This should use fallback behavior
            client = BallDontLieClient("fake_api_key_for_test")
            
            auth_info = client.get_authentication_info()
            assert auth_info["auth_manager_enabled"] is False
            
        finally:
            # Restore original state
            bdl_module.AUTH_MANAGER_AVAILABLE = original_auth_available
    
    async def test_tier_based_rate_limiting(self):
        """Test that different tiers have different rate limits."""
        # Create test auth manager with proper encryption key
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key().decode()
        auth_manager = AuthenticationManager(test_key)
        
        # Add keys with different tiers
        free_key_id = auth_manager.add_api_key("free_test_key", APITier.FREE)
        goat_key_id = auth_manager.add_api_key("goat_test_key", APITier.GOAT)
        
        # Test rate limits
        free_limits = auth_manager.get_tier_limits(free_key_id)
        goat_limits = auth_manager.get_tier_limits(goat_key_id)
        
        assert free_limits.requests_per_hour < goat_limits.requests_per_hour
        assert free_limits.requests_per_minute < goat_limits.requests_per_minute
        assert free_limits.concurrent_requests < goat_limits.concurrent_requests


async def demo_authentication_features():
    """Demonstrate the new authentication features."""
    print("\n🔐 Ball Don't Lie API Authentication Demo")
    print("=" * 50)
    
    # Create authentication manager
    print("\n1. Creating Authentication Manager...")
    auth_manager = AuthenticationManager()
    
    # Add sample API keys (these are fake keys for demo)
    print("\n2. Adding sample API keys...")
    free_key_id = auth_manager.add_api_key("bdl_free_demo_key_123456789", APITier.FREE, "Demo Free Key")
    allstar_key_id = auth_manager.add_api_key("all_star_demo_key_123456789", APITier.ALL_STAR, "Demo ALL-STAR Key")
    goat_key_id = auth_manager.add_api_key("goat_demo_key_123456789", APITier.GOAT, "Demo GOAT Key")
    
    print(f"   Added Free Key: {free_key_id}")
    print(f"   Added ALL-STAR Key: {allstar_key_id}")
    print(f"   Added GOAT Key: {goat_key_id}")
    
    # Show tier limits
    print("\n3. Ball Don't Lie API Tier Limits:")
    for key_id, tier_name in [(free_key_id, "FREE"), (allstar_key_id, "ALL-STAR"), (goat_key_id, "GOAT")]:
        limits = auth_manager.get_tier_limits(key_id)
        print(f"   {tier_name:8} | {limits.requests_per_hour:5}/hour | {limits.requests_per_minute:3}/min | {limits.concurrent_requests} concurrent")
    
    # Test rate limiting
    print("\n4. Testing Rate Limiting...")
    for i in range(3):
        allowed, info = await auth_manager.check_rate_limit(free_key_id)
        print(f"   Request {i+1}: {'✅ Allowed' if allowed else '❌ Blocked'} | Remaining: {info.get('minute_remaining', 0)}/min")
        if allowed:
            await auth_manager.record_request(free_key_id)
    
    # Show usage statistics
    print("\n5. Usage Statistics:")
    all_keys = auth_manager.list_api_keys()
    for key_id, stats in all_keys.items():
        print(f"   {stats['label']:15} | Tier: {stats['tier']:7} | Requests: {stats['total_requests']:2} | Active: {stats['is_active']}")
    
    # Demonstrate key management
    print("\n6. Key Management:")
    print(f"   Default key: {auth_manager.default_key_id}")
    
    # Switch default key
    auth_manager.set_default_key(allstar_key_id)
    print(f"   New default: {auth_manager.default_key_id}")
    
    # Deactivate a key
    auth_manager.deactivate_key(free_key_id)
    deactivated_stats = auth_manager.get_usage_stats(free_key_id)
    print(f"   Deactivated key active status: {deactivated_stats['is_active']}")
    
    print("\n✅ Authentication Demo Complete!")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_authentication_features())
    
    # Run tests if pytest is available
    try:
        import pytest
        print("\n🧪 Running Tests...")
        
        # Run authentication manager tests
        test_auth = TestAuthenticationManager()
        test_auth.setup_method()
        
        print("Testing API key management...")
        test_auth.test_add_and_retrieve_api_key()
        print("✅ API key management test passed")
        
        print("Testing tier limits...")
        test_auth.test_tier_limits()
        print("✅ Tier limits test passed")
        
        print("Testing rate limiting...")
        asyncio.run(test_auth.test_rate_limiting())
        print("✅ Rate limiting test passed")
        
        print("Testing key validation...")
        test_auth.test_key_validation()
        print("✅ Key validation test passed")
        
        print("Testing usage statistics...")
        test_auth.test_usage_statistics()
        print("✅ Usage statistics test passed")
        
        print("\n🎉 All tests passed!")
        
    except ImportError:
        print("\n📝 Install pytest to run automated tests: pip install pytest pytest-asyncio") 