#!/usr/bin/env python3
"""Run BTC LONG 50-Grid Bot with Position Verification (Auto-start)"""

import sys
import os
import json
import time
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from gridbot import GridBot, GridBotConfig, GridType
from gridbot.types import PositionDirection


# Global bot instance for signal handling
bot_instance = None


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global bot_instance
    if bot_instance:
        print("\n\n⏹️  Stopping grid bot...")
        bot_instance.stop()
    sys.exit(0)


def main():
    global bot_instance
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║          BTC LONG 50-Grid Bot - Auto Start                 ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Load configuration
    with open('btc_long_50grid_config.json', 'r') as f:
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
    
    # Display configuration
    print(f"\nConfiguration Summary:")
    print(f"Range: ${grid_config.lower_price:,.2f} - ${grid_config.upper_price:,.2f}")
    print(f"Grids: {grid_config.grid_count}")
    print(f"Investment: ${grid_config.total_investment} x {grid_config.leverage}x = ${grid_config.total_investment * grid_config.leverage:,.2f}")
    
    # Create grid bot with persistence
    persistence_file = f"gridbot_{grid_config.symbol}_long50_bitunix.db"
    bot = GridBot(exchange, grid_config, persistence_path=persistence_file)
    bot_instance = bot  # Store globally for signal handler
    
    # Set up callbacks
    def on_grid_trade(order):
        side = "BUY" if order.side.value == "BUY" else "SELL"
        print(f"\n📊 Grid Trade: {side} {order.quantity:.6f} @ ${order.fill_price:,.2f}")
    
    def on_state_change(state):
        print(f"\n🔄 State: {state.value}")
    
    def on_error(error):
        print(f"\n❌ Error: {error}")
    
    bot.on_grid_trade = on_grid_trade
    bot.on_state_change = on_state_change
    bot.on_error = on_error
    
    # Start the bot
    print("\n🚀 Starting BTC LONG 50-Grid Bot...")
    bot.start()
    
    # Check if bot started successfully
    if bot.state.value != "running":
        print("\n❌ Bot failed to start!")
        return
    
    # Monitor the bot
    print("\n✅ Grid bot is running! Press Ctrl+C to stop.")
    print("="*60)
    
    try:
        last_update = 0
        while bot.state.value == "running":
            current_time = time.time()
            
            # Update status every 3 seconds
            if current_time - last_update >= 3:
                # Get status
                status = bot.get_status()
                
                # Extract data safely
                stats = status.get('statistics', {})
                position = status.get('position', {})
                orders = status.get('orders', {})
                
                # Display status
                print(f"\r💹 Price: ${bot.last_websocket_price or 0:,.2f} | "
                      f"Trades: {stats.get('trades', 0)} | "
                      f"P&L: ${stats.get('total_profit', 0):.2f} | "
                      f"Pos: {position.get('size', 0):.4f} BTC | "
                      f"Orders: {orders.get('active_count', 0)}",
                      end="", flush=True)
                
                last_update = current_time
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        pass  # Handled by signal handler


if __name__ == "__main__":
    main()