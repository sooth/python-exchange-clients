#!/usr/bin/env python3
"""Test LMEX OHLCV directly"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.exchange_manager import exchange_manager

async def test():
    try:
        # Initialize exchange manager
        await exchange_manager.initialize()
        
        # Test OHLCV fetch
        print("Testing LMEX OHLCV fetch for BTC-PERP...")
        candles = await exchange_manager.fetch_ohlcv("lmex", "BTC-PERP", "1h", 10)
        
        print(f"Received {len(candles)} candles")
        if candles:
            print(f"\nFirst candle:")
            print(f"  Time: {candles[0].timestamp}")
            print(f"  Open: {candles[0].open}")
            print(f"  High: {candles[0].high}")
            print(f"  Low: {candles[0].low}")
            print(f"  Close: {candles[0].close}")
            print(f"  Volume: {candles[0].volume}")
            
            print(f"\nLast candle:")
            print(f"  Time: {candles[-1].timestamp}")
            print(f"  Open: {candles[-1].open}")
            print(f"  High: {candles[-1].high}")
            print(f"  Low: {candles[-1].low}")
            print(f"  Close: {candles[-1].close}")
            print(f"  Volume: {candles[-1].volume}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await exchange_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test())