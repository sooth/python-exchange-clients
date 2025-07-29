#!/usr/bin/env python3
"""Run full BitUnix validation with trading tests - Fixed for minimum order size"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.validator import ExchangeValidator

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║              BitUnix Full Validation Test                  ║
║                                                           ║
║  Running all tests including trading with proper sizing    ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Create exchange
    exchange = BitUnixExchange()
    
    # Create validator with modified trading parameters
    validator = ExchangeValidator(exchange, test_symbol="BTCUSDT")
    
    # Modify the validator to handle minimum order size properly
    original_validate_trading = validator._validate_trading
    
    def validate_trading_with_proper_sizing():
        """Modified trading validation with proper minimum order sizing"""
        print("\n🔍 Validating Trading Methods...")
        
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
        # Calculate the minimum order value in USD
        min_btc_qty = 0.0001
        min_order_value = min_btc_qty * limit_price
        
        # Use the greater of $10 or minimum required
        if min_order_value > 10.0:
            print(f"   ⚠️  Minimum order value at current price: ${min_order_value:.2f}")
            print(f"   Using minimum BTC quantity: {min_btc_qty} BTC")
            quantity = min_btc_qty
        else:
            # Can use $10 worth
            quantity = round(10.0 / limit_price, 6)
            # Ensure we meet minimum
            if quantity < min_btc_qty:
                quantity = min_btc_qty
        
        print(f"   Order Details:")
        print(f"   - Limit Price: ${limit_price:.2f} (20% below market)")
        print(f"   - Quantity: {quantity} BTC")
        print(f"   - Order Value: ${quantity * limit_price:.2f}")
        
        # Import necessary classes
        from exchanges.base import ExchangeOrderRequest
        
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
        
        result = validator._test_async_method(
            "placeOrder",
            lambda cb: exchange.placeOrder(order_request, cb),
            validator._validate_place_order_response
        )
        validator.results.append(result)
        
        # If order placed successfully, test cancel
        if result.passed and validator.test_order_id:
            print(f"   ✅ Order placed successfully! Order ID: {validator.test_order_id}")
            time.sleep(2)  # Give order time to register
            
            # Test cancelOrder
            print(f"   Cancelling order...")
            result = validator._test_async_method(
                "cancelOrder",
                lambda cb: exchange.cancelOrder(
                    orderID=validator.test_order_id,
                    symbol="BTCUSDT",
                    completion=cb
                ),
                validator._validate_cancel_order_response
            )
            validator.results.append(result)
            
            if result.passed:
                print(f"   ✅ Order cancelled successfully!")
            else:
                print(f"   ❌ Failed to cancel order - please check manually!")
    
    # Replace the trading validation method
    validator._validate_trading = validate_trading_with_proper_sizing
    
    # Import time for timestamp
    import time
    
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