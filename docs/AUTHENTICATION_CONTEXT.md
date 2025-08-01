# Authentication System - Technical Context

## Overview

The HoopHead authentication system provides enterprise-grade API key management for the Ball Don't Lie API with tiered access control, secure storage, and comprehensive usage tracking. This document details the technical implementation and architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Authentication Flow                        │
├─────────────────────────────────────────────────────────────┤
│  1. API Key Validation                                      │
│  2. Tier Detection & Rate Limit Check                      │
│  3. Request Processing with Usage Tracking                 │
│  4. Response Caching (Tier-Priority Based)                 │
│  5. Usage Statistics Update                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Authentication  │    │ Ball Don't Lie  │    │ Redis Cache     │
│ Manager         │    │ Client          │    │ (Sport-Specific)│
│                 │    │                 │    │                 │
│ • Key Storage   │◄──►│ • Rate Limiting │◄──►│ • TTL Strategy  │
│ • Tier Limits   │    │ • Error Handling│    │ • Hit Tracking  │
│ • Usage Stats   │    │ • Multi-Sport   │    │ • Compression   │
│ • Encryption    │    │ • Async Requests│    │ • Analytics     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. Authentication Manager (`auth_manager.py`)

**Purpose**: Central hub for API key management, encryption, and access control.

**Key Classes:**
- `AuthenticationManager`: Main controller class
- `APIKeyInfo`: Data structure for key metadata
- `TierLimits`: Rate limit configuration per tier
- `APITier`: Enum for access tiers (Free, Pro, Premium, Enterprise)

**Core Functionality:**
```python
# Key Management
key_id = auth_manager.add_api_key(api_key, APITier.PRO, "Production Key")
api_key = auth_manager.get_api_key(key_id)  # Decrypted on demand
auth_manager.remove_api_key(key_id)

# Rate Limiting
allowed, rate_info = await auth_manager.check_rate_limit(key_id)
await auth_manager.record_request(key_id, success=True)

# Usage Analytics
stats = auth_manager.get_usage_stats(key_id)
all_keys = auth_manager.list_api_keys()
```

### 2. Enhanced Ball Don't Lie Client (`ball_dont_lie_client.py`)

**Purpose**: HTTP client with integrated authentication and caching.

**Enhanced Features:**
- Automatic tier detection from API key format
- Pre-request rate limit validation
- Tier-based request timing
- Usage tracking integration
- Multi-key support with dynamic switching

**Authentication Integration Points:**
```python
# Initialization with auth manager integration
client = BallDontLieClient(api_key="your-key")  # Auto-adds to auth manager
client = BallDontLieClient(key_id="existing-key-id")  # Uses managed key

# Runtime authentication info
auth_info = client.get_authentication_info()
is_valid, result = await client.validate_current_key()
success = client.switch_api_key("other-key-id")
```

## Security Implementation

### Encryption Strategy

**Algorithm**: Fernet (AES 128 in CBC mode with HMAC-SHA256 for authentication)
**Key Management**: 
- Environment-based encryption keys (`HOOPHEAD_ENCRYPTION_KEY`)
- Auto-generation with warning for development
- URL-safe base64 encoding for storage compatibility

**Implementation:**
```python
# Encryption/Decryption Flow
cipher = Fernet(encryption_key.encode())
encrypted_key = cipher.encrypt(api_key.encode()).decode()
decrypted_key = cipher.decrypt(encrypted_key.encode()).decode()

# Key Storage
key_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]  # Unique identifier
```

### Access Control Matrix

| Tier | Hour Limit | Minute Limit | Concurrent | Cache Priority | Features |
|------|------------|--------------|------------|----------------|----------|
| Free | 100 | 10 | 1 | 1 (Low) | Basic API access |
| Pro | 1,000 | 50 | 3 | 2 (Medium) | + Historical data |
| Premium | 5,000 | 200 | 5 | 3 (High) | + Real-time updates |
| Enterprise | 50,000 | 1,000 | 10 | 4 (Maximum) | + Bulk operations |

## Rate Limiting Implementation

### Two-Tier Rate Limiting
1. **Minute-based**: Short-term burst protection
2. **Hour-based**: Long-term usage control

### Rate Limit Tracking
```python
# Time Window Management
current_time = time.time()
if current_time >= key_info.hourly_reset_time:
    key_info.hourly_requests = 0
    key_info.hourly_reset_time = current_time + 3600

if current_time >= key_info.minute_reset_time:
    key_info.minute_requests = 0
    key_info.minute_reset_time = current_time + 60

# Dynamic Request Timing
base_delay = 60.0 / tier_limits.requests_per_minute
await asyncio.sleep(base_delay - time_since_last_request)
```

### Rate Limit Enforcement Flow
```
Request → Rate Check → [Pass] → API Call → Record Usage → Response
             ↓
           [Fail] → Rate Limit Error (429) → Retry After Info
```

