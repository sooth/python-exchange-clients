#!/usr/bin/env python3
"""Calculate CVX SHORT grid levels"""

# Configuration
upper_price = 5.217
lower_price = 4.653
grid_count = 10
total_investment = 200
position_direction = "SHORT"

# Calculate grid spacing (arithmetic)
price_range = upper_price - lower_price
grid_spacing = price_range / (grid_count - 1)  # 9 intervals for 10 levels

print("CVX SHORT Grid Bot Analysis")
print("=" * 50)
print(f"Price Range: ${lower_price} - ${upper_price}")
print(f"Grid Count: {grid_count}")
print(f"Grid Spacing: ${grid_spacing:.4f}")
print(f"Investment per Grid: ${total_investment * 0.98 / grid_count:.2f}")  # 98% to account for fees
print()

# Calculate grid levels
grid_levels = []
for i in range(grid_count):
    price = lower_price + (i * grid_spacing)
    grid_levels.append(price)

# Assume current price is somewhere in the middle for this example
estimated_current_price = (upper_price + lower_price) / 2
print(f"Assuming current price: ${estimated_current_price:.3f}")
print()

# For SHORT position direction:
# - SELL orders are placed ABOVE current price (to enter short positions)
# - BUY orders are placed BELOW current price (to take profit/close shorts)

buy_orders = []
sell_orders = []

for i, price in enumerate(grid_levels):
    if price < estimated_current_price * 0.999:  # Below current = buy to close shorts
        buy_orders.append((i, price))
    elif price > estimated_current_price * 1.001:  # Above current = sell to open shorts
        sell_orders.append((i, price))

print("Initial Orders (SHORT Strategy):")
print("-" * 50)

print("\nSELL Orders (Short Entry):")
print(f"{'Level':<8} {'Price':<10} {'Quantity':<12} {'Value':<10}")
print("-" * 50)
investment_per_grid = total_investment * 0.98 / grid_count
for level, price in sell_orders:
    quantity = investment_per_grid / price
    print(f"Level {level:<2} ${price:<9.3f} {quantity:<11.3f} ${investment_per_grid:<9.2f}")

print(f"\nTotal Sell Orders: {len(sell_orders)}")
print(f"Total Sell Value: ${len(sell_orders) * investment_per_grid:.2f}")

print("\nBUY Orders (Profit Taking/Close Shorts):")
print(f"{'Level':<8} {'Price':<10} {'Quantity':<12} {'Value':<10}")
print("-" * 50)
for level, price in buy_orders:
    quantity = investment_per_grid / price
    print(f"Level {level:<2} ${price:<9.3f} {quantity:<11.3f} ${investment_per_grid:<9.2f}")

print(f"\nTotal Buy Orders: {len(buy_orders)}")

print("\nHow SHORT Grid Works:")
print("-" * 50)
print("1. SELL orders above current price open SHORT positions")
print("2. When a SELL fills (short opened), place BUY order one level below")
print("3. When a BUY fills (short closed), profit is captured")
print("4. Then place a new SELL order one level above to re-enter")
print("5. Profits come from selling high and buying back lower")

# Calculate profit per grid trade
fee_rate = 0.001  # 0.1%
# For shorts: profit = sell_price - buy_price (when prices fall)
gross_profit_per_grid = grid_spacing * (investment_per_grid / estimated_current_price)
fees_per_trade = investment_per_grid * fee_rate * 2  # Buy and sell
net_profit_per_grid = gross_profit_per_grid - fees_per_trade
profit_percentage = (net_profit_per_grid / investment_per_grid) * 100

print(f"\nProfit per Grid Trade:")
print(f"  Gross Profit: ${gross_profit_per_grid:.3f}")
print(f"  Fees (0.1% x2): ${fees_per_trade:.3f}")
print(f"  Net Profit: ${net_profit_per_grid:.3f}")
print(f"  Profit %: {profit_percentage:.2f}%")

print(f"\nRisk Analysis (SHORT):")
print(f"  Stop Loss: $5.35 (above upper range)")
print(f"  Risk: Price rising above $5.35 triggers stop")
print(f"  Max Loss if Stop Hit: ${(5.35 - upper_price) / upper_price * total_investment:.2f}")
print(f"  Trades to Break Even: {int((5.35 - upper_price) / upper_price * total_investment / net_profit_per_grid) + 1}")