#!/usr/bin/env python3
"""Test chart API endpoint"""

import requests
import json

# Test the candles endpoint
url = "http://localhost:8001/api/v1/market/candles/BTC-PERP"
params = {
    "interval": "1h",
    "exchange": "lmex",
    "limit": 10
}

try:
    response = requests.get(url, params=params)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Received {len(data)} candles")
        if data:
            print("\nFirst candle:")
            print(json.dumps(data[0], indent=2))
            print("\nLast candle:")
            print(json.dumps(data[-1], indent=2))
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")