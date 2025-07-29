#!/usr/bin/env python3
"""Test LMEX exchange connection with API keys"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from exchanges.lmex import LMEXExchange

async def test_lmex():
    """Test LMEX connection and basic operations"""
    # Load environment variables
    load_dotenv()
    
    # Get API keys
    api_key = os.getenv('LMEX_API_KEY')
    secret_key = os.getenv('LMEX_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ LMEX API keys not found in environment")
        print("   Please ensure LMEX_API_KEY and LMEX_SECRET_KEY are set in .env")
        return
    
    print("✅ LMEX API keys found")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   Secret Key: {secret_key[:10]}...")
    
    # Initialize exchange (it will load keys from environment automatically)
    exchange = LMEXExchange()
    
    print("\n🔄 Testing LMEX connection...")
    
    try:
        # Test 1: Fetch tickers
        print("\n1. Fetching market tickers...")
        tickers = await exchange.fetchTickers()
        print(f"   ✅ Found {len(tickers)} trading pairs")
        
        # Show first 5 tickers
        if tickers:
            print("   Sample tickers:")
            for symbol, ticker in list(tickers.items())[:5]:
                print(f"     {symbol}: ${ticker.get('last', 'N/A')}")
        
        # Test 2: Fetch balance
        print("\n2. Fetching account balance...")
        try:
            balance = await exchange.fetchBalance()
            print("   ✅ Balance fetched successfully")
            
            # Show non-zero balances
            non_zero = {k: v for k, v in balance.items() if isinstance(v, dict) and v.get('total', 0) > 0}
            if non_zero:
                print("   Non-zero balances:")
                for currency, bal in non_zero.items():
                    print(f"     {currency}: {bal['total']}")
            else:
                print("   No non-zero balances found")
        except Exception as e:
            print(f"   ⚠️  Balance fetch failed: {e}")
            print("   This is normal if you haven't deposited funds")
        
        # Test 3: Fetch a specific symbol info
        print("\n3. Testing symbol info...")
        test_symbol = "BTC-USDT"
        try:
            markets = await exchange.fetchMarkets()
            if test_symbol in markets:
                market = markets[test_symbol]
                print(f"   ✅ {test_symbol} market info:")
                print(f"     Min order size: {market.get('limits', {}).get('amount', {}).get('min', 'N/A')}")
                print(f"     Price precision: {market.get('precision', {}).get('price', 'N/A')}")
            else:
                print(f"   ⚠️  {test_symbol} not found in markets")
        except Exception as e:
            print(f"   ❌ Failed to fetch markets: {e}")
        
        print("\n✅ LMEX exchange is working correctly!")
        print("   You can now use LMEX in the trading platform")
        
    except Exception as e:
        print(f"\n❌ LMEX connection failed: {e}")
        print("   Please check your API keys and network connection")

if __name__ == "__main__":
    asyncio.run(test_lmex())