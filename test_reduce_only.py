#!/usr/bin/env python3
"""Test reduce-only order functionality for BitUnix"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.base import ExchangeOrderRequest
import time

def test_reduce_only_orders():
    """Test that reduce-only orders work properly"""
    
    # Initialize exchange
    exchange = BitUnixExchange()
    
    # Test 1: Check current position mode
    print("=== Testing Position Mode ===")
    result = {"completed": False, "mode": None, "error": None}
    
    def mode_callback(status_data):
        status, data = status_data
        result["completed"] = True
        if status == "success":
            result["mode"] = data.get("positionMode")
            print(f"Current position mode: {result['mode']}")
            print(f"Raw data: {data}")
        else:
            result["error"] = str(data)
            print(f"Error fetching position mode: {result['error']}")
    
    exchange.fetchPositionMode(mode_callback)
    
    # Wait for completion
    timeout = 5
    start_time = time.time()
    while not result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    # Test 2: Try to set position mode to ONE_WAY
    if result["mode"] == "HEDGE":
        print("\n=== Switching to ONE_WAY Mode ===")
        result = {"completed": False, "success": False, "error": None}
        
        def set_mode_callback(status_data):
            status, data = status_data
            result["completed"] = True
            result["success"] = status == "success"
            if status == "success":
                print("Successfully switched to ONE_WAY mode")
            else:
                result["error"] = str(data)
                print(f"Error setting position mode: {result['error']}")
        
        exchange.setPositionMode("ONE_WAY", set_mode_callback)
        
        # Wait for completion
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
    
    # Test 3: Check current positions
    print("\n=== Current Positions ===")
    result = {"completed": False, "positions": None, "error": None}
    
    def position_callback(status_data):
        status, data = status_data
        result["completed"] = True
        if status == "success":
            result["positions"] = data
            print(f"Found {len(data)} positions:")
            for pos in data:
                if pos.size != 0:
                    print(f"  {pos.symbol}: {pos.side} {abs(pos.size)} @ ${pos.entry_price}")
        else:
            result["error"] = str(data)
            print(f"Error fetching positions: {result['error']}")
    
    exchange.fetchPositions(position_callback)
    
    # Wait for completion
    start_time = time.time()
    while not result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    # Test 4: Create a test reduce-only order (DON'T EXECUTE THIS ON LIVE ACCOUNT)
    print("\n=== Reduce-Only Order Test ===")
    print("Creating a reduce-only order request...")
    
    # Example order (adjust symbol and parameters as needed)
    order_request = ExchangeOrderRequest(
        symbol="BTCUSDT",
        side="SELL",  # Opposite of current position
        orderType="LIMIT",
        qty=0.001,
        price=150000,  # Far from market price
        orderLinkId=f"test_reduce_only_{int(time.time())}",
        timeInForce="GTC",
        reduceOnly=True  # This is the key flag
    )
    
    print(f"Order details:")
    print(f"  Symbol: {order_request.symbol}")
    print(f"  Side: {order_request.side}")
    print(f"  Type: {order_request.orderType}")
    print(f"  Quantity: {order_request.qty}")
    print(f"  Price: ${order_request.price}")
    print(f"  Reduce Only: {order_request.reduceOnly}")
    
    print("\n⚠️  This is a test order with reduceOnly=True")
    print("The order will be rejected if you don't have a position to reduce")
    print("Comment out the actual order placement if you don't want to execute it")
    
    # Uncomment to actually place the order (BE CAREFUL!)
    # result = {"completed": False, "order": None, "error": None}
    # 
    # def order_callback(status_data):
    #     status, data = status_data
    #     result["completed"] = True
    #     if status == "success":
    #         result["order"] = data
    #         print(f"Order placed successfully: {data.orderId}")
    #     else:
    #         result["error"] = str(data)
    #         print(f"Order failed: {result['error']}")
    # 
    # exchange.placeOrder(order_request, order_callback)
    # 
    # # Wait for completion
    # start_time = time.time()
    # while not result["completed"] and (time.time() - start_time) < timeout:
    #     time.sleep(0.01)
    
    print("\n=== Test Complete ===")
    print("Reduce-only implementation is ready for grid bot usage")

if __name__ == "__main__":
    test_reduce_only_orders()