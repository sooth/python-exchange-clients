#!/usr/bin/env python3
"""Debug BitUnix WebSocket"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.base import WebSocketSubscription, WebSocketMessage, WebSocketState

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("=== BitUnix WebSocket Debug Test ===\n")
    
    exchange = BitUnixExchange()
    messages = []
    states = []
    
    def on_message(msg: WebSocketMessage):
        messages.append(msg)
        print(f"\n📨 MESSAGE: channel={msg.channel}, symbol={msg.symbol}")
        print(f"   Data: {msg.data}")
        print(f"   Raw: {msg.raw}")
    
    def on_state(state: WebSocketState):
        states.append(state)
        print(f"\n🔌 STATE: {state}")
    
    def on_error(error: Exception):
        print(f"\n❌ ERROR: {error}")
    
    # Test public WebSocket
    print("1. Testing PUBLIC WebSocket...")
    if exchange.connectWebSocket(on_message, on_state, on_error):
        print("   Connected!")
        time.sleep(3)
        
        # Check if we're using public or private
        ws_manager = exchange._ws_manager
        print(f"   Is Private: {ws_manager._is_private}")
        print(f"   Authenticated: {ws_manager._authenticated}")
        
        # Subscribe
        print("\n2. Subscribing to BTCUSDT ticker...")
        subs = [WebSocketSubscription(channel="ticker", symbol="BTCUSDT")]
        
        if exchange.subscribeWebSocket(subs):
            print("   Subscribed!")
            
            # Wait and show status
            print("\n3. Waiting for messages (10 seconds)...")
            for i in range(10):
                time.sleep(1)
                print(f"   {i+1}s: Messages={len(messages)}, State={exchange.getWebSocketState()}")
        
        # Show results
        print(f"\n4. Results:")
        print(f"   Total Messages: {len(messages)}")
        print(f"   States: {states}")
        
        # Disconnect
        exchange.disconnectWebSocket()
        print("\n5. Disconnected")
    else:
        print("   Failed to connect!")
    
    print("\nDebug test completed!")


if __name__ == "__main__":
    main()