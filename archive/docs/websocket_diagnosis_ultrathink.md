# WebSocket and Subscription Issues - Diagnosis and Fix Plan

## Problem Analysis

### Observed Issues:
1. **Subscription limit spam** - "Subscription limit reached (250 + 1 > 250)" logged hundreds of times
2. **Orders API error** - "'ExchangeOrder' object has no attribute 'clientOrderId'"
3. **Excessive logging** - Same errors repeated continuously, suggesting a loop

### Possible Root Causes (5-7):
1. **Frontend subscribing to all 470 tickers** - Would immediately exceed 250 limit
2. **No subscription deduplication** - Same symbols being subscribed multiple times
3. **Retry loop without backoff** - Failed subscriptions immediately retried
4. **Multiple UI components subscribing** - Each component (market list, chart, etc) subscribing independently
5. **WebSocket reconnection re-subscribing** - Not clearing old subscriptions on reconnect
6. **Backend forwarding all requests** - No filtering or batching at backend level
7. **Attribute mismatch in models** - ExchangeOrder has different attribute names

### Most Likely Causes (1-2):
1. **Frontend subscribing to all tickers** - Most likely given we have 470 pairs and 250 limit
2. **Subscription loop without proper state management** - Explains the continuous spam

## Phase 1: Investigate Subscription Pattern

### 1.1 Analyze Frontend Subscription Logic
- [x] Check what triggers WebSocket subscriptions in frontend
- [x] Identify which components subscribe to market data
- [x] Count how many subscriptions are attempted on page load
- [x] Check if market list subscribes to all tickers

### 1.2 Trace Subscription Flow
- [ ] Add logging to track subscription requests from frontend to backend
- [ ] Log unique symbols being subscribed
- [ ] Identify if duplicates are being sent
- [ ] Check subscription timing and frequency

## Phase 2: Fix Order Attribute Error

### 2.1 Investigate ExchangeOrder Model
- [x] Check ExchangeOrder class definition
- [x] Find what attribute name is used (clientId vs clientOrderId)
- [x] Update exchange_manager.py to use correct attribute
- [ ] Test order fetching after fix

## Phase 3: Implement Subscription Management

### 3.1 Frontend Subscription Limiting
- [x] Implement subscription limiting for market list (show top 30 pairs)
- [x] Only subscribe to visible tickers
- [x] Add selected symbol subscription
- [ ] Add lazy loading for additional pairs
- [ ] Implement subscription cleanup on component unmount

### 3.2 Backend Subscription Filtering
- [ ] Track active subscriptions per client
- [ ] Reject duplicate subscription requests
- [ ] Implement subscription prioritization
- [ ] Add subscription limit per client (e.g., 50 symbols max)

### 3.3 Smart Subscription Strategy
- [ ] Subscribe only to selected trading pair for detailed data
- [ ] Use polling for market list instead of WebSocket
- [ ] Batch ticker updates in intervals
- [ ] Implement subscription queuing with priority

## Phase 4: Optimize WebSocket Performance

### 4.1 Rate Limiting Improvements
- [ ] Ensure rate limiter is working correctly
- [ ] Add circuit breaker for subscription failures
- [ ] Implement exponential backoff for retries
- [ ] Add subscription cooldown period

### 4.2 Connection Management
- [ ] Clear all subscriptions on disconnect
- [ ] Prevent re-subscription storms on reconnect
- [ ] Implement connection state tracking
- [ ] Add subscription state persistence

## Phase 5: Testing and Validation

### 5.1 Load Testing
- [ ] Test with limited subscriptions (< 50)
- [ ] Monitor system resource usage
- [ ] Verify no subscription spam in logs
- [ ] Check WebSocket stability

### 5.2 Integration Testing
- [ ] Test order fetching after fixes
- [ ] Verify market data updates working
- [ ] Test reconnection scenarios
- [ ] Validate error handling

## Implementation Order:
1. Fix ExchangeOrder attribute error (quick win)
2. Limit frontend subscriptions to prevent spam
3. Implement proper subscription management
4. Optimize and test

## Success Criteria:
- No subscription limit errors in logs
- Orders API working correctly
- WebSocket stable with reasonable resource usage
- Frontend showing real-time data for selected symbols