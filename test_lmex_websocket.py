#!/usr/bin/env python3
"""Test LMEX WebSocket connection for public trade data"""

import asyncio
import websockets
import json
import time

async def test_lmex_websocket():
    """Test WebSocket connection to LMEX futures"""
    uri = "wss://ws.lmex.io/ws/futures"
    
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to LMEX WebSocket")
            
            # Subscribe to BTC-PERP trades
            subscribe_msg = {
                "op": "subscribe",
                "args": ["tradeHistoryApiV2:BTC-PERP"]
            }
            
            await websocket.send(json.dumps(subscribe_msg))
            print(f"Sent subscription: {subscribe_msg}")
            
            # Listen for messages
            message_count = 0
            start_time = time.time()
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(message)
                    
                    # Handle subscription confirmation
                    if data.get("event") == "subscribe" and data.get("success"):
                        print(f"Successfully subscribed to: {data.get('args')}")
                    
                    # Handle trade data
                    elif data.get("topic") and data.get("data"):
                        message_count += 1
                        trades = data["data"]
                        print(f"\nReceived {len(trades)} trades:")
                        for trade in trades[:3]:  # Show first 3 trades
                            print(f"  - Price: {trade['price']}, Size: {trade['size']}, Side: {trade['side']}, Time: {trade['timestamp']}")
                        
                        if message_count >= 5:
                            print(f"\nReceived {message_count} messages in {time.time() - start_time:.1f} seconds")
                            break
                    
                    # Handle ping/pong
                    elif data.get("op") == "pong":
                        print("Received pong")
                        
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    ping_msg = {"op": "ping"}
                    await websocket.send(json.dumps(ping_msg))
                    print("Sent ping")
                    
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_lmex_websocket())