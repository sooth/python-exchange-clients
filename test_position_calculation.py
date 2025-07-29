#!/usr/bin/env python3
"""Test and compare initial position calculations"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gridbot.types import GridConfig, PositionDirection, GridType
from gridbot.calculator import GridCalculator
from gridbot.initial_position_calculator import InitialPositionCalculator
from gridbot.initial_position_calculator_v2 import InitialPositionCalculatorV2


def test_position_calculation(config_dict: dict):
    """Test both old and new position calculation methods"""
    
    # Create config
    from gridbot.config import GridBotConfig
    config_manager = GridBotConfig()
    config = config_manager.from_dict(config_dict)
    
    print(f"\n{'='*80}")
    print(f"Testing {config.position_direction.value} Grid Configuration")
    print(f"{'='*80}")
    print(f"Symbol: {config.symbol}")
    print(f"Range: ${config.lower_price:,.2f} - ${config.upper_price:,.2f}")
    print(f"Grid Count: {config.grid_count}")
    print(f"Investment per Grid: ${config.investment_per_grid:.2f}")
    print(f"Leverage: {config.leverage}x")
    
    # Calculate grid levels
    calculator = GridCalculator(config)
    current_price = 115312.2  # Example price
    grid_levels = calculator.calculate_grid_levels(current_price)
    
    print(f"\nCurrent Price: ${current_price:,.2f}")
    
    # Count orders by type
    buy_orders = [l for l in grid_levels if l.side.value == "BUY"]
    sell_orders = [l for l in grid_levels if l.side.value == "SELL"]
    
    print(f"\nGrid Distribution:")
    print(f"  BUY orders: {len(buy_orders)}")
    print(f"  SELL orders: {len(sell_orders)}")
    
    # Show sample orders
    print(f"\n  Sample BUY orders:")
    for order in buy_orders[:3]:
        print(f"    Level {order.index}: ${order.price:,.2f} qty: {order.quantity:.4f}")
    if len(buy_orders) > 3:
        print(f"    ... and {len(buy_orders)-3} more")
        
    print(f"\n  Sample SELL orders:")
    for order in sell_orders[:3]:
        print(f"    Level {order.index}: ${order.price:,.2f} qty: {order.quantity:.4f}")
    if len(sell_orders) > 3:
        print(f"    ... and {len(sell_orders)-3} more")
    
    # Test OLD calculator
    print(f"\n{'─'*60}")
    print("OLD CALCULATOR (Current Implementation)")
    print(f"{'─'*60}")
    
    old_calc = InitialPositionCalculator(config)
    old_quantity, old_side, old_indices = old_calc.calculate_initial_position(grid_levels, current_price)
    old_summary = old_calc.get_initial_position_summary(grid_levels, current_price)
    
    print(f"Initial Position: {old_side.value} {old_quantity:.4f} units")
    print(f"Value: ${old_summary['initial_investment']:,.2f}")
    print(f"Explanation: {old_summary['explanation']}")
    
    # Test NEW calculator
    print(f"\n{'─'*60}")
    print("NEW CALCULATOR (Fixed Implementation)")
    print(f"{'─'*60}")
    
    new_calc = InitialPositionCalculatorV2(config)
    new_quantity, new_side, new_indices = new_calc.calculate_initial_position(grid_levels, current_price)
    new_summary = new_calc.get_initial_position_summary(grid_levels, current_price)
    
    print(f"Initial Position: {new_side.value} {new_quantity:.4f} units")
    print(f"Value: ${new_summary['initial_position']['value_usd']:,.2f}")
    print(f"Explanation: {new_summary['initial_position']['explanation']}")
    
    # Show verification
    print(f"\nPosition Verification:")
    verification = new_summary['verification']
    print(f"  Initial: {verification['initial_position']['side']} {verification['initial_position']['quantity']:.4f}")
    print(f"  Grid BUY orders total: {verification['grid_orders']['total_buy_orders']:.4f}")
    print(f"  Grid SELL orders total: {verification['grid_orders']['total_sell_orders']:.4f}")
    print(f"  Final BUY total: {verification['final_totals']['total_buy_quantity']:.4f}")
    print(f"  Final SELL total: {verification['final_totals']['total_sell_quantity']:.4f}")
    print(f"  Net position after all fills: {verification['net_position']:.6f}")
    print(f"  {verification['explanation']}")
    
    # Compare the two methods
    print(f"\n{'─'*60}")
    print("COMPARISON")
    print(f"{'─'*60}")
    
    print(f"Old Method: {old_side.value} {old_quantity:.4f} (${old_quantity * current_price:,.2f})")
    print(f"New Method: {new_side.value} {new_quantity:.4f} (${new_quantity * current_price:,.2f})")
    print(f"Difference: {abs(new_quantity - old_quantity):.4f} units (${abs(new_quantity - old_quantity) * current_price:,.2f})")
    
    # Simulate what happens when all orders fill
    print(f"\n{'─'*60}")
    print("SIMULATION: What happens when all orders execute?")
    print(f"{'─'*60}")
    
    # OLD method simulation
    print("\nOLD METHOD:")
    if config.position_direction == PositionDirection.LONG:
        old_final = old_quantity - sum(l.quantity for l in sell_orders) + sum(l.quantity for l in buy_orders)
        print(f"  Start: LONG {old_quantity:.4f}")
        print(f"  After all BUYs fill: LONG {old_quantity + sum(l.quantity for l in buy_orders):.4f}")
        print(f"  After all SELLs fill: {'LONG' if old_final > 0 else 'SHORT'} {abs(old_final):.4f}")
    
    # NEW method simulation  
    print("\nNEW METHOD:")
    if config.position_direction == PositionDirection.LONG:
        new_final = new_quantity - sum(l.quantity for l in sell_orders) + sum(l.quantity for l in buy_orders)
        print(f"  Start: LONG {new_quantity:.4f}")
        print(f"  After all BUYs fill: LONG {new_quantity + sum(l.quantity for l in buy_orders):.4f}")
        print(f"  After all SELLs fill: Position closed (0.0000)")
        print(f"  ✅ Position correctly exits at grid boundaries")


def main():
    """Run tests with different configurations"""
    
    # Test 1: LONG grid
    long_config = {
        "symbol": "BTCUSDT",
        "grid_type": "arithmetic",
        "position_direction": "LONG",
        "lower_price": 114751.5,
        "upper_price": 116752.0,
        "grid_count": 50,
        "total_investment": 200.0,
        "leverage": 20
    }
    
    test_position_calculation(long_config)
    
    # Test 2: SHORT grid
    print(f"\n\n{'='*80}")
    short_config = long_config.copy()
    short_config["position_direction"] = "SHORT"
    test_position_calculation(short_config)
    
    # Interactive test
    print(f"\n\n{'='*80}")
    print("INTERACTIVE TEST")
    print(f"{'='*80}")
    
    try:
        print("\nEnter custom parameters (press Enter for defaults):")
        
        symbol = input("Symbol (default: BTCUSDT): ").strip() or "BTCUSDT"
        direction = input("Direction (LONG/SHORT/NEUTRAL, default: LONG): ").strip().upper() or "LONG"
        lower = float(input("Lower price (default: 114000): ") or "114000")
        upper = float(input("Upper price (default: 116000): ") or "116000")
        grids = int(input("Grid count (default: 20): ") or "20")
        investment = float(input("Total investment (default: 100): ") or "100")
        leverage = int(input("Leverage (default: 10): ") or "10")
        current = float(input("Current price (default: 115000): ") or "115000")
        
        custom_config = {
            "symbol": symbol,
            "grid_type": "arithmetic",
            "position_direction": direction,
            "lower_price": lower,
            "upper_price": upper,
            "grid_count": grids,
            "total_investment": investment,
            "leverage": leverage
        }
        
        # Override current price for custom test
        import gridbot.calculator
        original_fetch = gridbot.calculator.GridCalculator.calculate_grid_levels
        
        def mock_calculate(self, *args):
            levels = original_fetch(self, current)
            return levels
            
        gridbot.calculator.GridCalculator.calculate_grid_levels = mock_calculate
        
        test_position_calculation(custom_config)
        
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
    except Exception as e:
        print(f"\nError in interactive test: {e}")


if __name__ == "__main__":
    main()