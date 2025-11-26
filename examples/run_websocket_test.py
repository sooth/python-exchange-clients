#!/usr/bin/env python3
"""Quick WebSocket Test Runner"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.base import WebSocketSubscription, WebSocketMessage, WebSocketState


def main():
    """Quick test to verify WebSocket is working"""
    print("=== BitUnix WebSocket Quick Test ===\n")
    
    exchange = BitUnixExchange()
    message_count = 0
    
    def on_message(msg: WebSocketMessage):
        nonlocal message_count
        message_count += 1
        if msg.channel == "ticker":
            print(f"\r✅ WebSocket Working! Price: ${msg.data.lastPrice:.2f} | Messages: {message_count}", end="", flush=True)
    
    def on_state(state: WebSocketState):
        print(f"\n🔌 State: {state}")
    
    def on_error(error: Exception):
        print(f"\n❌ Error: {error}")
    
    print("Connecting to WebSocket...")
    if exchange.connectWebSocket(on_message, on_state, on_error):
        time.sleep(2)
        
        print("Subscribing to BTCUSDT ticker...")
        subs = [WebSocketSubscription(channel="ticker", symbol="BTCUSDT")]
        
        if exchange.subscribeWebSocket(subs):
            print("✅ Subscribed! Receiving real-time data...\n")
            
            # Run for 10 seconds
            for i in range(10):
                time.sleep(1)
            
            print(f"\n\n✅ Success! Received {message_count} messages")
            print("WebSocket implementation is working correctly!")
        else:
            print("❌ Failed to subscribe")
    else:
        print("❌ Failed to connect")
    
    exchange.disconnectWebSocket()
    print("\nTest completed!")


if __name__ == "__main__":
    main()