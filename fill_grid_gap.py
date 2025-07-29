#!/usr/bin/env python3
"""Fill the gap in grid orders with immediate coverage"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.base import ExchangeOrderRequest


def fill_grid_gap():
    """Fill the gap between highest BUY and lowest SELL"""
    exchange = BitUnixExchange()
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║               GRID GAP FILLER                              ║
╚═══════════════════════════════════════════════════════════╝
""")
    
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
    
    print("📊 Fetching current BTC price...")
    exchange.fetchTickers(price_callback)
    
    time.sleep(2)
    
    print(f"Current price: ${current_price:,.2f}")
    
    # Get existing orders
    order_result = {"orders": None, "completed": False}
    
    def order_callback(status_data):
        status, data = status_data
        order_result["completed"] = True
        if status == "success":
            order_result["orders"] = data
    
    print("\n📋 Analyzing existing orders...")
    exchange.fetchOrders(order_callback)
    
    timeout = 5
    start_time = time.time()
    while not order_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    if not order_result["orders"]:
        print("❌ Failed to fetch orders")
        return
        
    btc_orders = [o for o in order_result["orders"] if o.symbol == "BTCUSDT"]
    grid_orders = [o for o in btc_orders if o.clientId and 'grid_' in o.clientId]
    
    # Find highest BUY and lowest SELL
    buy_prices = sorted([o.price for o in grid_orders if o.side == "BUY"], reverse=True)
    sell_prices = sorted([o.price for o in grid_orders if o.side == "SELL"])
    
    if not buy_prices or not sell_prices:
        print("❌ Could not find both BUY and SELL orders")
        return
    
    highest_buy = buy_prices[0]
    lowest_sell = sell_prices[0]
    gap = lowest_sell - highest_buy
    
    print(f"\n📊 Current gap analysis:")
    print(f"  Highest BUY: ${highest_buy:,.2f}")
    print(f"  Lowest SELL: ${lowest_sell:,.2f}")
    print(f"  Gap: ${gap:.2f}")
    print(f"  Current price: ${current_price:,.2f}")
    
    # Calculate grid spacing (50 levels from 114751.5 to 116752.0)
    grid_spacing = 40.83
    
    # Determine orders to place in the gap
    orders_to_place = []
    
    # Place BUY orders up to just below current price (with $10 buffer)
    next_buy = highest_buy + grid_spacing
    while next_buy < current_price - 10:
        orders_to_place.append(("BUY", next_buy))
        next_buy += grid_spacing
    
    # Place SELL orders down to just above current price (with $10 buffer)
    next_sell = lowest_sell - grid_spacing
    while next_sell > current_price + 10:
        orders_to_place.append(("SELL", next_sell))
        next_sell -= grid_spacing
    
    if not orders_to_place:
        print("\n✅ No orders needed - gap is minimal for current price movement")
        return
    
    print(f"\n📤 Placing {len(orders_to_place)} orders to fill the gap:")
    
    placed_count = 0
    for side, price in orders_to_place:
        print(f"\n{side} 0.001 @ ${price:.2f}")
        
        order_request = ExchangeOrderRequest(
            symbol="BTCUSDT",
            side=side,
            orderType='LIMIT',
            qty=0.001,
            price=price,
            orderLinkId=f'grid_gap_{side}_{int(price)}_{int(time.time()*1000)}',
            tradingType='PERP'
        )
        
        place_result = {"completed": False, "success": False, "order_id": None}
        
        def place_callback(status_data):
            status, data = status_data
            place_result["completed"] = True
            place_result["success"] = status == "success"
            if status == "success":
                place_result["order_id"] = data.orderId
        
        exchange.placeOrder(order_request, place_callback)
        
        # Wait for order placement
        place_start = time.time()
        while not place_result["completed"] and (time.time() - place_start) < 2:
            time.sleep(0.01)
        
        if place_result["success"]:
            placed_count += 1
            print(f"  ✅ Placed: {place_result['order_id']}")
        else:
            print(f"  ❌ Failed to place order")
        
        # Small delay between orders
        time.sleep(0.1)
    
    print(f"\n✅ Successfully placed {placed_count}/{len(orders_to_place)} gap-filling orders")
    
    # Check final state
    print("\n🔄 Checking final state...")
    time.sleep(2)
    
    final_result = {"orders": None, "completed": False}
    
    def final_callback(status_data):
        status, data = status_data
        final_result["completed"] = True
        if status == "success":
            final_result["orders"] = data
    
    exchange.fetchOrders(final_callback)
    
    final_start = time.time()
    while not final_result["completed"] and (time.time() - final_start) < timeout:
        time.sleep(0.01)
    
    if final_result["orders"]:
        final_btc = [o for o in final_result["orders"] if o.symbol == "BTCUSDT"]
        final_grid = [o for o in final_btc if o.clientId and ('grid_' in o.clientId or 'gap_' in o.clientId)]
        
        buy_orders = sorted([o.price for o in final_grid if o.side == "BUY"], reverse=True)
        sell_orders = sorted([o.price for o in final_grid if o.side == "SELL"])
        
        if buy_orders and sell_orders:
            new_gap = sell_orders[0] - buy_orders[0]
            print(f"\nFinal state:")
            print(f"  Highest BUY: ${buy_orders[0]:,.2f}")
            print(f"  Lowest SELL: ${sell_orders[0]:,.2f}")
            print(f"  Gap: ${new_gap:.2f}")
            
            if new_gap < 100:
                print(f"\n✅ Gap successfully reduced to ${new_gap:.2f}")
            else:
                print(f"\n⚠️  Gap is still ${new_gap:.2f} - this is normal given grid spacing of ${grid_spacing:.2f}")


if __name__ == "__main__":
    try:
        fill_grid_gap()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()