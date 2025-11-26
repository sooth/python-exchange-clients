#!/usr/bin/env python3
"""Test Exchange Abstraction Layer

This script tests the exchange abstraction layer to ensure
all exchanges can be used interchangeably.
"""

import sys
import os
import time
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.base import ExchangeInterface, WebSocketSubscription
from exchanges.bitunix import BitUnixExchange


class AbstractionLayerTester:
    """Test that exchanges work through the abstraction layer"""
    
    def __init__(self, exchanges: List[ExchangeInterface]):
        self.exchanges = exchanges
        self.results = {}
    
    def test_all(self):
        """Run all abstraction layer tests"""
        print("="*60)
        print("Exchange Abstraction Layer Test")
        print("="*60)
        print(f"\nTesting {len(self.exchanges)} exchange(s)\n")
        
        for exchange in self.exchanges:
            print(f"\n{'='*40}")
            print(f"Testing: {exchange.get_name()}")
            print(f"{'='*40}")
            
            self.results[exchange.get_name()] = {
                "basic_info": self._test_basic_info(exchange),
                "market_data": self._test_market_data(exchange),
                "account_data": self._test_account_data(exchange),
                "websocket": self._test_websocket(exchange)
            }
        
        self._print_summary()
    
    def _test_basic_info(self, exchange: ExchangeInterface) -> Dict[str, Any]:
        """Test basic exchange information methods"""
        print("\n1. Basic Information:")
        
        results = {}
        
        # Test get_name
        try:
            name = exchange.get_name()
            print(f"   ✅ Exchange Name: {name}")
            results["get_name"] = {"passed": True, "value": name}
        except Exception as e:
            print(f"   ❌ get_name failed: {e}")
            results["get_name"] = {"passed": False, "error": str(e)}
        
        # Test symbol formatting
        try:
            formatted = exchange.get_symbol_format("BTCUSDT")
            print(f"   ✅ Symbol Format: BTCUSDT → {formatted}")
            results["symbol_format"] = {"passed": True, "value": formatted}
        except Exception as e:
            print(f"   ❌ get_symbol_format failed: {e}")
            results["symbol_format"] = {"passed": False, "error": str(e)}
        
        # Test side translation
        try:
            from exchanges.base import PositionSide
            
            # To exchange format
            buy_side = exchange.translate_side_to_exchange(PositionSide.LONG)
            sell_side = exchange.translate_side_to_exchange(PositionSide.SHORT)
            
            # From exchange format
            long_side = exchange.translate_side_from_exchange(buy_side)
            short_side = exchange.translate_side_from_exchange(sell_side)
            
            print(f"   ✅ Side Translation: LONG→{buy_side}→{long_side}, SHORT→{sell_side}→{short_side}")
            results["side_translation"] = {"passed": True, "values": {
                "long_to_buy": buy_side,
                "short_to_sell": sell_side,
                "buy_to_long": long_side,
                "sell_to_short": short_side
            }}
        except Exception as e:
            print(f"   ❌ Side translation failed: {e}")
            results["side_translation"] = {"passed": False, "error": str(e)}
        
        return results
    
    def _test_market_data(self, exchange: ExchangeInterface) -> Dict[str, Any]:
        """Test market data methods"""
        print("\n2. Market Data:")
        
        results = {}
        
        # Test fetchTickers
        print("   Testing fetchTickers...")
        ticker_result = self._test_async_method(
            exchange.fetchTickers,
            "fetchTickers"
        )
        results["fetchTickers"] = ticker_result
        
        if ticker_result["passed"] and ticker_result.get("data"):
            tickers = ticker_result["data"]
            print(f"   ✅ Received {len(tickers)} tickers")
            
            # Show sample ticker
            if tickers:
                sample = tickers[0]
                print(f"   Sample: {sample.symbol} - ${sample.lastPrice}")
        
        return results
    
    def _test_account_data(self, exchange: ExchangeInterface) -> Dict[str, Any]:
        """Test account data methods"""
        print("\n3. Account Data:")
        
        results = {}
        
        # Test fetchBalance
        print("   Testing fetchBalance...")
        balance_result = self._test_async_method(
            exchange.fetchBalance,
            "fetchBalance"
        )
        results["fetchBalance"] = balance_result
        
        if balance_result["passed"] and balance_result.get("data"):
            balances = balance_result["data"]
            print(f"   ✅ Received {len(balances)} balance(s)")
            
            # Show non-zero balances
            for balance in balances:
                if balance.balance > 0:
                    print(f"   {balance.asset}: {balance.balance:.4f}")
        
        # Test fetchPositions
        print("   Testing fetchPositions...")
        position_result = self._test_async_method(
            exchange.fetchPositions,
            "fetchPositions"
        )
        results["fetchPositions"] = position_result
        
        if position_result["passed"] and position_result.get("data"):
            positions = position_result["data"]
            print(f"   ✅ Received {len(positions)} position(s)")
            
            # Show open positions
            for position in positions:
                if position.size != 0:
                    print(f"   {position.symbol}: {position.size} @ ${position.entryPrice}")
        
        # Test fetchOrders
        print("   Testing fetchOrders...")
        order_result = self._test_async_method(
            exchange.fetchOrders,
            "fetchOrders"
        )
        results["fetchOrders"] = order_result
        
        if order_result["passed"] and order_result.get("data"):
            orders = order_result["data"]
            print(f"   ✅ Received {len(orders)} order(s)")
        
        return results
    
    def _test_websocket(self, exchange: ExchangeInterface) -> Dict[str, Any]:
        """Test WebSocket functionality"""
        print("\n4. WebSocket:")
        
        results = {}
        message_count = 0
        
        def on_message(msg):
            nonlocal message_count
            message_count += 1
        
        def on_state(state):
            print(f"   WebSocket state: {state}")
        
        def on_error(error):
            print(f"   WebSocket error: {error}")
        
        try:
            # Test connection
            print("   Connecting to WebSocket...")
            connected = exchange.connectWebSocket(on_message, on_state, on_error)
            
            if connected:
                time.sleep(2)
                
                # Test subscription
                subs = [WebSocketSubscription(channel="ticker", symbol="BTCUSDT")]
                subscribed = exchange.subscribeWebSocket(subs)
                
                if subscribed:
                    print("   ✅ WebSocket connected and subscribed")
                    
                    # Wait for messages
                    time.sleep(5)
                    
                    results["websocket"] = {
                        "passed": True,
                        "connected": True,
                        "messages_received": message_count
                    }
                    
                    print(f"   Received {message_count} messages in 5 seconds")
                else:
                    print("   ❌ Failed to subscribe")
                    results["websocket"] = {"passed": False, "error": "Subscription failed"}
                
                # Disconnect
                exchange.disconnectWebSocket()
            else:
                print("   ❌ Failed to connect")
                results["websocket"] = {"passed": False, "error": "Connection failed"}
        
        except Exception as e:
            print(f"   ❌ WebSocket test failed: {e}")
            results["websocket"] = {"passed": False, "error": str(e)}
        
        return results
    
    def _test_async_method(self, method, name: str) -> Dict[str, Any]:
        """Test an async method with callback"""
        result = {"completed": False, "status": None, "data": None}
        
        def callback(status_data):
            status, data = status_data
            result["completed"] = True
            result["status"] = status
            result["data"] = data
        
        try:
            method(callback)
            
            # Wait for completion
            timeout = 10
            start_time = time.time()
            while not result["completed"] and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if not result["completed"]:
                return {"passed": False, "error": "Timeout"}
            
            if result["status"] == "success":
                return {"passed": True, "data": result["data"]}
            else:
                return {"passed": False, "error": str(result["data"])}
        
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        
        for exchange_name, results in self.results.items():
            print(f"\n{exchange_name}:")
            
            total_tests = 0
            passed_tests = 0
            
            for category, tests in results.items():
                print(f"\n  {category.replace('_', ' ').title()}:")
                
                if isinstance(tests, dict):
                    for test_name, test_result in tests.items():
                        total_tests += 1
                        
                        if isinstance(test_result, dict) and test_result.get("passed"):
                            print(f"    ✅ {test_name}")
                            passed_tests += 1
                        else:
                            error = test_result.get("error", "Unknown error") if isinstance(test_result, dict) else "Failed"
                            print(f"    ❌ {test_name}: {error}")
            
            success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            print(f"\n  Overall: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")


def main():
    """Main test function"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║          Exchange Abstraction Layer Tester                 ║
║                                                           ║
║  This tests that exchanges work correctly through the     ║
║  unified abstraction layer interface.                     ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Create list of exchanges to test
    exchanges = [
        BitUnixExchange()
        # Add more exchanges here as they implement the interface
        # LMEXExchange(),
        # BinanceExchange(),
    ]
    
    # Run tests
    tester = AbstractionLayerTester(exchanges)
    tester.test_all()
    
    print("\n✅ Abstraction layer test completed!")
    print("\nThe abstraction layer allows you to:")
    print("- Switch between exchanges with minimal code changes")
    print("- Use a consistent interface for all operations")
    print("- Build exchange-agnostic trading strategies")
    print("- Test strategies across multiple exchanges")


if __name__ == "__main__":
    main()