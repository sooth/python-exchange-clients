#!/usr/bin/env python3
"""Test LMEX orderbook to get bid/ask prices"""

import requests
import json

def test_orderbook():
    """Test LMEX orderbook endpoint"""
    # Try orderbook endpoint for BTC-PERP
    url = "https://api.lmex.io/futures/api/v2.2/orderbook?symbol=BTC-PERP"
    
    print(f"Fetching orderbook from: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\nOrderbook structure: {list(data.keys())}")
            
            # Show top of orderbook
            if 'buyQuote' in data and data['buyQuote']:
                best_bid = data['buyQuote'][0]
                print(f"\nBest bid: Price={best_bid.get('price')}, Size={best_bid.get('size')}")
            
            if 'sellQuote' in data and data['sellQuote']:
                best_ask = data['sellQuote'][0]
                print(f"Best ask: Price={best_ask.get('price')}, Size={best_ask.get('size')}")
                
            # Also check market summary for the same symbol
            print("\n--- Checking market_summary ---")
            summary_url = "https://api.lmex.io/futures/api/v2.2/market_summary"
            summary_response = requests.get(summary_url)
            
            if summary_response.status_code == 200:
                markets = summary_response.json()
                for market in markets:
                    if market.get('symbol') == 'BTC-PERP':
                        print(f"Market summary for BTC-PERP:")
                        print(f"  Last: {market.get('last')}")
                        print(f"  Bid: {market.get('bid')}")
                        print(f"  Ask: {market.get('ask')}")
                        print(f"  Volume: {market.get('volume')}")
                        break
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_orderbook()