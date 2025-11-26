#!/usr/bin/env python3
"""Test orders through backend API"""

import requests
import json
from pprint import pprint

# Backend API URL
API_URL = "http://localhost:8001/api/v1"

def fetch_orders():
    """Fetch all open orders"""
    try:
        response = requests.get(f"{API_URL}/trading/orders")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching orders: {e}")
        return []

def main():
    print("Fetching all open orders from backend API...")
    print("=" * 80)
    
    orders = fetch_orders()
    
    if not orders:
        print("No orders found or error occurred")
        return
    
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
        print(json.dumps(order, indent=2, default=str))
        
    # Display ENA orders (Regular limit orders)
    print("\n" + "=" * 80)
    print("\nENA-PERP Orders (Regular limit orders):")
    print("-" * 80)
    for i, order in enumerate(ena_orders):
        print(f"\nENA Order {i+1}:")
        print(json.dumps(order, indent=2, default=str))
    
    # Compare fields
    print("\n" + "=" * 80)
    print("\nFIELD COMPARISON:")
    print("-" * 80)
    
    if avax_orders and ena_orders:
        # Get all unique fields
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
        
        print("\nCommon fields with potentially different values:")
        common_fields = avax_fields & ena_fields
        differences = []
        
        for field in sorted(common_fields):
            # Get unique values for each
            avax_values = list(set(str(order.get(field)) for order in avax_orders))
            ena_values = list(set(str(order.get(field)) for order in ena_orders))
            
            # Skip if values are obviously different (like symbol, id, etc)
            if field not in ['symbol', 'id', 'client_order_id', 'timestamp', 'price', 'amount']:
                if avax_values != ena_values:
                    differences.append({
                        'field': field,
                        'avax': avax_values,
                        'ena': ena_values
                    })
        
        for diff in differences:
            print(f"\n  {diff['field']}:")
            print(f"    AVAX: {diff['avax']}")
            print(f"    ENA:  {diff['ena']}")
    
    # Show all fields for reference
    print("\n" + "=" * 80)
    print("\nALL FIELDS REFERENCE:")
    if orders:
        all_fields = set()
        for order in orders:
            all_fields.update(order.keys())
        print("Available fields:", sorted(all_fields))

if __name__ == "__main__":
    main()