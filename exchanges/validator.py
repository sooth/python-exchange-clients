"""Exchange Implementation Validator

This module provides comprehensive validation testing for exchange implementations
to ensure they properly implement the ExchangeInterface abstraction layer.
"""

import time
import json
from typing import Dict, List, Any, Tuple, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from .base import (
    ExchangeInterface, ExchangeOrderRequest, ExchangeOrderResponse,
    ExchangeTicker, ExchangeBalance, ExchangePosition, ExchangeOrder,
    WebSocketSubscription, WebSocketMessage, WebSocketState,
    PositionSide, TradingType
)


@dataclass
class ValidationResult:
    """Result of a validation test"""
    test_name: str
    passed: bool
    message: str
    duration: float
    error: Optional[Exception] = None
    details: Optional[Dict[str, Any]] = None


class ExchangeValidator:
    """
    Comprehensive validator for exchange implementations.
    
    Tests all required methods of the ExchangeInterface to ensure
    proper implementation and functionality.
    """
    
    def __init__(self, exchange: ExchangeInterface, test_symbol: str = "BTCUSDT"):
        """
        Initialize validator.
        
        Args:
            exchange: Exchange instance to validate
            test_symbol: Symbol to use for testing (should be liquid)
        """
        self.exchange = exchange
        self.test_symbol = test_symbol
        self.results: List[ValidationResult] = []
        self.test_order_id: Optional[str] = None
        self.test_client_order_id: Optional[str] = None
    
    def validate_all(self, include_trading: bool = False, include_websocket: bool = True) -> Dict[str, Any]:
        """
        Run all validation tests.
        
        Args:
            include_trading: Whether to include tests that place real orders
            include_websocket: Whether to include WebSocket tests
            
        Returns:
            Summary of validation results
        """
        print(f"\n{'='*60}")
        print(f"Validating {self.exchange.get_name()} Exchange Implementation")
        print(f"{'='*60}\n")
        
        # Basic interface tests
        self._validate_basic_interface()
        
        # Market data tests
        self._validate_market_data()
        
        # Account data tests
        self._validate_account_data()
        
        # Trading tests (optional)
        if include_trading:
            self._validate_trading()
        
        # WebSocket tests (optional)
        if include_websocket:
            self._validate_websocket()
        
        # Generate summary
        return self._generate_summary()
    
    def _validate_basic_interface(self):
        """Validate basic interface methods"""
        print("🔍 Validating Basic Interface Methods...")
        
        # Test get_name
        result = self._test_method(
            "get_name",
            lambda: self.exchange.get_name(),
            lambda name: isinstance(name, str) and len(name) > 0
        )
        self.results.append(result)
        
        # Test get_symbol_format
        result = self._test_method(
            "get_symbol_format",
            lambda: self.exchange.get_symbol_format("BTCUSDT"),
            lambda symbol: isinstance(symbol, str) and len(symbol) > 0
        )
        self.results.append(result)
        
        # Test translate_side_to_exchange
        result = self._test_method(
            "translate_side_to_exchange",
            lambda: self.exchange.translate_side_to_exchange(PositionSide.LONG),
            lambda side: side in ["BUY", "LONG", "Buy", "buy"]
        )
        self.results.append(result)
        
        # Test translate_side_from_exchange
        result = self._test_method(
            "translate_side_from_exchange",
            lambda: self.exchange.translate_side_from_exchange("BUY"),
            lambda side: side == PositionSide.LONG
        )
        self.results.append(result)
    
    def _validate_market_data(self):
        """Validate market data methods"""
        print("\n🔍 Validating Market Data Methods...")
        
        # Test fetchTickers
        result = self._test_async_method(
            "fetchTickers",
            self.exchange.fetchTickers,
            self._validate_tickers_response
        )
        self.results.append(result)
        
        # Test fetchSymbolInfo
        result = self._test_async_method(
            "fetchSymbolInfo",
            lambda cb: self.exchange.fetchSymbolInfo(self.test_symbol, cb),
            self._validate_symbol_info_response
        )
        self.results.append(result)
    
    def _validate_account_data(self):
        """Validate account data methods"""
        print("\n🔍 Validating Account Data Methods...")
        
        # Test fetchBalance
        result = self._test_async_method(
            "fetchBalance",
            self.exchange.fetchBalance,
            self._validate_balance_response
        )
        self.results.append(result)
        
        # Test fetchPositions
        result = self._test_async_method(
            "fetchPositions",
            self.exchange.fetchPositions,
            self._validate_positions_response
        )
        self.results.append(result)
        
        # Test fetchOrders
        result = self._test_async_method(
            "fetchOrders",
            self.exchange.fetchOrders,
            self._validate_orders_response
        )
        self.results.append(result)
        
        # Test fetchAccountEquity
        result = self._test_async_method(
            "fetchAccountEquity",
            self.exchange.fetchAccountEquity,
            self._validate_account_equity_response
        )
        self.results.append(result)
    
    def _validate_trading(self):
        """Validate trading methods"""
        print("\n🔍 Validating Trading Methods...")
        
        # Get current price first
        current_price = self._get_current_price()
        if not current_price:
            self.results.append(ValidationResult(
                test_name="placeOrder",
                passed=False,
                message="Could not get current price for order placement",
                duration=0
            ))
            return
        
        # Calculate safe limit price (far from market)
        limit_price = round(current_price * 0.8, 2)  # 20% below market
        
        # Test placeOrder with limit order
        order_request = ExchangeOrderRequest(
            symbol=self.test_symbol,
            side="BUY",
            orderType="LIMIT",
            qty=0.001,  # Small quantity
            price=limit_price,
            orderLinkId=f"validator_test_{int(time.time())}",
            tradingType="PERP"
        )
        
        result = self._test_async_method(
            "placeOrder",
            lambda cb: self.exchange.placeOrder(order_request, cb),
            self._validate_place_order_response
        )
        self.results.append(result)
        
        # If order placed successfully, test cancel
        if result.passed and self.test_order_id:
            time.sleep(1)  # Give order time to register
            
            # Test cancelOrder
            result = self._test_async_method(
                "cancelOrder",
                lambda cb: self.exchange.cancelOrder(
                    orderID=self.test_order_id,
                    symbol=self.test_symbol,
                    completion=cb
                ),
                self._validate_cancel_order_response
            )
            self.results.append(result)
    
    def _validate_websocket(self):
        """Validate WebSocket methods"""
        print("\n🔍 Validating WebSocket Methods...")
        
        ws_connected = False
        messages_received = 0
        
        def on_message(msg: WebSocketMessage):
            nonlocal messages_received
            messages_received += 1
        
        def on_state(state: WebSocketState):
            nonlocal ws_connected
            if state == WebSocketState.CONNECTED or state == WebSocketState.AUTHENTICATED:
                ws_connected = True
        
        def on_error(error: Exception):
            pass
        
        # Test connectWebSocket
        start_time = time.time()
        try:
            success = self.exchange.connectWebSocket(on_message, on_state, on_error)
            duration = time.time() - start_time
            
            if success:
                # Wait for connection
                time.sleep(3)
                
                # Test isWebSocketConnected
                is_connected = self.exchange.isWebSocketConnected()
                
                # Test getWebSocketState
                state = self.exchange.getWebSocketState()
                
                result = ValidationResult(
                    test_name="connectWebSocket",
                    passed=success and is_connected and ws_connected,
                    message=f"Connected: {success}, State: {state}",
                    duration=duration,
                    details={"state": str(state), "is_connected": is_connected}
                )
            else:
                result = ValidationResult(
                    test_name="connectWebSocket",
                    passed=False,
                    message="Failed to connect",
                    duration=duration
                )
            
            self.results.append(result)
            
            if success:
                # Test subscribeWebSocket
                subscriptions = [
                    WebSocketSubscription(channel="ticker", symbol=self.test_symbol)
                ]
                
                sub_result = self._test_method(
                    "subscribeWebSocket",
                    lambda: self.exchange.subscribeWebSocket(subscriptions),
                    lambda result: result is True
                )
                self.results.append(sub_result)
                
                # Wait for messages
                time.sleep(5)
                
                # Validate messages received
                msg_result = ValidationResult(
                    test_name="WebSocket message flow",
                    passed=messages_received > 0,
                    message=f"Received {messages_received} messages",
                    duration=5.0,
                    details={"message_count": messages_received}
                )
                self.results.append(msg_result)
                
                # Test unsubscribeWebSocket
                unsub_result = self._test_method(
                    "unsubscribeWebSocket",
                    lambda: self.exchange.unsubscribeWebSocket(subscriptions),
                    lambda result: result is True
                )
                self.results.append(unsub_result)
                
                # Test disconnectWebSocket
                disc_result = self._test_method(
                    "disconnectWebSocket",
                    lambda: self.exchange.disconnectWebSocket(),
                    lambda _: True  # Void method returns None
                )
                self.results.append(disc_result)
        
        except Exception as e:
            result = ValidationResult(
                test_name="connectWebSocket",
                passed=False,
                message=f"Exception: {str(e)}",
                duration=time.time() - start_time,
                error=e
            )
            self.results.append(result)
    
    def _test_method(self, name: str, method: Callable, validator: Callable[[Any], bool]) -> ValidationResult:
        """Test a synchronous method"""
        start_time = time.time()
        
        try:
            result = method()
            duration = time.time() - start_time
            
            if validator(result):
                return ValidationResult(
                    test_name=name,
                    passed=True,
                    message=f"✅ Returned: {result}",
                    duration=duration,
                    details={"result": result}
                )
            else:
                return ValidationResult(
                    test_name=name,
                    passed=False,
                    message=f"❌ Invalid result: {result}",
                    duration=duration,
                    details={"result": result}
                )
        
        except Exception as e:
            return ValidationResult(
                test_name=name,
                passed=False,
                message=f"❌ Exception: {str(e)}",
                duration=time.time() - start_time,
                error=e
            )
    
    def _test_async_method(self, name: str, method: Callable, validator: Callable) -> ValidationResult:
        """Test an asynchronous method with callback"""
        start_time = time.time()
        result_data = {"completed": False, "status": None, "data": None}
        
        def callback(status_data: Tuple[str, Any]):
            status, data = status_data
            result_data["completed"] = True
            result_data["status"] = status
            result_data["data"] = data
        
        try:
            method(callback)
            
            # Wait for completion
            timeout = 10
            while not result_data["completed"] and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            duration = time.time() - start_time
            
            if not result_data["completed"]:
                return ValidationResult(
                    test_name=name,
                    passed=False,
                    message="❌ Timeout waiting for response",
                    duration=duration
                )
            
            if result_data["status"] == "success":
                if validator(result_data["data"]):
                    return ValidationResult(
                        test_name=name,
                        passed=True,
                        message=f"✅ Success",
                        duration=duration,
                        details={"data_type": type(result_data["data"]).__name__}
                    )
                else:
                    return ValidationResult(
                        test_name=name,
                        passed=False,
                        message=f"❌ Invalid response data",
                        duration=duration,
                        details={"data": str(result_data["data"])[:100]}
                    )
            else:
                return ValidationResult(
                    test_name=name,
                    passed=False,
                    message=f"❌ Failed: {result_data['data']}",
                    duration=duration,
                    error=result_data["data"] if isinstance(result_data["data"], Exception) else None
                )
        
        except Exception as e:
            return ValidationResult(
                test_name=name,
                passed=False,
                message=f"❌ Exception: {str(e)}",
                duration=time.time() - start_time,
                error=e
            )
    
    def _validate_tickers_response(self, data: Any) -> bool:
        """Validate fetchTickers response"""
        if not isinstance(data, list):
            return False
        
        if len(data) == 0:
            return False
        
        # Check first ticker
        ticker = data[0]
        required_attrs = ['symbol', 'lastPrice', 'bidPrice', 'askPrice', 'volume']
        
        for attr in required_attrs:
            if not hasattr(ticker, attr):
                return False
        
        # Find test symbol
        for t in data:
            if t.symbol == self.test_symbol:
                return True
        
        return True  # Even if test symbol not found, format is correct
    
    def _validate_symbol_info_response(self, data: Any) -> bool:
        """Validate fetchSymbolInfo response"""
        return isinstance(data, dict) and len(data) > 0
    
    def _validate_balance_response(self, data: Any) -> bool:
        """Validate fetchBalance response"""
        if not isinstance(data, list):
            return False
        
        if len(data) == 0:
            return True  # Empty balance is valid
        
        # Check first balance
        balance = data[0]
        required_attrs = ['asset', 'balance', 'available', 'locked']
        
        for attr in required_attrs:
            if not hasattr(balance, attr):
                return False
        
        return True
    
    def _validate_positions_response(self, data: Any) -> bool:
        """Validate fetchPositions response"""
        if not isinstance(data, list):
            return False
        
        # Empty positions is valid
        if len(data) == 0:
            return True
        
        # Check first position
        position = data[0]
        required_attrs = ['symbol', 'size', 'entryPrice', 'markPrice', 'pnl']
        
        for attr in required_attrs:
            if not hasattr(position, attr):
                return False
        
        return True
    
    def _validate_orders_response(self, data: Any) -> bool:
        """Validate fetchOrders response"""
        if not isinstance(data, list):
            return False
        
        # Empty orders is valid
        if len(data) == 0:
            return True
        
        # Check first order
        order = data[0]
        required_attrs = ['orderId', 'symbol', 'side', 'orderType', 'qty', 'status']
        
        for attr in required_attrs:
            if not hasattr(order, attr):
                return False
        
        return True
    
    def _validate_account_equity_response(self, data: Any) -> bool:
        """Validate fetchAccountEquity response"""
        return isinstance(data, (int, float)) and data >= 0
    
    def _validate_place_order_response(self, data: Any) -> bool:
        """Validate placeOrder response"""
        if not isinstance(data, ExchangeOrderResponse):
            return False
        
        required_attrs = ['orderId', 'symbol', 'side', 'orderType', 'qty', 'status']
        
        for attr in required_attrs:
            if not hasattr(data, attr):
                return False
        
        # Store order ID for cancel test
        self.test_order_id = data.orderId
        self.test_client_order_id = data.clientId
        
        return True
    
    def _validate_cancel_order_response(self, data: Any) -> bool:
        """Validate cancelOrder response"""
        # Success response varies by exchange
        return True
    
    def _get_current_price(self) -> Optional[float]:
        """Get current price for test symbol"""
        result = {"price": None, "completed": False}
        
        def callback(status_data):
            status, data = status_data
            result["completed"] = True
            if status == "success":
                for ticker in data:
                    if ticker.symbol == self.test_symbol:
                        result["price"] = ticker.lastPrice
                        break
        
        self.exchange.fetchTickers(callback)
        
        timeout = 5
        start_time = time.time()
        while not result["completed"] and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        return result["price"]
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate validation summary"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        print(f"\n{'='*60}")
        print(f"Validation Summary for {self.exchange.get_name()}")
        print(f"{'='*60}\n")
        
        # Group results by category
        categories = {
            "Basic Interface": ["get_name", "get_symbol_format", "translate_side_to_exchange", "translate_side_from_exchange"],
            "Market Data": ["fetchTickers", "fetchSymbolInfo"],
            "Account Data": ["fetchBalance", "fetchPositions", "fetchOrders", "fetchAccountEquity"],
            "Trading": ["placeOrder", "cancelOrder"],
            "WebSocket": ["connectWebSocket", "subscribeWebSocket", "WebSocket message flow", "unsubscribeWebSocket", "disconnectWebSocket"]
        }
        
        for category, tests in categories.items():
            category_results = [r for r in self.results if r.test_name in tests]
            if category_results:
                print(f"\n{category}:")
                for result in category_results:
                    status = "✅" if result.passed else "❌"
                    print(f"  {status} {result.test_name}: {result.message}")
                    if result.error:
                        print(f"     Error: {type(result.error).__name__}: {str(result.error)}")
        
        # Overall summary
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"{'='*60}\n")
        
        # Return summary data
        return {
            "exchange": self.exchange.get_name(),
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": success_rate,
            "results": [
                {
                    "test": r.test_name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration": r.duration,
                    "error": str(r.error) if r.error else None,
                    "details": r.details
                }
                for r in self.results
            ],
            "timestamp": datetime.now().isoformat()
        }


def validate_exchange(exchange: ExchangeInterface, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to validate an exchange implementation.
    
    Args:
        exchange: Exchange instance to validate
        **kwargs: Additional arguments for validator
        
    Returns:
        Validation summary
    """
    validator = ExchangeValidator(exchange, **kwargs)
    return validator.validate_all(**kwargs)