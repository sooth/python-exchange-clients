# Python Exchange Clients

A Python client library for cryptocurrency exchanges, currently supporting LMEX and BitUnix.

## Features

- Unified interface for multiple exchanges
- Support for spot and futures trading
- WebSocket support for real-time data
- Grid bot creation and management (LMEX)
- Comprehensive order management
- Symbol precision handling
- Async and sync operation modes

## Installation

```bash
pip install python-exchange-clients
```

## Quick Start

```python
from exchanges import LMEXExchange, BitUnixExchange

# Initialize exchange
lmex = LMEXExchange()

# Fetch tickers
def ticker_callback(error, tickers):
    if error:
        print(f"Error: {error}")
    else:
        for ticker in tickers:
            print(f"{ticker.symbol}: {ticker.last_price}")

lmex.fetchTickers(ticker_callback)

# Place an order
from exchanges.base import ExchangeOrderRequest

order = ExchangeOrderRequest(
    symbol="BTC-PERP",
    side="BUY",
    orderType="LIMIT",
    qty=0.001,
    price=45000.0,
    timeInForce="GTC"
)

def order_callback(error, response):
    if error:
        print(f"Order failed: {error}")
    else:
        print(f"Order placed: {response}")

lmex.placeOrder(order, order_callback)
```

## Supported Exchanges

### LMEX
- Futures trading
- Grid bot support
- WebSocket support (planned)
- Full order management

### BitUnix
- Futures trading
- WebSocket support
- Full order management

## Configuration

Set your API credentials in environment variables:

```bash
# LMEX
export LMEX_API_KEY="your_api_key"
export LMEX_SECRET_KEY="your_secret_key"
export LMEX_BEARER_TOKEN="your_bearer_token"  # For grid bots

# BitUnix
export BITUNIX_API_KEY="your_api_key"
export BITUNIX_SECRET_KEY="your_secret_key"
```

## Advanced Usage

### Grid Bot Creation (LMEX)

```python
lmex = LMEXExchange()

def bot_callback(error, data):
    if error:
        print(f"Failed to create bot: {error}")
    else:
        print(f"Bot created: {data}")

lmex.createGridBot(
    symbol="BTC-PERP",
    direction="LONG",
    upper_price=50000,
    lower_price=45000,
    leverage=10,
    wallet_mode="CROSS",
    grid_number=20,
    initial_margin=1000,
    cancel_all_on_stop=False,
    close_all_on_stop=False,
    completion=bot_callback
)
```

### Using Adapters for Async Operations

```python
from exchanges.adapters import LMEXAdapter
import asyncio

async def main():
    adapter = LMEXAdapter()
    
    # Fetch positions asynchronously
    positions = await adapter.fetch_positions()
    for position in positions:
        print(f"{position['symbol']}: {position['size']} @ {position['entryPrice']}")

asyncio.run(main())
```

## API Documentation

See the [full documentation](https://github.com/yourusername/python-exchange-clients/wiki) for detailed API reference.

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.