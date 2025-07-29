#!/usr/bin/env python3
"""Debug Grid Bot Gap Issues"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange


def main():
    exchange = BitUnixExchange()
    
    # Get current price
    current_price = None
    
    def price_callback(status_data):
        nonlocal current_price
        status, data = status_data
        if status == "success":
            for ticker in data:
                if ticker.symbol == "BTCUSDT":
                    current_price = ticker.lastPrice
                    break
    
    print("Fetching current BTC price...")
    exchange.fetchTickers(price_callback)
    
    import time
    time.sleep(2)
    
    print(f"\nCurrent BTC price: ${current_price:,.2f}")
    
    # Get orders
    order_result = {"orders": None, "completed": False}
    
    def order_callback(status_data):
        status, data = status_data
        order_result["completed"] = True
        if status == "success":
            order_result["orders"] = data
    
    exchange.fetchOrders(order_callback)
    
    timeout = 5
    start_time = time.time()
    while not order_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if order_result["orders"]:
        btc_orders = [o for o in order_result["orders"] if o.symbol == "BTCUSDT"]
        grid_orders = [o for o in btc_orders if o.clientId and 'grid_' in o.clientId]
        
        # Get all order prices
        order_prices = [(o.price, o.side) for o in grid_orders]
        order_prices.sort()
        
        print(f"\n📊 Order Analysis:")
        print(f"Total grid orders: {len(grid_orders)}")
        
        # Find closest buy and sell to current price
        buy_prices = [p for p, side in order_prices if side == "BUY"]
        sell_prices = [p for p, side in order_prices if side == "SELL"]
        
        if buy_prices:
            closest_buy = max([p for p in buy_prices if p < current_price], default=None)
            if closest_buy:
                buy_gap = current_price - closest_buy
                print(f"\nClosest BUY order: ${closest_buy:,.2f} (${buy_gap:.2f} below current)")
            else:
                print(f"\n❌ NO BUY orders below current price!")
        
        if sell_prices:
            closest_sell = min([p for p in sell_prices if p > current_price], default=None)
            if closest_sell:
                sell_gap = closest_sell - current_price
                print(f"Closest SELL order: ${closest_sell:,.2f} (${sell_gap:.2f} above current)")
            else:
                print(f"❌ NO SELL orders above current price!")
        
        # Check for gaps
        print(f"\n🔍 Gap Analysis:")
        all_prices = [p for p, _ in order_prices]
        all_prices.sort()
        
        gaps = []
        for i in range(len(all_prices) - 1):
            gap = all_prices[i+1] - all_prices[i]
            if gap > 100:  # More than $100 gap
                gaps.append((all_prices[i], all_prices[i+1], gap))
        
        if gaps:
            print(f"Found {len(gaps)} large gaps:")
            for p1, p2, gap in gaps:
                print(f"  ${p1:,.2f} → ${p2:,.2f} (gap: ${gap:.2f})")
                if p1 < current_price < p2:
                    print(f"  ⚠️  Current price is IN THIS GAP!")
        
        # Check grid spacing
        print(f"\n📏 Expected grid spacing: $40.01")
        actual_spacings = []
        for i in range(len(all_prices) - 1):
            actual_spacings.append(all_prices[i+1] - all_prices[i])
        
        if actual_spacings:
            avg_spacing = sum(actual_spacings) / len(actual_spacings)
            print(f"Average actual spacing: ${avg_spacing:.2f}")


if __name__ == "__main__":
    main()