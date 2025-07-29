#!/usr/bin/env python3
"""Start CVX Short Grid Bot with WebSocket - ACTUAL TRADING"""

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
║        CVX SHORT Grid Bot - LIVE TRADING MODE              ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
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
    print(f"WebSocket: Enabled")
    
    # Price position analysis
    price_position_pct = ((current_price - grid_config.lower_price) / 
                         (grid_config.upper_price - grid_config.lower_price)) * 100
    print(f"\nPrice Position: {price_position_pct:.1f}% of range")
    
    if current_price > grid_config.upper_price:
        print("⚠️  WARNING: Current price is ABOVE the grid range!")
        print("   The bot will open a SHORT position and place BUY orders below.")
    elif current_price < grid_config.lower_price:
        print("⚠️  WARNING: Current price is BELOW the grid range!")
        print("   This is ideal for SHORT - all SELL orders will be placed above.")
    else:
        print(f"✅ Current price is within the grid range")
    
    # Risk warnings for SHORT position
    print("\n" + "="*60)
    print("⚠️  SHORT POSITION RISK WARNING")
    print("="*60)
    print("You are about to start a SHORT grid bot. This means:")
    print("- The bot will SELL (short) as price rises")
    print("- The bot will BUY (cover) as price falls")
    print("- You will LOSE money if price rises above your stop loss")
    print("- Maximum loss if stop loss hit: ~${:.2f}".format(
        grid_config.total_investment * abs((grid_config.stop_loss - grid_config.upper_price) / grid_config.upper_price)
    ))
    
    # Create grid bot with persistence
    persistence_file = f"gridbot_{grid_config.symbol}_bitunix.db"
    print(f"\n📁 Using persistence file: {persistence_file}")
    
    bot = GridBot(exchange, grid_config, persistence_path=persistence_file)
    bot_instance = bot  # Store globally for signal handler
    
    # Set up callbacks
    def on_grid_trade(order):
        side = "SELL (Short)" if order.side.value == "SELL" else "BUY (Cover)"
        print(f"\n📊 Grid Trade Executed:")
        print(f"   {side} {order.quantity} CVX @ ${order.fill_price:.3f}")
        print(f"   Order ID: {order.order_id}")
    
    def on_state_change(state):
        print(f"\n🔄 Bot State Changed: {state.value}")
    
    def on_error(error):
        print(f"\n❌ Error: {error}")
    
    bot.on_grid_trade = on_grid_trade
    bot.on_state_change = on_state_change
    bot.on_error = on_error
    
    # IMPORTANT: AUTO-START WITHOUT CONFIRMATION
    print("\n" + "="*60)
    print("🚀 STARTING CVX SHORT GRID BOT IN 5 SECONDS...")
    print("⚠️  REAL ORDERS WILL BE PLACED!")
    print("Press Ctrl+C NOW to cancel!")
    print("="*60)
    
    # Countdown
    for i in range(5, 0, -1):
        print(f"\rStarting in {i}...", end="", flush=True)
        time.sleep(1)
    
    print("\n\n🚀 Starting CVX SHORT Grid Bot...")
    
    # START THE BOT - THIS WILL PLACE REAL ORDERS
    bot.start()
    
    # Monitor the bot
    print("\n" + "="*60)
    print("Grid bot is running! Press Ctrl+C to stop.")
    print("="*60)
    
    try:
        last_update = 0
        while bot.state.value == "running":
            current_time = time.time()
            
            # Update status every 5 seconds
            if current_time - last_update >= 5:
                # Get status
                status = bot.get_status()
                
                # Clear line and display status
                print(f"\r📊 WebSocket: {'✅' if bot.websocket_connected else '❌'} | "
                      f"Price: ${bot.last_websocket_price or current_price:.3f} | "
                      f"Grid P&L: ${status['stats']['grid_profit']:.2f} | "
                      f"Pos P&L: ${status['stats']['position_profit']:.2f} | "
                      f"Total: ${status['stats']['total_profit']:.2f} | "
                      f"Trades: {status['stats']['trades']} | "
                      f"Orders: {status['active_orders']} | "
                      f"Pos: {status['position']['size']:.3f} @ ${status['position']['entry_price']:.3f}",
                      end="", flush=True)
                
                last_update = current_time
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        pass  # Handled by signal handler
        
    # Final summary (if we get here)
    if bot_instance:
        final_status = bot.get_status()
        print("\n\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        print(f"Total Trades: {final_status['stats']['trades']}")
        print(f"Grid Profit: ${final_status['stats']['grid_profit']:.2f}")
        print(f"Position P&L: ${final_status['stats']['position_profit']:.2f}")
        print(f"Total Profit: ${final_status['stats']['total_profit']:.2f}")
        print(f"Win Rate: {final_status['stats']['win_rate']:.1f}%")
        print(f"Final Position: {final_status['position']['size']:.3f} CVX")
        
        if abs(final_status['position']['size']) > 0:
            print(f"\n⚠️  WARNING: You still have an open position of {final_status['position']['size']:.3f} CVX")
            print("   Consider closing this position manually if needed.")


if __name__ == "__main__":
    main()