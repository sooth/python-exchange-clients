#!/usr/bin/env python3
"""Setup BitUnix for grid bot - close positions and set ONE_WAY mode"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.base import ExchangeOrderRequest
import time

def setup_position_mode():
    """Close all positions and set ONE_WAY mode"""
    
    exchange = BitUnixExchange()
    
    print("=== BitUnix Grid Bot Setup ===")
    print("This script will help prepare your account for grid trading.")
    
    # Step 1: Check current positions
    print("\n1. Checking for open positions...")
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
        print(f"\n⚠️  Found {len(open_positions)} open positions:")
        for pos in open_positions:
            side = "LONG" if pos.size > 0 else "SHORT"
            print(f"   - {pos.symbol}: {side} {abs(pos.size)} @ ${pos.entryPrice}")
        
        print("\n⚠️  WARNING: You have open positions!")
        print("Position mode cannot be changed while positions are open.")
        response = input("\nDo you want to close all positions? (yes/no): ").lower()
        
        if response != 'yes':
            print("Exiting without changes.")
            return
        
        # Close each position
        for pos in open_positions:
            print(f"\nClosing {pos.symbol} position...")
            close_side = "SELL" if pos.size > 0 else "BUY"
            
            order = ExchangeOrderRequest(
                symbol=pos.symbol,
                side=close_side,
                orderType="MARKET",
                qty=abs(pos.size),
                orderLinkId=f"close_{pos.symbol}_{int(time.time())}",
                tradingType="PERP"
            )
            
            result = {"completed": False, "success": False}
            
            def order_callback(status_data):
                status, data = status_data
                result["completed"] = True
                result["success"] = status == "success"
                if status == "success":
                    print(f"✅ Closed {pos.symbol} position")
                else:
                    print(f"❌ Failed to close {pos.symbol}: {data}")
            
            exchange.placeOrder(order, order_callback)
            
            start_time = time.time()
            while not result["completed"] and (time.time() - start_time) < timeout:
                time.sleep(0.01)
            
            time.sleep(0.5)  # Rate limit
    else:
        print("✅ No open positions found")
    
    # Step 2: Check for open orders
    print("\n2. Checking for open orders...")
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
        print(f"\n⚠️  Found {len(orders_result['orders'])} open orders")
        response = input("Do you want to cancel all orders? (yes/no): ").lower()
        
        if response == 'yes':
            for order in orders_result["orders"]:
                cancel_result = {"completed": False}
                
                def cancel_callback(status_data):
                    status, data = status_data
                    cancel_result["completed"] = True
                    if status == "success":
                        print(f"✅ Cancelled order {order.orderId}")
                    else:
                        print(f"❌ Failed to cancel {order.orderId}: {data}")
                
                exchange.cancelOrder(
                    orderID=order.orderId,
                    symbol=order.symbol,
                    completion=cancel_callback
                )
                
                start_time = time.time()
                while not cancel_result["completed"] and (time.time() - start_time) < timeout:
                    time.sleep(0.01)
                
                time.sleep(0.1)  # Rate limit
    else:
        print("✅ No open orders found")
    
    # Step 3: Check current position mode
    print("\n3. Checking position mode...")
    mode_result = {"completed": False, "mode": None}
    
    def mode_callback(status_data):
        status, data = status_data
        mode_result["completed"] = True
        if status == "success":
            mode_result["mode"] = data.get("positionMode")
            print(f"Current position mode: {mode_result['mode']}")
    
    exchange.fetchPositionMode(mode_callback)
    
    start_time = time.time()
    while not mode_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if mode_result["mode"] == "ONE_WAY":
        print("✅ Already in ONE_WAY mode - perfect for grid trading!")
        return
    
    # Step 4: Switch to ONE_WAY mode
    print("\n4. Switching to ONE_WAY mode...")
    switch_result = {"completed": False, "success": False, "error": None}
    
    def switch_callback(status_data):
        status, data = status_data
        switch_result["completed"] = True
        switch_result["success"] = status == "success"
        if status == "success":
            print("✅ Successfully switched to ONE_WAY mode!")
        else:
            switch_result["error"] = str(data)
            print(f"❌ Failed to switch mode: {data}")
    
    exchange.setPositionMode("ONE_WAY", switch_callback)
    
    start_time = time.time()
    while not switch_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if switch_result["success"]:
        print("\n✅ Setup complete! Your account is ready for grid trading.")
        print("You can now start the grid bot.")
    else:
        print("\n❌ Setup failed!")
        print("Please ensure all positions and orders are closed and try again.")

if __name__ == "__main__":
    setup_position_mode()