#!/usr/bin/env python3
"""Test chart timestamp fix"""

import requests
import json
from datetime import datetime

# Test the candles API
url = "http://localhost:8001/api/v1/market/candles/BTC-PERP"
params = {
    "interval": "1h",
    "exchange": "lmex",
    "limit": 3
}

try:
    response = requests.get(url, params=params)
    if response.status_code == 200:
        candles = response.json()
        print(f"Received {len(candles)} candles\n")
        
        for i, candle in enumerate(candles):
            timestamp_str = candle['timestamp']
            print(f"Candle {i+1}:")
            print(f"  Raw timestamp: {timestamp_str}")
            
            # Test the frontend's timestamp conversion logic
            # Add 'Z' if not present
            normalized = timestamp_str if timestamp_str.endswith('Z') else f"{timestamp_str}Z"
            print(f"  Normalized: {normalized}")
            
            # Convert to Unix timestamp in seconds (as frontend does)
            try:
                dt = datetime.fromisoformat(normalized.replace('Z', '+00:00'))
                unix_seconds = int(dt.timestamp())
                print(f"  Unix seconds: {unix_seconds}")
                print(f"  Verification: {datetime.fromtimestamp(unix_seconds).isoformat()}")
                print(f"  Success: ✓")
            except Exception as e:
                print(f"  Error: {e}")
            print()
            
    else:
        print(f"Error: {response.status_code} - {response.text}")
        
except Exception as e:
    print(f"Error: {e}")