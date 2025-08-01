"""
Application settings and configuration management.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Supabase Database settings
    supabase_url: str = ""
    supabase_key: str = ""
    database_url: str = ""  # Will be constructed from Supabase URL
    
    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    
    # Application settings
    app_name: str = "HoopHead API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"
    
    # Ball Don't Lie API settings
    balldontlie_api_key: str = ""
    balldontlie_api_base_url: str = "https://api.balldontlie.io/v1"
    api_request_delay: float = 0.6  # Delay between requests in seconds
    max_retries: int = 3
    cache_ttl: int = 3600  # Cache time-to-live in seconds
    
    # Security settings
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    
    # MCP settings
    mcp_server_name: str = "hoophead-mcp"
    mcp_server_version: str = "0.1.0"
    
    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 