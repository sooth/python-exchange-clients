#!/usr/bin/env python3
"""Fix XRP position - close excess and set correct leverage"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.base import ExchangeOrderRequest
import time

def fix_xrp_position():
    """Fix the XRP position issues"""
    
    exchange = BitUnixExchange()
    
    print("=== Checking Current Position ===")
    position_info = {"completed": False, "position": None}
    
    def pos_callback(status_data):
        status, data = status_data
        position_info["completed"] = True
        if status == "success":
            for pos in data:
                if pos.symbol == "XRPUSDT":
                    position_info["position"] = pos
                    print(f"Current position: {pos.side} {pos.size}")
                    print(f"Current leverage: {pos.raw_response.get('leverage', 'Unknown')}")
                    break
    
    exchange.fetchPositions(pos_callback)
    
    # Wait for completion
    timeout = 5
    start_time = time.time()
    while not position_info["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if not position_info["position"]:
        print("No XRP position found")
        return
    
    current_size = position_info["position"].size
    target_size = 76.8  # What we actually wanted
    excess_size = current_size - target_size
    
    print(f"\nCurrent size: {current_size}")
    print(f"Target size: {target_size}")
    print(f"Excess to close: {excess_size}")
    
    # First, set correct leverage
    print("\n=== Setting Leverage to 20x ===")
    leverage_result = {"completed": False, "success": False}
    
    def leverage_callback(status_data):
        status, data = status_data
        leverage_result["completed"] = True
        leverage_result["success"] = status == "success"
        if status == "success":
            print("✅ Leverage set to 20x")
        else:
            print(f"❌ Failed to set leverage: {data}")
    
    exchange.setLeverage(
        symbol="XRPUSDT",
        marginCoin="USDT",
        leverage=20,
        completion=leverage_callback
    )
    
    # Wait for completion
    start_time = time.time()
    while not leverage_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    # Close excess position
    if excess_size > 0:
        print(f"\n=== Closing Excess Position ({excess_size} XRP) ===")
        
        # Use market order to close excess
        close_request = ExchangeOrderRequest(
            symbol="XRPUSDT",
            side="SELL",  # Opposite of BUY position
            orderType="MARKET",
            qty=excess_size,
            orderLinkId=f"close_excess_{int(time.time())}",
            tradingType="PERP"
        )
        
        result = {"completed": False, "success": False, "error": None}
        
        def order_callback(status_data):
            status, data = status_data
            result["completed"] = True
            if status == "success":
                result["success"] = True
                print(f"✅ Successfully closed {excess_size} XRP")
            else:
                result["error"] = str(data)
                print(f"❌ Failed to close position: {data}")
        
        exchange.placeOrder(close_request, order_callback)
        
        # Wait for completion
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
    
    # Cancel all existing orders
    print("\n=== Canceling All Existing Orders ===")
    orders_result = {"completed": False, "orders": []}
    
    def orders_callback(status_data):
        status, data = status_data
        orders_result["completed"] = True
        if status == "success":
            orders_result["orders"] = data
    
    exchange.fetchOrders(symbol="XRPUSDT", completion=orders_callback)
    
    # Wait for completion
    start_time = time.time()
    while not orders_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if orders_result["orders"]:
        print(f"Found {len(orders_result['orders'])} orders to cancel")
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
                symbol="XRPUSDT",
                completion=cancel_callback
            )
            
            # Wait for completion
            start_time = time.time()
            while not cancel_result["completed"] and (time.time() - start_time) < timeout:
                time.sleep(0.01)
            
            time.sleep(0.1)  # Rate limiting
    
    print("\n=== Done! ===")
    print("You can now restart the grid bot with the correct configuration.")

if __name__ == "__main__":
    fix_xrp_position()