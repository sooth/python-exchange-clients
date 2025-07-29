#!/usr/bin/env python3
"""Run BTC LONG Grid Bot with WebSocket"""

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
║          BTC LONG Grid Bot - High Frequency Trading        ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Load configuration
    with open('btc_long_gridbot_config.json', 'r') as f:
        config_data = json.load(f)
    
    print("Configuration loaded from btc_long_gridbot_config.json")
    
    # Create exchange
    exchange = BitUnixExchange()
    
    # Get current price
    print("\nFetching current BTC price...")
    current_price = None
    
    def price_callback(status_data):
        nonlocal current_price
        status, data = status_data
        if status == "success":
            for ticker in data:
                if ticker.symbol == "BTCUSDT":
                    current_price = ticker.lastPrice
                    break
    
    exchange.fetchTickers(price_callback)
    time.sleep(2)
    
    if not current_price:
        print("Failed to get current BTC price")
        return
    
    print(f"Current BTC price: ${current_price:,.2f}")
    
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
    print("\n" + "="*60)
    print("GRID BOT CONFIGURATION")
    print("="*60)
    print(f"Symbol: {grid_config.symbol}")
    print(f"Direction: {grid_config.position_direction.value} (Going Long)")
    print(f"Price Range: ${grid_config.lower_price:,.2f} - ${grid_config.upper_price:,.2f}")
    print(f"Range Size: ${grid_config.upper_price - grid_config.lower_price:,.2f} ({((grid_config.upper_price - grid_config.lower_price) / grid_config.lower_price * 100):.2f}%)")
    print(f"Current Price: ${current_price:,.2f}")
    print(f"Grid Count: {grid_config.grid_count}")
    print(f"Grid Spacing: ${grid_config.grid_spacing:,.2f}")
    print(f"Total Investment: ${grid_config.total_investment}")
    print(f"Investment per Grid: ${grid_config.investment_per_grid:.2f}")
    print(f"Stop Loss: ${grid_config.stop_loss:,.2f}")
    print(f"Take Profit: ${grid_config.take_profit:,.2f}")
    print(f"Leverage: {grid_config.leverage}x")
    print(f"WebSocket: Enabled")
    
    # Calculate effective position sizes with leverage
    print(f"\n💰 With {grid_config.leverage}x leverage:")
    print(f"   Effective Investment: ${grid_config.total_investment * grid_config.leverage:,.2f}")
    print(f"   Per Grid Effective: ${grid_config.investment_per_grid * grid_config.leverage:.2f}")
    
    # Price position analysis
    price_position_pct = ((current_price - grid_config.lower_price) / 
                         (grid_config.upper_price - grid_config.lower_price)) * 100
    print(f"\n📍 Price Position: {price_position_pct:.1f}% of range")
    
    if current_price > grid_config.upper_price:
        print("⚠️  WARNING: Current price is ABOVE the grid range!")
        print("   The bot will wait for price to enter the range before placing orders.")
    elif current_price < grid_config.lower_price:
        print("⚠️  WARNING: Current price is BELOW the grid range!")
        print("   This is good for LONG - all BUY orders will be placed above.")
    else:
        print(f"✅ Current price is within the grid range")
        grids_below = int((current_price - grid_config.lower_price) / grid_config.grid_spacing)
        grids_above = grid_config.grid_count - grids_below
        print(f"   ~{grids_below} grids below current price (BUY orders)")
        print(f"   ~{grids_above} grids above current price (SELL orders)")
    
    # Risk warnings for LONG position with high leverage
    print("\n" + "="*60)
    print("⚠️  HIGH LEVERAGE RISK WARNING")
    print("="*60)
    print(f"You are using {grid_config.leverage}x leverage. This means:")
    print(f"- A 1% price move = {grid_config.leverage}% profit/loss")
    print(f"- Liquidation price is very close to your entry")
    print(f"- Maximum loss if stop loss hit: ~${abs((grid_config.stop_loss - grid_config.lower_price) / grid_config.lower_price * grid_config.total_investment):.2f}")
    
    # Liquidation estimate (rough calculation)
    liquidation_pct = 100 / grid_config.leverage * 0.8  # 80% of maintenance margin
    print(f"\n⚠️  Estimated liquidation: ~{liquidation_pct:.2f}% below entry price")
    
    # Create grid bot with persistence
    persistence_file = f"gridbot_{grid_config.symbol}_long_bitunix.db"
    print(f"\n📁 Using persistence file: {persistence_file}")
    
    bot = GridBot(exchange, grid_config, persistence_path=persistence_file)
    bot_instance = bot  # Store globally for signal handler
    
    # Set up callbacks
    def on_grid_trade(order):
        side = "BUY" if order.side.value == "BUY" else "SELL"
        print(f"\n📊 Grid Trade Executed:")
        print(f"   {side} {order.quantity:.6f} BTC @ ${order.fill_price:,.2f}")
        print(f"   Order ID: {order.order_id}")
    
    def on_state_change(state):
        print(f"\n🔄 Bot State Changed: {state.value}")
    
    def on_error(error):
        print(f"\n❌ Error: {error}")
    
    bot.on_grid_trade = on_grid_trade
    bot.on_state_change = on_state_change
    bot.on_error = on_error
    
    # Confirm before starting
    print("\n" + "="*60)
    print("Ready to start the BTC LONG grid bot")
    print(f"⚠️  This will manage ${grid_config.total_investment} with {grid_config.leverage}x leverage")
    print(f"⚠️  200 grid orders will be placed!")
    print("="*60)
    
    user_input = input("\nStart the grid bot? (yes/no): ").strip().lower()
    
    if user_input != 'yes':
        print("Grid bot start cancelled.")
        return
    
    # Start the bot
    print("\n🚀 Starting BTC LONG Grid Bot...")
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
                      f"Price: ${bot.last_websocket_price or current_price:,.2f} | "
                      f"Grid P&L: ${status['stats']['grid_profit']:.2f} | "
                      f"Pos P&L: ${status['stats']['position_profit']:.2f} | "
                      f"Total: ${status['stats']['total_profit']:.2f} | "
                      f"Trades: {status['stats']['trades']} | "
                      f"Orders: {status['active_orders']} | "
                      f"Pos: {status['position']['size']:.6f} @ ${status['position']['entry_price']:,.2f}",
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
        print(f"Final Position: {final_status['position']['size']:.6f} BTC")
        
        if abs(final_status['position']['size']) > 0:
            print(f"\n⚠️  WARNING: You still have an open position of {final_status['position']['size']:.6f} BTC")
            print("   Consider closing this position manually if needed.")


if __name__ == "__main__":
    main()