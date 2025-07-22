#!/usr/bin/env python3
"""
Interactive LMEX Grid Bot Creator

This script provides an interactive interface to create grid bots on LMEX.
It prompts for all required parameters with sensible defaults.
"""

import os
import sys
import time
import json
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from exchanges.lmex import LMEXExchange

# Load environment variables
load_dotenv()


def get_input_with_default(prompt, default=None, input_type=str):
    """Get user input with optional default value"""
    if default is not None:
        prompt_text = f"{prompt} [{default}]: "
    else:
        prompt_text = f"{prompt}: "
    
    user_input = input(prompt_text).strip()
    
    if not user_input and default is not None:
        return default
    
    if not user_input:
        return None
    
    try:
        return input_type(user_input)
    except ValueError:
        print(f"Invalid input. Please enter a valid {input_type.__name__}")
        return get_input_with_default(prompt, default, input_type)


def get_yes_no(prompt, default=None):
    """Get yes/no input from user"""
    if default is not None:
        default_str = "Y" if default else "N"
        prompt_text = f"{prompt} [{default_str}]: "
    else:
        prompt_text = f"{prompt} (Y/N): "
    
    user_input = input(prompt_text).strip().upper()
    
    if not user_input and default is not None:
        return default
    
    if user_input in ['Y', 'YES']:
        return True
    elif user_input in ['N', 'NO']:
        return False
    else:
        print("Please enter Y or N")
        return get_yes_no(prompt, default)


