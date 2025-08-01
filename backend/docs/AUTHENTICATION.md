# Ball Don't Lie API Authentication & Key Management

## Overview

The HoopHead project now includes a comprehensive authentication and API key management system for the Ball Don't Lie API. This system provides:

- **Tiered Access Management**: Support for different API key tiers (Free, Pro, Premium, Enterprise)
- **Secure Key Storage**: Encrypted storage of API keys with rotation support
- **Rate Limiting**: Tier-based rate limiting with automatic enforcement
- **Usage Tracking**: Detailed analytics and usage statistics per API key
- **Multi-Key Support**: Manage multiple API keys and switch between them dynamically

## Quick Start

### Basic Usage

```python
import asyncio
from backend.src.adapters.external.ball_dont_lie_client import BallDontLieClient, Sport

async def main():
    # Initialize client with API key (automatically detected tier)
    async with BallDontLieClient("your-api-key-here") as client:
        # Make API calls - rate limiting is automatic
        teams = await client.get_teams(Sport.NBA)
        print(f"Found {len(teams.data['data'])} NBA teams")

asyncio.run(main())
```

### Advanced Authentication Management

```python
from backend.src.adapters.external.auth_manager import AuthenticationManager, APITier

# Create authentication manager
auth_manager = AuthenticationManager()

# Add multiple API keys with different tiers
free_key_id = auth_manager.add_api_key("your-free-key", APITier.FREE, "Development Key")
pro_key_id = auth_manager.add_api_key("your-pro-key", APITier.PRO, "Production Key")

# Use specific key with client
async with BallDontLieClient(key_id=pro_key_id) as client:
    # This will use the Pro tier limits and tracking
    response = await client.get_players(Sport.NBA, search="LeBron")
```

## API Tier Limits

| Tier       | Requests/Hour | Requests/Minute | Concurrent | Features |
|------------|---------------|-----------------|------------|----------|
| **Free**   | 100           | 10              | 1          | Basic stats, teams, players |
| **Pro**    | 1,000         | 50              | 3          | + Advanced stats, historical data |
| **Premium**| 5,000         | 200             | 5          | + Real-time data |
| **Enterprise**| 50,000     | 1,000           | 10         | + Bulk export |

## Environment Variables

### Required
- `BALLDONTLIE_API_KEY`: Your primary Ball Don't Lie API key

### Optional
- `HOOPHEAD_ENCRYPTION_KEY`: Encryption key for secure API key storage (auto-generated if not provided)
- `HOOPHEAD_API_KEYS`: JSON array of additional API keys with their tiers

Example `.env` file:
```bash
BALLDONTLIE_API_KEY=your-primary-api-key-here
HOOPHEAD_ENCRYPTION_KEY=your-32-character-encryption-key
HOOPHEAD_API_KEYS='[{"key": "backup-key", "tier": "pro", "label": "Backup"}]'
```

## Authentication Manager API

### Key Management

```python
from backend.src.adapters.external.auth_manager import AuthenticationManager, APITier

auth_manager = AuthenticationManager()

# Add API key
key_id = auth_manager.add_api_key(
    api_key="your-api-key",
    tier=APITier.PRO,
    label="Production Key",
    set_as_default=True
)

# Get API key
api_key = auth_manager.get_api_key(key_id)

# Remove API key
auth_manager.remove_api_key(key_id)

# Set default key
auth_manager.set_default_key(key_id)

# Deactivate/reactivate key
auth_manager.deactivate_key(key_id)
auth_manager.activate_key(key_id)
```

### Rate Limiting

```python
# Check if request is allowed
allowed, rate_info = await auth_manager.check_rate_limit(key_id)

if allowed:
    # Make API request
    await auth_manager.record_request(key_id, success=True)
else:
    print(f"Rate limit exceeded. Try again in {rate_info['minute_reset']} seconds")
```

### Usage Statistics

