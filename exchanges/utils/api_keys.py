"""API Key Storage for Exchange Clients"""

import os
from typing import Dict, Optional
from dotenv import load_dotenv


class APIKeyStorage:
    """
    Manages API keys for different exchanges.
    Keys are loaded from environment variables.
    """
    _shared_instance = None

    def __init__(self):
        # Load environment variables
        load_dotenv()
        self._keys_cache = {}

    @classmethod
    def shared(cls):
        """Get shared instance"""
        if cls._shared_instance is None:
            cls._shared_instance = cls()
        return cls._shared_instance

    def getKeys(self, exchange: str) -> Dict[str, str]:
        """
        Get API keys for a specific exchange.

        Args:
            exchange: Exchange name (e.g., "BitUnix", "LMEX")

        Returns:
            Dictionary with 'apiKey' and 'secretKey'
        """
        # Check cache first
        if exchange in self._keys_cache:
            return self._keys_cache[exchange]

        # Load from environment
        keys = {}

        if exchange.upper() == "BITUNIX":
            keys = {
                "apiKey": os.getenv("BITUNIX_API_KEY", ""),
                "secretKey": os.getenv("BITUNIX_SECRET_KEY", "")
            }
        elif exchange.upper() == "LMEX":
            keys = {
                "apiKey": os.getenv("LMEX_API_KEY", ""),
                "secretKey": os.getenv("LMEX_SECRET_KEY", "")
            }

        # Cache the result
        self._keys_cache[exchange] = keys
        return keys

    def getBearerToken(self, exchange: str) -> Optional[str]:
        """
        Get bearer token for exchanges that use it (like LMEX for grid bots).

        Args:
            exchange: Exchange name

        Returns:
            Bearer token or None
        """
        if exchange.upper() == "LMEX":
            return os.getenv("LMEX_BEARER_TOKEN")
        return None
