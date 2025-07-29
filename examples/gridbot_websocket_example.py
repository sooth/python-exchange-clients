#!/usr/bin/env python3
"""BitUnix Grid Bot with WebSocket Example"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.bitunix import BitUnixExchange
from gridbot import GridBot, GridBotConfig, GridType, PositionDirection


def main():
    """Run grid bot with WebSocket support"""
    print("=== BitUnix Grid Bot with WebSocket ===\n")
    
    # Initialize exchange
    exchange = BitUnixExchange()
    
    # Create configuration
    config_manager = GridBotConfig()
    
    # Example: ETH grid with WebSocket
    eth_config = config_manager.from_dict({
        'symbol': 'ETHUSDT',
        'grid_type': GridType.ARITHMETIC,
        'position_direction': PositionDirection.NEUTRAL,
        'upper_price': 2500,
        'lower_price': 2300,
        'grid_count': 10,
        'total_investment': 500,
        'leverage': 1,
        'stop_loss': 2200,
        'max_drawdown_percentage': 10,
        'post_only': False  # Disable post-only for market orders
    })
    
    print("Configuration Summary:")
    print(f"Symbol: {eth_config.symbol}")
    print(f"Range: ${eth_config.lower_price} - ${eth_config.upper_price}")
    print(f"Grid Count: {eth_config.grid_count}")
    print(f"Grid Spacing: ${eth_config.grid_spacing:.2f}")
    print(f"Investment per Grid: ${eth_config.investment_per_grid:.2f}")
    print(f"Stop Loss: ${eth_config.stop_loss}")
    print()
    
    # Create grid bot
    bot = GridBot(exchange, eth_config, persistence_path="eth_gridbot_websocket.db")
    
    # The bot will automatically use WebSocket if available
    # You can disable WebSocket if needed:
    # bot.use_websocket = False
    
    print("WebSocket Features:")
    print("✅ Real-time price updates via ticker channel")
    print("✅ Instant order fill notifications")
    print("✅ Live position and P&L updates")
    print("✅ Automatic reconnection on disconnection")
    print("✅ Fallback to REST API if WebSocket fails")
    print()
    
    # Set up callbacks
    def on_trade(order):
        print(f"\n🎯 TRADE EXECUTED via WebSocket!")
        print(f"   {order.side.value} {order.quantity} @ ${order.fill_price}")
        print(f"   Grid Level: {order.grid_index}")
    
    def on_state_change(state):
        print(f"\n📊 Bot State Changed: {state.value}")
    
    def on_error(error):
        print(f"\n❌ Bot Error: {error}")
    
    bot.on_grid_trade = on_trade
    bot.on_state_change = on_state_change
    bot.on_error = on_error
    
    # Check current price
    print("Fetching current market price...")
    def ticker_callback(status, data):
        if status == "success":
            for ticker in data:
                if ticker.symbol == "ETHUSDT":
                    current_price = ticker.lastPrice
                    print(f"Current ETH Price: ${current_price:.2f}")
                    
                    # Show where we are in the grid
                    position_in_range = (current_price - eth_config.lower_price) / (eth_config.upper_price - eth_config.lower_price)
                    print(f"Position in Range: {position_in_range * 100:.1f}%")
                    
                    # Calculate initial orders
                    grid_levels = bot.calculator.calculate_grid_levels(current_price)
                    initial_orders = bot.calculator.get_initial_orders(grid_levels, current_price)
                    
                    buy_orders = [o for o in initial_orders if o.side.value == "BUY"]
                    sell_orders = [o for o in initial_orders if o.side.value == "SELL"]
                    
                    print(f"\nInitial Orders:")
                    print(f"  Buy Orders: {len(buy_orders)}")
                    print(f"  Sell Orders: {len(sell_orders)}")
                    break
    
    exchange.fetchTickers(ticker_callback)
    
    print("\n" + "="*60)
    print("WebSocket Grid Bot Example")
    print("="*60)
    print("\nThis example demonstrates the grid bot with WebSocket support.")
    print("When running, you'll see:")
    print("- Real-time price updates")
    print("- Instant order fill notifications")
    print("- Live position updates")
    print("- WebSocket connection status")
    print("\nTo start the bot with WebSocket:")
    print("1. Ensure you have API keys configured")
    print("2. Review the configuration above")
    print("3. Uncomment the bot.start() line below")
    print("4. The bot will automatically connect to WebSocket")
    
    # Example: Start the bot (uncomment to run)
    """
    print("\nStarting Grid Bot with WebSocket...")
    bot.start()
    
    # Monitor the bot
    try:
        while bot.state == GridState.RUNNING:
            time.sleep(10)
            
            # Get current status
            status = bot.get_status()
            
            # The price shown here comes from WebSocket in real-time!
            ws_state = "Connected" if bot.websocket_connected else "Disconnected"
            
            print(f"\n📊 Status Update (WebSocket: {ws_state})")
            print(f"   Trades: {status['statistics']['trades']}")
            print(f"   Win Rate: {status['statistics']['win_rate']:.1f}%")
            print(f"   Profit: ${status['statistics']['total_profit']:.2f}")
            print(f"   Position: {status['position']['size']} @ ${status['position']['entry_price']:.2f}")
            
    except KeyboardInterrupt:
        print("\n\nStopping bot...")
        bot.stop()
    """
    
    print("\n" + "="*60)
    print("Key Differences with WebSocket:")
    print("="*60)
    print("1. **Instant Updates**: Order fills are detected immediately")
    print("2. **Real-time Prices**: No 1-second polling delay")
    print("3. **Lower Latency**: Faster reaction to market movements")
    print("4. **Reduced API Load**: No constant REST API calls")
    print("5. **Better Reliability**: Automatic reconnection")
    
    print("\nWebSocket Channels Used:")
    print("- ticker: Real-time price updates")
    print("- orders: Order status changes")
    print("- positions: Position and P&L updates")
    
    print("\nMonitoring Output:")
    print("When running, you'll see status updates like:")
    print("🔌 WebSocket: connected | Price: $2,435.67 | Orders: 10 active")
    
    print("\nThis indicates WebSocket is working and providing real-time data!")


if __name__ == "__main__":
    main()