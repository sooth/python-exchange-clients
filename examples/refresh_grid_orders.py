#!/usr/bin/env python3
"""Refresh grid orders - remove duplicates and fill gaps"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from gridbot import GridBot, GridBotConfig, GridType
from gridbot.types import PositionDirection, OrderSide
from gridbot.calculator import GridCalculator


def refresh_grid_orders():
    """Refresh grid orders by removing duplicates and filling gaps"""
    exchange = BitUnixExchange()
    
    # Load configuration
    with open('btc_long_50grid_config.json', 'r') as f:
        config_data = json.load(f)
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║              GRID ORDER REFRESH TOOL                       ║
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
    
    # Group by price to find duplicates
    orders_by_price = {}
    for order in grid_orders:
        price_key = f"{order.side}_{order.price:.2f}"
        if price_key not in orders_by_price:
            orders_by_price[price_key] = []
        orders_by_price[price_key].append(order)
    
    # Step 1: Cancel duplicate orders
    print("\n🗑️  Cancelling duplicate orders...")
    cancel_count = 0
    orders_to_keep = {}  # Track which orders we're keeping
    
    for price_key, orders in orders_by_price.items():
        if len(orders) > 1:
            # Keep the first order, cancel the rest
            orders_to_keep[price_key] = orders[0]
            for dup_order in orders[1:]:
                print(f"  Cancelling duplicate {dup_order.side} order at ${dup_order.price:.2f}")
                
                cancel_result = {"completed": False, "success": False}
                
                def cancel_callback(status_data):
                    status, data = status_data
                    cancel_result["completed"] = True
                    cancel_result["success"] = status == "success"
                
                exchange.cancelOrder(dup_order.orderId, cancel_callback)
                
                # Wait for cancellation
                cancel_start = time.time()
                while not cancel_result["completed"] and (time.time() - cancel_start) < 2:
                    time.sleep(0.01)
                
                if cancel_result["success"]:
                    cancel_count += 1
                else:
                    print(f"    ❌ Failed to cancel order {dup_order.orderId}")
        else:
            # No duplicates, keep the order
            orders_to_keep[price_key] = orders[0]
    
    print(f"✅ Cancelled {cancel_count} duplicate orders")
    
    # Wait a bit for cancellations to process
    if cancel_count > 0:
        print("⏳ Waiting for cancellations to process...")
        time.sleep(2)
    
    # Step 2: Calculate expected grid levels
    print("\n📐 Calculating grid levels...")
    config_manager = GridBotConfig()
    grid_config = config_manager.from_dict(config_data)
    
    calculator = GridCalculator(grid_config)
    grid_levels = calculator.calculate_grid_levels(current_price)
    
    # Step 3: Find missing orders
    print("\n🔍 Finding missing orders...")
    missing_levels = []
    
    for level in grid_levels:
        # Skip levels too close to current price
        price_diff_pct = abs(level.price - current_price) / current_price
        if price_diff_pct < 0.0005:  # 0.05% minimum distance
            continue
        
        # For LONG positions, check proper order placement
        if grid_config.position_direction == PositionDirection.LONG:
            # BUY orders should be below current price
            if level.side == OrderSide.BUY and level.price >= current_price:
                continue
            # SELL orders should be above current price
            if level.side == OrderSide.SELL and level.price <= current_price:
                continue
        
        # Check if we have an order at this level
        has_order = False
        price_key = f"{level.side.value}_{level.price:.2f}"
        
        # Check exact match first
        if price_key in orders_to_keep:
            has_order = True
        else:
            # Check for close match (within $1)
            for existing_key, existing_order in orders_to_keep.items():
                existing_side, existing_price_str = existing_key.split('_')
                existing_price = float(existing_price_str)
                
                if existing_side == level.side.value and abs(existing_price - level.price) < 1:
                    has_order = True
                    break
        
        if not has_order:
            missing_levels.append(level)
    
    print(f"Found {len(missing_levels)} missing orders")
    
    # Step 4: Place missing orders
    if missing_levels:
        print("\n📤 Placing missing orders...")
        
        # Group by 10 to avoid overwhelming the API
        batch_size = 10
        placed_count = 0
        
        for i in range(0, len(missing_levels), batch_size):
            batch = missing_levels[i:i+batch_size]
            print(f"\nPlacing batch {i//batch_size + 1} ({len(batch)} orders):")
            
            for level in batch:
                print(f"  {level.side.value} {level.quantity:.6f} @ ${level.price:.2f}")
                
                from exchanges.base import ExchangeOrderRequest
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
                    print(f"    ✅ Placed: {place_result['order_id']}")
                else:
                    print(f"    ❌ Failed to place order")
                
                # Small delay between orders
                time.sleep(0.1)
            
            # Delay between batches
            if i + batch_size < len(missing_levels):
                print("⏳ Waiting before next batch...")
                time.sleep(1)
        
        print(f"\n✅ Successfully placed {placed_count}/{len(missing_levels)} orders")
    else:
        print("\n✅ No missing orders - grid is complete!")
    
    # Step 5: Final summary
    print("\n" + "="*60)
    print("GRID REFRESH SUMMARY")
    print("="*60)
    print(f"Duplicate orders cancelled: {cancel_count}")
    print(f"New orders placed: {placed_count if missing_levels else 0}")
    print(f"Current price: ${current_price:,.2f}")
    
    # Verify final state
    print("\n🔄 Fetching final order state...")
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
        final_grid = [o for o in final_btc if o.clientId and 'grid_' in o.clientId]
        
        buy_orders = [o for o in final_grid if o.side == "BUY"]
        sell_orders = [o for o in final_grid if o.side == "SELL"]
        
        print(f"\nFinal grid state:")
        print(f"  Total grid orders: {len(final_grid)}")
        print(f"  BUY orders: {len(buy_orders)}")
        print(f"  SELL orders: {len(sell_orders)}")
        
        if buy_orders:
            buy_prices = [o.price for o in buy_orders]
            print(f"  Highest BUY: ${max(buy_prices):,.2f}")
        
        if sell_orders:
            sell_prices = [o.price for o in sell_orders]
            print(f"  Lowest SELL: ${min(sell_prices):,.2f}")
            
            if buy_orders:
                gap = min(sell_prices) - max(buy_prices)
                print(f"  Gap: ${gap:.2f}")
    
    print("\n✅ Grid refresh complete!")


if __name__ == "__main__":
    try:
        refresh_grid_orders()
    except KeyboardInterrupt:
        print("\n\n❌ Refresh cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()