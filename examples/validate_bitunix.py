#!/usr/bin/env python3
"""BitUnix Exchange Implementation Validator

This script validates that BitUnix properly implements all required
methods of the ExchangeInterface abstraction layer.
"""

import sys
import os
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange
from exchanges.validator import ExchangeValidator, validate_exchange


def main():
    """Run BitUnix validation tests"""
    parser = argparse.ArgumentParser(description="Validate BitUnix Exchange Implementation")
    parser.add_argument(
        "--symbol",
        default="BTCUSDT",
        help="Symbol to use for testing (default: BTCUSDT)"
    )
    parser.add_argument(
        "--include-trading",
        action="store_true",
        help="Include trading tests (will place real orders)"
    )
    parser.add_argument(
        "--skip-websocket",
        action="store_true",
        help="Skip WebSocket tests"
    )
    parser.add_argument(
        "--output",
        help="Output file for validation results (JSON format)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    
    args = parser.parse_args()
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║              BitUnix Exchange Validator                    ║
║                                                           ║
║  This tool validates the BitUnix implementation against   ║
║  the ExchangeInterface abstraction layer.                 ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Create exchange instance
    print("Initializing BitUnix exchange...")
    exchange = BitUnixExchange()
    
    # Create validator
    validator = ExchangeValidator(exchange, test_symbol=args.symbol)
    
    # Show test configuration
    print(f"\nTest Configuration:")
    print(f"  Exchange: {exchange.get_name()}")
    print(f"  Test Symbol: {args.symbol}")
    print(f"  Include Trading: {args.include_trading}")
    print(f"  Include WebSocket: {not args.skip_websocket}")
    
    if args.include_trading:
        print(f"\n⚠️  WARNING: Trading tests will place real orders on {args.symbol}!")
        print("  Orders will be placed far from market price but may still execute.")
        print("  Ensure you have a small balance for testing.")
    
    input("\nPress Enter to continue...")
    
    # Run validation
    results = validator.validate_all(
        include_trading=args.include_trading,
        include_websocket=not args.skip_websocket
    )
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # Show detailed results if verbose
    if args.verbose:
        print("\n" + "="*60)
        print("Detailed Results")
        print("="*60)
        
        for result in results["results"]:
            print(f"\nTest: {result['test']}")
            print(f"  Passed: {result['passed']}")
            print(f"  Duration: {result['duration']:.3f}s")
            if result['details']:
                print(f"  Details: {json.dumps(result['details'], indent=4)}")
            if result['error']:
                print(f"  Error: {result['error']}")
    
    # Show recommendations
    if results["failed"] > 0:
        print("\n" + "="*60)
        print("Recommendations")
        print("="*60)
        
        failed_tests = [r for r in results["results"] if not r["passed"]]
        
        for test in failed_tests:
            print(f"\n❌ {test['test']}:")
            
            # Provide specific recommendations
            if "API" in test.get("error", "") or "credentials" in test.get("error", ""):
                print("  → Check API keys in exchanges/utils/api_keys.json")
                print("  → Ensure API keys have required permissions")
            
            elif "WebSocket" in test["test"]:
                print("  → Check network connectivity")
                print("  → Verify WebSocket endpoints are accessible")
                print("  → Try running: wscat -c wss://fapi.bitunix.com/public/")
            
            elif "timeout" in test["message"].lower():
                print("  → Increase timeout duration")
                print("  → Check network latency")
                print("  → Verify API endpoint availability")
            
            else:
                print(f"  → Review implementation of {test['test']} method")
                print("  → Check error: {test.get('error', 'Unknown error')}")
    
    # Exit with appropriate code
    exit_code = 0 if results["success_rate"] == 100 else 1
    
    print(f"\nValidation {'PASSED' if exit_code == 0 else 'FAILED'}")
    sys.exit(exit_code)


def quick_test():
    """Run a quick validation test"""
    print("Running quick BitUnix validation...")
    
    exchange = BitUnixExchange()
    validator = ExchangeValidator(exchange, test_symbol="BTCUSDT")
    results = validator.validate_all(include_trading=False, include_websocket=True)
    
    print(f"\nQuick Test Results:")
    print(f"  Success Rate: {results['success_rate']:.1f}%")
    print(f"  Passed: {results['passed']}/{results['total_tests']}")
    
    return results


if __name__ == "__main__":
    # Check if running quick test
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_test()
    else:
        main()