def main():
    """Main function for interactive grid bot creation"""
    
    print("🤖 LMEX Grid Bot Creator")
    print("=" * 50)
    
    # Check for bearer token
    bearer_token = os.getenv("LMEX_BEARER_TOKEN")
    if not bearer_token:
        print("\n❌ Error: LMEX_BEARER_TOKEN not found in .env file")
        print("Please add your LMEX bearer token to the .env file:")
        print("LMEX_BEARER_TOKEN=your_token_here")
        return
    
    print("✅ Bearer token found\n")
    
    # Initialize LMEX exchange
    lmex = LMEXExchange()
    
    # Get grid bot parameters
    print("📊 Grid Bot Configuration")
    print("-" * 30)
    
    # Symbol
    symbol = get_input_with_default("Symbol (e.g., BTC-PERP, ETH-PERP, SOL-PERP)", input_type=str)
    if not symbol:
        print("Symbol is required!")
        return
    symbol = symbol.upper()
    if not symbol.endswith('-PERP'):
        symbol += '-PERP'
    
    # Direction
    direction_input = get_input_with_default("Direction (LONG/SHORT)", "LONG", str).upper()
    if direction_input not in ['LONG', 'SHORT']:
        print("Direction must be LONG or SHORT!")
        return
    direction = direction_input
    
    # Upper price
    upper_price = get_input_with_default("Upper price", input_type=float)
    if not upper_price:
        print("Upper price is required!")
        return
    
    # Lower price
    lower_price = get_input_with_default("Lower price", input_type=float)
    if not lower_price:
        print("Lower price is required!")
        return
    
    if lower_price >= upper_price:
        print("Lower price must be less than upper price!")
        return
    
    # Grid number
    grid_number = get_input_with_default("Number of grids", 200, int)
    if grid_number < 2:
        print("Grid number must be at least 2!")
        return
    
    # Initial margin
    initial_margin = get_input_with_default("Initial margin (USDT)", input_type=float)
    if not initial_margin or initial_margin <= 0:
        print("Initial margin must be greater than 0!")
        return
    
    # Leverage
    leverage = get_input_with_default("Leverage", 100, int)
    if leverage < 1 or leverage > 125:
        print("Leverage must be between 1 and 125!")
        return
    
    # Wallet mode
    wallet_mode_input = get_input_with_default("Wallet mode (CROSS/ISOLATED)", "CROSS", str).upper()
    if wallet_mode_input not in ['CROSS', 'ISOLATED']:
        print("Wallet mode must be CROSS or ISOLATED!")
        return
    wallet_mode = wallet_mode_input
    
    # Bot stop actions
    cancel_all_on_stop = get_yes_no("Cancel all orders on stop?", False)
    close_all_on_stop = get_yes_no("Close all positions on stop?", False)
    
    # Calculate order size per grid
    total_position_value = initial_margin * leverage
    order_size_per_grid = total_position_value / grid_number
    
    # Display configuration summary
    print("\n" + "=" * 50)
    print("📋 Configuration Summary")
    print("=" * 50)
    print(f"Symbol: {symbol}")
    print(f"Direction: {direction}")
    print(f"Upper Price: ${upper_price:,.2f}")
    print(f"Lower Price: ${lower_price:,.2f}")
    print(f"Price Range: ${upper_price - lower_price:,.2f} ({((upper_price - lower_price) / lower_price * 100):.2f}%)")
    print(f"Mid Price: ${(upper_price + lower_price) / 2:,.2f}")
    print(f"Grid Number: {grid_number}")
    print(f"Grid Spacing: ${(upper_price - lower_price) / grid_number:,.4f}")
    print(f"Initial Margin: ${initial_margin:,.2f} USDT")
    print(f"Leverage: {leverage}x")
    print(f"Total Position Value: ${total_position_value:,.2f}")
    print(f"Order Size per Grid: ${order_size_per_grid:,.2f}")
    print(f"Wallet Mode: {wallet_mode}")
    print(f"Cancel All on Stop: {cancel_all_on_stop}")
    print(f"Close All on Stop: {close_all_on_stop}")
    print("=" * 50)
    
    # Check if order size is $5 or less
    if order_size_per_grid <= 5.0:
        print(f"\n⚠️  WARNING: Order size per grid is ${order_size_per_grid:,.2f}")
        print("This is $5 or less, which may result in very small trades.")
        if not get_yes_no("Are you sure you want to continue with this small order size?", False):
            print("\n❌ Cancelled due to small order size")
            return
    
    # Confirmation
    if not get_yes_no("\n⚠️  Create this grid bot?", False):
        print("\n❌ Cancelled by user")
        return
    
    print("\n🚀 Creating grid bot...")
    
    # Result container
    result = {"error": None, "data": None, "completed": False}
    
    def completion_callback(error, data):
        """Callback for grid bot creation"""
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
        return
    
    print("\n✅ Grid bot created successfully!")
    
    if result["data"] and isinstance(result["data"], dict):
        data = result["data"]
        if "data" in data and "tradingBot" in data["data"]:
            bot = data["data"]["tradingBot"]
            print("\n📊 Grid Bot Details:")
            print(f"Bot ID: {bot.get('tradingBotShortId', 'N/A')}")
            print(f"Full ID: {bot.get('tradingBotId', 'N/A')}")
            print(f"State: {bot.get('state', 'N/A')}")
            print(f"Created At: {bot.get('createdAt', 'N/A')}")
            
            if "detail" in bot:
                detail = bot["detail"]
                print(f"\nConfiguration:")
                print(f"  Initial Last Price: ${float(detail.get('initialLastPrice', 0)):,.2f}")
                print(f"  Contract Per Step: {detail.get('contractPerStep', 'N/A')}")
                print(f"  Total Investment: ${float(detail.get('totalInvestment', 0)):,.2f} USDT")
    
    # Ask if user wants to view all bots
    if get_yes_no("\nView all grid bots?", True):
        print("\n📊 Fetching all grid bots...")
        
        bots_result = {"error": None, "data": None, "completed": False}
        
        def bots_callback(error, data):
            """Callback for fetching grid bots"""
            bots_result["error"] = error
            bots_result["data"] = data
            bots_result["completed"] = True
        
        lmex.fetchGridBots(bots_callback)
        
        # Wait for completion
        start_time = time.time()
        while not bots_result["completed"] and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if bots_result["completed"] and not bots_result["error"] and bots_result["data"]:
            bots = bots_result["data"]
            print(f"\n📈 Total grid bots: {len(bots)}")
            
            # Group by symbol
            bots_by_symbol = {}
            for bot in bots:
                sym = bot.get("symbol", "Unknown")
                if sym not in bots_by_symbol:
                    bots_by_symbol[sym] = []
                bots_by_symbol[sym].append(bot)
            
            # Display summary
            print("\n📊 Grid Bots by Symbol:")
            for sym, sym_bots in sorted(bots_by_symbol.items()):
                total_profit = sum(float(bot.get("totalProfit", 0)) for bot in sym_bots)
                print(f"\n{sym}: {len(sym_bots)} bot(s), Total Profit: ${total_profit:,.2f}")
                
                for bot in sym_bots:
                    print(f"  - {bot.get('tradingBotShortId', 'N/A')} ({bot.get('direction', 'N/A')}): "
                          f"${float(bot.get('totalProfit', 0)):,.2f} profit, "
                          f"{bot.get('state', 'N/A')}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")