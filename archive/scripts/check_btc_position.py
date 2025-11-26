#!/usr/bin/env python3
"""Check current BTC position"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange

exchange = BitUnixExchange()

# Get positions
position_result = {"data": None, "completed": False}

def position_callback(status_data):
    status, data = status_data
    position_result["completed"] = True
    if status == "success":
        position_result["data"] = data

print("Fetching positions...")
exchange.fetchPositions(position_callback)

# Wait for result
timeout = 5
start_time = time.time()
while not position_result["completed"] and (time.time() - start_time) < timeout:
    time.sleep(0.01)

if position_result["data"]:
    print(f"\nTotal positions: {len(position_result['data'])}")
    
    btc_position = None
    for pos in position_result["data"]:
        print(f"\n{pos.symbol}:")
        print(f"  Side: {getattr(pos, 'side', 'N/A')}")
        print(f"  Size: {pos.size}")
        print(f"  Entry: ${pos.entryPrice}")
        
        if pos.symbol == "BTCUSDT":
            btc_position = pos
    
    if btc_position:
        print(f"\n🎯 BTC Position Found:")
        print(f"  Direction: {'LONG' if btc_position.side == 'BUY' else 'SHORT'}")
        print(f"  Size: {btc_position.size} BTC")
        print(f"  Value: ${btc_position.size * btc_position.entryPrice:,.2f}")
    else:
        print("\n❌ No BTC position found!")
        
    # Get orders too
    order_result = {"data": None, "completed": False}
    
    def order_callback(status_data):
        status, data = status_data
        order_result["completed"] = True
        if status == "success":
            order_result["data"] = data
    
    print("\n\nFetching orders...")
    exchange.fetchOrders(order_callback)
    
    # Wait for result
    start_time = time.time()
    while not order_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
        
    if order_result["data"]:
        btc_orders = [o for o in order_result["data"] if o.symbol == "BTCUSDT"]
        grid_orders = [o for o in btc_orders if o.clientId and 'grid_' in o.clientId]
        
        buy_orders = [o for o in grid_orders if o.side == "BUY"]
        sell_orders = [o for o in grid_orders if o.side == "SELL"]
        
        print(f"\nGrid Orders:")
        print(f"  Total: {len(grid_orders)}")
        print(f"  BUY orders: {len(buy_orders)} (total qty: {sum(o.qty for o in buy_orders):.4f})")
        print(f"  SELL orders: {len(sell_orders)} (total qty: {sum(o.qty for o in sell_orders):.4f})")
        
        if btc_position and getattr(btc_position, 'side', None) == "BUY":
            # LONG position
            position_size = btc_position.size
            sell_total = sum(o.quantity for o in sell_orders)
            buy_total = sum(o.quantity for o in buy_orders)
            
            print(f"\n📊 Position Analysis (LONG):")
            print(f"  Current position: {position_size:.4f} BTC")
            print(f"  SELL orders total: {sell_total:.4f} BTC")
            print(f"  BUY orders total: {buy_total:.4f} BTC")
            print(f"  Net after all fills: {position_size + buy_total - sell_total:.4f} BTC")
            
            if abs(position_size + buy_total - sell_total) < 0.0001:
                print("  ✅ Position is balanced!")
            else:
                print(f"  ⚠️ Position is NOT balanced!")
                print(f"  Need initial position of: {sell_total - buy_total:.4f} BTC")