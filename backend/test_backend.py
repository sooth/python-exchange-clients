#!/usr/bin/env python3
"""
Quick test script to verify backend is working
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"


async def test_backend():
    async with httpx.AsyncClient() as client:
        print("Testing Backend API...")
        print("-" * 50)
        
        # Test root endpoint
        print("1. Testing root endpoint...")
        response = await client.get(BASE_URL)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # Test health endpoint
        print("2. Testing health endpoint...")
        response = await client.get(f"{BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # Test exchanges endpoint
        print("3. Testing available exchanges...")
        response = await client.get(f"{API_URL}/market/exchanges")
        print(f"   Status: {response.status_code}")
        print(f"   Exchanges: {response.json()}")
        print()
        
        # Test ticker endpoint
        print("4. Testing ticker endpoint...")
        try:
            response = await client.get(f"{API_URL}/market/ticker/BTCUSDT?exchange=bitunix")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                ticker = response.json()
                print(f"   BTC Price: ${ticker.get('last', 'N/A')}")
        except Exception as e:
            print(f"   Error: {e}")
        print()
        
        print("Backend test complete!")


if __name__ == "__main__":
    asyncio.run(test_backend())