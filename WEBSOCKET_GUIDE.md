# WebSocket Implementation Guide

## Overview

This guide covers the WebSocket implementation for the Python Exchange Clients library, specifically for BitUnix exchange. WebSocket support provides real-time market data and account updates, replacing the need for constant REST API polling.

## Features

### Real-time Data Streams
- **Ticker Updates**: Live price, volume, and 24h statistics
- **Order Book**: Real-time bid/ask levels
- **Trade Feed**: Live trade executions
- **Order Updates**: Instant order status changes
- **Position Updates**: Real-time position and P&L
- **Balance Updates**: Live account balance changes

### Technical Features
- Automatic reconnection with exponential backoff
- Thread-safe message handling
- Heartbeat/ping-pong for connection health
- Subscription management
- Authentication for private channels
- Graceful degradation to REST API

## Architecture

### Abstraction Layer (`exchanges/base.py`)
- `WebSocketState`: Connection state enumeration
- `WebSocketSubscription`: Channel subscription configuration
- `WebSocketMessage`: Unified message format
- `ExchangeInterface`: WebSocket method definitions

### Base WebSocket Manager (`exchanges/websocket_manager.py`)
- `BaseWebSocketManager`: Abstract base class with common functionality
- Connection lifecycle management
- Automatic reconnection logic
- Message queue and processing
- Subscription tracking

### BitUnix Implementation (`exchanges/bitunix.py`)
- `BitUnixWebSocketManager`: BitUnix-specific implementation
- Public/private channel support
- Authentication handling
- Message parsing and transformation

## Usage

### Basic WebSocket Connection

```python
from exchanges.bitunix import BitUnixExchange

# Initialize exchange
exchange = BitUnixExchange()

# Define callbacks
def on_message(message):
    print(f"Channel: {message.channel}, Symbol: {message.symbol}")
    print(f"Data: {message.data}")

def on_state_change(state):
    print(f"WebSocket state: {state}")

def on_error(error):
    print(f"WebSocket error: {error}")

# Connect to WebSocket
exchange.connectWebSocket(
    on_message=on_message,
    on_state_change=on_state_change,
    on_error=on_error
)

# Subscribe to channels
from exchanges.base import WebSocketSubscription

subscriptions = [
    WebSocketSubscription(channel="ticker", symbol="BTCUSDT"),
    WebSocketSubscription(channel="orderbook", symbol="BTCUSDT", params={"depth": 20}),
    WebSocketSubscription(channel="trades", symbol="BTCUSDT")
]

exchange.subscribeWebSocket(subscriptions)
```

### Grid Bot with WebSocket

The grid bot automatically uses WebSocket when available:

```python
from gridbot import GridBot, GridBotConfig

# Create grid bot
bot = GridBot(exchange, config)

# WebSocket is enabled by default
bot.use_websocket = True  # Can be disabled if needed

# Start bot - will connect to WebSocket automatically
bot.start()
```

### Testing WebSocket

Run the test script to verify WebSocket functionality:

```bash
python test_websocket.py
```

Test options:
1. Public channels (no authentication required)
2. Private channels (requires API keys)
3. Reconnection handling
4. All tests

## Configuration

### API Keys for Private Channels

Private channels (orders, positions, balance) require API key authentication. Configure your keys in `exchanges/utils/api_keys.json`:

```json
{
  "BitUnix": {
    "apiKey": "your-api-key",
    "secretKey": "your-secret-key"
  }
}
```

### WebSocket URLs

- Public: `wss://fapi.bitunix.com/public/`
- Private: `wss://fapi.bitunix.com/private/`

## Channel Reference

### Public Channels

#### Ticker
```python
WebSocketSubscription(channel="ticker", symbol="BTCUSDT")
```
Returns: Real-time price, volume, 24h statistics

#### Order Book
```python
WebSocketSubscription(channel="orderbook", symbol="BTCUSDT", params={"depth": 20})
```
Returns: Bid/ask levels with specified depth

#### Trades
```python
WebSocketSubscription(channel="trades", symbol="BTCUSDT")
```
Returns: Real-time trade executions

### Private Channels (Requires Authentication)

#### Orders
```python
WebSocketSubscription(channel="orders")
```
Returns: Order status updates for all symbols

#### Positions
```python
WebSocketSubscription(channel="positions")
```
Returns: Position updates for all symbols

#### Balance
```python
WebSocketSubscription(channel="balance")
```
Returns: Account balance updates

## Troubleshooting

### Connection Issues

1. **Check network connectivity**
   ```bash
   # Test WebSocket endpoint
   wscat -c wss://fapi.bitunix.com/public/
   ```

2. **Verify API keys** (for private channels)
   - Ensure keys are properly configured
   - Check key permissions

3. **Enable logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Common Error Messages

- `"Cannot connect to private channels without API credentials"`: Configure API keys
- `"WebSocket disconnected"`: Check network, will auto-reconnect
- `"Authentication failed"`: Verify API key and secret
- `"Subscription failed"`: Check symbol format and channel name

### Performance Tips

1. **Subscribe only to needed channels** - Reduce bandwidth and processing
2. **Use appropriate depths for order book** - Start with depth=5 or 10
3. **Monitor connection state** - React to disconnections appropriately
4. **Handle message bursts** - Messages are queued and processed sequentially

## Grid Bot Integration

The grid bot leverages WebSocket for:

1. **Real-time price monitoring** - No polling delay
2. **Instant order fill detection** - Immediate reaction to fills
3. **Live position tracking** - Real-time P&L updates
4. **Connection status display** - Shows WebSocket state

Benefits:
- Reduced latency (< 100ms vs 1s polling)
- Lower API rate limit usage
- More accurate fill detection
- Better market reaction time

## Example Applications

### 1. Real-time Price Monitor
See `test_websocket.py` for a complete example

### 2. Grid Bot with WebSocket
See `examples/gridbot_websocket_example.py`

### 3. Custom Trading Bot
```python
# Subscribe to multiple symbols
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
subscriptions = [
    WebSocketSubscription(channel="ticker", symbol=symbol)
    for symbol in symbols
]
exchange.subscribeWebSocket(subscriptions)
```

## Best Practices

1. **Always implement all three callbacks** (message, state, error)
2. **Handle reconnections gracefully** - State will change to RECONNECTING
3. **Process messages quickly** - Don't block in message handler
4. **Monitor connection health** - Check state periodically
5. **Use REST API as fallback** - For non-streaming operations
6. **Respect rate limits** - Max 300 subscriptions per connection

## Future Enhancements

- [ ] Support for additional exchanges
- [ ] WebSocket connection pooling
- [ ] Built-in message rate limiting
- [ ] Enhanced error recovery
- [ ] Message replay on reconnection