# Python Exchange Clients

A unified Python library for interacting with multiple cryptocurrency exchanges (LMEX and BitUnix) with a consistent interface.

## Features

- **Unified Interface**: Common protocol for all exchanges
- **Symbol Precision Management**: Automatic handling of decimal places for prices and quantities
- **Contract Size Conversion**: Proper handling of different contract sizes for futures trading
- **WebSocket Support**: Real-time data streaming (where supported)
- **Grid Bot Support**: Create and manage grid trading bots on LMEX
- **Type Safety**: Full type hints for better IDE support

## Installation

```bash
pip install python-exchange-clients
```

## Quick Start

### Basic Setup

1. Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

2. Import and use the exchanges:

```python
from exchanges.lmex import LMEXExchange
from exchanges.bitunix import BitUnixExchange
from exchanges.base import ExchangeOrderRequest

# Initialize exchanges
lmex = LMEXExchange()
bitunix = BitUnixExchange()
```

### Fetching Market Data

```python
# Fetch all tickers
def handle_tickers(status, tickers):
    if status == "success":
        for ticker in tickers:
            print(f"{ticker.symbol}: ${ticker.lastPrice}")
    else:
        print(f"Error: {tickers}")

lmex.fetchTickers(handle_tickers)
```

### Placing Orders

```python
# Create an order request
order_request = ExchangeOrderRequest(
    symbol="BTC-PERP",
    side="LONG",
    orderType="LIMIT",
    qty=0.001,  # BTC amount
    price=65000.0,
    timeInForce="GTC"
)

# Place the order
def handle_order(status, response):
    if status == "success":
        print(f"Order placed: {response.orderId}")
    else:
        print(f"Order failed: {response}")

lmex.placeOrder(order_request, handle_order)
```

### Managing Positions

```python
# Fetch open positions
def handle_positions(status, positions):
    if status == "success":
        for pos in positions:
            print(f"{pos.symbol}: {pos.size} @ {pos.entryPrice}, PnL: {pos.pnl}")
    else:
        print(f"Error: {positions}")

lmex.fetchPositions(handle_positions)
```

### Account Information

```python
# Fetch account balance
def handle_balance(status, balances):
    if status == "success":
        for balance in balances:
            print(f"{balance.asset}: {balance.available} available, {balance.locked} locked")
    else:
        print(f"Error: {balances}")

lmex.fetchBalance(handle_balance)

# Fetch account equity
def handle_equity(status, equity):
    if status == "success":
        print(f"Total equity: ${equity}")
    else:
        print(f"Error: {equity}")

lmex.fetchAccountEquity(handle_equity)
```

### Grid Bot Trading (LMEX Only)

```python
# Create a grid bot
def handle_grid_bot(error, result):
    if error:
        print(f"Error creating grid bot: {error}")
    else:
        print(f"Grid bot created: {result}")

lmex.createGridBot(
    symbol="BTC-PERP",
    direction="LONG",
    upper_price=70000.0,
    lower_price=60000.0,
    leverage=10,
    wallet_mode="CROSS",
    grid_number=20,
    initial_margin=1000.0,  # USDT
    cancel_all_on_stop=True,
    close_all_on_stop=True,
    completion=handle_grid_bot
)

# Fetch existing grid bots
def handle_grid_bots(error, bots):
    if error:
        print(f"Error: {error}")
    else:
        for bot in bots:
            print(f"Bot {bot['tradingBotId']}: {bot['symbol']} {bot['direction']}")
            print(f"  Total profit: ${bot['totalProfitInUsdt']}")

lmex.fetchGridBots(handle_grid_bots)
```

### Advanced Features

#### Setting Leverage

```python
def handle_leverage(status, result):
    if status == "success":
        print(f"Leverage set: {result}")
    else:
        print(f"Error: {result}")

lmex.setLeverage("BTC-PERP", 20, completion=handle_leverage)
```

#### Fetching Order History

```python
import time

# Get orders from last 24 hours
end_time = int(time.time() * 1000)
start_time = end_time - (24 * 60 * 60 * 1000)

def handle_history(status, orders):
    if status == "success":
        for order in orders:
            print(f"Order: {order}")
    else:
        print(f"Error: {orders}")

lmex.fetchHistoryOrders(
    symbol="BTC-PERP",
    startTime=start_time,
    endTime=end_time,
    limit=50,
    completion=handle_history
)
```

#### Canceling Orders

```python
def handle_cancel(status, result):
    if status == "success":
        print(f"Order canceled: {result}")
    else:
        print(f"Error: {result}")

lmex.cancelOrder(
    orderID="12345678",
    symbol="BTC-PERP",
    completion=handle_cancel
)
```

## Symbol Precision

The library automatically handles decimal precision for different symbols:

```python
from exchanges.utils.precision import SymbolPrecisionManager

# Get precision for a symbol
precision_manager = SymbolPrecisionManager.get_instance("LMEX")
price_precision = precision_manager.get_price_precision("BTC-PERP")
qty_precision = precision_manager.get_quantity_precision("BTC-PERP")

print(f"BTC-PERP price precision: {price_precision} decimals")
print(f"BTC-PERP quantity precision: {qty_precision} decimals")
```

## Contract Size Handling

The library automatically converts between asset amounts and contract sizes:

```python
# When placing an order for DOGE-PERP with contract size 1.0
order_request = ExchangeOrderRequest(
    symbol="DOGE-PERP",
    side="LONG",
    orderType="LIMIT",
    qty=1000,  # 1000 DOGE
    price=0.35,
    timeInForce="GTC"
)
# The library will automatically convert to 1000 contracts
```

## Error Handling

All callbacks follow a consistent pattern:

```python
def callback(status, result):
    if status == "success":
        # Handle successful result
        process_data(result)
    else:
        # Handle error (result is the exception)
        print(f"Error: {result}")
        # Can check specific error types
        if "Insufficient balance" in str(result):
            handle_insufficient_balance()
```

## Environment Variables

The library uses the following environment variables:

- `LMEX_API_KEY`: Your LMEX API key
- `LMEX_SECRET_KEY`: Your LMEX secret key
- `LMEX_BEARER_TOKEN`: Optional LMEX bearer token for grid bot features
- `BITUNIX_API_KEY`: Your BitUnix API key
- `BITUNIX_SECRET_KEY`: Your BitUnix secret key
- `BITUNIX_PASSPHRASE`: Your BitUnix passphrase

## Testing

Run the test suite:

```bash
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and feature requests, please use the GitHub issue tracker.