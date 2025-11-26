#!/usr/bin/env python3
"""Test different order parameter combinations for BitUnix"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.base import ExchangeOrderRequest
import time

def test_order_combinations():
    """Test different order parameter combinations"""
    
    exchange = BitUnixExchange()
    
    # Test combinations
    test_cases = [
        {
            "name": "Standard SELL (no reduce-only)",
            "order": ExchangeOrderRequest(
                symbol="XRPUSDT",
                side="SELL",
                orderType="LIMIT",
                qty=1.0,
                price=4.0000,  # Far from market
                orderLinkId=f"test_standard_{int(time.time())}",
                timeInForce="GTC",
                reduceOnly=False
            )
        },
        {
            "name": "Reduce-only with CLOSE",
            "order": ExchangeOrderRequest(
                symbol="XRPUSDT",
                side="SELL",
                orderType="LIMIT",
                qty=1.0,
                price=4.0000,
                orderLinkId=f"test_reduce_close_{int(time.time())}",
                timeInForce="GTC",
                reduceOnly=True
            )
        },
        {
            "name": "Standard SELL with positionIdx",
            "order": ExchangeOrderRequest(
                symbol="XRPUSDT",
                side="SELL",
                orderType="LIMIT",
                qty=1.0,
                price=4.0000,
                orderLinkId=f"test_posidx_{int(time.time())}",
                timeInForce="GTC",
                reduceOnly=False,
                positionIdx=0  # One-way mode
            )
        }
    ]
    
    for test in test_cases:
        print(f"\n=== Testing: {test['name']} ===")
        order = test['order']
        
        result = {"completed": False, "success": False, "error": None, "order_id": None}
        
        def callback(status_data):
            status, data = status_data
            result["completed"] = True
            if status == "success":
                result["success"] = True
                result["order_id"] = data.orderId
                print(f"✅ Success! Order ID: {data.orderId}")
            else:
                result["error"] = str(data)
                print(f"❌ Failed: {data}")
        
        # Place order
        exchange.placeOrder(order, callback)
        
        # Wait for completion
        timeout = 5
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        # Cancel if successful (cleanup)
        if result["success"] and result["order_id"]:
            print("Canceling test order...")
            cancel_result = {"completed": False}
            
            def cancel_callback(status_data):
                status, data = status_data
                cancel_result["completed"] = True
                if status == "success":
                    print("✅ Order cancelled")
                else:
                    print(f"❌ Cancel failed: {data}")
            
            exchange.cancelOrder(
                orderID=result["order_id"],
                symbol="XRPUSDT",
                completion=cancel_callback
            )
            
            # Wait for cancel
            start_time = time.time()
            while not cancel_result["completed"] and (time.time() - start_time) < timeout:
                time.sleep(0.01)
        
        time.sleep(1)  # Rate limiting

if __name__ == "__main__":
    test_order_combinations()