#!/usr/bin/env python3
"""Test Grid Bot WebSocket Integration"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from gridbot import GridBot, GridBotConfig, GridType
from gridbot.types import PositionDirection

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║            Grid Bot WebSocket Integration Test             ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Create exchange
    exchange = BitUnixExchange()
    
    # Get current price
    print("Fetching current BTCUSDT price...")
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
        print("Failed to get current price")
        return
    
    print(f"Current BTCUSDT price: ${current_price:,.2f}")
    
    # Create grid config for testing
    config_manager = GridBotConfig()
    config = config_manager.from_dict({
        'symbol': 'BTCUSDT',
        'grid_type': GridType.ARITHMETIC,
        'position_direction': PositionDirection.NEUTRAL,
        'upper_price': current_price * 1.05,  # 5% above
        'lower_price': current_price * 0.95,  # 5% below
        'grid_count': 5,
        'total_investment': 50.0,  # Small test amount
        'leverage': 1,
        'stop_loss': current_price * 0.90,  # 10% stop loss
        'max_drawdown_percentage': 10,
        'post_only': True
    })
    
    # Create grid bot
    print("\nCreating Grid Bot...")
    bot = GridBot(exchange, config)
    
    # Set up callbacks
    def on_grid_trade(trade):
        print(f"\n📊 Grid Trade: {trade}")
    
    def on_state_change(state):
        print(f"\n🔄 State Change: {state}")
    
    def on_error(error):
        print(f"\n❌ Error: {error}")
    
    bot.on_grid_trade = on_grid_trade
    bot.on_state_change = on_state_change
    bot.on_error = on_error
    
    # Show grid info
    print(f"\nGrid Configuration:")
    print(f"  Symbol: {config.symbol}")
    print(f"  Range: ${config.lower_price:,.2f} - ${config.upper_price:,.2f}")
    print(f"  Levels: {config.grid_count}")
    print(f"  Investment: ${config.total_investment}")
    print(f"  WebSocket: {'Enabled' if bot.use_websocket else 'Disabled'}")
    
    # Test WebSocket connection
    print("\n1. Testing WebSocket connection...")
    ws_connected = bot._connect_websocket()
    
    if ws_connected:
        print("   ✅ WebSocket connected successfully!")
        
        # Wait for some messages
        print("\n2. Waiting for WebSocket messages (10 seconds)...")
        time.sleep(10)
        
        # Check if we received price updates
        if bot.last_websocket_price:
            print(f"   ✅ Receiving price updates: ${bot.last_websocket_price:,.2f}")
        else:
            print("   ⚠️  No price updates received")
        
        # Check WebSocket state
        ws_state = exchange.getWebSocketState()
        print(f"\n3. WebSocket State: {ws_state}")
        print(f"   Connected: {exchange.isWebSocketConnected()}")
        
        # Disconnect
        print("\n4. Disconnecting WebSocket...")
        exchange.disconnectWebSocket()
        print("   ✅ Disconnected")
        
    else:
        print("   ❌ WebSocket connection failed!")
    
    print("\n✅ Grid Bot WebSocket integration test completed!")
    
    # Show summary
    print(f"\nSummary:")
    print(f"  WebSocket Support: {'✅ Working' if ws_connected else '❌ Failed'}")
    print(f"  Price Updates: {'✅ Received' if bot.last_websocket_price else '❌ Not received'}")
    print(f"  Ready for Trading: {'✅ Yes' if ws_connected else '❌ No (will use REST API)'}")


if __name__ == "__main__":
    main()