#!/usr/bin/env python3
"""Test candles API response"""

import requests
import json

url = "http://localhost:8001/api/v1/market/candles/BTC-PERP"
params = {
    "interval": "1h",
    "exchange": "lmex",
    "limit": 2
}

try:
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nReceived {len(data)} candles")
        
        for i, candle in enumerate(data):
            print(f"\nCandle {i+1}:")
            print(f"  Timestamp: {candle.get('timestamp')} (type: {type(candle.get('timestamp')).__name__})")
            print(f"  Open: {candle.get('open')}")
            print(f"  Close: {candle.get('close')}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")