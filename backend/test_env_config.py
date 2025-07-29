#!/usr/bin/env python3
"""Test script to verify environment configuration"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings
from backend.services.api_key_service import api_key_service


def test_env_config():
    print("Testing Environment Configuration")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    print(f"1. .env file exists: {os.path.exists(env_file)}")
    
    # Check loaded settings
    print("\n2. Loaded Settings:")
    print(f"   - BITUNIX_API_KEY: {'***' + settings.BITUNIX_API_KEY[-4:] if settings.BITUNIX_API_KEY else 'Not set'}")
    print(f"   - BITUNIX_API_SECRET: {'***' + settings.BITUNIX_API_SECRET[-4:] if settings.BITUNIX_API_SECRET else 'Not set'}")
    print(f"   - DEFAULT_EXCHANGE: {settings.DEFAULT_EXCHANGE}")
    print(f"   - SUPPORTED_EXCHANGES: {settings.SUPPORTED_EXCHANGES}")
    
    # Check API key service
    print("\n3. API Key Service:")
    print(f"   - Has Bitunix keys: {api_key_service.has_keys('bitunix')}")
    print(f"   - Bitunix keys valid: {api_key_service.validate_keys('bitunix')}")
    print(f"   - Configured exchanges: {api_key_service.get_configured_exchanges()}")
    
    # Check environment variables directly
    print("\n4. Direct Environment Variables:")
    print(f"   - BITUNIX_API_KEY from env: {'Set' if os.getenv('BITUNIX_API_KEY') else 'Not set'}")
    print(f"   - BITUNIX_SECRET_KEY from env: {'Set' if os.getenv('BITUNIX_SECRET_KEY') else 'Not set'}")
    
    # Success if API key service has the keys, even if settings doesn't
    return api_key_service.has_keys('bitunix') and api_key_service.validate_keys('bitunix')


if __name__ == "__main__":
    success = test_env_config()
    print(f"\n{'✓' if success else '✗'} Environment configuration {'successful' if success else 'failed'}")
    sys.exit(0 if success else 1)