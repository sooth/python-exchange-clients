#!/usr/bin/env python3
"""Test Bitunix API Integration with real credentials"""

import asyncio
import logging
import os
import sys
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.exchange_manager import exchange_manager
from backend.core.config import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_bitunix_connectivity():
    """Test basic connectivity and API key validation"""
    print("\n=== Testing Bitunix API Integration ===\n")
    
    # Check environment variables
    print("1. Checking environment variables...")
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_SECRET_KEY')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY or BITUNIX_SECRET_KEY not found in environment")
        return False
    else:
        print(f"✅ API Key: {api_key[:10]}...")
        print(f"✅ API Secret: {api_secret[:10]}...")
    
    # Initialize exchange manager
    print("\n2. Initializing exchange manager...")
    try:
        await exchange_manager.initialize()
        print("✅ Exchange manager initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False
    
    # Get connected exchanges
    exchanges = await exchange_manager.get_connected_exchanges()
    print(f"\n3. Connected exchanges: {exchanges}")
    
    if 'bitunix' not in exchanges:
        print("❌ Bitunix not connected")
        return False
    
    print("✅ Bitunix connected\n")
    return True


async def test_fetch_tickers():
    """Test fetching all tickers"""
    print("\n4. Testing fetchTickers()...")
    try:
        tickers = await exchange_manager.fetch_all_tickers('bitunix')
        print(f"✅ Fetched {len(tickers)} tickers")
        
        # Show first 5 tickers
        print("\nSample tickers:")
        for ticker in tickers[:5]:
            print(f"  {ticker.symbol}: ${ticker.last}")
    except Exception as e:
        print(f"❌ Failed to fetch tickers: {e}")
        logger.error(f"Ticker error details: {e}", exc_info=True)


async def test_fetch_balance():
    """Test fetching account balance"""
    print("\n5. Testing fetchBalance()...")
    try:
        account_info = await exchange_manager.fetch_balance('bitunix')
        print(f"✅ Fetched account balance")
        print(f"   Total USD Value: ${account_info.total_value_usd}")
        
        print("\nBalances:")
        for currency, balance in account_info.balances.items():
            if balance.total > 0:
                print(f"  {currency}: {balance.total} (free: {balance.free}, used: {balance.used})")
    except Exception as e:
        print(f"❌ Failed to fetch balance: {e}")
        logger.error(f"Balance error details: {e}", exc_info=True)


async def test_fetch_positions():
    """Test fetching open positions"""
    print("\n6. Testing fetchPositions()...")
    try:
        positions = await exchange_manager.fetch_positions('bitunix')
        print(f"✅ Fetched {len(positions)} positions")
        
        if positions:
            print("\nOpen positions:")
            for pos in positions:
                print(f"  {pos.symbol}: {pos.side} {pos.size} @ ${pos.entry_price}")
                print(f"    PnL: ${pos.unrealized_pnl} ({pos.percentage}%)")
        else:
            print("  No open positions")
    except Exception as e:
        print(f"❌ Failed to fetch positions: {e}")
        logger.error(f"Position error details: {e}", exc_info=True)


async def test_fetch_orders():
    """Test fetching open orders"""
    print("\n7. Testing fetchOrders()...")
    try:
        orders = await exchange_manager.fetch_orders('bitunix')
        print(f"✅ Fetched {len(orders)} open orders")
        
        if orders:
            print("\nOpen orders:")
            for order in orders[:5]:  # Show first 5
                print(f"  {order.symbol}: {order.side} {order.amount} @ ${order.price}")
                print(f"    Status: {order.status}, Filled: {order.filled}")
        else:
            print("  No open orders")
    except Exception as e:
        print(f"❌ Failed to fetch orders: {e}")
        logger.error(f"Order error details: {e}", exc_info=True)


async def test_fetch_symbol_info():
    """Test fetching symbol information"""
    print("\n8. Testing fetchSymbolInfo()...")
    try:
        symbol_info = await exchange_manager.fetch_symbol_info('bitunix', 'BTCUSDT')
        print(f"✅ Fetched symbol info for BTCUSDT")
        print(f"   Type: {symbol_info.type}")
        print(f"   Tick Size: {symbol_info.tick_size}")
        print(f"   Lot Size: {symbol_info.lot_size}")
        print(f"   Min Notional: {symbol_info.min_notional}")
        print(f"   Max Leverage: {symbol_info.max_leverage}")
        print(f"   Maker Fee: {symbol_info.maker_fee}")
        print(f"   Taker Fee: {symbol_info.taker_fee}")
    except Exception as e:
        print(f"❌ Failed to fetch symbol info: {e}")
        logger.error(f"Symbol info error details: {e}", exc_info=True)


async def main():
    """Run all tests"""
    try:
        # Test connectivity first
        connected = await test_bitunix_connectivity()
        if not connected:
            print("\n⚠️ Cannot proceed without connection")
            return
        
        # Run all tests
        await test_fetch_tickers()
        await test_fetch_balance()
        await test_fetch_positions()
        await test_fetch_orders()
        await test_fetch_symbol_info()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.error(f"Test error details: {e}", exc_info=True)
    finally:
        # Cleanup
        await exchange_manager.cleanup()
        print("\n👋 Cleaned up connections")


if __name__ == "__main__":
    asyncio.run(main())