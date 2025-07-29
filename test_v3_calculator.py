#!/usr/bin/env python3
"""Test the V3 position calculator"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gridbot.types import GridConfig, PositionDirection, GridType, OrderSide
from gridbot.calculator import GridCalculator
from gridbot.initial_position_calculator_v3 import InitialPositionCalculatorV3
from gridbot.config import GridBotConfig

# Test configuration
config_dict = {
    "symbol": "BTCUSDT",
    "grid_type": "arithmetic",
    "position_direction": "LONG",
    "lower_price": 114751.5,
    "upper_price": 116752.0,
    "grid_count": 40,
    "total_investment": 200.0,
    "leverage": 20
}

# Create config
config_manager = GridBotConfig()
config = config_manager.from_dict(config_dict)

print(f"Configuration:")
print(f"  Symbol: {config.symbol}")
print(f"  Direction: {config.position_direction.value}")
print(f"  Range: ${config.lower_price:,.2f} - ${config.upper_price:,.2f}")
print(f"  Grid Count: {config.grid_count}")
print(f"  Total Investment: ${config.total_investment}")
print(f"  Leverage: {config.leverage}x")
print(f"  Total Capital: ${config.total_investment * config.leverage}")

# Calculate grid levels
calculator = GridCalculator(config)
current_price = 115735.2  # From the actual run
grid_levels = calculator.calculate_grid_levels(current_price)

# Count original distribution
buy_orders_orig = [l for l in grid_levels if l.side.value == "BUY"]
sell_orders_orig = [l for l in grid_levels if l.side.value == "SELL"]

print(f"\nOriginal Grid Distribution at ${current_price:,.2f}:")
print(f"  BUY orders: {len(buy_orders_orig)}")
print(f"  SELL orders: {len(sell_orders_orig)}")

# Apply V3 calculator
calc_v3 = InitialPositionCalculatorV3(config)
(initial_qty, initial_side), updated_grid = calc_v3.calculate_grid_with_leverage(grid_levels, current_price)

# Verify the calculation
verification = calc_v3.verify_calculations(updated_grid, initial_qty, initial_side, current_price)

print(f"\n{'='*60}")
print(f"V3 CALCULATOR RESULTS")
print(f"{'='*60}")

print(f"\nInitial Position:")
print(f"  Side: {initial_side.value}")
print(f"  Quantity: {initial_qty:.4f} BTC")
print(f"  Value: ${initial_qty * current_price:,.2f}")

print(f"\nGrid Orders After Adjustment:")
buy_orders = [l for l in updated_grid if l.side == OrderSide.BUY]
sell_orders = [l for l in updated_grid if l.side == OrderSide.SELL]

if buy_orders:
    print(f"  BUY orders: {len(buy_orders)} × {buy_orders[0].quantity:.4f} = {verification['grid_totals']['buy_total']:.4f} BTC")
if sell_orders:
    print(f"  SELL orders: {len(sell_orders)} × {sell_orders[0].quantity:.4f} = {verification['grid_totals']['sell_total']:.4f} BTC")

print(f"\nCapital Deployment:")
print(f"  Total available: {verification['total_capital_btc']:.4f} BTC (${verification['total_capital_usd']:,.2f})")
print(f"  Capital deployed: {verification['capital_deployed']:.4f} BTC")
print(f"  Utilization: {verification['capital_utilization']:.1f}%")

print(f"\nPosition Flow:")
print(f"  1. Start: {initial_side.value} {initial_qty:.4f} BTC")
if config.position_direction == PositionDirection.LONG:
    print(f"  2. After all BUYs: LONG {initial_qty + verification['grid_totals']['buy_total']:.4f} BTC")
    print(f"  3. After all SELLs: Position = {verification['final_position']:.4f} BTC")
else:
    print(f"  2. After all SELLs: SHORT {initial_qty + verification['grid_totals']['sell_total']:.4f} BTC")
    print(f"  3. After all BUYs: Position = {abs(verification['final_position']):.4f} BTC")

print(f"\n✅ Verification:")
print(f"  Will close to zero: {'YES' if verification['will_close_to_zero'] else 'NO'}")
print(f"  Final position: {verification['final_position']:.6f} BTC")

# Also test with equal buy/sell distribution
print(f"\n\n{'='*60}")
print(f"TEST WITH BALANCED GRID (equal BUY/SELL)")
print(f"{'='*60}")

# Force balanced grid for testing
balanced_price = (config.lower_price + config.upper_price) / 2
balanced_grid = calculator.calculate_grid_levels(balanced_price)

(initial_qty_b, initial_side_b), updated_grid_b = calc_v3.calculate_grid_with_leverage(balanced_grid, balanced_price)
verification_b = calc_v3.verify_calculations(updated_grid_b, initial_qty_b, initial_side_b, balanced_price)

print(f"\nBalanced grid at ${balanced_price:,.2f}:")
print(f"  BUY orders: {sum(1 for l in updated_grid_b if l.side == OrderSide.BUY)}")
print(f"  SELL orders: {sum(1 for l in updated_grid_b if l.side == OrderSide.SELL)}")
print(f"  Initial position: {initial_qty_b:.4f} BTC")
print(f"  Will close to zero: {'YES' if verification_b['will_close_to_zero'] else 'NO'}")

# OrderSide already imported above