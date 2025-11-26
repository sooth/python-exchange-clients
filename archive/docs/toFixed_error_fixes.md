# toFixed Error Fixes

## Problem
The backend uses Python's `Decimal` type for numeric values, which gets serialized as strings in JSON. The frontend was expecting `number` types and calling `.toFixed()` directly, causing "toFixed is not a function" errors.

## Solution
Updated all formatting functions to handle both `number` and `string` inputs:

### 1. Updated Type Definitions
- Modified interfaces to accept `number | string` for numeric fields
- Files: `frontend/types/api.ts`

### 2. Fixed Formatting Functions
Updated all components to handle string inputs:

```typescript
// Before
const formatPrice = (price: number) => {
  if (price >= 1000) return price.toFixed(0)
  // ...
}

// After
const formatPrice = (price: number | string) => {
  const numPrice = typeof price === 'string' ? parseFloat(price) : price
  if (isNaN(numPrice)) return '0.00'
  if (numPrice >= 1000) return numPrice.toFixed(0)
  // ...
}
```

### 3. Components Fixed
- `Positions.tsx` - formatPrice, formatAmount, formatPnL, formatPercentage, formatCurrency
- `OrderBook.tsx` - formatPrice, formatAmount
- `OpenOrders.tsx` - formatPrice, formatAmount  
- `RecentTrades.tsx` - formatPrice, formatAmount
- `OrderForm.tsx` - parseFloat with fallback defaults
- `MarketInfo.tsx` - Added NaN checks
- `MarketList.tsx` - Added NaN checks

## Result
All numeric formatting functions now safely handle:
- String inputs from the backend
- NaN values
- Undefined/null values
- Type conversion errors

The frontend will no longer crash when receiving Decimal values serialized as strings from the Python backend.