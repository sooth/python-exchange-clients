#!/usr/bin/env python3
"""Run full BitUnix validation with enhanced trading tests"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.validator import ExchangeValidator
from exchanges.base import ExchangeOrderRequest

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║              BitUnix Full Validation Test                  ║
║                                                           ║
║  Enhanced trading validation with order verification       ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Create exchange
    exchange = BitUnixExchange()
    
    # Create validator with modified trading parameters
    validator = ExchangeValidator(exchange, test_symbol="BTCUSDT")
    
    # Modify the validator to handle enhanced trading validation
    original_validate_trading = validator._validate_trading
    
    def validate_trading_enhanced():
        """Enhanced trading validation with order verification"""
        print("\n🔍 Validating Trading Methods (Enhanced)...")
        
        # Get current price first
        current_price = validator._get_current_price()
        if not current_price:
            validator.results.append(validator.ValidationResult(
                test_name="placeOrder",
                passed=False,
                message="Could not get current price for order placement",
                duration=0
            ))
            return
        
        print(f"   Current BTCUSDT Price: ${current_price:.2f}")
        
        # Calculate safe limit price (20% below market)
        limit_price = round(current_price * 0.8, 2)
        
        # BitUnix requires minimum 0.0001 BTC
        min_btc_qty = 0.0001
        min_order_value = min_btc_qty * limit_price
        
        # Use the greater of $10 or minimum required
        if min_order_value > 10.0:
            print(f"   ⚠️  Minimum order value at current price: ${min_order_value:.2f}")
            quantity = min_btc_qty
        else:
            # Can use $10 worth
            quantity = round(10.0 / limit_price, 6)
            # Ensure we meet minimum
            if quantity < min_btc_qty:
                quantity = min_btc_qty
        
        print(f"\n   📝 Order Details:")
        print(f"   - Limit Price: ${limit_price:.2f} (20% below market)")
        print(f"   - Quantity: {quantity} BTC")
        print(f"   - Order Value: ${quantity * limit_price:.2f}")
        
        # Test placeOrder with limit order
        order_request = ExchangeOrderRequest(
            symbol="BTCUSDT",
            side="BUY",
            orderType="LIMIT",
            qty=quantity,
            price=limit_price,
            orderLinkId=f"validator_test_{int(time.time())}",
            tradingType="PERP"
        )
        
        print(f"\n   📤 Placing order...")
        result = validator._test_async_method(
            "placeOrder",
            lambda cb: exchange.placeOrder(order_request, cb),
            validator._validate_place_order_response
        )
        validator.results.append(result)
        
        # If order placed successfully, verify and then cancel
        if result.passed and validator.test_order_id:
            print(f"   ✅ Order placed successfully!")
            print(f"   - Order ID: {validator.test_order_id}")
            if validator.test_client_order_id:
                print(f"   - Client Order ID: {validator.test_client_order_id}")
            
            # Wait a moment for order to be registered
            print(f"\n   ⏳ Waiting 2 seconds for order to register...")
            time.sleep(2)
            
            # Fetch open orders to verify our order exists
            print(f"\n   🔍 Verifying order exists in open orders...")
            verify_result = {"found": False, "completed": False}
            
            def verify_callback(status_data):
                status, data = status_data
                verify_result["completed"] = True
                if status == "success":
                    for order in data:
                        if order.orderId == validator.test_order_id:
                            verify_result["found"] = True
                            print(f"   ✅ Order found in open orders!")
                            print(f"      - Status: {order.status}")
                            print(f"      - Side: {order.side}")
                            print(f"      - Type: {order.orderType}")
                            print(f"      - Qty: {order.qty}")
                            print(f"      - Price: {order.price}")
                            break
            
            exchange.fetchOrders(verify_callback)
            
            # Wait for verification
            timeout = 5
            start_time = time.time()
            while not verify_result["completed"] and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if not verify_result["found"]:
                print(f"   ⚠️  Order not found in open orders - it may have been filled or rejected")
            
            # Test cancelOrder
            print(f"\n   ❌ Cancelling order...")
            cancel_result = validator._test_async_method(
                "cancelOrder",
                lambda cb: exchange.cancelOrder(
                    orderID=validator.test_order_id,
                    symbol="BTCUSDT",
                    completion=cb
                ),
                validator._validate_cancel_order_response
            )
            validator.results.append(cancel_result)
            
            if cancel_result.passed:
                print(f"   ✅ Order cancelled successfully!")
                
                # Verify order is no longer in open orders
                print(f"\n   🔍 Verifying order is cancelled...")
                time.sleep(1)
                
                verify_result2 = {"found": False, "completed": False}
                
                def verify_callback2(status_data):
                    status, data = status_data
                    verify_result2["completed"] = True
                    if status == "success":
                        for order in data:
                            if order.orderId == validator.test_order_id:
                                verify_result2["found"] = True
                                print(f"   ⚠️  Order still found with status: {order.status}")
                                break
                
                exchange.fetchOrders(verify_callback2)
                
                # Wait for verification
                start_time = time.time()
                while not verify_result2["completed"] and time.time() - start_time < timeout:
                    time.sleep(0.1)
                
                if not verify_result2["found"]:
                    print(f"   ✅ Confirmed: Order no longer in open orders")
                
            else:
                print(f"   ❌ Failed to cancel order")
                if cancel_result.error:
                    print(f"      Error: {cancel_result.error}")
        else:
            print(f"   ❌ Failed to place order")
            if result.error:
                print(f"      Error: {result.error}")
    
    # Replace the trading validation method
    validator._validate_trading = validate_trading_enhanced
    
    # Run validation
    results = validator.validate_all(
        include_trading=True,
        include_websocket=True
    )
    
    # Show detailed results
    print("\n" + "="*60)
    print("Detailed Test Results")
    print("="*60)
    
    for result in results["results"]:
        status = "✅" if result["passed"] else "❌"
        print(f"\n{status} {result['test']}:")
        print(f"   Duration: {result['duration']:.3f}s")
        if result.get("details"):
            print(f"   Details: {result['details']}")
        if result.get("error"):
            print(f"   Error: {result['error']}")
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"FINAL RESULT: {results['success_rate']:.1f}% Success Rate")
    print(f"{'='*60}")
    
    if results["success_rate"] == 100:
        print("\n🎉 ALL TESTS PASSED! BitUnix implementation is fully compliant.")
    else:
        print(f"\n⚠️  {results['failed']} test(s) failed. See details above.")
    
    return results


if __name__ == "__main__":
    main()