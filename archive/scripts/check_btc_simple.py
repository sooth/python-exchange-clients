#!/usr/bin/env python3
"""Simple check of BTC position"""

import json

# From the raw response we saw
raw_response = {"code":0,"data":[{"positionId":"6230511510852749846","symbol":"BTCUSDT","marginCoin":None,"qty":"0.001","entryValue":"115.8287","side":"SELL","marginMode":"CROSS","positionMode":"HEDGE","leverage":100,"fee":"-0.018532592","funding":"0","realizedPNL":"-0.018532592","margin":"1.2","unrealizedPNL":"0.0174","liqPrice":"4577398.8","avgOpenPrice":"115828.7","marginRate":"0.0048","ctime":"1753461683000","mtime":"1753461683000"},{"positionId":"751695968758088861","symbol":"ENAUSDT","marginCoin":None,"qty":"1839","entryValue":"884.559","side":"BUY","marginMode":"CROSS","positionMode":"HEDGE","leverage":20,"fee":"-0.14152944","funding":"-2.811519648105","realizedPNL":"-2.953049088105","margin":"44.228","unrealizedPNL":"112.5468","liqPrice":"0","avgOpenPrice":"0.4810","marginRate":"0.0048","ctime":"1753251453000","mtime":"1753459211000"}],"msg":"result.success"}

print("Raw positions from API:")
for pos in raw_response['data']:
    if pos['symbol'] == 'BTCUSDT':
        print(f"\n🚨 BTC Position Found:")
        print(f"  Symbol: {pos['symbol']}")
        print(f"  Side: {pos['side']}")
        print(f"  Quantity: {pos['qty']}")
        print(f"  Entry Price: ${pos['avgOpenPrice']}")
        print(f"  Position Direction: {'SHORT' if pos['side'] == 'SELL' else 'LONG'}")
        
print("\n⚠️  CRITICAL ISSUE:")
print("  - Grid bot is configured for LONG position")
print("  - But there's an existing 0.001 BTC SHORT position!")
print("  - This happened because the bot placed a SELL order at market instead of BUY")
print("  - The position calculator returned 0 initial position when it should have returned a BUY position")