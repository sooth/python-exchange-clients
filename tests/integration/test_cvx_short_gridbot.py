#!/usr/bin/env python3
"""Test CVX Short Grid Bot with WebSocket (No Interactive Mode)"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from gridbot import GridBot, GridBotConfig, GridType
from gridbot.types import PositionDirection


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║           CVX SHORT Grid Bot Test (WebSocket)              ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Load configuration
    with open('cvx_short_gridbot_config.json', 'r') as f:
        config_data = json.load(f)
    
    print("Configuration loaded from cvx_short_gridbot_config.json")
    
    # Create exchange
    exchange = BitUnixExchange()
    
    # Get current price
    print("\nFetching current CVX price...")
    current_price = None
    
    def price_callback(status_data):
        nonlocal current_price
        status, data = status_data
        if status == "success":
            for ticker in data:
                if ticker.symbol == "CVXUSDT":
                    current_price = ticker.lastPrice
                    break
    
    exchange.fetchTickers(price_callback)
    time.sleep(2)
    
    if not current_price:
        print("Failed to get current CVX price")
        return
    
    print(f"Current CVX price: ${current_price:.3f}")
    
    # Create grid config
    config_manager = GridBotConfig()
    
    # Map the JSON config to GridBotConfig format
    grid_config = config_manager.from_dict({
        'symbol': config_data['symbol'],
        'grid_type': GridType.ARITHMETIC,
        'position_direction': PositionDirection.SHORT,
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
    
    # Display configuration
    print("\n" + "="*60)
    print("GRID BOT CONFIGURATION")
    print("="*60)
    print(f"Symbol: {grid_config.symbol}")
    print(f"Direction: {grid_config.position_direction.value} (Shorting)")
    print(f"Price Range: ${grid_config.lower_price:.3f} - ${grid_config.upper_price:.3f}")
    print(f"Current Price: ${current_price:.3f}")
    print(f"Grid Count: {grid_config.grid_count}")
    print(f"Grid Spacing: ${grid_config.grid_spacing:.3f}")
    print(f"Total Investment: ${grid_config.total_investment}")
    print(f"Investment per Grid: ${grid_config.investment_per_grid:.2f}")
    print(f"Stop Loss: ${grid_config.stop_loss:.3f}")
    print(f"Leverage: {grid_config.leverage}x")
    
    # Price position analysis
    price_position_pct = ((current_price - grid_config.lower_price) / 
                         (grid_config.upper_price - grid_config.lower_price)) * 100
    print(f"\nPrice Position: {price_position_pct:.1f}% of range")
    
    if current_price > grid_config.upper_price:
        print("⚠️  WARNING: Current price is ABOVE the grid range!")
        print("   The bot will wait for price to enter the range before placing orders.")
    elif current_price < grid_config.lower_price:
        print("⚠️  WARNING: Current price is BELOW the grid range!")
        print("   This is good for a SHORT grid - all sell orders will be placed.")
    else:
        print(f"✅ Current price is within the grid range")
    
    # Test WebSocket connection
    print("\n" + "="*60)
    print("TESTING WEBSOCKET CONNECTION")
    print("="*60)
    
    # Create grid bot
    bot = GridBot(exchange, grid_config)
    
    # Test WebSocket
    print("1. Connecting to WebSocket...")
    if bot._connect_websocket():
        print("   ✅ WebSocket connected successfully!")
        
        print("\n2. Waiting for real-time updates (10 seconds)...")
        time.sleep(10)
        
        if bot.last_websocket_price:
            print(f"   ✅ Receiving CVX price updates: ${bot.last_websocket_price:.3f}")
        else:
            print("   ⚠️  No price updates received yet")
        
        # Show WebSocket state
        ws_state = exchange.getWebSocketState()
        print(f"\n3. WebSocket State: {ws_state}")
        print(f"   Connected: {exchange.isWebSocketConnected()}")
        
        # Test grid calculations
        print("\n" + "="*60)
        print("GRID CALCULATION TEST")
        print("="*60)
        
        # Calculate grid levels
        grid_levels = bot.calculator.calculate_grid_levels(current_price)
        print(f"Calculated {len(grid_levels)} grid levels:")
        
        # Show first few levels
        for i, level in enumerate(grid_levels[:5]):
            side = "SELL" if level.side.value == "SELL" else "BUY"
            print(f"   Level {level.index}: {side} {level.quantity:.4f} CVX @ ${level.price:.3f}")
        
        if len(grid_levels) > 5:
            print(f"   ... and {len(grid_levels) - 5} more levels")
        
        # Calculate initial position
        print("\n" + "="*60)
        print("INITIAL POSITION CALCULATION")
        print("="*60)
        
        position_summary = bot.initial_position_calculator.get_initial_position_summary(
            grid_levels, current_price
        )
        
        print(f"Price Location: {position_summary['price_location_pct']:.1f}% of range")
        print(f"Initial Action: {position_summary['initial_side']} {position_summary['initial_quantity']:.4f} CVX")
        print(f"Explanation: {position_summary['explanation']}")
        
        # Risk analysis
        print("\n" + "="*60)
        print("RISK ANALYSIS")
        print("="*60)
        
        # Maximum loss calculation
        max_loss_pct = ((grid_config.stop_loss - grid_config.upper_price) / grid_config.upper_price) * 100
        max_loss_usd = grid_config.total_investment * (max_loss_pct / 100)
        
        print(f"Stop Loss: ${grid_config.stop_loss:.3f}")
        print(f"Maximum Loss: ${abs(max_loss_usd):.2f} ({abs(max_loss_pct):.1f}%)")
        print(f"Risk/Reward: Short position - profits when price falls")
        
        # Disconnect WebSocket
        print("\n4. Disconnecting WebSocket...")
        exchange.disconnectWebSocket()
        print("   ✅ Disconnected")
        
    else:
        print("   ❌ WebSocket connection failed!")
    
    print("\n" + "="*60)
    print("CVX SHORT Grid Bot Test Complete!")
    print("="*60)
    print("\nSummary:")
    print(f"- Configuration: ✅ Loaded")
    print(f"- Current Price: ${current_price:.3f}")
    print(f"- WebSocket: {'✅ Working' if bot.last_websocket_price else '⚠️ Check connection'}")
    print(f"- Grid Levels: ✅ Calculated")
    print(f"- Ready to Trade: {'✅ Yes' if bot.last_websocket_price else '⚠️ Check WebSocket'}")
    
    print("\n⚠️  This was a TEST RUN - no orders were placed.")
    print("   To start actual trading, use run_cvx_short_gridbot.py")


if __name__ == "__main__":
    main()