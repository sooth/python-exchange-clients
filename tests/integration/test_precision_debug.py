#!/usr/bin/env python3
"""Debug precision manager for BitUnix"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.utils.precision import SymbolPrecisionManager

def main():
    # Get BitUnix precision manager
    pm = SymbolPrecisionManager.get_instance("BitUnix")
    
    # Check BTCUSDT precision
    symbol = "BTCUSDT"
    info = pm.get_symbol_info(symbol)
    print(f"Symbol info for {symbol}:")
    print(f"  Raw info: {info}")
    
    price_precision = pm.get_price_precision(symbol)
    quantity_precision = pm.get_quantity_precision(symbol)
    min_volume = pm.get_min_trade_volume(symbol)
    
    print(f"\nPrecision values:")
    print(f"  Price precision: {price_precision}")
    print(f"  Quantity precision: {quantity_precision}")
    print(f"  Min trade volume: {min_volume}")
    
    # Test formatting
    test_qty = 0.000108
    formatted_qty = f"{test_qty:.{quantity_precision}f}"
    print(f"\nFormatting test:")
    print(f"  Original quantity: {test_qty}")
    print(f"  Formatted quantity: {formatted_qty}")
    
    # Test with minimum
    min_qty = 0.0001
    formatted_min = f"{min_qty:.{quantity_precision}f}"
    print(f"\nMinimum quantity formatting:")
    print(f"  Min quantity: {min_qty}")
    print(f"  Formatted min: {formatted_min}")

if __name__ == "__main__":
    main()