## Caching Integration

### Sport-Specific TTL Strategy
```python
sport_ttl_strategies = {
    Sport.NBA: {
        'teams': 86400,      # 24 hours (teams change rarely)
        'players': 21600,    # 6 hours (trades happen)  
        'games': 3600,       # 1 hour (game results)
        'stats': 1800,       # 30 min (very dynamic)
    },
    # Similar strategies for MLB, NFL, NHL, EPL
}
```

### Cache Priority by Tier
- Higher tiers get cache priority during eviction
- Cache hits still recorded for usage tracking
- Compressed storage for large responses (>1KB)

### Cache Key Structure
```
hoophead:v1:{sport}:{endpoint}:{params_hash}
```

## Error Handling Strategy

### Authentication Errors
```python
try:
    response = await client.get_teams(Sport.NBA)
except APIAuthenticationError as e:
    # Handle invalid/expired keys
    logger.error(f"Auth failed: {e.context}")
except APIRateLimitError as e:
    # Handle rate limit exceeded
    retry_after = e.retry_after
    await asyncio.sleep(retry_after)
```

### Graceful Degradation
1. **Auth Manager Unavailable**: Falls back to simple API key handling
2. **Rate Limit Exceeded**: Returns structured error with retry timing
3. **Cache Miss**: Proceeds with API request and caches result
4. **API Error**: Retries with exponential backoff

## Usage Analytics

### Tracked Metrics
- **Total Requests**: Lifetime request count per key
- **Rate Limit Usage**: Current hour/minute consumption
- **Success/Failure Rates**: API call success tracking
- **Cache Hit Rates**: Efficiency metrics
- **Tier Utilization**: Feature usage by tier

### Analytics API
```python
# Individual Key Stats
stats = auth_manager.get_usage_stats(key_id)
{
    "total_requests": 1547,
    "hourly_remaining": 453,
    "minute_remaining": 8,
    "tier": "pro",
    "features": ["basic_stats", "advanced_stats", "historical_data"]
}

# All Keys Overview
all_keys = auth_manager.list_api_keys()
# Returns dictionary with usage stats for all managed keys
```

## Environment Configuration

### Required Environment Variables
```bash
# Primary API key (automatically detected tier)
BALLDONTLIE_API_KEY=your-primary-api-key

# Optional: Encryption key for secure storage
HOOPHEAD_ENCRYPTION_KEY=your-32-character-base64-key

# Optional: Additional keys with tier specification
HOOPHEAD_API_KEYS='[
  {"key": "backup-key", "tier": "pro", "label": "Backup Production"},
  {"key": "dev-key", "tier": "free", "label": "Development"}
]'
```

### Configuration Loading Priority
1. Constructor parameters (highest priority)
2. Environment variables (`BALLDONTLIE_API_KEY`)
3. Settings file (`settings.balldontlie_api_key`)
4. Fallback to auth manager default key

## Testing Strategy

### Unit Tests Coverage
- **Key Management**: Add, remove, activate, deactivate operations
- **Encryption**: Encrypt/decrypt cycle validation
- **Rate Limiting**: Time window and counter logic
- **Tier Detection**: API key format recognition
- **Usage Tracking**: Request counting and statistics

### Integration Tests
- **Auth Manager + Client**: End-to-end authentication flow
- **Rate Limit Enforcement**: Actual request throttling
- **Cache Integration**: Authentication + caching behavior
- **Error Scenarios**: Fallback behavior validation

### Demo Script
The `test_authentication_integration.py` includes:
- Live demonstration of tier limits
- Rate limiting in action
- Usage statistics tracking
- Key management operations

## Performance Considerations

### Optimization Strategies
1. **Lazy Decryption**: Keys only decrypted when needed
2. **In-Memory Caching**: Key info cached to avoid repeated crypto operations
3. **Async Operations**: Non-blocking rate limit checks and usage recording
4. **Efficient Key Lookup**: SHA256 hash-based key identification

### Memory Usage
- Minimal overhead: ~1KB per managed API key
- Compressed cache entries for large responses
- Automatic cleanup of expired rate limit counters

## Future Enhancements

### Planned Features
1. **Persistent Storage**: Database-backed key storage for production
2. **Key Rotation**: Automated key rotation with zero downtime
3. **Advanced Analytics**: Machine learning for usage pattern analysis
4. **Audit Logging**: Comprehensive security event logging
5. **Multi-Tenant Support**: Organization-level key management

### Scalability Roadmap
1. **Distributed Rate Limiting**: Redis-based rate limiting for multi-instance deployments
2. **Key Sharding**: Distributed key storage for high-volume scenarios
3. **Real-time Monitoring**: Live dashboards for API usage and health
4. **Auto-scaling**: Dynamic tier upgrades based on usage patterns

This authentication system provides a solid foundation for enterprise-grade API management while maintaining simplicity for development use cases. 