# Order Filter Test Checklist

## Implementation Summary

1. **UI Changes**:
   - Changed from checkboxes to button-style filters
   - "Orders" and "TP/SL" buttons are now styled like the chart timeframe buttons
   - Active state: darker background (bg-background-hover)
   - Inactive state: lighter text with hover effect
   - Both filters can be active simultaneously

2. **TP/SL Detection Logic**:
   - Improved detection to handle various order type formats
   - Checks for stop price or trigger price fields
   - Checks if order type contains: 'stop', 'take_profit', 'tp', or 'sl'
   - Orders are classified as regular if they don't match TP/SL criteria
   - Visual indicator: TP/SL orders show with yellow badge

3. **Debug Features**:
   - Console logging of order data for debugging
   - Visual type badges in the order table

## Testing Steps

### 1. Visual Check
- [ ] Open the trading interface
- [ ] Navigate to the Orders section
- [ ] Verify "Orders" and "TP/SL" buttons appear before "Show all symbols"
- [ ] Verify buttons have proper styling (not checkboxes)

### 2. Filter Functionality
- [ ] Click "Orders" button - should toggle regular orders visibility
- [ ] Click "TP/SL" button - should toggle TP/SL orders visibility
- [ ] Both buttons can be active/inactive independently
- [ ] Order count updates based on active filters

### 3. Order Type Detection
- [ ] Check console for order debug information
- [ ] Regular orders (limit/market) should show with gray badge
- [ ] TP/SL orders should show with yellow badge
- [ ] AVAX-PERP sell orders should now be correctly identified

### 4. Persistence
- [ ] Toggle filter states
- [ ] Refresh the page
- [ ] Verify filter preferences are maintained

### 5. Combined Filters
- [ ] Test with both filters active (show all orders)
- [ ] Test with only "Orders" active (hide TP/SL)
- [ ] Test with only "TP/SL" active (hide regular orders)
- [ ] Test with both inactive (show no orders)

## Debug Information

Check browser console for order type debugging:
```javascript
Order types debug: [
  {
    symbol: "AVAX-PERP",
    side: "sell",
    type: "limit",  // or whatever type is returned
    price: 123.45,
    stopPrice: undefined,
    triggerPrice: undefined,
    allFields: [...]
  }
]
```

## Known Issues to Watch For

1. If regular orders still appear as TP/SL, check:
   - Console output for actual order type values
   - Whether orders have unexpected stop/trigger price fields
   
2. If TP/SL orders don't show:
   - Verify actual TP/SL orders exist
   - Check if order type naming is different than expected

## Next Steps if Issues Persist

1. Share console debug output showing order data
2. Provide examples of order types that are misclassified
3. Check backend response for additional order fields