#!/usr/bin/env python3
"""Debug script to check raw order data from BitUnix"""

import asyncio
import sys
import os
import json
import time
import hashlib
import requests
from urllib.parse import urlencode

# BitUnix API endpoints
BASE_URL = "https://fapi.bitunix.com"

def sign_request(params, secret_key):
    """Sign request parameters"""
    # Sort params and create query string
    query_string = urlencode(sorted(params.items()))
    
    # Create signature
    signature = hashlib.sha256((query_string + secret_key).encode()).hexdigest()
    
    return signature

def get_open_orders():
    """Get open orders with raw response"""
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("Please set BITUNIX_API_KEY and BITUNIX_API_SECRET environment variables")
        return None
    
    # Prepare request
    timestamp = int(time.time() * 1000)
    params = {
        'timestamp': timestamp,
        'recv_window': 5000
    }
    
    # Add signature
    signature = sign_request(params, api_secret)
    params['signature'] = signature
    
    # Make request
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    url = f"{BASE_URL}/api/v1/futures/trade/get_pending_orders"
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching orders: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None

def main():
    print("Fetching raw order data from BitUnix...")
    print("=" * 80)
    
    response = get_open_orders()
    
    if not response:
        print("Failed to fetch orders")
        return
    
    print("Raw API Response:")
    print(json.dumps(response, indent=2))
    
    # Analyze the data
    if response.get('code') == 0 and 'data' in response:
        orders = response['data']
        
        print(f"\n\nFound {len(orders)} orders")
        print("=" * 80)
        
        # Separate AVAX and ENA orders
        avax_orders = []
        ena_orders = []
        
        for order in orders:
            if 'AVAX' in order.get('s', ''):
                avax_orders.append(order)
            elif 'ENA' in order.get('s', ''):
                ena_orders.append(order)
        
        # Display AVAX orders
        if avax_orders:
            print("\nAVAX-PERP Raw Orders:")
            print("-" * 80)
            for i, order in enumerate(avax_orders):
                print(f"\nAVAX Order {i+1}:")
                print(json.dumps(order, indent=2))
                
                # List all fields
                print("\nFields in this order:")
                for key, value in order.items():
                    print(f"  {key}: {value} (type: {type(value).__name__})")
        
        # Display ENA orders
        if ena_orders:
            print("\n\nENA-PERP Raw Orders:")
            print("-" * 80)
            for i, order in enumerate(ena_orders):
                print(f"\nENA Order {i+1}:")
                print(json.dumps(order, indent=2))
                
                # List all fields
                print("\nFields in this order:")
                for key, value in order.items():
                    print(f"  {key}: {value} (type: {type(value).__name__})")
        
        # Compare fields
        if avax_orders and ena_orders:
            print("\n\n" + "=" * 80)
            print("FIELD COMPARISON:")
            print("-" * 80)
            
            avax_fields = set()
            ena_fields = set()
            
            for order in avax_orders:
                avax_fields.update(order.keys())
            for order in ena_orders:
                ena_fields.update(order.keys())
            
            print("\nFields only in AVAX orders:")
            unique_avax = avax_fields - ena_fields
            if unique_avax:
                print(f"  {sorted(unique_avax)}")
            else:
                print("  (none)")
            
            print("\nFields only in ENA orders:")
            unique_ena = ena_fields - avax_fields
            if unique_ena:
                print(f"  {sorted(unique_ena)}")
            else:
                print("  (none)")
            
            print("\nAll available fields:")
            all_fields = avax_fields | ena_fields
            print(f"  {sorted(all_fields)}")

if __name__ == "__main__":
    main()