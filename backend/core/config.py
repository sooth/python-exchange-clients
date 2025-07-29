from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "Unified Exchange Trading Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Allow all origins for local development
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    DATABASE_URL: Optional[str] = None
    REDIS_URL: str = "redis://localhost:6379"
    
    RATE_LIMIT_PER_MINUTE: int = 600
    
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_CONNECTION_TIMEOUT: int = 60
    
    SUPPORTED_EXCHANGES: List[str] = ["lmex"]
    DEFAULT_EXCHANGE: str = "lmex"
    
    # Exchange API Keys
    BITUNIX_API_KEY: Optional[str] = None
    BITUNIX_API_SECRET: Optional[str] = None
    LMEX_API_KEY: Optional[str] = None
    LMEX_API_SECRET: Optional[str] = None
    
    # Exchange Configuration
    BITUNIX_TESTNET: bool = False
    LMEX_TESTNET: bool = False
    
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields like LMEX_SECRET_KEY

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override with environment variables if they exist
        if os.getenv('BITUNIX_API_KEY'):
            self.BITUNIX_API_KEY = os.getenv('BITUNIX_API_KEY')
        if os.getenv('BITUNIX_SECRET_KEY'):
            self.BITUNIX_API_SECRET = os.getenv('BITUNIX_SECRET_KEY')
        elif os.getenv('BITUNIX_API_SECRET'):
            self.BITUNIX_API_SECRET = os.getenv('BITUNIX_API_SECRET')
        if os.getenv('LMEX_API_KEY'):
            self.LMEX_API_KEY = os.getenv('LMEX_API_KEY')
        if os.getenv('LMEX_SECRET_KEY'):
            self.LMEX_API_SECRET = os.getenv('LMEX_SECRET_KEY')
        elif os.getenv('LMEX_API_SECRET'):
            self.LMEX_API_SECRET = os.getenv('LMEX_API_SECRET')


settings = Settings()