#!/usr/bin/env python3
"""
Test LMEX Grid Bot Creation

This script tests the creation of a grid bot on LMEX with the following parameters:
- Symbol: SOL-PERP (LONG)
- Upper Price: 204.72
- Lower Price: 193.99
- Grid Number: 200
- Initial Margin: 200 USDT
- Leverage: 100x
"""

import os
import sys
from dotenv import load_dotenv
import time
import json

# Add the package to the path for local testing
sys.path.insert(0, os.path.dirname(__file__))

# Import from the new library
from exchanges.lmex import LMEXExchange

# Load environment variables
load_dotenv()

def main(test_mode=False):
    """Main function to test grid bot creation
    
    Args:
        test_mode: If True, only test imports and setup without creating actual bots
    """
    
    # Check for bearer token
    bearer_token = os.getenv("LMEX_BEARER_TOKEN")
    if not bearer_token:
        if test_mode:
            print("⚠️  Warning: LMEX_BEARER_TOKEN not found in .env file")
            print("   Continuing in test mode...")
        else:
            print("❌ Error: LMEX_BEARER_TOKEN not found in .env file")
            print("Please add your LMEX bearer token to the .env file:")
            print("LMEX_BEARER_TOKEN=your_token_here")
            return
    else:
        print("✅ Bearer token found in .env file")
    
    # Initialize LMEX exchange
    lmex = LMEXExchange()
    
    # Grid bot parameters (matching the working curl command)
    symbol = "SOL-PERP"
    direction = "LONG"
    upper_price = 204.72  # Will be formatted based on symbol precision
    lower_price = 193.99  # Will be formatted based on symbol precision
    grid_number = 200
    initial_margin = 200  # USDT
    leverage = 100  # Matching the curl command
    wallet_mode = "CROSS"  # or "ISOLATED"
    cancel_all_on_stop = False  # Matching the curl command
    close_all_on_stop = False  # Matching the curl command
    
    print("\n📊 Grid Bot Configuration:")
    print(f"  Symbol: {symbol}")
    print(f"  Direction: {direction}")
    print(f"  Upper Price: ${upper_price:,.2f}")
    print(f"  Lower Price: ${lower_price:,.2f}")
    print(f"  Price Range: ${upper_price - lower_price:,.2f} ({((upper_price - lower_price) / lower_price * 100):.2f}%)")
    print(f"  Mid Price: ${(upper_price + lower_price) / 2:,.2f}")
    print(f"  Grid Number: {grid_number}")
    print(f"  Grid Spacing: ${(upper_price - lower_price) / grid_number:,.2f}")
    print(f"  Initial Margin: ${initial_margin}")
    print(f"  Leverage: {leverage}x")
    print(f"  Wallet Mode: {wallet_mode}")
    print(f"  Cancel All on Stop: {cancel_all_on_stop}")
    print(f"  Close All on Stop: {close_all_on_stop}")
    
    # Confirmation prompt
    if test_mode:
        print("\n🧪 TEST MODE: Will only test functionality without creating real bots")
    else:
        print("\n⚠️  WARNING: This will create a real grid bot on LMEX!")
        print("Press Enter to continue or Ctrl+C to cancel...")
        try:
            input()
        except KeyboardInterrupt:
            print("\n\n❌ Cancelled by user")
            return
    
    if test_mode:
        print("\n🧪 Skipping grid bot creation in test mode")
        print("✅ Library imports and setup successful!")
    else:
        print("\n🚀 Creating grid bot...")
        
        # Result container
        result = {"error": None, "data": None, "completed": False}
        
        def completion_callback(error, data):
            """Callback for grid bot creation - using old (error, data) format"""
            # Note: The new library's createGridBot still uses (error, data) format
            # for compatibility with the Bearer token API
            result["error"] = error
            result["data"] = data
            result["completed"] = True
        
        # Create the grid bot
        lmex.createGridBot(
        symbol=symbol,
        direction=direction,
        upper_price=upper_price,
        lower_price=lower_price,
        leverage=leverage,
        wallet_mode=wallet_mode,
        grid_number=grid_number,
        initial_margin=initial_margin,
        cancel_all_on_stop=cancel_all_on_stop,
        close_all_on_stop=close_all_on_stop,
        completion=completion_callback
        )
        
        # Wait for completion (with timeout)
        timeout = 10  # seconds
        start_time = time.time()
        while not result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if not result["completed"]:
            print("\n❌ Error: Request timed out")
            return
        
        # Handle result
        if result["error"]:
            print(f"\n❌ Error creating grid bot: {result['error']}")
        else:
            print("\n✅ Grid bot created successfully!")
            if result["data"]:
                print("\n📋 Response data:")
                print(json.dumps(result["data"], indent=2))
    
    # Optionally fetch and display all grid bots
    print("\n📊 Fetching all grid bots...")
    
    bots_result = {"error": None, "data": None, "completed": False}
    
    def bots_callback(error, data):
        """Callback for fetching grid bots - using old (error, data) format"""
        # Note: The new library's fetchGridBots still uses (error, data) format
        # for compatibility with the Bearer token API
        bots_result["error"] = error
        bots_result["data"] = data
        bots_result["completed"] = True
    
    lmex.fetchGridBots(bots_callback)
    
    # Wait for completion
    start_time = time.time()
    while not bots_result["completed"] and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if bots_result["completed"] and not bots_result["error"] and bots_result["data"]:
        print(f"\n📈 Total grid bots found: {len(bots_result['data'])}")
        
        # Find and display the SOL bot
        sol_bots = [bot for bot in bots_result["data"] if bot.get("symbol") == symbol]
        if sol_bots:
            print(f"\n🔍 {symbol} grid bots:")
            for bot in sol_bots:
                print(f"\n  Bot ID: {bot.get('tradingBotId')}")
                print(f"  Direction: {bot.get('direction', 'N/A')}")
                print(f"  Entry Price: ${bot.get('entryPrice', 0):,.2f}")
                print(f"  Total Contracts: {bot.get('totalContracts', 0)}")
                print(f"  Total Profit: ${bot.get('totalProfit', 0):,.2f}")
                print(f"  Realized Profit: ${bot.get('realizedProfit', 0):,.2f}")
                print(f"  Unrealized Profit: ${bot.get('unrealizedProfit', 0):,.2f}")
                print(f"  Created At: {bot.get('createdAt', 'N/A')}")
                if bot.get('upperPrice'):
                    print(f"  Upper Price: ${bot['upperPrice']:,.2f}")
                if bot.get('lowerPrice'):
                    print(f"  Lower Price: ${bot['lowerPrice']:,.2f}")

if __name__ == "__main__":
    # Check command line arguments
    import sys
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    main(test_mode=test_mode)