```python
# Get usage stats for a key
stats = auth_manager.get_usage_stats(key_id)
print(f"Total requests: {stats['total_requests']}")
print(f"Hourly remaining: {stats['hourly_remaining']}")

# Get all keys with stats
all_keys = auth_manager.list_api_keys()
for key_id, stats in all_keys.items():
    print(f"{stats['label']}: {stats['tier']} tier, {stats['total_requests']} requests")
```

## Enhanced Ball Don't Lie Client

### Authentication Info

```python
async with BallDontLieClient() as client:
    # Get authentication information
    auth_info = client.get_authentication_info()
    print(f"Using {auth_info['usage_stats']['tier']} tier key")
    print(f"Requests remaining: {auth_info['usage_stats']['hourly_remaining']}")
```

### Key Switching

```python
async with BallDontLieClient() as client:
    # Switch to different API key during session
    success = client.switch_api_key("other-key-id")
    
    if success:
        # Now using different key with its tier limits
        response = await client.get_games(Sport.NBA)
```

### Key Validation

```python
async with BallDontLieClient("your-api-key") as client:
    # Validate current API key
    is_valid, validation_info = await client.validate_current_key()
    
    if is_valid:
        print(f"Key is valid. Tier: {validation_info['tier']}")
    else:
        print(f"Key validation failed: {validation_info['error']}")
```

## Rate Limiting Behavior

### Automatic Enforcement
- Rate limits are checked before each API request
- Requests are blocked if limits are exceeded
- Different tiers have different limits and recovery times

### Dynamic Rate Limiting
- Request delays are calculated based on tier limits
- Higher tiers get faster request rates
- Concurrent request limits prevent overwhelming the API

### Cache Integration
- Cached responses don't count against rate limits
- Higher tiers get cache priority during eviction
- Cache hits are still recorded for usage statistics

## Error Handling

### Authentication Errors
```python
from backend.src.core.exceptions import APIAuthenticationError, APIRateLimitError

try:
    async with BallDontLieClient("invalid-key") as client:
        response = await client.get_teams(Sport.NBA)
except APIAuthenticationError as e:
    print(f"Authentication failed: {e}")
except APIRateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.retry_after} seconds")
```

### Fallback Behavior
- If authentication manager is unavailable, client falls back to basic API key handling
- Environment variables are used as fallback for key storage
- Rate limiting reverts to simple delay-based approach

## Security Considerations

### Key Storage
- API keys are encrypted at rest using Fernet (AES 128)
- Encryption keys should be stored securely (environment variables, key management services)
- Keys are only decrypted when needed for API requests

### Key Rotation
- Support for multiple active keys allows for seamless key rotation
- Old keys can be deactivated without removing usage history
- New keys can be tested before switching production traffic

### Access Control
- Different tiers provide natural access control boundaries
- Usage tracking helps identify unusual activity patterns
- Rate limiting prevents abuse and cost overruns

## Testing

Run the authentication system tests:

```bash
# Run the test/demo script
cd tests
python test_authentication_integration.py

# Or run with pytest
pytest test_authentication_integration.py -v
```

## Migration from Simple Authentication

Existing code using the old simple authentication will continue to work. The new system is backward compatible:

```python
# Old way (still works)
client = BallDontLieClient("your-api-key")

# New way (recommended)
# API key is automatically added to authentication manager
client = BallDontLieClient("your-api-key")  # Now includes tier detection and rate limiting
```

## Troubleshooting

### Common Issues

1. **"No valid API key available"**: Set `BALLDONTLIE_API_KEY` environment variable
2. **Rate limit errors**: Check your tier limits and current usage with `get_usage_stats()`
3. **Encryption errors**: Ensure `HOOPHEAD_ENCRYPTION_KEY` is set and consistent
4. **Import errors**: Check that the cryptography package is installed

### Debug Logging

Enable debug logging to see authentication details:

```python
import logging
logging.getLogger('backend.src.adapters.external').setLevel(logging.DEBUG)
```

### Key Validation

Test your API key independently:

```python
from backend.src.adapters.external.ball_dont_lie_client import validate_api_key_quick

is_valid, result = await validate_api_key_quick("your-api-key")
print(f"Key valid: {is_valid}")
print(f"Details: {result}")
``` 