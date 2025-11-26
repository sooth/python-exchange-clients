#!/usr/bin/env python3
"""Test LMEX OSS (Orderbook Streaming Service) WebSocket"""

import asyncio
import websockets
import json

async def test_oss_websocket():
    """Test WebSocket connection to LMEX OSS futures"""
    uri = "wss://ws.lmex.io/ws/oss/futures"
    
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to LMEX OSS WebSocket")
            
            # Subscribe to orderbook updates
            subscriptions = [
                {"op": "subscribe", "args": ["update:BTC-PERP_0"]},
                {"op": "subscribe", "args": ["snapshotL1:BTC-PERP"]}
            ]
            
            for sub in subscriptions:
                await websocket.send(json.dumps(sub))
                print(f"Sent: {sub}")
            
            # Listen for messages
            message_count = 0
            
            while message_count < 5:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    message_count += 1
                    
                    print(f"\nMessage {message_count}:")
                    
                    # Handle subscription confirmation
                    if data.get("event") == "subscribe":
                        print(f"  Event: {data.get('event')}")
                        print(f"  Success: {data.get('success', False)}")
                        print(f"  Args: {data.get('args', [])}")
                    
                    # Handle orderbook data
                    elif data.get("topic") and data.get("data"):
                        topic = data["topic"]
                        orderbook = data["data"]
                        
                        print(f"  Topic: {topic}")
                        print(f"  Symbol: {orderbook.get('symbol', 'N/A')}")
                        
                        # Show bid/ask data
                        if "bids" in orderbook and orderbook["bids"]:
                            best_bid = orderbook["bids"][0]
                            print(f"  Best Bid: ${float(best_bid[0]):,.1f} (size: {best_bid[1]})")
                        
                        if "asks" in orderbook and orderbook["asks"]:
                            best_ask = orderbook["asks"][0]
                            print(f"  Best Ask: ${float(best_ask[0]):,.1f} (size: {best_ask[1]})")
                        
                        print(f"  Type: {orderbook.get('type', 'unknown')}")
                        if orderbook.get('seqNum'):
                            print(f"  Sequence: {orderbook.get('seqNum')}")
                    
                    else:
                        print(f"  Unknown message: {json.dumps(data)[:100]}...")
                        
                except asyncio.TimeoutError:
                    print("  Waiting for data...")
                    
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_oss_websocket())