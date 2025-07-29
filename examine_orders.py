#!/usr/bin/env python3
"""Script to examine open orders and identify differences between regular and TP/SL orders"""

import asyncio
import sys
import os
import json
from pprint import pprint
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.bitunix import BitunixExchange

async def examine_orders():
    """Pull open orders and examine AVAX vs ENA orders"""
    
    # Initialize exchange
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("Please set BITUNIX_API_KEY and BITUNIX_API_SECRET environment variables")
        return
    
    exchange = BitunixExchange(api_key, api_secret)
    
    print("Fetching all open orders...")
    print("=" * 80)
    
    try:
        # Fetch all open orders
        orders = await exchange.fetch_open_orders()
        
        # Separate AVAX and ENA orders
        avax_orders = []
        ena_orders = []
        
        for order in orders:
            if 'AVAX' in order.get('symbol', ''):
                avax_orders.append(order)
            elif 'ENA' in order.get('symbol', ''):
                ena_orders.append(order)
        
        print(f"\nFound {len(avax_orders)} AVAX orders")
        print(f"Found {len(ena_orders)} ENA orders")
        print("\n" + "=" * 80)
        
        # Display AVAX orders (TP/SL)
        print("\nAVAX-PERP Orders (TP/SL at 27.58/23.94):")
        print("-" * 80)
        for i, order in enumerate(avax_orders):
            print(f"\nAVAX Order {i+1}:")
            print(json.dumps(order, indent=2))
            
        # Display ENA orders (Regular limit orders)
        print("\n" + "=" * 80)
        print("\nENA-PERP Orders (Regular limit orders):")
        print("-" * 80)
        for i, order in enumerate(ena_orders):
            print(f"\nENA Order {i+1}:")
            print(json.dumps(order, indent=2))
        
        # Compare fields
        print("\n" + "=" * 80)
        print("\nFIELD COMPARISON:")
        print("-" * 80)
        
        if avax_orders and ena_orders:
            avax_fields = set()
            ena_fields = set()
            
            for order in avax_orders:
                avax_fields.update(order.keys())
            for order in ena_orders:
                ena_fields.update(order.keys())
            
            print("\nFields only in AVAX orders:")
            unique_avax = avax_fields - ena_fields
            if unique_avax:
                for field in sorted(unique_avax):
                    values = [order.get(field) for order in avax_orders if field in order]
                    print(f"  - {field}: {values}")
            else:
                print("  (none)")
            
            print("\nFields only in ENA orders:")
            unique_ena = ena_fields - avax_fields
            if unique_ena:
                for field in sorted(unique_ena):
                    values = [order.get(field) for order in ena_orders if field in order]
                    print(f"  - {field}: {values}")
            else:
                print("  (none)")
            
            print("\nCommon fields with different values:")
            common_fields = avax_fields & ena_fields
            for field in sorted(common_fields):
                avax_values = [order.get(field) for order in avax_orders]
                ena_values = [order.get(field) for order in ena_orders]
                
                # Check if values are consistently different
                if len(set(avax_values)) == 1 and len(set(ena_values)) == 1:
                    if avax_values[0] != ena_values[0]:
                        print(f"  - {field}:")
                        print(f"      AVAX: {avax_values[0]}")
                        print(f"      ENA:  {ena_values[0]}")
        
        # Also try raw API call to see if ccxt is transforming data
        print("\n" + "=" * 80)
        print("\nRAW API RESPONSE:")
        print("-" * 80)
        
        try:
            raw_response = await exchange.private_get_api_v1_order_open_orders()
            if raw_response and 'data' in raw_response:
                raw_orders = raw_response['data']
                
                raw_avax = [o for o in raw_orders if 'AVAX' in o.get('symbol', '')]
                raw_ena = [o for o in raw_orders if 'ENA' in o.get('symbol', '')]
                
                if raw_avax:
                    print("\nRaw AVAX order:")
                    print(json.dumps(raw_avax[0], indent=2))
                
                if raw_ena:
                    print("\nRaw ENA order:")
                    print(json.dumps(raw_ena[0], indent=2))
        except Exception as e:
            print(f"Could not fetch raw response: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(examine_orders())