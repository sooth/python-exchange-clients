#!/usr/bin/env python3
"""Test the new position calculation"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gridbot.types import GridConfig, PositionDirection, GridType
from gridbot.calculator import GridCalculator
from gridbot.initial_position_calculator_v2 import InitialPositionCalculatorV2
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

# Calculate grid levels
calculator = GridCalculator(config)
current_price = 115735.2  # From the actual run
grid_levels = calculator.calculate_grid_levels(current_price)

# Count orders by type
buy_orders = [l for l in grid_levels if l.side.value == "BUY"]
sell_orders = [l for l in grid_levels if l.side.value == "SELL"]

print(f"\nGrid Distribution at ${current_price:,.2f}:")
print(f"  BUY orders: {len(buy_orders)}")
print(f"  SELL orders: {len(sell_orders)}")

# Calculate quantities
buy_total = sum(l.quantity for l in buy_orders)
sell_total = sum(l.quantity for l in sell_orders)

print(f"\nOrder Quantities:")
print(f"  Total BUY quantity: {buy_total:.4f} BTC")
print(f"  Total SELL quantity: {sell_total:.4f} BTC")

# Calculate initial position with new formula
calc = InitialPositionCalculatorV2(config)
quantity, side, indices = calc.calculate_initial_position(grid_levels, current_price)

# Adjust grid quantities for balance
grid_levels = calc.adjust_grid_quantities_for_balance(grid_levels, current_price)

# Recalculate totals after adjustment
buy_total = sum(l.quantity for l in buy_orders)
sell_total = sum(l.quantity for l in sell_orders)

print(f"\nInitial Position Calculation:")
print(f"  Total Capital: ${config.total_investment} × {config.leverage} = ${config.total_investment * config.leverage}")
print(f"  Total Capital in BTC: ${config.total_investment * config.leverage} / ${current_price:,.2f} = {(config.total_investment * config.leverage) / current_price:.4f} BTC")
print(f"  Sum of BUY orders: {buy_total:.4f} BTC")
print(f"  Initial Position = Total Capital - BUY orders")
print(f"  Initial Position = {(config.total_investment * config.leverage) / current_price:.4f} - {buy_total:.4f} = {quantity:.4f} BTC")
print(f"  Side: {side.value}")

# Verify the balance
print(f"\nBalance Verification:")
print(f"  Initial Position: {quantity:.4f} BTC")
print(f"  + BUY orders: {buy_total:.4f} BTC")
print(f"  = Total deployed: {quantity + buy_total:.4f} BTC")
print(f"  Expected total: {(config.total_investment * config.leverage) / current_price:.4f} BTC")
print(f"  Match: {'✅' if abs((quantity + buy_total) - (config.total_investment * config.leverage) / current_price) < 0.0001 else '❌'}")

print(f"\nExit Verification:")
print(f"  SELL orders total: {sell_total:.4f} BTC")
print(f"  Initial position: {quantity:.4f} BTC")
print(f"  Difference: {abs(sell_total - quantity):.4f} BTC")
print(f"  Close to equal: {'✅' if abs(sell_total - quantity) < 0.002 else '❌'}")

# Show what happens when orders execute
print(f"\nWhen all orders execute:")
print(f"  Starting position: LONG {quantity:.4f} BTC")
print(f"  After all BUYs: LONG {quantity + buy_total:.4f} BTC")
print(f"  After all SELLs: Position = {quantity + buy_total - sell_total:.4f} BTC")
print(f"  Final position close to 0: {'✅' if abs(quantity + buy_total - sell_total) < 0.0001 else '❌'}")

print(f"\nKey insight:")
print(f"  Initial ({quantity:.4f}) = Total Capital ({(config.total_investment * config.leverage) / current_price:.4f}) - BUYs ({buy_total:.4f})")
print(f"  SELLs ({sell_total:.4f}) = Initial ({quantity:.4f})")
print(f"  Therefore: Initial + BUYs - SELLs = Total - BUYs + BUYs - Initial = Total - Initial = BUYs")
print(f"  Final position = BUYs = {buy_total:.4f} BTC (not 0!)")