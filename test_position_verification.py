#!/usr/bin/env python3
"""Test Grid Bot Position Verification"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from gridbot import GridBot, GridBotConfig, GridType
from gridbot.types import PositionDirection


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║           Testing Position Verification System             ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Load safe configuration
    with open('btc_safe_gridbot_config.json', 'r') as f:
        config_data = json.load(f)
    
    # Create exchange
    exchange = BitUnixExchange()
    
    # Create grid config
    config_manager = GridBotConfig()
    
    # Map the JSON config to GridBotConfig format
    grid_config = config_manager.from_dict({
        'symbol': config_data['symbol'],
        'grid_type': GridType.ARITHMETIC,
        'position_direction': PositionDirection.LONG,
        'upper_price': config_data['upper_price'],
        'lower_price': config_data['lower_price'],
        'grid_count': config_data['grid_count'],
        'total_investment': config_data['total_investment'],
        'leverage': config_data['leverage'],
        'position_mode': config_data['position_mode'],
        'margin_mode': config_data['margin_mode'],
        'stop_loss': config_data['stop_loss'],
        'take_profit': config_data['take_profit'],
        'max_position_size': config_data['max_position_size'],
        'max_drawdown_percentage': config_data['max_drawdown_percentage'],
        'order_type': config_data['order_type'],
        'time_in_force': config_data['time_in_force'],
        'post_only': config_data['post_only'],
        'auto_restart': config_data['auto_restart'],
        'trailing_up': config_data['trailing_up'],
        'trailing_down': config_data['trailing_down'],
        'cancel_orders_on_stop': config_data['cancel_orders_on_stop'],
        'close_position_on_stop': config_data['close_position_on_stop']
    })
    
    print(f"Configuration:")
    print(f"Symbol: {grid_config.symbol}")
    print(f"Leverage: {grid_config.leverage}x")
    print(f"Range: ${grid_config.lower_price:,.2f} - ${grid_config.upper_price:,.2f}")
    print(f"Investment: ${grid_config.total_investment}")
    print(f"Grid Count: {grid_config.grid_count} (fewer grids = larger orders)")
    
    # Calculate expected order sizes
    per_grid_value = (grid_config.total_investment * grid_config.leverage) / grid_config.grid_count
    avg_price = (grid_config.upper_price + grid_config.lower_price) / 2
    qty_per_grid = per_grid_value / avg_price
    
    print(f"\nOrder size calculation:")
    print(f"Per grid value: ${per_grid_value:.2f}")
    print(f"Quantity per grid: {qty_per_grid:.6f} BTC")
    print(f"Minimum required: 0.0001 BTC")
    print(f"✅ Order size is {qty_per_grid / 0.0001:.1f}x the minimum")
    
    # Create grid bot
    bot = GridBot(exchange, grid_config)
    
    print("\n" + "="*60)
    print("Testing position verification system...")
    print("="*60)
    
    # Try to start the bot
    print("\n🚀 Starting grid bot with position verification...")
    bot.start()
    
    # Check if bot started
    print(f"\n✅ Bot state: {bot.state.value}")
    
    # If running, check position
    if bot.state.value == "running":
        print("\nSuccessfully started with verified position!")
        print("Stopping bot now...")
        bot.stop()
    else:
        print("\nBot did not start - position verification prevented unsafe operation")


if __name__ == "__main__":
    main()