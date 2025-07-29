#!/usr/bin/env python3
"""Analyze BTC SHORT Grid Bot Configuration"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bitunix import BitUnixExchange


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║           BTC SHORT Grid Bot Analysis                      ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Load configuration
    with open('btc_short_gridbot_config.json', 'r') as f:
        config = json.load(f)
    
    # Get current price
    exchange = BitUnixExchange()
    current_price = None
    
    def price_callback(status_data):
        nonlocal current_price
        status, data = status_data
        if status == "success":
            for ticker in data:
                if ticker.symbol == "BTCUSDT":
                    current_price = ticker.lastPrice
                    break
    
    print("Fetching current BTC price...")
    exchange.fetchTickers(price_callback)
    import time
    time.sleep(2)
    
    if not current_price:
        current_price = 116000  # Fallback
        print(f"Using estimated price: ${current_price:,.2f}")
    else:
        print(f"Current BTC price: ${current_price:,.2f}")
    
    # Configuration Analysis
    print("\n" + "="*60)
    print("CONFIGURATION ANALYSIS")
    print("="*60)
    
    # Basic parameters
    range_size = config['upper_price'] - config['lower_price']
    range_pct = (range_size / config['lower_price']) * 100
    grid_spacing = range_size / config['grid_count']
    grid_spacing_pct = (grid_spacing / config['lower_price']) * 100
    
    print(f"Symbol: {config['symbol']}")
    print(f"Direction: {config['position_direction']} 📉")
    print(f"Range: ${config['lower_price']:,} - ${config['upper_price']:,}")
    print(f"Range Size: ${range_size:,.2f} ({range_pct:.2f}%)") 
    print(f"Grid Count: {config['grid_count']}")
    print(f"Grid Spacing: ${grid_spacing:.2f} ({grid_spacing_pct:.3f}%)")
    print(f"Leverage: {config['leverage']}x")
    
    # Investment analysis
    print(f"\n💰 INVESTMENT BREAKDOWN:")
    print(f"Total Investment: ${config['total_investment']}")
    print(f"Per Grid: ${config['total_investment'] / config['grid_count']:.2f}")
    print(f"With {config['leverage']}x leverage:")
    print(f"  - Effective Capital: ${config['total_investment'] * config['leverage']:,}")
    print(f"  - Per Grid Effective: ${(config['total_investment'] * config['leverage']) / config['grid_count']:.2f}")
    
    # Position sizing
    avg_price = (config['upper_price'] + config['lower_price']) / 2
    total_btc = (config['total_investment'] * config['leverage']) / avg_price
    btc_per_grid = total_btc / config['grid_count']
    
    print(f"\n📊 POSITION SIZING (at avg price ${avg_price:,.2f}):")
    print(f"Total BTC managed: {total_btc:.6f} BTC")
    print(f"BTC per grid: {btc_per_grid:.6f} BTC")
    print(f"Value per grid: ${btc_per_grid * avg_price:.2f}")
    
    # Check minimum order size
    min_order_size = 0.0001  # BTC minimum
    if btc_per_grid < min_order_size:
        print(f"\n❌ WARNING: Grid order size {btc_per_grid:.6f} < minimum {min_order_size}")
        print(f"   Need at least ${min_order_size * avg_price * config['grid_count'] / config['leverage']:.2f} investment")
        print(f"   Or reduce grids to {int(total_btc / min_order_size)}")
    else:
        print(f"\n✅ Grid order size {btc_per_grid:.6f} meets minimum {min_order_size}")
    
    # Current price position
    if current_price >= config['lower_price'] and current_price <= config['upper_price']:
        price_position_pct = ((current_price - config['lower_price']) / range_size) * 100
        grids_below = int((current_price - config['lower_price']) / grid_spacing)
        grids_above = config['grid_count'] - grids_below
        
        print(f"\n📍 CURRENT PRICE POSITION:")
        print(f"Price is at {price_position_pct:.1f}% of range")
        print(f"For SHORT position:")
        print(f"  - {grids_above} SELL orders above ${current_price:,.2f}")
        print(f"  - {grids_below} BUY orders below ${current_price:,.2f}")
        
        # Initial position calculation for SHORT
        initial_position_size = grids_below * btc_per_grid
        initial_position_value = initial_position_size * current_price
        initial_margin_used = initial_position_value / config['leverage']
        
        print(f"\nInitial SHORT position: ~{initial_position_size:.6f} BTC")
        print(f"Initial position value: ${initial_position_value:,.2f}")
        print(f"Initial margin used: ${initial_margin_used:.2f}")
    else:
        if current_price > config['upper_price']:
            print(f"\n⚠️  Current price (${current_price:,.2f}) is ABOVE the grid range!")
            print("   This is good for SHORT - all SELL orders will be placed below.")
        else:
            print(f"\n⚠️  Current price (${current_price:,.2f}) is BELOW the grid range!")
    
    # Risk analysis
    print(f"\n⚠️  RISK ANALYSIS:")
    print(f"Stop Loss: ${config['stop_loss']:,}")
    print(f"Take Profit: ${config['take_profit']:,}")
    
    # Liquidation calculation for SHORT
    maintenance_margin_pct = 0.5  # 0.5% for BTC typically
    liquidation_distance_pct = (100 - maintenance_margin_pct) / config['leverage']
    liquidation_price = config['upper_price'] * (1 + liquidation_distance_pct/100)
    
    print(f"\nWith {config['leverage']}x leverage:")
    print(f"  - 1% price move = {config['leverage']}% P&L")
    print(f"  - Estimated liquidation: ~{liquidation_distance_pct:.2f}% above entry")
    print(f"  - Liquidation price: ~${liquidation_price:,.2f}")
    
    if liquidation_price < config['stop_loss']:
        print(f"  - ✅ Stop loss protects from liquidation")
    else:
        print(f"  - ⚠️  Liquidation before stop loss!")
    
    # Profit potential
    print(f"\n💰 PROFIT POTENTIAL (per completed grid cycle):")
    profit_per_grid = grid_spacing * btc_per_grid
    print(f"Profit per grid trade: ${profit_per_grid:.2f}")
    print(f"If 50% of grids complete: ${profit_per_grid * config['grid_count'] * 0.5:.2f}")
    print(f"If all grids complete: ${profit_per_grid * config['grid_count']:.2f}")
    
    # Summary
    print(f"\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"✅ Moderate-frequency grid trading setup")
    print(f"✅ 100 grids across a {range_pct:.2f}% range")
    print(f"✅ {config['leverage']}x leverage - Moderate risk")
    if btc_per_grid >= min_order_size:
        print(f"✅ Order sizes meet exchange minimum")
    else:
        print(f"❌ Order sizes TOO SMALL for exchange")
    print(f"💡 Best for: Ranging or slowly declining markets")
    print(f"💡 Risk: Sharp upward moves could trigger stop loss")


if __name__ == "__main__":
    main()