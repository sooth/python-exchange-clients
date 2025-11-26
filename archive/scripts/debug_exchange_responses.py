#!/usr/bin/env python3
"""Debug exchange responses through the exchange manager"""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

# Set environment variables for API keys
os.environ['LMEX_API_KEY'] = 'f15a019fe600ecb408b7b8818e883407e3942ab42401b92743c5d7256e4f4910'
os.environ['LMEX_SECRET_KEY'] = '868939aa28b3c295110ed7caeb29ccc57f0c06b9c79371f6fb390dbc183df638'

from backend.services.exchange_manager import exchange_manager

async def debug_responses():
    """Debug exchange responses"""
    await exchange_manager.initialize()
    
    exchange = exchange_manager.get_exchange('lmex')
    
    print("=== Testing fetchOrders ===")
    try:
        orders = await exchange.fetchOrders()
        print(f"Orders type: {type(orders)}")
        print(f"Number of orders: {len(orders)}")
        if orders:
            order = orders[0]
            print(f"\nFirst order type: {type(order)}")
            print(f"First order: {order}")
            if hasattr(order, '__dict__'):
                print(f"Order attributes: {order.__dict__}")
            print(f"\nTrying to access properties:")
            for attr in ['orderId', 'clientId', 'symbol', 'side', 'orderType', 'status', 'price', 'qty']:
                if hasattr(order, attr):
                    print(f"  order.{attr} = {getattr(order, attr)}")
                else:
                    print(f"  order.{attr} = NOT FOUND")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Testing fetchBalance ===")
    try:
        balance = await exchange.fetchBalance()
        print(f"Balance type: {type(balance)}")
        print(f"Number of balances: {len(balance)}")
        if balance:
            item = balance[0]
            print(f"\nFirst balance type: {type(item)}")
            print(f"First balance: {item}")
            if hasattr(item, '__dict__'):
                print(f"Balance attributes: {item.__dict__}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Testing fetchPositions ===")
    try:
        positions = await exchange.fetchPositions()
        print(f"Positions type: {type(positions)}")
        print(f"Number of positions: {len(positions)}")
        if positions:
            pos = positions[0]
            print(f"\nFirst position type: {type(pos)}")
            print(f"First position: {pos}")
            if hasattr(pos, '__dict__'):
                print(f"Position attributes: {pos.__dict__}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_responses())