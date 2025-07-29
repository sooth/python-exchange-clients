#!/usr/bin/env python3
"""Calculate CVX grid levels"""

# Configuration
upper_price = 5.199
lower_price = 4.708
grid_count = 10
total_investment = 200
position_direction = "LONG"

# Calculate grid spacing (arithmetic)
price_range = upper_price - lower_price
grid_spacing = price_range / (grid_count - 1)  # 9 intervals for 10 levels

print("CVX Grid Bot Analysis")
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
# In reality, the bot will fetch the actual current price
estimated_current_price = (upper_price + lower_price) / 2
print(f"Assuming current price: ${estimated_current_price:.3f}")
print()

# For LONG position direction:
# - Buy orders are placed BELOW current price
# - Sell orders are placed ABOVE current price (to take profit)

buy_orders = []
sell_orders = []

for i, price in enumerate(grid_levels):
    if price < estimated_current_price * 0.999:  # 0.1% buffer to avoid immediate execution
        buy_orders.append((i, price))
    elif price > estimated_current_price * 1.001:  # 0.1% buffer
        sell_orders.append((i, price))

print("Initial Orders:")
print("-" * 50)

print("\nBUY Orders (Entry/Accumulation):")
print(f"{'Level':<8} {'Price':<10} {'Quantity':<12} {'Value':<10}")
print("-" * 50)
investment_per_grid = total_investment * 0.98 / grid_count
for level, price in buy_orders:
    quantity = investment_per_grid / price
    print(f"Level {level:<2} ${price:<9.3f} {quantity:<11.3f} ${investment_per_grid:<9.2f}")

print(f"\nTotal Buy Orders: {len(buy_orders)}")
print(f"Total Buy Value: ${len(buy_orders) * investment_per_grid:.2f}")

print("\nSELL Orders (Profit Taking):")
print(f"{'Level':<8} {'Price':<10} {'Quantity':<12} {'Value':<10}")
print("-" * 50)
for level, price in sell_orders:
    quantity = investment_per_grid / price
    print(f"Level {level:<2} ${price:<9.3f} {quantity:<11.3f} ${investment_per_grid:<9.2f}")

print(f"\nTotal Sell Orders: {len(sell_orders)}")

print("\nHow it works:")
print("-" * 50)
print("1. Buy orders are placed below current price to accumulate on dips")
print("2. When a buy order fills, a sell order is placed at the next level up")
print("3. When a sell order fills, a buy order is placed at the next level down")
print("4. This creates a profit on each completed buy-sell cycle")

# Calculate profit per grid trade
fee_rate = 0.001  # 0.1%
gross_profit_per_grid = grid_spacing * (investment_per_grid / estimated_current_price)
fees_per_trade = investment_per_grid * fee_rate * 2  # Buy and sell
net_profit_per_grid = gross_profit_per_grid - fees_per_trade
profit_percentage = (net_profit_per_grid / investment_per_grid) * 100

print(f"\nProfit per Grid Trade:")
print(f"  Gross Profit: ${gross_profit_per_grid:.3f}")
print(f"  Fees (0.1% x2): ${fees_per_trade:.3f}")
print(f"  Net Profit: ${net_profit_per_grid:.3f}")
print(f"  Profit %: {profit_percentage:.2f}%")

print(f"\nRisk Analysis:")
print(f"  Stop Loss: $4.50")
print(f"  Max Loss if Stop Hit: ${(lower_price - 4.50) / lower_price * total_investment:.2f}")
print(f"  Trades to Break Even: {int((lower_price - 4.50) / lower_price * total_investment / net_profit_per_grid) + 1}")