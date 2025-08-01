"""
Application settings and configuration management.
All values should come from environment variables for production safety.
"""
import os
from typing import Optional, Dict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings - all values from environment variables."""
    
    # Supabase Database settings
    supabase_url: str = ""
    supabase_key: str = ""
    database_url: str = ""  # Will be constructed from Supabase URL
    
    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_max_connections: int = 10
    
    # Application settings
    app_name: str = "HoopHead API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"
    
    # Ball Don't Lie API settings (multi-sport)
    balldontlie_api_key: str = ""
    api_request_delay: float = 0.6  # Delay between requests in seconds
    max_retries: int = 3
    cache_ttl: int = 3600  # Cache time-to-live in seconds
    
    # Ball Don't Lie API endpoints (sport-specific)
    balldontlie_nba_base_url: str = "https://api.balldontlie.io/v1"
    balldontlie_mlb_base_url: str = "https://api.balldontlie.io/mlb/v1"
    balldontlie_nfl_base_url: str = "https://api.balldontlie.io/nfl/v1"
    balldontlie_nhl_base_url: str = "https://api.balldontlie.io/nhl/v1"
    balldontlie_epl_base_url: str = "https://api.balldontlie.io/epl/v1"
    
    # User Agent for API requests
    api_user_agent: str = "HoopHead/0.1.0"
    
    # Security settings
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # MCP settings
    mcp_server_name: str = "hoophead-mcp"
    mcp_server_version: str = "0.1.0"
    
    # Logging settings
    log_level: str = "INFO"
    
    @property
    def sport_base_urls(self) -> Dict[str, str]:
        """Get all sport base URLs as a dictionary."""
        return {
            "nba": self.balldontlie_nba_base_url,
            "mlb": self.balldontlie_mlb_base_url,
            "nfl": self.balldontlie_nfl_base_url,
            "nhl": self.balldontlie_nhl_base_url,
            "epl": self.balldontlie_epl_base_url,
        }
    
    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL URL from Supabase URL."""
        if self.supabase_url and "supabase.co" in self.supabase_url:
            # Extract project ref from Supabase URL
            project_ref = self.supabase_url.split("//")[1].split(".")[0]
            return f"postgresql://postgres:[password]@db.{project_ref}.supabase.co:5432/postgres"
        return self.database_url or "postgresql://hoophead:password@localhost:5432/hoophead"
    
    @property
    def redis_connection_kwargs(self) -> Dict[str, any]:
        """Get Redis connection parameters."""
        from urllib.parse import urlparse
        
        if self.redis_url.startswith('redis://'):
            parsed = urlparse(self.redis_url)
            return {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 6379,
                'db': parsed.path.lstrip('/') or self.redis_db,
                'password': parsed.password or self.redis_password,
                'max_connections': self.redis_max_connections,
                'decode_responses': True
            }
        else:
            return {
                'host': 'localhost',
                'port': 6379,
                'db': self.redis_db,
                'password': self.redis_password,
                'max_connections': self.redis_max_connections,
                'decode_responses': True
            }
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 