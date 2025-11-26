#!/usr/bin/env python3
"""Dry run test for grid bot resume - shows what orders would be placed"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from gridbot import GridBot, GridBotConfig, GridType
from gridbot.types import PositionDirection, OrderSide
from gridbot.calculator import GridCalculator


def analyze_existing_orders():
    """Analyze existing orders and show what's missing"""
    exchange = BitUnixExchange()
    
    # Load configuration
    with open('btc_long_50grid_config.json', 'r') as f:
        config_data = json.load(f)
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║              GRID BOT DRY RUN - RESUME ANALYSIS            ║
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
    
    print("Fetching current BTC price...")
    exchange.fetchTickers(price_callback)
    
    time.sleep(2)
    
    print(f"\n📊 Current BTC price: ${current_price:,.2f}")
    
    # Get existing orders
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
        
        print(f"\n📋 Found {len(grid_orders)} existing grid orders")
        
        # Group by side and price
        buy_orders = {}
        sell_orders = {}
        
        for order in grid_orders:
            price_key = f"{order.price:.2f}"
            if order.side == "BUY":
                if price_key not in buy_orders:
                    buy_orders[price_key] = []
                buy_orders[price_key].append(order)
            else:
                if price_key not in sell_orders:
                    sell_orders[price_key] = []
                sell_orders[price_key].append(order)
        
        # Show duplicates
        print("\n🔍 Checking for duplicate orders:")
        duplicates_found = False
        for price, orders in buy_orders.items():
            if len(orders) > 1:
                print(f"  ❗ {len(orders)} BUY orders at ${price}")
                duplicates_found = True
        for price, orders in sell_orders.items():
            if len(orders) > 1:
                print(f"  ❗ {len(orders)} SELL orders at ${price}")
                duplicates_found = True
        
        if not duplicates_found:
            print("  ✅ No duplicate orders found")
        
        # Create grid configuration
        config_manager = GridBotConfig()
        grid_config = config_manager.from_dict(config_data)
        
        # Calculate expected grid levels
        calculator = GridCalculator(grid_config)
        grid_levels = calculator.calculate_grid_levels(current_price)
        
        print(f"\n📐 Grid Configuration:")
        print(f"  Range: ${grid_config.lower_price:,.2f} - ${grid_config.upper_price:,.2f}")
        print(f"  Levels: {grid_config.grid_count}")
        print(f"  Spacing: ${(grid_config.upper_price - grid_config.lower_price) / (grid_config.grid_count - 1):.2f}")
        
        # Analyze coverage
        print(f"\n📊 Order Coverage Analysis:")
        
        # Find which levels have orders
        covered_levels = []
        missing_levels = []
        
        for level in grid_levels:
            # Check if we should have an order at this level
            should_have_order = False
            
            if grid_config.position_direction == PositionDirection.LONG:
                # For LONG: BUY below price, SELL above price
                if (level.side == OrderSide.BUY and level.price < current_price - 50) or \
                   (level.side == OrderSide.SELL and level.price > current_price + 50):
                    should_have_order = True
            
            if should_have_order:
                # Check if we have an order near this price
                has_order = False
                
                if level.side == OrderSide.BUY:
                    for price_str in buy_orders.keys():
                        order_price = float(price_str)
                        if abs(order_price - level.price) < 1:  # Within $1
                            has_order = True
                            break
                else:
                    for price_str in sell_orders.keys():
                        order_price = float(price_str)
                        if abs(order_price - level.price) < 1:  # Within $1
                            has_order = True
                            break
                
                if has_order:
                    covered_levels.append(level)
                else:
                    missing_levels.append(level)
        
        print(f"  Covered levels: {len(covered_levels)}")
        print(f"  Missing levels: {len(missing_levels)}")
        
        # Show gap analysis
        buy_prices = sorted([float(p) for p in buy_orders.keys()])
        sell_prices = sorted([float(p) for p in sell_orders.keys()])
        
        if buy_prices:
            highest_buy = max(buy_prices)
            print(f"\n  Highest BUY: ${highest_buy:,.2f} (${current_price - highest_buy:.2f} below current)")
        
        if sell_prices:
            lowest_sell = min(sell_prices)
            print(f"  Lowest SELL: ${lowest_sell:,.2f} (${lowest_sell - current_price:.2f} above current)")
            
            if buy_prices:
                gap = lowest_sell - highest_buy
                print(f"  Gap between highest BUY and lowest SELL: ${gap:.2f}")
        
        # Show what orders would be placed
        print(f"\n🎯 Orders that WOULD be placed to fill gaps:")
        
        if missing_levels:
            # Group by side for cleaner display
            missing_buys = [l for l in missing_levels if l.side == OrderSide.BUY]
            missing_sells = [l for l in missing_levels if l.side == OrderSide.SELL]
            
            if missing_buys:
                print(f"\n  BUY orders ({len(missing_buys)} total):")
                for level in sorted(missing_buys, key=lambda x: x.price, reverse=True)[:10]:
                    print(f"    Level {level.index}: ${level.price:,.2f} (qty: {level.quantity:.6f})")
                if len(missing_buys) > 10:
                    print(f"    ... and {len(missing_buys) - 10} more")
            
            if missing_sells:
                print(f"\n  SELL orders ({len(missing_sells)} total):")
                for level in sorted(missing_sells, key=lambda x: x.price)[:10]:
                    print(f"    Level {level.index}: ${level.price:,.2f} (qty: {level.quantity:.6f})")
                if len(missing_sells) > 10:
                    print(f"    ... and {len(missing_sells) - 10} more")
        else:
            print("  ✅ No missing orders - grid coverage is complete!")
        
        # Show recommended actions
        print(f"\n💡 Recommended Actions:")
        if duplicates_found:
            print("  1. Remove duplicate orders at same price levels")
        if missing_levels:
            print(f"  2. Place {len(missing_levels)} missing orders to ensure continuous coverage")
        if gap > 100:
            print(f"  3. Address the ${gap:.2f} gap around current price")
        
        print("\n✅ Dry run complete - no orders were actually placed")


if __name__ == "__main__":
    analyze_existing_orders()