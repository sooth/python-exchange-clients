# WebSocket Architecture Analysis Report

## Executive Summary

The frontend currently uses **three separate WebSocket systems** operating independently:
1. **Backend WebSocket** (`websocket.ts`) - For general trading data
2. **LMEX Chart WebSocket** (`lmexChartWebSocket.ts`) - For real-time candle data
3. **LMEX Orderbook WebSocket** (`lmexOrderbookWebSocket.ts`) - For orderbook and price updates

## Current WebSocket Flow

### 1. Backend WebSocket System
- **URL**: `ws://localhost:8001/api/v1/ws/connect`
- **Usage**: Used by OrderBook, MarketInfo, Positions, Orders, Trades components
- **Pattern**: Singleton with pub/sub via EventTarget
- **Components**:
  - `OrderBook.tsx` - Subscribes to 'orderbook' channel
  - `MarketInfo.tsx` - Subscribes to 'ticker' channel
  - `Positions.tsx` - Subscribes to 'positions' channel
  - `OpenOrders.tsx` - Subscribes to 'orders' channel
  - `RecentTrades.tsx` - Subscribes to 'trades' channel

### 2. LMEX Chart WebSocket
- **URL**: `wss://ws.lmex.io/ws/futures` (for futures)
- **Usage**: Used exclusively by ChartContainer for trade aggregation
- **Pattern**: Singleton pattern via `getChartWebSocket()`
- **Purpose**: Subscribes to `tradeHistoryApiV2` to aggregate trades into candles
- **Issue**: Only provides trade data, not direct price updates

### 3. LMEX Orderbook WebSocket
- **URL**: `wss://ws.lmex.io/ws/oss/futures` (for futures)
- **Usage**: Used by ChartContainer and MarketInfo
- **Pattern**: Attempted singleton but creates multiple instances
- **Purpose**: Subscribes to orderbook updates for bid/ask prices
- **Critical Issue**: ChartContainer creates a new instance instead of using singleton

## Data Flow Issues

### ChartContainer.tsx Issues:
1. **Multiple Connections**: Creates 3 WebSocket connections:
   - Chart WebSocket (singleton) - for trade data
   - Orderbook WebSocket (singleton) - potentially shared
   - **NEW Orderbook WebSocket instance** (line 285) - dedicated instance for price updates

2. **Price Update Logic** (lines 273-374):
   ```typescript
   // Creates a new orderbook WebSocket instance for chart updates
   const ws = new (getOrderbookWebSocket(true).constructor as any)(true)
   ```
   This bypasses the singleton pattern and creates a duplicate connection.

3. **Trade vs Price Confusion**:
   - Trade data is used for candle aggregation (volume, OHLC)
   - Price data (bid/ask) is used for real-time price updates
   - These are mixed in the same component without clear separation

### MarketInfo.tsx:
- Uses both backend WebSocket (ticker) and LMEX orderbook WebSocket (bid/ask)
- Properly uses singleton pattern for orderbook WebSocket
- Falls back to ticker data if no WebSocket bid/ask available

## Identified Issues

### 1. No Rate Limiting
- **Finding**: No throttling, debouncing, or rate limiting found in any WebSocket implementation
- **Risk**: Can overwhelm the UI with updates, especially during high-frequency trading
- **Impact**: Performance degradation, potential browser freezing

### 2. Multiple WebSocket Instances
- **ChartContainer** creates 3 connections (1 duplicate)
- **MarketInfo** uses 2 connections
- **Total connections per user**: Up to 5 WebSocket connections
- **Impact**: Resource waste, potential rate limiting from exchange

### 3. Error Recovery Gaps
- Each WebSocket has its own reconnection logic
- No coordinated error handling
- No backpressure handling
- Exponential backoff varies between implementations

### 4. Blocking Scenarios
- Synchronous message processing in all WebSocket handlers
- No queue management for high-frequency updates
- UI updates directly tied to WebSocket messages

### 5. Architectural Issues
- Mixing singleton and instance patterns
- No clear separation between data sources
- Duplicate subscriptions possible
- No WebSocket connection pooling

## Reconnection Logic Comparison

### Backend WebSocket:
- Max attempts: 5
- Exponential backoff: 1s * 2^n (max 30s)
- Ping interval: 30s

### LMEX Chart WebSocket:
- Max attempts: 5
- Exponential backoff: 1s * 2^n (max 30s)
- Ping interval: 30s
- Handles resubscription on reconnect

### LMEX Orderbook WebSocket:
- Max attempts: 5
- Exponential backoff: 1s * 2^n (max 30s)
- Ping interval: 30s
- Uses listener pattern for multiple subscribers

## Performance Concerns

1. **ChartContainer Price Updates**:
   - Updates chart on every bid/ask change
   - No throttling of chart updates
   - Can cause excessive re-renders

2. **OrderBook Component**:
   - Processes full orderbook on every update
   - No incremental updates
   - Recalculates depth on every message

3. **Memory Leaks**:
   - ChartContainer creates new WebSocket instance without proper cleanup
   - Potential listener accumulation in singleton instances

## Recommendations

### Immediate Fixes:
1. Fix ChartContainer to use singleton orderbook WebSocket
2. Implement rate limiting/throttling for UI updates
3. Add proper cleanup for all WebSocket connections

### Architectural Improvements:
1. Consolidate to single WebSocket connection per exchange
2. Implement message queue with backpressure handling
3. Add centralized error handling and recovery
4. Separate data processing from UI updates

### Performance Optimizations:
1. Implement update batching
2. Add request/response throttling
3. Use Web Workers for data processing
4. Implement incremental updates for orderbook

## Critical Code Sections

### ChartContainer.tsx (Line 285):
```typescript
// BUG: Creates new instance instead of using singleton
const ws = new (getOrderbookWebSocket(true).constructor as any)(true)
```

### lmexOrderbookWebSocket.ts (Line 36):
```typescript
export class LMEXOrderbookWebSocket {
  // Has singleton pattern but bypassed by ChartContainer
}
```

### websocket.ts (Line 186):
```typescript
// Backend WebSocket singleton - properly implemented
let wsClient: WebSocketClient | null = null
```

## Conclusion

The current WebSocket architecture suffers from:
- **Fragmentation**: Three separate systems with no coordination
- **Duplication**: Multiple connections to same data sources
- **Performance**: No rate limiting or update batching
- **Reliability**: Independent error handling with gaps
- **Maintainability**: Mixed patterns and unclear data flow

Priority should be given to consolidating WebSocket connections and implementing proper rate limiting to prevent UI performance issues.