#!/usr/bin/env python3
"""Refresh grid orders with tighter spacing tolerance"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.base import ExchangeOrderRequest
from gridbot import GridBot, GridBotConfig, GridType
from gridbot.types import PositionDirection, OrderSide
from gridbot.calculator import GridCalculator


def refresh_grid_tight():
    """Refresh grid orders with tighter tolerance for close orders"""
    exchange = BitUnixExchange()
    
    # Load configuration
    with open('btc_long_50grid_config.json', 'r') as f:
        config_data = json.load(f)
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║          GRID ORDER REFRESH - TIGHT SPACING                ║
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
    
    print("\n📋 Fetching existing orders...")
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
    
    print(f"Found {len(grid_orders)} existing grid orders")
    
    # Track existing orders
    existing_prices = set()
    for order in grid_orders:
        existing_prices.add((order.side, round(order.price, 2)))
    
    # Calculate expected grid levels
    config_manager = GridBotConfig()
    grid_config = config_manager.from_dict(config_data)
    
    calculator = GridCalculator(grid_config)
    grid_levels = calculator.calculate_grid_levels(current_price)
    
    # Find missing orders with MUCH tighter tolerance
    print("\n🔍 Finding missing orders with tight spacing...")
    missing_levels = []
    
    # Use a much smaller minimum distance - just $20 to avoid immediate execution
    MIN_DISTANCE_USD = 20.0
    
    for level in grid_levels:
        # For LONG positions, check proper order placement
        if grid_config.position_direction == PositionDirection.LONG:
            # BUY orders should be below current price
            if level.side == OrderSide.BUY and level.price >= current_price - MIN_DISTANCE_USD:
                continue
            # SELL orders should be above current price  
            if level.side == OrderSide.SELL and level.price <= current_price + MIN_DISTANCE_USD:
                continue
        
        # Check if we already have this order
        price_tuple = (level.side.value, round(level.price, 2))
        if price_tuple not in existing_prices:
            missing_levels.append(level)
    
    print(f"Found {len(missing_levels)} missing orders")
    
    # Show what we're about to place
    if missing_levels:
        print("\n📊 Orders to place:")
        for level in sorted(missing_levels, key=lambda x: x.price):
            distance = abs(level.price - current_price)
            print(f"  Level {level.index}: {level.side.value} @ ${level.price:,.2f} (${distance:.2f} from current)")
    
    # Place missing orders
    if missing_levels:
        print("\n📤 Placing missing orders...")
        placed_count = 0
        
        for level in missing_levels:
            print(f"\nPlacing {level.side.value} {level.quantity:.6f} @ ${level.price:.2f}")
            
            order_request = ExchangeOrderRequest(
                symbol=grid_config.symbol,
                side=level.side.value,
                orderType='LIMIT',
                qty=level.quantity,
                price=level.price,
                orderLinkId=f'grid_{grid_config.symbol}_{level.index}_{int(time.time()*1000)}',
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
        
        print(f"\n✅ Successfully placed {placed_count}/{len(missing_levels)} orders")
    else:
        print("\n✅ No missing orders - grid is complete!")
    
    # Final summary
    print("\n" + "="*60)
    print("GRID REFRESH COMPLETE")
    print("="*60)
    print(f"Current price: ${current_price:,.2f}")
    print(f"Orders placed: {placed_count if missing_levels else 0}")
    
    # Show final gap status
    time.sleep(2)
    print("\n🔄 Checking final gap...")
    
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
        final_grid = [o for o in final_btc if o.clientId and 'grid_' in o.clientId]
        
        buy_orders = sorted([o.price for o in final_grid if o.side == "BUY"], reverse=True)
        sell_orders = sorted([o.price for o in final_grid if o.side == "SELL"])
        
        if buy_orders and sell_orders:
            gap = sell_orders[0] - buy_orders[0]
            print(f"\nFinal state:")
            print(f"  Highest BUY: ${buy_orders[0]:,.2f}")
            print(f"  Lowest SELL: ${sell_orders[0]:,.2f}")
            print(f"  Gap: ${gap:.2f}")
            
            if gap > 100:
                print(f"\n⚠️  Gap is still large. This is due to grid spacing of $40.83")
                print(f"   With current price at ${current_price:,.2f}, we're between grid levels")
            else:
                print(f"\n✅ Gap is reasonable for grid spacing")


if __name__ == "__main__":
    try:
        refresh_grid_tight()
    except KeyboardInterrupt:
        print("\n\n❌ Refresh cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()