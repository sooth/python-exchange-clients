#!/usr/bin/env python3
"""Test LMEX ticker data"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.exchange_manager import exchange_manager

async def test():
    try:
        # Initialize exchange manager
        await exchange_manager.initialize()
        
        # Get raw exchange
        ex = exchange_manager.get_exchange("lmex")
        
        # Fetch all tickers
        print("Fetching LMEX tickers...")
        tickers = await ex.fetchTickers()
        
        # Find BTC-PERP
        btc_ticker = None
        for ticker in tickers:
            if hasattr(ticker, 'symbol') and ticker.symbol == 'BTC-PERP':
                btc_ticker = ticker
                break
        
        if btc_ticker:
            print(f"\nBTC-PERP ticker data:")
            print(f"  Symbol: {btc_ticker.symbol}")
            print(f"  Last Price: {btc_ticker.lastPrice if hasattr(btc_ticker, 'lastPrice') else 'N/A'}")
            print(f"  Bid Price: {btc_ticker.bidPrice if hasattr(btc_ticker, 'bidPrice') else 'N/A'}")
            print(f"  Ask Price: {btc_ticker.askPrice if hasattr(btc_ticker, 'askPrice') else 'N/A'}")
            print(f"  Volume: {btc_ticker.volume if hasattr(btc_ticker, 'volume') else 'N/A'}")
            
            # Check raw response
            if hasattr(btc_ticker, 'raw_response'):
                print(f"\n  Raw response: {btc_ticker.raw_response}")
        else:
            print("BTC-PERP not found in tickers")
            print(f"Available symbols: {[t.symbol for t in tickers[:5] if hasattr(t, 'symbol')]}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await exchange_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test())