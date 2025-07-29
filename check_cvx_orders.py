#!/usr/bin/env python3
"""Check CVX orders and positions"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange


def main():
    print("Checking CVX orders and positions...\n")
    
    exchange = BitUnixExchange()
    
    # Check positions
    print("=== POSITIONS ===")
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
            print(f"CVX Position Found:")
            print(f"  Size: {pos.size} CVX")
            print(f"  Entry Price: ${pos.entryPrice:.3f}")
            print(f"  Mark Price: ${pos.markPrice:.3f}")
            print(f"  PnL: ${pos.pnl:.2f}")
            print(f"  Side: {'SHORT' if pos.size < 0 else 'LONG'}")
            break
    
    if not cvx_position:
        print("No CVX position found")
    
    # Check orders
    print("\n=== OPEN ORDERS ===")
    orders = []
    
    def order_callback(status_data):
        nonlocal orders
        status, data = status_data
        if status == "success":
            orders = data
    
    exchange.fetchOrders(order_callback)
    time.sleep(2)
    
    cvx_orders = [o for o in orders if o.symbol == "CVXUSDT"]
    
    if cvx_orders:
        print(f"Found {len(cvx_orders)} CVX orders:")
        # Sort by price
        cvx_orders.sort(key=lambda x: x.price if x.price else 0)
        
        for order in cvx_orders:
            print(f"\n  Order ID: {order.orderId}")
            print(f"  Type: {order.orderType} {order.side}")
            print(f"  Price: ${order.price:.3f}")
            print(f"  Quantity: {order.qty} CVX")
            print(f"  Status: {order.status}")
            if order.clientId:
                print(f"  Client ID: {order.clientId}")
    else:
        print("No open CVX orders found")
    
    # Summary
    print("\n=== SUMMARY ===")
    if cvx_position:
        print(f"Position: {cvx_position.size} CVX (SHORT)")
        print(f"Entry: ${cvx_position.entryPrice:.3f}")
        print(f"Current PnL: ${cvx_position.pnl:.2f}")
    
    print(f"\nOpen Orders: {len(cvx_orders)}")
    if cvx_orders:
        buy_orders = [o for o in cvx_orders if o.side == "BUY"]
        sell_orders = [o for o in cvx_orders if o.side == "SELL"]
        print(f"  BUY orders: {len(buy_orders)}")
        print(f"  SELL orders: {len(sell_orders)}")


if __name__ == "__main__":
    main()