#!/usr/bin/env python3
"""Test LMEX orderbook subscription with different formats"""

import asyncio
import websockets
import json

async def test_orderbook():
    uri = "wss://ws.lmex.io/ws/futures"
    
    async with websockets.connect(uri) as websocket:
        print("Connected!")
        
        # Try different subscription formats
        subscriptions = [
            {"op": "subscribe", "args": ["orderBookApi:BTC-PERP_0"]},
            {"op": "subscribe", "args": ["orderbook:BTC-PERP"]},
            {"op": "subscribe", "args": ["orderBookL2Api:BTC-PERP_0"]},
            {"op": "subscribe", "args": ["update:BTC-PERP"]}
        ]
        
        for sub in subscriptions:
            await websocket.send(json.dumps(sub))
            print(f"Sent: {sub}")
        
        # Listen for any response
        for i in range(10):
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(message)
                print(f"\nReceived: {json.dumps(data, indent=2)}")
                
                # If we get orderbook data, show it
                if "data" in data and isinstance(data["data"], dict):
                    d = data["data"]
                    if "buyQuote" in d or "sellQuote" in d or "bids" in d or "asks" in d:
                        print("*** ORDERBOOK DATA FOUND! ***")
                        break
                        
            except asyncio.TimeoutError:
                print(".", end="", flush=True)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_orderbook())