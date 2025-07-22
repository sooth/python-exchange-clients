#!/usr/bin/env python3
"""Grid bot example for LMEX exchange."""

from exchanges import LMEXExchange
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_grid_bot_example():
    """Example of creating a grid bot on LMEX."""
    
    # Check for bearer token
    bearer_token = os.getenv("LMEX_BEARER_TOKEN")
    if not bearer_token:
        print("Error: LMEX_BEARER_TOKEN not found in environment variables")
        print("Grid bots require a bearer token from LMEX web interface")
        return
    
    # Initialize exchange
    lmex = LMEXExchange()
    
    # Grid bot parameters
    params = {
        "symbol": "ETH-PERP",
        "direction": "LONG",
        "upper_price": 2500.0,
        "lower_price": 2200.0,
        "leverage": 20,
        "wallet_mode": "CROSS",
        "grid_number": 50,
        "initial_margin": 100,  # USDT
        "cancel_all_on_stop": False,
        "close_all_on_stop": False
    }
    
    print("Creating grid bot with parameters:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    
    def creation_callback(error, data):
        if error:
            print(f"\nError creating grid bot: {error}")
        else:
            print(f"\nGrid bot created successfully!")
            print(f"Response: {data}")
    
    # Note: Uncomment to actually create the bot
    # lmex.createGridBot(**params, completion=creation_callback)
    print("\n(Grid bot creation commented out for safety)")


def list_grid_bots_example():
    """Example of listing existing grid bots."""
    
    # Initialize exchange
    lmex = LMEXExchange()
    
    print("\nFetching existing grid bots...")
    
    def bots_callback(error, bots):
        if error:
            print(f"Error fetching bots: {error}")
        else:
            print(f"\nFound {len(bots)} grid bots:")
            
            for bot in bots:
                print(f"\nBot ID: {bot['tradingBotId']}")
                print(f"  Symbol: {bot['symbol']}")
                print(f"  Direction: {bot.get('direction', 'N/A')}")
                print(f"  Total Profit: ${bot['totalProfit']:.2f}")
                print(f"  Realized Profit: ${bot['realizedProfit']:.2f}")
                print(f"  Unrealized Profit: ${bot['unrealizedProfit']:.2f}")
                
                if bot.get('upperPrice'):
                    print(f"  Price Range: ${bot['lowerPrice']} - ${bot['upperPrice']}")
                
                if bot.get('entryPrice'):
                    print(f"  Entry Price: ${bot['entryPrice']}")
                    print(f"  Contracts: {bot.get('totalContracts', 0)}")
    
    lmex.fetchGridBots(bots_callback)


def grid_bot_profit_analysis():
    """Analyze profits from all grid bots."""
    
    # Initialize exchange
    lmex = LMEXExchange()
    
    def analyze_callback(error, bots):
        if error:
            print(f"Error fetching bots: {error}")
            return
        
        # Calculate totals
        total_profit = sum(bot['totalProfit'] for bot in bots)
        total_realized = sum(bot['realizedProfit'] for bot in bots)
        total_unrealized = sum(bot['unrealizedProfit'] for bot in bots)
        
        print("\n=== Grid Bot Profit Analysis ===")
        print(f"Total Bots: {len(bots)}")
        print(f"Total Profit: ${total_profit:.2f}")
        print(f"  Realized: ${total_realized:.2f}")
        print(f"  Unrealized: ${total_unrealized:.2f}")
        
        # Group by symbol
        by_symbol = {}
        for bot in bots:
            symbol = bot['symbol']
            if symbol not in by_symbol:
                by_symbol[symbol] = []
            by_symbol[symbol].append(bot)
        
        print("\nProfit by Symbol:")
        for symbol, symbol_bots in sorted(by_symbol.items()):
            symbol_profit = sum(bot['totalProfit'] for bot in symbol_bots)
            print(f"  {symbol}: ${symbol_profit:.2f} ({len(symbol_bots)} bots)")
    
    lmex.fetchGridBots(analyze_callback)


if __name__ == "__main__":
    # Run examples
    create_grid_bot_example()
    list_grid_bots_example()
    grid_bot_profit_analysis()