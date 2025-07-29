#!/usr/bin/env python3
"""Test BitUnix WebSocket Implementation"""

import sys
import os
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.base import WebSocketSubscription, WebSocketMessage, WebSocketState


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebSocketTester:
    """Test harness for BitUnix WebSocket functionality"""
    
    def __init__(self):
        self.exchange = BitUnixExchange()
        self.message_count = 0
        self.start_time = time.time()
        self.last_ticker_time = 0
        self.last_order_time = 0
        self.last_position_time = 0
        
    def on_message(self, message: WebSocketMessage):
        """Handle WebSocket messages"""
        self.message_count += 1
        current_time = time.time()
        
        if message.channel == "ticker":
            self.last_ticker_time = current_time
            ticker = message.data
            print(f"\n📈 Ticker Update - {message.symbol}")
            print(f"   Last Price: ${ticker.lastPrice:.2f}")
            print(f"   Bid: ${ticker.bidPrice:.2f} | Ask: ${ticker.askPrice:.2f}")
            print(f"   Volume: {ticker.volume:,.2f}")
            
        elif message.channel == "orderbook":
            print(f"\n📊 Order Book Update - {message.symbol}")
            orderbook = message.data
            print(f"   Bids: {len(orderbook['bids'])} levels")
            print(f"   Asks: {len(orderbook['asks'])} levels")
            if orderbook['bids']:
                print(f"   Best Bid: ${orderbook['bids'][0][0]:.2f} x {orderbook['bids'][0][1]}")
            if orderbook['asks']:
                print(f"   Best Ask: ${orderbook['asks'][0][0]:.2f} x {orderbook['asks'][0][1]}")
                
        elif message.channel == "trades":
            print(f"\n💱 Trade Update - {message.symbol}")
            trades = message.data
            for trade in trades[:3]:  # Show first 3 trades
                print(f"   {trade['side']} {trade['quantity']} @ ${trade['price']:.2f}")
                
        elif message.channel == "order":
            self.last_order_time = current_time
            order = message.data
            print(f"\n📋 Order Update")
            print(f"   Symbol: {order.symbol}")
            print(f"   Order ID: {order.orderId}")
            print(f"   Side: {order.side} | Type: {order.orderType}")
            print(f"   Quantity: {order.qty} @ ${order.price or 'MARKET'}")
            print(f"   Status: {order.status}")
            
        elif message.channel == "position":
            self.last_position_time = current_time
            position = message.data
            print(f"\n💼 Position Update - {message.symbol}")
            print(f"   Size: {position.size}")
            print(f"   Entry: ${position.entryPrice:.2f}")
            print(f"   Mark: ${position.markPrice:.2f}")
            print(f"   PnL: ${position.pnl:.2f} ({position.pnlPercentage:.2f}%)")
            
        elif message.channel == "balance":
            print(f"\n💰 Balance Update")
            balances = message.data
            for balance in balances:
                if balance.balance > 0:
                    print(f"   {balance.asset}: {balance.balance:.4f} (Available: {balance.available:.4f})")
    
    def on_state_change(self, state: WebSocketState):
        """Handle WebSocket state changes"""
        print(f"\n🔌 WebSocket State: {state}")
        
    def on_error(self, error: Exception):
        """Handle WebSocket errors"""
        print(f"\n❌ WebSocket Error: {error}")
    
    def run_public_test(self):
        """Test public WebSocket channels"""
        print("\n" + "="*60)
        print("🧪 Testing PUBLIC WebSocket Channels")
        print("="*60)
        
        # Connect to public WebSocket
        print("\nConnecting to public WebSocket...")
        if not self.exchange.connectWebSocket(
            on_message=self.on_message,
            on_state_change=self.on_state_change,
            on_error=self.on_error
        ):
            print("❌ Failed to connect to WebSocket")
            return False
        
        # Wait for connection
        time.sleep(3)
        
        # Subscribe to public channels
        print("\nSubscribing to public channels...")
        subscriptions = [
            WebSocketSubscription(channel="ticker", symbol="BTCUSDT"),
            WebSocketSubscription(channel="ticker", symbol="ETHUSDT"),
            WebSocketSubscription(channel="orderbook", symbol="BTCUSDT", params={"depth": 5}),
            WebSocketSubscription(channel="trades", symbol="BTCUSDT")
        ]
        
        if not self.exchange.subscribeWebSocket(subscriptions):
            print("❌ Failed to subscribe to channels")
            return False
        
        print("✅ Subscribed successfully!")
        
        # Monitor for 30 seconds
        print(f"\nMonitoring for 30 seconds...")
        start_time = time.time()
        
        while time.time() - start_time < 30:
            elapsed = time.time() - start_time
            status = f"\r⏱️  Elapsed: {elapsed:.1f}s | Messages: {self.message_count}"
            
            # Check data freshness
            current_time = time.time()
            if self.last_ticker_time > 0:
                ticker_age = current_time - self.last_ticker_time
                status += f" | Last ticker: {ticker_age:.1f}s ago"
            
            print(status, end="", flush=True)
            time.sleep(0.1)
        
        print("\n\n✅ Public channel test completed!")
        print(f"Total messages received: {self.message_count}")
        
        # Disconnect
        print("\nDisconnecting...")
        self.exchange.disconnectWebSocket()
        time.sleep(2)
        
        return True
    
    def run_private_test(self):
        """Test private WebSocket channels (requires API keys)"""
        print("\n" + "="*60)
        print("🧪 Testing PRIVATE WebSocket Channels")
        print("="*60)
        
        # Reset counters
        self.message_count = 0
        self.last_order_time = 0
        self.last_position_time = 0
        
        # Connect to WebSocket (will use private if API keys available)
        print("\nConnecting to WebSocket with authentication...")
        if not self.exchange.connectWebSocket(
            on_message=self.on_message,
            on_state_change=self.on_state_change,
            on_error=self.on_error
        ):
            print("❌ Failed to connect to WebSocket")
            return False
        
        # Wait for authentication
        time.sleep(5)
        
        # Check if authenticated
        state = self.exchange.getWebSocketState()
        if state != WebSocketState.AUTHENTICATED:
            print(f"⚠️  Not authenticated. State: {state}")
            print("Make sure API keys are configured in exchanges/utils/api_keys.json")
            self.exchange.disconnectWebSocket()
            return False
        
        # Subscribe to private channels
        print("\nSubscribing to private channels...")
        subscriptions = [
            WebSocketSubscription(channel="orders"),
            WebSocketSubscription(channel="positions"),
            WebSocketSubscription(channel="balance"),
            WebSocketSubscription(channel="ticker", symbol="BTCUSDT")  # Also get ticker
        ]
        
        if not self.exchange.subscribeWebSocket(subscriptions):
            print("❌ Failed to subscribe to channels")
            return False
        
        print("✅ Subscribed successfully!")
        
        # Monitor for 60 seconds
        print(f"\nMonitoring for 60 seconds...")
        print("Place an order or make a trade to see real-time updates!")
        start_time = time.time()
        
        while time.time() - start_time < 60:
            elapsed = time.time() - start_time
            status = f"\r⏱️  Elapsed: {elapsed:.1f}s | Messages: {self.message_count}"
            
            # Check data freshness
            current_time = time.time()
            if self.last_order_time > 0:
                order_age = current_time - self.last_order_time
                status += f" | Last order: {order_age:.1f}s ago"
            if self.last_position_time > 0:
                position_age = current_time - self.last_position_time
                status += f" | Last position: {position_age:.1f}s ago"
            
            print(status, end="", flush=True)
            time.sleep(0.1)
        
        print("\n\n✅ Private channel test completed!")
        print(f"Total messages received: {self.message_count}")
        
        # Disconnect
        print("\nDisconnecting...")
        self.exchange.disconnectWebSocket()
        time.sleep(2)
        
        return True
    
    def run_reconnection_test(self):
        """Test WebSocket reconnection"""
        print("\n" + "="*60)
        print("🧪 Testing WebSocket Reconnection")
        print("="*60)
        
        # Connect
        print("\nConnecting to WebSocket...")
        if not self.exchange.connectWebSocket(
            on_message=self.on_message,
            on_state_change=self.on_state_change,
            on_error=self.on_error
        ):
            print("❌ Failed to connect to WebSocket")
            return False
        
        # Subscribe
        time.sleep(3)
        subscriptions = [WebSocketSubscription(channel="ticker", symbol="BTCUSDT")]
        self.exchange.subscribeWebSocket(subscriptions)
        
        print("✅ Connected and subscribed")
        print("\nWebSocket should automatically reconnect if connection is lost")
        print("Try disconnecting your network to test reconnection...")
        print("Monitoring for 120 seconds...\n")
        
        start_time = time.time()
        last_state = self.exchange.getWebSocketState()
        
        while time.time() - start_time < 120:
            current_state = self.exchange.getWebSocketState()
            if current_state != last_state:
                print(f"\n🔄 State changed: {last_state} → {current_state}")
                last_state = current_state
            
            elapsed = time.time() - start_time
            print(f"\r⏱️  Elapsed: {elapsed:.1f}s | State: {current_state} | Messages: {self.message_count}", end="", flush=True)
            time.sleep(0.5)
        
        print("\n\n✅ Reconnection test completed!")
        
        # Disconnect
        self.exchange.disconnectWebSocket()
        return True


def main():
    """Run WebSocket tests"""
    print("=" * 60)
    print("BitUnix WebSocket Test Suite")
    print("=" * 60)
    
    tester = WebSocketTester()
    
    # Test menu
    while True:
        print("\nSelect test to run:")
        print("1. Test PUBLIC channels (ticker, orderbook, trades)")
        print("2. Test PRIVATE channels (orders, positions, balance)")
        print("3. Test reconnection handling")
        print("4. Run all tests")
        print("0. Exit")
        
        choice = input("\nEnter choice (0-4): ").strip()
        
        if choice == "0":
            print("Exiting...")
            break
        elif choice == "1":
            tester.run_public_test()
        elif choice == "2":
            tester.run_private_test()
        elif choice == "3":
            tester.run_reconnection_test()
        elif choice == "4":
            tester.run_public_test()
            tester.run_private_test()
            tester.run_reconnection_test()
        else:
            print("Invalid choice!")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    main()