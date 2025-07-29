#!/usr/bin/env python3
"""Test Bitunix API connectivity with real credentials"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.exchange_manager import exchange_manager
from backend.services.api_key_service import api_key_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_bitunix_api():
    print("Testing Bitunix API Integration")
    print("=" * 50)
    
    # Check if we have API keys
    if not api_key_service.has_keys('bitunix'):
        print("❌ No Bitunix API keys found!")
        return False
    
    print("✓ Bitunix API keys loaded")
    
    # Initialize exchange manager
    print("\n1. Initializing Exchange Manager...")
    await exchange_manager.initialize()
    
    # Get Bitunix exchange
    try:
        exchange = exchange_manager.get_exchange('bitunix')
        print("✓ Bitunix exchange initialized")
    except Exception as e:
        print(f"❌ Failed to get exchange: {e}")
        return False
    
    # Test 1: Fetch Tickers
    print("\n2. Testing fetchTickers()...")
    try:
        tickers = await exchange_manager.fetch_all_tickers('bitunix')
        print(f"✓ Fetched {len(tickers)} tickers")
        if tickers:
            print(f"   Sample: {tickers[0].symbol} - Last: ${tickers[0].last}")
    except Exception as e:
        print(f"❌ Failed to fetch tickers: {e}")
    
    # Test 2: Fetch Balance
    print("\n3. Testing fetchBalance()...")
    try:
        balance = await exchange_manager.fetch_balance('bitunix')
        print(f"✓ Fetched balance for {len(balance.balances)} currencies")
        for currency, bal in list(balance.balances.items())[:3]:
            if bal.total > 0:
                print(f"   {currency}: {bal.total} (Free: {bal.free}, Used: {bal.used})")
    except Exception as e:
        print(f"❌ Failed to fetch balance: {e}")
    
    # Test 3: Fetch Positions
    print("\n4. Testing fetchPositions()...")
    try:
        positions = await exchange_manager.fetch_positions('bitunix')
        print(f"✓ Fetched {len(positions)} positions")
        for pos in positions:
            print(f"   {pos.symbol}: {pos.side} {pos.size} @ {pos.entry_price}")
    except Exception as e:
        print(f"❌ Failed to fetch positions: {e}")
    
    # Test 4: Fetch Open Orders
    print("\n5. Testing fetchOrders()...")
    try:
        orders = await exchange_manager.fetch_orders('bitunix')
        print(f"✓ Fetched {len(orders)} open orders")
        for order in orders[:3]:
            print(f"   {order.symbol}: {order.side} {order.amount} @ {order.price}")
    except Exception as e:
        print(f"❌ Failed to fetch orders: {e}")
    
    # Test 5: Fetch Symbol Info
    print("\n6. Testing fetchSymbolInfo('BTCUSDT')...")
    try:
        info = await exchange_manager.fetch_symbol_info('bitunix', 'BTCUSDT')
        print(f"✓ Fetched symbol info:")
        print(f"   Symbol: {info.symbol}")
        print(f"   Type: {info.type}")
        print(f"   Tick Size: {info.tick_size}")
        print(f"   Lot Size: {info.lot_size}")
        print(f"   Max Leverage: {info.max_leverage}")
    except Exception as e:
        print(f"❌ Failed to fetch symbol info: {e}")
    
    print("\n" + "=" * 50)
    print("✓ Bitunix API integration test complete!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_bitunix_api())
    sys.exit(0 if success else 1)