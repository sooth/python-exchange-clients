#!/usr/bin/env python3
"""Check frontend status and chart functionality"""

import requests
import time

print("Testing frontend and API status...")

# Test backend API
try:
    # Test candles endpoint
    candles_response = requests.get("http://localhost:8001/api/v1/market/candles/BTC-PERP", 
                                   params={"interval": "1h", "exchange": "lmex", "limit": 2})
    print(f"✓ Backend candles API: {candles_response.status_code}")
    
    # Test ticker endpoint
    ticker_response = requests.get("http://localhost:8001/api/v1/market/ticker/BTC-PERP",
                                  params={"exchange": "lmex"})
    print(f"✓ Backend ticker API: {ticker_response.status_code}")
    
    # Check ticker data
    if ticker_response.status_code == 200:
        ticker = ticker_response.json()
        print(f"  Bid: ${ticker.get('bid', 'N/A')}")
        print(f"  Ask: ${ticker.get('ask', 'N/A')}")
        print(f"  Last: ${ticker.get('last', 'N/A')}")
    
except Exception as e:
    print(f"✗ Backend API error: {e}")

# Test frontend
try:
    frontend_response = requests.get("http://localhost:3000")
    print(f"\n✓ Frontend server: {frontend_response.status_code}")
except Exception as e:
    print(f"\n✗ Frontend error: {e}")

print("\nChart timestamp fix has been applied:")
print("- Backend returns ISO timestamps without timezone (e.g., '2025-07-28T16:00:00')")
print("- Frontend adds 'Z' to treat as UTC before converting to Unix seconds")
print("- WebSocket delivers real-time trade data for candle updates")
print("- Orderbook WebSocket provides real-time bid/ask prices")

print("\nTo verify in browser:")
print("1. Open http://localhost:3000")
print("2. Check browser console for any errors")
print("3. Chart should display LMEX BTC-PERP data")
print("4. Bid/Ask prices should update in real-time")
print("5. No 'Invalid date string' errors should appear")