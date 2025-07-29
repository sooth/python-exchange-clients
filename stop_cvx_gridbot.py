#!/usr/bin/env python3
"""Stop CVX Grid Bot and show final status"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange


def main():
    print("=== Stopping CVX Grid Bot ===\n")
    
    exchange = BitUnixExchange()
    
    # First, check current orders
    print("1. Checking current CVX orders...")
    orders = []
    
    def order_callback(status_data):
        nonlocal orders
        status, data = status_data
        if status == "success":
            orders = data
    
    exchange.fetchOrders(order_callback)
    time.sleep(2)
    
    cvx_orders = [o for o in orders if o.symbol == "CVXUSDT" and "grid_" in (o.clientId or "")]
    
    if cvx_orders:
        print(f"Found {len(cvx_orders)} grid orders to cancel")
        
        # Cancel all grid orders
        print("\n2. Cancelling all grid orders...")
        cancelled_count = 0
        failed_count = 0
        
        for order in cvx_orders:
            print(f"   Cancelling order {order.orderId} ({order.side} {order.qty} @ ${order.price})... ", end="", flush=True)
            
            result = {"success": False, "completed": False}
            
            def cancel_callback(status_data):
                nonlocal result
                status, data = status_data
                result["completed"] = True
                result["success"] = status == "success"
            
            exchange.cancelOrder(
                orderID=order.orderId,
                symbol="CVXUSDT",
                completion=cancel_callback
            )
            
            # Wait for completion
            timeout = 5
            start_time = time.time()
            while not result["completed"] and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if result["success"]:
                print("✅ Cancelled")
                cancelled_count += 1
            else:
                print("❌ Failed")
                failed_count += 1
            
            # Small delay between cancellations
            time.sleep(0.5)
        
        print(f"\nCancellation Summary:")
        print(f"  Cancelled: {cancelled_count}")
        print(f"  Failed: {failed_count}")
    else:
        print("No active grid orders found")
    
    # Check final position
    print("\n3. Checking final position...")
    positions = []
    
    def position_callback(status_data):
        nonlocal positions
        status, data = status_data
        if status == "success":
            positions = data
    
    exchange.fetchPositions(position_callback)
    time.sleep(2)
    
    cvx_position = None
    for pos in positions:
        if pos.symbol == "CVXUSDT":
            cvx_position = pos
            break
    
    if cvx_position:
        print(f"\n⚠️  WARNING: You still have an open CVX position!")
        print(f"  Size: {cvx_position.size} CVX ({'SHORT' if cvx_position.size < 0 else 'LONG'})")
        print(f"  Entry Price: ${cvx_position.entryPrice:.3f}")
        print(f"  Mark Price: ${cvx_position.markPrice:.3f}")
        print(f"  Unrealized PnL: ${cvx_position.pnl:.2f}")
        print(f"\n  This position will remain open. Close it manually if needed.")
    else:
        print("No open CVX position")
    
    print("\n✅ Grid bot stopped successfully!")
    
    # Note about persistence
    print("\n📁 Note: The bot state is saved in gridbot_CVXUSDT_bitunix.db")
    print("   You can resume the bot later and it will continue from where it left off.")


if __name__ == "__main__":
    main()