#!/usr/bin/env python3
"""Basic usage example for python-exchange-clients."""

from exchanges import LMEXExchange, BitUnixExchange
from exchanges.base import ExchangeOrderRequest
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def example_lmex():
    """Example usage of LMEX exchange."""
    print("=== LMEX Example ===")
    
    # Initialize exchange
    lmex = LMEXExchange()
    
    # Fetch tickers
    print("\nFetching tickers...")
    
    def ticker_callback(status, data):
        if status == "failure":
            print(f"Error fetching tickers: {data}")
        else:
            print(f"Found {len(data)} tickers")
            # Show first 5 tickers
            for ticker in data[:5]:
                print(f"  {ticker.symbol}: ${ticker.lastPrice if hasattr(ticker, 'lastPrice') else 'N/A'}")
    
    lmex.fetchTickers(ticker_callback)
    
    # Fetch positions
    print("\nFetching positions...")
    
    def position_callback(status, data):
        if status == "failure":
            print(f"Error fetching positions: {data}")
        else:
            print(f"Found {len(data)} positions")
            for pos in data:
                print(f"  {pos.symbol}: {pos.size} @ ${pos.entryPrice} (PnL: ${pos.pnl:.2f})")
    
    lmex.fetchPositions(position_callback)


def example_bitunix():
    """Example usage of BitUnix exchange."""
    print("\n=== BitUnix Example ===")
    
    # Initialize exchange
    bitunix = BitUnixExchange()
    
    # Subscribe to ticker updates
    symbol = "BTCUSDT"
    print(f"\nSubscribing to {symbol} ticker...")
    bitunix.subscribeToTicker(symbol)
    
    # Get last trade price
    price = bitunix.lastTradePrice(symbol)
    print(f"Last trade price for {symbol}: ${price}")


def example_place_order():
    """Example of placing an order."""
    print("\n=== Place Order Example ===")
    
    # Initialize exchange
    lmex = LMEXExchange()
    
    # Create order request
    order = ExchangeOrderRequest(
        symbol="BTC-PERP",
        side="BUY",
        orderType="LIMIT",
        qty=0.001,  # Small test order
        price=45000.0,
        timeInForce="GTC"
    )
    
    print(f"\nPlacing test order: {order.side} {order.qty} {order.symbol} @ ${order.price}")
    
    def order_callback(status, data):
        if status == "failure":
            print(f"Order failed: {data}")
        else:
            print(f"Order placed successfully!")
            print(f"Response: {data}")
    
    # Note: Uncomment to actually place the order
    # lmex.placeOrder(order, order_callback)
    print("(Order placement commented out for safety)")


if __name__ == "__main__":
    # Run examples
    example_lmex()
    example_bitunix()
    example_place_order()