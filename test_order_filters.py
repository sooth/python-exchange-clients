#!/usr/bin/env python3
"""Test script to verify order filter functionality"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.base import BaseExchange
from exchanges.bitunix import BitunixExchange
import uuid

async def test_order_filters():
    """Create various order types to test the filters"""
    
    # Initialize exchange
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("Please set BITUNIX_API_KEY and BITUNIX_API_SECRET environment variables")
        return
    
    exchange = BitunixExchange(api_key, api_secret)
    
    # Test symbol
    symbol = 'BTC/USDT'
    
    print("Testing order filters by creating different order types...")
    print("=" * 50)
    
    try:
        # Get current price
        ticker = await exchange.fetch_ticker(symbol)
        current_price = float(ticker['bid'])
        
        print(f"Current {symbol} price: {current_price}")
        print()
        
        # Create regular limit order (far from market)
        limit_price = current_price * 0.9  # 10% below market
        print(f"Creating regular limit order at {limit_price:.2f}...")
        try:
            limit_order = await exchange.create_order(
                symbol=symbol,
                type='limit',
                side='buy',
                amount=0.001,
                price=limit_price
            )
            print(f"✓ Limit order created: {limit_order['id']}")
        except Exception as e:
            print(f"✗ Failed to create limit order: {e}")
        
        # Create stop-loss order
        stop_price = current_price * 0.95  # 5% below market
        print(f"\nCreating stop-loss order at {stop_price:.2f}...")
        try:
            stop_order = await exchange.create_order(
                symbol=symbol,
                type='stop',
                side='sell',
                amount=0.001,
                price=stop_price,
                params={'stopPrice': stop_price}
            )
            print(f"✓ Stop-loss order created: {stop_order['id']}")
        except Exception as e:
            print(f"✗ Failed to create stop-loss order: {e}")
        
        # Create take-profit order
        tp_price = current_price * 1.05  # 5% above market
        print(f"\nCreating take-profit order at {tp_price:.2f}...")
        try:
            tp_order = await exchange.create_order(
                symbol=symbol,
                type='take_profit',
                side='sell',
                amount=0.001,
                price=tp_price,
                params={'stopPrice': tp_price}
            )
            print(f"✓ Take-profit order created: {tp_order['id']}")
        except Exception as e:
            print(f"✗ Failed to create take-profit order: {e}")
        
        print("\n" + "=" * 50)
        print("Order creation complete!")
        print("\nTo test the filters:")
        print("1. Open the trading interface")
        print("2. Check the 'Orders' checkbox - should show only limit/market orders")
        print("3. Check the 'TP/SL' checkbox - should show only stop/take-profit orders")
        print("4. Uncheck both - should show 'No open orders'")
        print("5. Refresh the page - filter preferences should persist")
        
        # Fetch and display all orders
        print("\n" + "=" * 50)
        print("Current open orders:")
        orders = await exchange.fetch_open_orders(symbol)
        
        regular_orders = []
        tpsl_orders = []
        
        for order in orders:
            order_type = order['type']
            if order_type in ['limit', 'market']:
                regular_orders.append(order)
            elif order_type in ['stop', 'stop_limit', 'take_profit', 'take_profit_limit']:
                tpsl_orders.append(order)
        
        print(f"\nRegular orders ({len(regular_orders)}):")
        for order in regular_orders:
            print(f"  - {order['type']} {order['side']} {order['amount']} @ {order['price']}")
        
        print(f"\nTP/SL orders ({len(tpsl_orders)}):")
        for order in tpsl_orders:
            print(f"  - {order['type']} {order['side']} {order['amount']} @ {order['price']}")
        
        print("\n" + "=" * 50)
        input("Press Enter to cancel all test orders...")
        
        # Cancel all orders
        print("\nCancelling all test orders...")
        for order in orders:
            try:
                await exchange.cancel_order(order['id'], symbol)
                print(f"✓ Cancelled order {order['id']}")
            except Exception as e:
                print(f"✗ Failed to cancel order {order['id']}: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_order_filters())