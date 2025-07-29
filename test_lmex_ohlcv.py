#!/usr/bin/env python3
"""Test LMEX OHLCV/Candles endpoint"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.lmex import LMEXExchange
import json

def test_ohlcv():
    """Test fetching OHLCV data from LMEX"""
    exchange = LMEXExchange()
    
    # Test parameters
    symbol = "BTC-PERP"
    timeframe = "1h"
    limit = 10
    
    print(f"Testing LMEX OHLCV fetch for {symbol} {timeframe}")
    print("=" * 50)
    
    result = None
    error = None
    
    def callback(res):
        nonlocal result, error
        status, data = res
        if status == "success":
            result = data
        else:
            error = data
    
    # Fetch OHLCV data
    exchange.fetchOHLCV(symbol, timeframe, limit, callback)
    
    if error:
        print(f"Error: {error}")
        return False
    
    if result:
        print(f"Successfully fetched {len(result)} candles")
        print("\nFirst candle:")
        print(json.dumps(result[0], indent=2))
        print("\nLast candle:")
        print(json.dumps(result[-1], indent=2))
        return True
    
    return False

if __name__ == "__main__":
    success = test_ohlcv()
    sys.exit(0 if success else 1)