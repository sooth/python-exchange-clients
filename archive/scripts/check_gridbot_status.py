#!/usr/bin/env python3
"""Check Grid Bot Status"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange


def main():
    exchange = BitUnixExchange()
    
    print("="*60)
    print("GRID BOT STATUS CHECK")
    print("="*60)
    
    # Check positions
    print("\n📊 POSITIONS:")
    position_result = {"positions": None, "completed": False}
    
    def position_callback(status_data):
        status, data = status_data
        position_result["completed"] = True
        if status == "success":
            position_result["positions"] = data
    
    exchange.fetchPositions(position_callback)
    
    import time
    timeout = 5
    start_time = time.time()
    while not position_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if position_result["positions"]:
        for pos in position_result["positions"]:
            if pos.symbol == "BTCUSDT" and abs(pos.size) > 0:
                print(f"Symbol: {pos.symbol}")
                print(f"Size: {pos.size} BTC")
                print(f"Entry Price: ${pos.entryPrice:,.2f}")
                print(f"Mark Price: ${pos.markPrice:,.2f}")
                print(f"Unrealized PnL: ${pos.pnl:.2f}")
                leverage = getattr(pos, 'leverage', 'N/A')
                print(f"Leverage: {leverage}x" if leverage != 'N/A' else f"Leverage: {leverage}")
    
    # Check orders
    print("\n📋 ACTIVE ORDERS:")
    order_result = {"orders": None, "completed": False}
    
    def order_callback(status_data):
        status, data = status_data
        order_result["completed"] = True
        if status == "success":
            order_result["orders"] = data
    
    exchange.fetchOrders(order_callback)
    
    start_time = time.time()
    while not order_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if order_result["orders"]:
        btc_orders = [o for o in order_result["orders"] if o.symbol == "BTCUSDT"]
        grid_orders = [o for o in btc_orders if o.clientId and 'grid_' in o.clientId]
        
        print(f"Total BTC orders: {len(btc_orders)}")
        print(f"Grid orders: {len(grid_orders)}")
        
        if grid_orders:
            # Count by side
            buy_orders = [o for o in grid_orders if o.side == "BUY"]
            sell_orders = [o for o in grid_orders if o.side == "SELL"]
            
            print(f"  - BUY orders: {len(buy_orders)}")
            print(f"  - SELL orders: {len(sell_orders)}")
            
            # Show price range
            if buy_orders:
                buy_prices = [o.price for o in buy_orders]
                print(f"  - BUY range: ${min(buy_prices):,.2f} - ${max(buy_prices):,.2f}")
            
            if sell_orders:
                sell_prices = [o.price for o in sell_orders]
                print(f"  - SELL range: ${min(sell_prices):,.2f} - ${max(sell_prices):,.2f}")


if __name__ == "__main__":
    main()