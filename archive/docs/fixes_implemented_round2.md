# WebSocket Fixes - Round 2

## Issues Fixed

### 1. Order Attribute Mapping (FIXED)
**Problem**: API endpoint was using wrong attribute names when creating ExchangeOrderRequest
**Solution**: Fixed mapping in `trading.py`:
- `type` → `orderType`
- `quantity` → `qty`
- `clientOrderId` → `orderLinkId`

### 2. Repeated WebSocket Subscriptions (FIXED)
**Problem**: Frontend was re-subscribing to the same symbols repeatedly due to:
- Symbol array being recreated on every render
- Callback function being recreated on every render
- No deduplication in WebSocket manager

**Solutions Implemented**:

#### Frontend Fixes (`MarketList.tsx`):
1. **Memoized symbol arrays**:
   ```typescript
   const topMarketSymbols = useMemo(() => {
     return topMarkets.map(t => t.symbol)
   }, [topMarkets])
   ```

2. **Memoized callback function**:
   ```typescript
   const handleTickerUpdate = useCallback((symbol: string, data: Ticker) => {
     setTickerData(prev => ({
       ...prev,
       [symbol]: data
     }))
   }, [])
   ```

#### Backend Fixes (`bitunix.py`):
1. **Added subscription tracking**:
   - Track active subscriptions in `_active_subscriptions` set
   - Skip duplicate subscription requests
   - Clear subscriptions on disconnect

2. **Subscription deduplication**:
   ```python
   # Create a unique key for this subscription
   sub_key = f"{channel.get('symbol', '')}-{channel.get('ch', '')}"
   if sub_key not in self._active_subscriptions:
       filtered_channels.append(channel)
       self._active_subscriptions.add(sub_key)
   ```

## Testing the Fixes

1. Start the platform:
   ```bash
   ./start_trading_platform.sh
   ```

2. Check for improvements:
   - No more repeated "Sending subscribe request" logs
   - Order operations should work without 400 errors
   - WebSocket subscriptions should be stable

## Result

The system should now:
- Only subscribe to each symbol once
- Not re-subscribe when components re-render
- Properly handle order operations
- Have much cleaner logs without spam