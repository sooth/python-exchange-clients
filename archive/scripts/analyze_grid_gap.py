#!/usr/bin/env python3
"""Analyze grid gap issue"""

# Calculate expected grid levels
lower = 114751.5
upper = 116752.0
count = 50
spacing = (upper - lower) / (count - 1)
current = 115446.30

print(f'Grid range: ${lower:,.2f} - ${upper:,.2f}')
print(f'Grid spacing: ${spacing:.2f}')
print(f'Current price: ${current:,.2f}')
print()

# Calculate which level the current price is at
level_index = (current - lower) / spacing
print(f'Current price is at level: {level_index:.1f}')
print()

# Show expected orders around current price
print('Expected orders around current price:')
for i in range(50):
    price = lower + (i * spacing)
    if abs(price - current) < 300:
        side = 'BUY' if price < current else 'SELL'
        distance = abs(price - current)
        print(f'  Level {i}: ${price:,.2f} ({side}) - ${distance:.2f} from current')

print('\nISSUE: Orders at levels 16-18 are missing!')
print('These should be SELL orders just above current price')