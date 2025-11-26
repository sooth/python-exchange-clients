#!/usr/bin/env python3
"""Debug script to check order types and fields"""

import asyncio
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.bitunix import BitunixExchange

async def debug_order_types():
    """Check what order types and fields are returned"""
    
    # Initialize exchange
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("Please set BITUNIX_API_KEY and BITUNIX_API_SECRET environment variables")
        return
    
    exchange = BitunixExchange(api_key, api_secret)
    
    print("Fetching all open orders to debug order types...")
    print("=" * 50)
    
    try:
        # Fetch all open orders
        orders = await exchange.fetch_open_orders()
        
        print(f"Found {len(orders)} open orders\n")
        
        for i, order in enumerate(orders):
            print(f"Order {i+1}:")
            print(f"  Symbol: {order.get('symbol')}")
            print(f"  Side: {order.get('side')}")
            print(f"  Type: {order.get('type')}")
            print(f"  Status: {order.get('status')}")
            print(f"  Price: {order.get('price')}")
            print(f"  Amount: {order.get('amount')}")
            
            # Check for additional fields that might indicate TP/SL
            print(f"  Stop Price: {order.get('stopPrice', 'N/A')}")
            print(f"  Trigger Price: {order.get('triggerPrice', 'N/A')}")
            print(f"  Order Type (raw): {order.get('orderType', 'N/A')}")
            print(f"  Is Stop: {order.get('isStop', 'N/A')}")
            print(f"  Is TP/SL: {order.get('isTpSl', 'N/A')}")
            print(f"  Reduce Only: {order.get('reduceOnly', 'N/A')}")
            
            # Print all fields for debugging
            print(f"\n  All fields:")
            for key, value in order.items():
                if key not in ['symbol', 'side', 'type', 'status', 'price', 'amount']:
                    print(f"    {key}: {value}")
            
            print("\n" + "-" * 40 + "\n")
        
        # Also check the raw response if available
        print("Fetching raw order data...")
        raw_orders = await exchange.private_get_api_v1_order_open_orders()
        
        if raw_orders and 'data' in raw_orders:
            print("\nRaw order data structure:")
            if raw_orders['data']:
                print(json.dumps(raw_orders['data'][0], indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(debug_order_types())