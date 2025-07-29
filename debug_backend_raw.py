#!/usr/bin/env python3
"""Debug script to check raw order data through backend"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import backend modules
from backend.services.exchange_manager import exchange_manager
from backend.models.trading import OrderResponse
import asyncio

async def get_raw_orders():
    """Get raw order data through backend"""
    
    # Get the LMEX exchange instance
    try:
        ex = exchange_manager.get_exchange('lmex')
    except Exception as e:
        print(f"Error getting exchange: {e}")
        return None
    
    # Fetch orders using the raw method
    print("Fetching orders from LMEX...")
    
    # Create a completion callback to capture raw data
    raw_orders_data = None
    
    def completion_callback(result):
        nonlocal raw_orders_data
        status, data = result
        if status == "success":
            raw_orders_data = data
        else:
            print(f"Error: {data}")
    
    # Call fetchOrders which should give us ExchangeOrder objects
    ex.fetchOrders(completion_callback)
    
    # Wait a bit for async operation
    await asyncio.sleep(2)
    
    return raw_orders_data

async def main():
    print("Fetching orders through backend...")
    print("=" * 80)
    
    # Get raw ExchangeOrder objects
    orders = await get_raw_orders()
    
    if not orders:
        print("No orders fetched")
        return
    
    print(f"\nFound {len(orders)} orders")
    
    # Separate AVAX and ENA orders
    avax_orders = []
    ena_orders = []
    
    for order in orders:
        if hasattr(order, '__dict__'):
            # It's an object, convert to dict for inspection
            order_dict = order.__dict__
        else:
            order_dict = order
            
        symbol = order_dict.get('symbol', '') if isinstance(order_dict, dict) else getattr(order, 'symbol', '')
        
        if 'AVAX' in str(symbol):
            avax_orders.append(order)
        elif 'ENA' in str(symbol):
            ena_orders.append(order)
    
    print(f"Found {len(avax_orders)} AVAX orders")
    print(f"Found {len(ena_orders)} ENA orders")
    
    # Display AVAX orders
    if avax_orders:
        print("\n" + "=" * 80)
        print("AVAX-PERP Orders (Should be TP/SL):")
        print("-" * 80)
        for i, order in enumerate(avax_orders):
            print(f"\nAVAX Order {i+1}:")
            if hasattr(order, '__dict__'):
                print("Object attributes:")
                for attr, value in order.__dict__.items():
                    print(f"  {attr}: {value}")
            else:
                print(json.dumps(order, indent=2))
    
    # Display ENA orders
    if ena_orders:
        print("\n" + "=" * 80)
        print("ENA-PERP Orders (Regular limit orders):")
        print("-" * 80)
        for i, order in enumerate(ena_orders):
            print(f"\nENA Order {i+1}:")
            if hasattr(order, '__dict__'):
                print("Object attributes:")
                for attr, value in order.__dict__.items():
                    print(f"  {attr}: {value}")
            else:
                print(json.dumps(order, indent=2))
    
    # Now let's also check what the API endpoint returns directly
    print("\n" + "=" * 80)
    print("Checking OrderResponse transformation:")
    print("-" * 80)
    
    # Get transformed OrderResponse objects
    try:
        order_responses = await exchange_manager.fetch_orders('lmex')
        
        avax_responses = [o for o in order_responses if 'AVAX' in o.symbol]
        ena_responses = [o for o in order_responses if 'ENA' in o.symbol]
        
        if avax_responses:
            print("\nAVAX OrderResponse:")
            for resp in avax_responses:
                print(json.dumps(resp.dict(), indent=2, default=str))
        
        if ena_responses:
            print("\nENA OrderResponse:")
            for resp in ena_responses:
                print(json.dumps(resp.dict(), indent=2, default=str))
    except Exception as e:
        print(f"Error getting OrderResponses: {e}")

if __name__ == "__main__":
    asyncio.run(main())