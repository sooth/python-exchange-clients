#!/usr/bin/env python3
"""Simple synchronous test for LMEX exchange"""

import os
import sys
from dotenv import load_dotenv
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from exchanges.lmex import LMEXExchange

def main():
    """Test LMEX connection"""
    # Load environment variables
    load_dotenv()
    
    # Check API keys
    api_key = os.getenv('LMEX_API_KEY')
    secret_key = os.getenv('LMEX_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ LMEX API keys not found in environment")
        return
    
    print("✅ LMEX API keys found")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   Secret Key: {secret_key[:10]}...")
    
    # Initialize exchange
    exchange = LMEXExchange()
    
    print("\n🔄 Testing LMEX connection...")
    
    # Test 1: Fetch tickers
    print("\n1. Fetching market tickers...")
    tickers_result = None
    error = None
    
    def ticker_callback(result):
        nonlocal tickers_result, error
        if isinstance(result, tuple):
            status, data = result
            if status == "success":
                tickers_result = data
            else:
                error = data
        else:
            error = Exception(f"Unexpected result format: {result}")
    
    exchange.fetchTickers(ticker_callback)
    
    # Wait a bit for the callback
    time.sleep(2)
    
    if error:
        print(f"   ❌ Error: {error}")
    elif tickers_result:
        # Check if it's a dictionary or list
        if isinstance(tickers_result, dict):
            print(f"   ✅ Found {len(tickers_result)} trading pairs")
            print("   Sample tickers:")
            for symbol, ticker in list(tickers_result.items())[:5]:
                if isinstance(ticker, dict):
                    print(f"     {symbol}: ${ticker.get('price', ticker.get('last', 'N/A'))}")
                else:
                    print(f"     {symbol}: ${ticker.price}")
        else:
            print(f"   ✅ Found {len(tickers_result)} trading pairs")
            print("   Sample tickers:")
            for ticker in tickers_result[:5]:
                print(f"     {ticker.symbol}: ${ticker.price}")
    else:
        print("   ⚠️  No response received")
    
    # Test 2: Fetch balance
    print("\n2. Fetching account balance...")
    balance_result = None
    error = None
    
    def balance_callback(result):
        nonlocal balance_result, error
        if isinstance(result, tuple):
            status, data = result
            if status == "success":
                balance_result = data
            else:
                error = data
        else:
            error = Exception(f"Unexpected result format: {result}")
    
    exchange.fetchBalance(balance_callback)
    
    # Wait a bit for the callback
    time.sleep(2)
    
    if error:
        print(f"   ⚠️  Balance fetch failed: {error}")
        print("   This is normal if you haven't deposited funds")
    elif balance_result:
        print("   ✅ Balance fetched successfully")
        # Show non-zero balances
        non_zero = [b for b in balance_result if b.balance > 0]
        if non_zero:
            print("   Non-zero balances:")
            for bal in non_zero:
                # ExchangeBalance has coin and balance attributes
                print(f"     {bal.asset}: {bal.balance}")
        else:
            print("   No non-zero balances found")
    else:
        print("   ⚠️  No response received")
    
    print("\n✅ LMEX exchange testing complete!")
    print("   Now restart the trading platform to use LMEX only")

if __name__ == "__main__":
    main()