#!/usr/bin/env python3
"""Debug LMEX API responses to understand data structure"""

import asyncio
import sys
sys.path.append('.')

from exchanges.lmex import LMEXExchange

async def debug_lmex():
    """Debug LMEX responses"""
    # Initialize exchange
    exchange = LMEXExchange()
    
    # Set credentials
    exchange.apiKey = 'f15a019fe600ecb408b7b8818e883407e3942ab42401b92743c5d7256e4f4910'
    exchange.secret = '868939aa28b3c295110ed7caeb29ccc57f0c06b9c79371f6fb390dbc183df638'
    
    print("=== Testing LMEX fetchOrders ===")
    try:
        orders = exchange.fetchOrders()
        print(f"Orders type: {type(orders)}")
        print(f"Number of orders: {len(orders)}")
        if orders:
            print(f"\nFirst order type: {type(orders[0])}")
            print(f"First order attributes: {dir(orders[0])}")
            if hasattr(orders[0], '__dict__'):
                print(f"\nFirst order dict: {orders[0].__dict__}")
            if hasattr(orders[0], 'to_dict'):
                print(f"\nFirst order to_dict: {orders[0].to_dict()}")
    except Exception as e:
        print(f"Error fetching orders: {type(e).__name__}: {e}")
    
    print("\n=== Testing LMEX fetchBalance ===")
    try:
        balance = exchange.fetchBalance()
        print(f"Balance type: {type(balance)}")
        print(f"Number of balances: {len(balance)}")
        if balance:
            print(f"\nFirst balance type: {type(balance[0])}")
            print(f"First balance attributes: {dir(balance[0])}")
            if hasattr(balance[0], '__dict__'):
                print(f"\nFirst balance dict: {balance[0].__dict__}")
    except Exception as e:
        print(f"Error fetching balance: {type(e).__name__}: {e}")
    
    print("\n=== Testing LMEX fetchPositions ===")
    try:
        positions = exchange.fetchPositions()
        print(f"Positions type: {type(positions)}")
        print(f"Number of positions: {len(positions)}")
        if positions:
            print(f"\nFirst position type: {type(positions[0])}")
            print(f"First position attributes: {dir(positions[0])}")
            if hasattr(positions[0], '__dict__'):
                print(f"\nFirst position dict: {positions[0].__dict__}")
    except Exception as e:
        print(f"Error fetching positions: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(debug_lmex())