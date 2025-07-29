#!/usr/bin/env python3
"""Test grid bot with new position calculator"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gridbot import GridBot, GridBotConfig
from exchanges.bitunix import BitUnixExchange
from gridbot.types import PositionDirection

# Prevent actual trading
DRY_RUN = True


def test_grid_bot_calculation(config_file: str):
    """Test grid bot with new position calculation"""
    
    # Load config
    config_manager = GridBotConfig()
    config = config_manager.load_from_file(config_file)
    
    print(f"\n{'='*80}")
    print(f"Testing Grid Bot with New Position Calculator")
    print(f"{'='*80}")
    print(f"Config: {config_file}")
    print(f"Symbol: {config.symbol}")
    print(f"Direction: {config.position_direction.value}")
    print(f"Range: ${config.lower_price:,.2f} - ${config.upper_price:,.2f}")
    print(f"Grid Count: {config.grid_count}")
    print(f"Total Investment: ${config.total_investment:.2f}")
    print(f"Leverage: {config.leverage}x")
    
    # Initialize exchange (mock for dry run)
    if DRY_RUN:
        print("\n⚠️  DRY RUN MODE - No actual orders will be placed")
        
    exchange = BitUnixExchange()
    
    # Create bot instance
    bot = GridBot(exchange, config)
    
    # Get current price
    print("\nFetching current price...")
    current_price = 115312.2  # Example price for testing
    print(f"Current price: ${current_price:,.2f}")
    
    # Calculate grid levels
    grid_levels = bot.calculator.calculate_grid_levels(current_price)
    
    # Get initial position calculation
    initial_calc = bot.initial_position_calculator
    quantity, side, indices = initial_calc.calculate_initial_position(grid_levels, current_price)
    summary = initial_calc.get_initial_position_summary(grid_levels, current_price)
    
    print(f"\n{'─'*60}")
    print("INITIAL POSITION CALCULATION")
    print(f"{'─'*60}")
    
    print(f"\nGrid Distribution:")
    print(f"  BUY orders: {summary['grid_distribution']['buy_orders']}")
    print(f"  SELL orders: {summary['grid_distribution']['sell_orders']}")
    print(f"  Total orders: {summary['grid_distribution']['total_orders']}")
    
    print(f"\nInitial Position Required:")
    print(f"  Side: {summary['initial_position']['side']}")
    print(f"  Quantity: {summary['initial_position']['quantity']:.4f}")
    print(f"  Value: ${summary['initial_position']['value_usd']:,.2f}")
    print(f"  Explanation: {summary['initial_position']['explanation']}")
    
    print(f"\nPosition Verification:")
    verification = summary['verification']
    print(f"  Initial {verification['initial_position']['side']}: {verification['initial_position']['quantity']:.4f}")
    print(f"  + Grid BUY orders: {verification['grid_orders']['total_buy_orders']:.4f}")
    print(f"  = Total BUY: {verification['final_totals']['total_buy_quantity']:.4f}")
    print(f"  Total SELL: {verification['final_totals']['total_sell_quantity']:.4f}")
    print(f"  Net after all fills: {verification['net_position']:.6f}")
    print(f"  {verification['explanation']}")
    
    # Show what orders would be placed
    print(f"\n{'─'*60}")
    print("ORDERS TO BE PLACED")
    print(f"{'─'*60}")
    
    initial_orders = bot.calculator.get_initial_orders(grid_levels, current_price)
    
    buy_orders = [o for o in initial_orders if o.side.value == "BUY"]
    sell_orders = [o for o in initial_orders if o.side.value == "SELL"]
    
    print(f"\nBUY Orders ({len(buy_orders)}):")
    for i, order in enumerate(buy_orders[:5]):
        print(f"  {i+1}. ${order.price:,.2f} x {order.quantity:.4f}")
    if len(buy_orders) > 5:
        print(f"  ... and {len(buy_orders)-5} more")
        
    print(f"\nSELL Orders ({len(sell_orders)}):")
    for i, order in enumerate(sell_orders[:5]):
        print(f"  {i+1}. ${order.price:,.2f} x {order.quantity:.4f}")
    if len(sell_orders) > 5:
        print(f"  ... and {len(sell_orders)-5} more")
    
    # Simulate execution
    print(f"\n{'─'*60}")
    print("EXECUTION SIMULATION")
    print(f"{'─'*60}")
    
    if DRY_RUN:
        print("\n1. Open initial position:")
        print(f"   {side.value} {quantity:.4f} @ MARKET (${current_price:,.2f})")
        print(f"   Cost: ${quantity * current_price:,.2f}")
        
        print("\n2. Place grid orders:")
        print(f"   {len(buy_orders)} BUY orders")
        print(f"   {len(sell_orders)} SELL orders")
        
        print("\n3. When all orders execute:")
        if config.position_direction == PositionDirection.LONG:
            print(f"   - All {len(buy_orders)} BUY orders fill: Position increases")
            print(f"   - All {len(sell_orders)} SELL orders fill: Position closes to 0")
        else:
            print(f"   - All {len(sell_orders)} SELL orders fill: Short position increases")
            print(f"   - All {len(buy_orders)} BUY orders fill: Short position closes")
            
        if abs(verification['net_position']) > 0.0001:
            print(f"   ⚠️  Warning: {abs(verification['net_position']):.4f} units remain")
        else:
            print(f"   ✅ Position perfectly balanced!")


def main():
    """Run tests with different configurations"""
    
    # Test with existing config
    config_file = "btc_long_50grid_config.json"
    
    if os.path.exists(config_file):
        test_grid_bot_calculation(config_file)
    else:
        print(f"Config file {config_file} not found")
        
    # Create a SHORT config for testing
    print(f"\n\n{'='*80}")
    print("Creating SHORT configuration for testing...")
    
    short_config = {
        "symbol": "BTCUSDT",
        "grid_type": "arithmetic",
        "position_direction": "SHORT",
        "lower_price": 110000.0,
        "upper_price": 120000.0,
        "grid_count": 40,
        "total_investment": 500.0,
        "leverage": 10
    }
    
    import json
    with open("test_short_config.json", "w") as f:
        json.dump(short_config, f, indent=2)
        
    test_grid_bot_calculation("test_short_config.json")
    
    # Cleanup
    os.remove("test_short_config.json")


if __name__ == "__main__":
    main()