#!/usr/bin/env python3
"""Test all API endpoints to identify issues"""

import requests
import json

BASE_URL = "http://localhost:8001/api/v1"
EXCHANGE = "lmex"

def test_endpoint(name, url, params=None):
    """Test an endpoint and report results"""
    print(f"\n=== Testing {name} ===")
    print(f"URL: {url}")
    if params:
        print(f"Params: {params}")
    
    try:
        response = requests.get(url, params=params)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Response: List with {len(data)} items")
                if data:
                    print(f"First item: {json.dumps(data[0], indent=2)[:200]}...")
            else:
                print(f"Response: {json.dumps(data, indent=2)[:200]}...")
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

# Test all endpoints
print("Testing Exchange Trading Platform API Endpoints")
print("=" * 50)

# Public endpoints
test_endpoint("Ticker", f"{BASE_URL}/market/ticker/BTC-PERP", {"exchange": EXCHANGE})
test_endpoint("Symbol Info", f"{BASE_URL}/market/symbol/BTC-PERP", {"exchange": EXCHANGE})
test_endpoint("Candles", f"{BASE_URL}/market/candles/BTC-PERP", {"interval": "1h", "exchange": EXCHANGE, "limit": 2})
test_endpoint("All Tickers", f"{BASE_URL}/market/tickers", {"exchange": EXCHANGE})

# Private endpoints
test_endpoint("Open Orders", f"{BASE_URL}/trading/orders", {"exchange": EXCHANGE})
test_endpoint("Positions", f"{BASE_URL}/trading/positions", {"exchange": EXCHANGE})
test_endpoint("Account Balance", f"{BASE_URL}/account/balance", {"exchange": EXCHANGE})