#!/usr/bin/env python3
"""Test LMEX WebSocket orderbook subscription"""

import asyncio
import websockets
import json
import time

async def test_orderbook_websocket():
    """Test WebSocket connection to LMEX futures orderbook"""
    uri = "wss://ws.lmex.io/ws/futures"
    
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to LMEX WebSocket")
            
            # Subscribe to orderbook updates
            subscribe_msgs = [
                {
                    "op": "subscribe",
                    "args": ["orderBookApi:BTC-PERP_0"]  # Grouping 0 for best precision
                },
                {
                    "op": "subscribe", 
                    "args": ["update:BTC-PERP"]  # Incremental updates
                }
            ]
            
            for msg in subscribe_msgs:
                await websocket.send(json.dumps(msg))
                print(f"Sent subscription: {msg}")
            
            # Listen for messages
            message_count = 0
            best_bid = 0
            best_ask = 0
            
            while message_count < 10:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    # Handle subscription confirmation
                    if data.get("event") == "subscribe" and data.get("success"):
                        print(f"Successfully subscribed to: {data.get('args')}")
                    
                    # Handle orderbook data
                    elif data.get("topic") and data.get("data"):
                        message_count += 1
                        topic = data["topic"]
                        orderbook = data["data"]
                        
                        print(f"\nReceived {topic}:")
                        
                        # orderBookApi format
                        if "buyQuote" in orderbook and "sellQuote" in orderbook:
                            if orderbook["buyQuote"]:
                                best_bid = float(orderbook["buyQuote"][0]["price"])
                                print(f"  Best Bid: ${best_bid:,.1f} (size: {orderbook['buyQuote'][0]['size']})")
                            if orderbook["sellQuote"]:
                                best_ask = float(orderbook["sellQuote"][0]["price"])
                                print(f"  Best Ask: ${best_ask:,.1f} (size: {orderbook['sellQuote'][0]['size']})")
                            print(f"  Spread: ${best_ask - best_bid:.1f}")
                        
                        # update format
                        elif "bids" in orderbook or "asks" in orderbook:
                            if orderbook.get("bids"):
                                # Sort bids by price descending
                                sorted_bids = sorted(orderbook["bids"], key=lambda x: float(x[0]), reverse=True)
                                if sorted_bids:
                                    best_bid = float(sorted_bids[0][0])
                                    print(f"  Best Bid: ${best_bid:,.1f} (size: {sorted_bids[0][1]})")
                            
                            if orderbook.get("asks"):
                                # Sort asks by price ascending
                                sorted_asks = sorted(orderbook["asks"], key=lambda x: float(x[0]))
                                if sorted_asks:
                                    best_ask = float(sorted_asks[0][0])
                                    print(f"  Best Ask: ${best_ask:,.1f} (size: {sorted_asks[0][1]})")
                            
                            if best_bid and best_ask:
                                print(f"  Spread: ${best_ask - best_bid:.1f}")
                            
                            print(f"  Type: {orderbook.get('type', 'unknown')}")
                        
                except asyncio.TimeoutError:
                    print(".", end="", flush=True)
                    
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_orderbook_websocket())