#!/usr/bin/env python3
"""Check BitUnix position mode and status"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
import time

def check_status():
    """Check current status"""
    
    exchange = BitUnixExchange()
    
    print("=== BitUnix Account Status ===")
    
    # Check positions
    print("\n📊 Open Positions:")
    positions_result = {"completed": False, "positions": []}
    
    def pos_callback(status_data):
        status, data = status_data
        positions_result["completed"] = True
        if status == "success":
            positions_result["positions"] = data
    
    exchange.fetchPositions(pos_callback)
    
    timeout = 5
    start_time = time.time()
    while not positions_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    open_positions = [p for p in positions_result["positions"] if p.size != 0]
    
    if open_positions:
        for pos in open_positions:
            side = "LONG" if pos.size > 0 else "SHORT"
            mode = pos.raw_response.get('positionMode', 'Unknown') if pos.raw_response else 'Unknown'
            print(f"   {pos.symbol}: {side} {abs(pos.size)} @ ${pos.entryPrice} (Mode: {mode})")
    else:
        print("   No open positions")
    
    # Check orders
    print("\n📋 Open Orders:")
    orders_result = {"completed": False, "orders": []}
    
    def orders_callback(status_data):
        status, data = status_data
        orders_result["completed"] = True
        if status == "success":
            orders_result["orders"] = data
    
    exchange.fetchOrders(completion=orders_callback)
    
    start_time = time.time()
    while not orders_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if orders_result["orders"]:
        for order in orders_result["orders"][:5]:  # Show first 5
            print(f"   {order.symbol}: {order.side} {order.qty} @ ${order.price}")
        if len(orders_result["orders"]) > 5:
            print(f"   ... and {len(orders_result['orders']) - 5} more orders")
    else:
        print("   No open orders")
    
    # Check position mode
    print("\n⚙️  Position Mode:")
    mode_result = {"completed": False, "mode": None}
    
    def mode_callback(status_data):
        status, data = status_data
        mode_result["completed"] = True
        if status == "success":
            mode_result["mode"] = data.get("positionMode")
            mode_result["source"] = data.get("source", "unknown")
    
    exchange.fetchPositionMode(mode_callback)
    
    start_time = time.time()
    while not mode_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if mode_result["mode"]:
        print(f"   Current mode: {mode_result['mode']} (source: {mode_result['source']})")
        if mode_result["mode"] == "HEDGE":
            print("   ⚠️  WARNING: Grid bot requires ONE_WAY mode!")
    else:
        print("   Could not determine position mode")
    
    # Summary
    print("\n📌 Summary:")
    if open_positions or orders_result["orders"]:
        print("   ❌ Cannot switch to ONE_WAY mode - positions/orders exist")
        print("   Action needed: Close all positions and cancel all orders")
    elif mode_result["mode"] == "HEDGE":
        print("   ⚠️  Ready to switch to ONE_WAY mode")
        print("   Run: python setup_position_mode.py")
    else:
        print("   ✅ Ready for grid trading!")

if __name__ == "__main__":
    check_status()