import logging
from typing import Dict, Optional, Tuple
from backend.core.config import settings

logger = logging.getLogger(__name__)


class APIKeyService:
    """Service for managing exchange API keys"""
    
    def __init__(self):
        self._keys: Dict[str, Tuple[str, str]] = {}
        self._load_from_env()
    
    def _load_from_env(self):
        """Load API keys from environment variables"""
        import os
        
        # Load Bitunix keys - check both possible env var names
        bitunix_key = os.getenv('BITUNIX_API_KEY') or settings.BITUNIX_API_KEY
        bitunix_secret = os.getenv('BITUNIX_SECRET_KEY') or os.getenv('BITUNIX_API_SECRET') or settings.BITUNIX_API_SECRET
        
        if bitunix_key and bitunix_secret:
            self._keys['bitunix'] = (bitunix_key, bitunix_secret)
            logger.info("Loaded Bitunix API keys from environment")
        else:
            logger.warning("Bitunix API keys not found in environment")
        
        # Load LMEX keys - check both possible env var names
        lmex_key = os.getenv('LMEX_API_KEY') or settings.LMEX_API_KEY
        lmex_secret = os.getenv('LMEX_SECRET_KEY') or os.getenv('LMEX_API_SECRET') or settings.LMEX_API_SECRET
        
        if lmex_key and lmex_secret:
            self._keys['lmex'] = (lmex_key, lmex_secret)
            logger.info("Loaded LMEX API keys from environment")
        else:
            logger.warning("LMEX API keys not found in environment")
    
    def get_keys(self, exchange: str) -> Optional[Tuple[str, str]]:
        """Get API keys for an exchange
        
        Returns:
            Tuple of (api_key, api_secret) or None if not found
        """
        return self._keys.get(exchange.lower())
    
    def has_keys(self, exchange: str) -> bool:
        """Check if API keys exist for an exchange"""
        return exchange.lower() in self._keys
    
    def set_keys(self, exchange: str, api_key: str, api_secret: str, passphrase: Optional[str] = None):
        """Set API keys for an exchange (runtime only, not persisted)"""
        self._keys[exchange.lower()] = (api_key, api_secret)
        logger.info(f"API keys set for {exchange}")
    
    def validate_keys(self, exchange: str) -> bool:
        """Validate that API keys are properly formatted"""
        keys = self.get_keys(exchange)
        if not keys:
            return False
        
        api_key, api_secret = keys
        
        # Basic validation - keys should not be empty and have reasonable length
        if not api_key or not api_secret:
            return False
        
        if len(api_key) < 10 or len(api_secret) < 10:
            logger.warning(f"API keys for {exchange} appear to be too short")
            return False
        
        return True
    
    def get_configured_exchanges(self) -> list[str]:
        """Get list of exchanges with configured API keys"""
        return [ex for ex in self._keys.keys() if self.validate_keys(ex)]


# Singleton instance
api_key_service = APIKeyService()