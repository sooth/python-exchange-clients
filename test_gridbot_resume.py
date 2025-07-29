#!/usr/bin/env python3
"""Test Grid Bot Resume Mode with Fixes"""

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
║        Testing Grid Bot Resume Mode with Fixes             ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Load configuration
    with open('btc_long_50grid_config.json', 'r') as f:
        config_data = json.load(f)
    
    # Create exchange
    exchange = BitUnixExchange()
    
    # Create grid config
    config_manager = GridBotConfig()
    
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
    print(f"Range: ${grid_config.lower_price:,.2f} - ${grid_config.upper_price:,.2f}")
    print(f"Grids: {grid_config.grid_count}")
    
    # Create grid bot
    persistence_file = f"gridbot_{grid_config.symbol}_long50_bitunix.db"
    bot = GridBot(exchange, grid_config, persistence_path=persistence_file)
    
    # Set up callbacks
    fill_count = 0
    
    def on_grid_trade(order):
        nonlocal fill_count
        fill_count += 1
        side = "BUY" if order.side.value == "BUY" else "SELL"
        print(f"\n✅ Grid Trade #{fill_count}: {side} {order.quantity:.6f} @ ${order.fill_price:,.2f}")
    
    def on_state_change(state):
        print(f"\n🔄 State: {state.value}")
    
    def on_error(error):
        print(f"\n❌ Error: {error}")
    
    bot.on_grid_trade = on_grid_trade
    bot.on_state_change = on_state_change
    bot.on_error = on_error
    
    print("\n🚀 Starting grid bot in RESUME mode...")
    bot.start()
    
    if bot.state.value != "running":
        print("\n❌ Bot failed to start!")
        return
    
    print("\n✅ Grid bot resumed successfully!")
    print("Monitoring for order fills and WebSocket updates...")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    # Monitor for a short time to see if orders are being detected
    monitor_time = 30  # Monitor for 30 seconds
    start_time = time.time()
    last_status_time = 0
    
    try:
        while (time.time() - start_time) < monitor_time:
            current_time = time.time()
            
            # Show status every 5 seconds
            if current_time - last_status_time >= 5:
                status = bot.get_status()
                stats = status.get('statistics', {})
                orders = status.get('orders', {})
                
                print(f"\r⏰ {int(monitor_time - (current_time - start_time))}s | "
                      f"Fills: {fill_count} | "
                      f"Orders: {orders.get('active_count', 0)} | "
                      f"WebSocket: {'✅' if bot.websocket_connected else '❌'} | "
                      f"Price: ${bot.last_websocket_price or 0:,.2f}",
                      end="", flush=True)
                
                last_status_time = current_time
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\nStopping bot...")
    
    print(f"\n\nTest Summary:")
    print(f"Total fills detected: {fill_count}")
    print(f"WebSocket connected: {'Yes' if bot.websocket_connected else 'No'}")
    print(f"Final price: ${bot.last_websocket_price or 0:,.2f}")
    
    # Stop the bot
    bot.stop()


if __name__ == "__main__":
    main()