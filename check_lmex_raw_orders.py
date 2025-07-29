#!/usr/bin/env python3
"""Check raw LMEX order data"""

import json
import time
import hmac
import hashlib
import requests
import os

def create_signature(secret, path, nonce, data=""):
    """Create HMAC SHA256 signature for LMEX"""
    message = path + str(nonce) + data
    return hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_lmex_orders():
    """Get raw order data from LMEX"""
    api_key = os.getenv('LMEX_API_KEY')
    api_secret = os.getenv('LMEX_SECRET_KEY')  # LMEX uses SECRET_KEY not API_SECRET
    
    if not api_key or not api_secret:
        print("Please set LMEX_API_KEY and LMEX_API_SECRET environment variables")
        return None
    
    base_url = "https://api.lmex.io/futures"
    path = "/api/v2.2/user/open_orders"
    
    # Create nonce
    nonce = int(time.time() * 1000)
    
    # Create signature
    signature = create_signature(api_secret, path, nonce)
    
    # Create headers
    headers = {
        "LMX-ACCESS-KEY": api_key,
        "LMX-ACCESS-SIGNATURE": signature,
        "LMX-ACCESS-NONCE": str(nonce),
        "Content-Type": "application/json"
    }
    
    url = base_url + path
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error Response: {response.text}")
            return None
    except Exception as e:
        print(f"Request Error: {e}")
        return None

def main():
    print("Fetching raw order data from LMEX...")
    print("=" * 80)
    
    data = get_lmex_orders()
    
    if not data:
        print("Failed to fetch orders")
        return
    
    print("\nRaw LMEX Response:")
    print(json.dumps(data, indent=2))
    
    # Analyze orders
    orders = data if isinstance(data, list) else data.get('orders', [])
    
    # Separate AVAX and ENA orders
    avax_orders = []
    ena_orders = []
    
    for order in orders:
        symbol = order.get('symbol', '')
        if 'AVAX' in symbol:
            avax_orders.append(order)
        elif 'ENA' in symbol:
            ena_orders.append(order)
    
    print(f"\n\nFound {len(avax_orders)} AVAX orders")
    print(f"Found {len(ena_orders)} ENA orders")
    
    # Display AVAX orders with all fields
    if avax_orders:
        print("\n" + "=" * 80)
        print("AVAX-PERP Orders (Should be TP/SL):")
        print("-" * 80)
        for i, order in enumerate(avax_orders):
            print(f"\nAVAX Order {i+1}:")
            print(json.dumps(order, indent=2))
            
            print("\nAll fields in this order:")
            for key, value in sorted(order.items()):
                print(f"  {key}: {value} (type: {type(value).__name__})")
    
    # Display ENA orders with all fields
    if ena_orders:
        print("\n" + "=" * 80)
        print("ENA-PERP Orders (Regular limit orders):")
        print("-" * 80)
        for i, order in enumerate(ena_orders):
            print(f"\nENA Order {i+1}:")
            print(json.dumps(order, indent=2))
            
            print("\nAll fields in this order:")
            for key, value in sorted(order.items()):
                print(f"  {key}: {value} (type: {type(value).__name__})")
    
    # Field comparison
    if avax_orders and ena_orders:
        print("\n" + "=" * 80)
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
        all_fields = sorted(avax_fields | ena_fields)
        for field in all_fields:
            print(f"  - {field}")

if __name__ == "__main__":
    main()