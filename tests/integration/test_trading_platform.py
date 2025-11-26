#!/usr/bin/env python3
"""
Test script to verify the unified exchange trading platform is working
"""
import asyncio
import httpx
import websockets
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"
WS_URL = "ws://localhost:8000/api/v1/ws/connect"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
NC = '\033[0m'

def print_test(name: str, passed: bool, message: str = ""):
    status = f"{GREEN}✓ PASSED{NC}" if passed else f"{RED}✗ FAILED{NC}"
    print(f"  {name}: {status}")
    if message and not passed:
        print(f"    {message}")

async def test_api_endpoints():
    """Test REST API endpoints"""
    print(f"\n{YELLOW}Testing REST API Endpoints...{NC}")
    
    async with httpx.AsyncClient() as client:
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Root endpoint
        tests_total += 1
        try:
            response = await client.get(BASE_URL)
            passed = response.status_code == 200
            if passed:
                tests_passed += 1
            print_test("Root endpoint", passed, f"Status: {response.status_code}")
        except Exception as e:
            print_test("Root endpoint", False, str(e))
        
        # Test 2: Health check
        tests_total += 1
        try:
            response = await client.get(f"{BASE_URL}/health")
            passed = response.status_code == 200
            if passed:
                tests_passed += 1
            print_test("Health check", passed)
        except Exception as e:
            print_test("Health check", False, str(e))
        
        # Test 3: Get exchanges
        tests_total += 1
        try:
            response = await client.get(f"{API_URL}/market/exchanges")
            passed = response.status_code == 200 and len(response.json()) > 0
            if passed:
                tests_passed += 1
                exchanges = response.json()
                print_test("Get exchanges", passed)
                print(f"    Available exchanges: {', '.join(exchanges)}")
        except Exception as e:
            print_test("Get exchanges", False, str(e))
        
        # Test 4: Get tickers
        tests_total += 1
        try:
            response = await client.get(f"{API_URL}/market/tickers?exchange=bitunix")
            passed = response.status_code == 200
            if passed:
                tests_passed += 1
                tickers = response.json()
                print_test("Get tickers", passed)
                print(f"    Found {len(tickers)} trading pairs")
        except Exception as e:
            print_test("Get tickers", False, str(e))
        
        # Test 5: API Documentation
        tests_total += 1
        try:
            response = await client.get(f"{API_URL}/docs")
            passed = response.status_code == 200
            if passed:
                tests_passed += 1
            print_test("API documentation", passed)
        except Exception as e:
            print_test("API documentation", False, str(e))
        
        print(f"\nAPI Tests: {tests_passed}/{tests_total} passed")
        return tests_passed == tests_total

async def test_websocket():
    """Test WebSocket connection"""
    print(f"\n{YELLOW}Testing WebSocket Connection...{NC}")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print_test("WebSocket connection", True)
            
            # Test subscription
            subscription = {
                "type": "subscribe",
                "channel": "ticker",
                "symbols": ["BTCUSDT"]
            }
            
            await websocket.send(json.dumps(subscription))
            print_test("Send subscription", True)
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            message = json.loads(response)
            
            received_message = message.get('type') in ['info', 'ticker']
            print_test("Receive message", received_message)
            
            if received_message:
                print(f"    Message type: {message.get('type')}")
            
            return True
    except Exception as e:
        print_test("WebSocket connection", False, str(e))
        return False

async def test_system_integration():
    """Test system integration"""
    print(f"\n{YELLOW}Testing System Integration...{NC}")
    
    # Give services time to start
    print("  Waiting for services to initialize...")
    await asyncio.sleep(2)
    
    # Test backend availability
    backend_ok = await test_api_endpoints()
    
    # Test WebSocket
    ws_ok = await test_websocket()
    
    # Summary
    print(f"\n{YELLOW}========================================{NC}")
    print(f"{YELLOW}Test Summary{NC}")
    print(f"{YELLOW}========================================{NC}")
    
    all_passed = backend_ok and ws_ok
    
    if all_passed:
        print(f"{GREEN}✓ All tests passed!{NC}")
        print(f"\nThe trading platform is ready to use:")
        print(f"  - Backend API: http://localhost:8000")
        print(f"  - API Docs: http://localhost:8000/api/v1/docs")
        print(f"  - Frontend: http://localhost:3000")
    else:
        print(f"{RED}✗ Some tests failed.{NC}")
        print(f"\nPlease check:")
        print(f"  1. Backend is running on port 8000")
        print(f"  2. All dependencies are installed")
        print(f"  3. Exchange API keys are configured (if needed)")
    
    return all_passed

async def main():
    print(f"{YELLOW}Unified Exchange Trading Platform - System Test{NC}")
    print("=" * 50)
    
    try:
        success = await test_system_integration()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{NC}")
        exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{NC}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())