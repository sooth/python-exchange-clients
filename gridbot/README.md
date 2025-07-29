# Grid Bot Trading System

A comprehensive grid trading bot implementation for cryptocurrency exchanges, built on top of the exchange abstraction layer.

## Features

### Core Features
- ✅ **Arithmetic and Geometric Grids** - Equal interval or percentage-based grid spacing
- ✅ **Multiple Position Directions** - Long-only, short-only, or neutral (both directions)
- ✅ **Advanced Order Management** - Bulk order placement with rate limiting
- ✅ **Real-time Position Tracking** - Track P&L, trades, and performance metrics
- ✅ **Risk Management** - Stop loss, take profit, and drawdown controls
- ✅ **State Persistence** - Resume bot after restarts
- ✅ **CLI Interface** - Interactive command-line control

### Exchange Support
- BitUnix (Primary)
- LMEX (Secondary)

## Quick Start

### 1. Installation

```bash
# Ensure you have the exchange clients installed
pip install -r requirements.txt
```

### 2. Configuration

Create a configuration file (e.g., `btc_grid.json`):

```json
{
  "symbol": "BTCUSDT",
  "grid_type": "arithmetic",
  "position_direction": "NEUTRAL",
  "upper_price": 45000,
  "lower_price": 42000,
  "grid_count": 20,
  "total_investment": 1000,
  "leverage": 1,
  "stop_loss": 40000,
  "max_drawdown_percentage": 20
}
```

### 3. Run the Bot

```bash
# Using configuration file
python -m gridbot.cli start --config btc_grid.json --exchange bitunix

# Using interactive wizard
python -m gridbot.cli start --wizard --exchange bitunix
```

### 4. Monitor Performance

```bash
# Check status
python -m gridbot.cli status

# Real-time monitoring
python -m gridbot.cli monitor

# View trade history
python -m gridbot.cli history --limit 20
```

## Grid Bot Strategies

### Conservative Strategy
- Wide price range (10-20%)
- Lower grid count (10-20)
- No leverage
- Stop loss set 5-10% below range

### Aggressive Strategy
- Tight price range (5-10%)
- Higher grid count (30-50)
- Moderate leverage (2-5x)
- Trailing features enabled

### Scalping Strategy
- Very tight range (2-5%)
- Maximum grid count (50-100)
- Higher leverage (5-10x)
- Quick profit targets

## Configuration Options

### Basic Settings
- `symbol`: Trading pair (e.g., "BTCUSDT")
- `grid_type`: "arithmetic" or "geometric"
- `position_direction`: "LONG", "SHORT", or "NEUTRAL"
- `upper_price`: Upper price boundary
- `lower_price`: Lower price boundary
- `grid_count`: Number of grid levels
- `total_investment`: Total capital to invest

### Risk Management
- `stop_loss`: Stop loss price
- `take_profit`: Take profit percentage
- `max_position_size`: Maximum position value
- `max_drawdown_percentage`: Maximum allowed drawdown

### Advanced Settings
- `leverage`: Leverage multiplier (1-125)
- `post_only`: Use post-only orders
- `trailing_up/trailing_down`: Enable grid trailing
- `cancel_orders_on_stop`: Cancel orders when stopping
- `close_position_on_stop`: Close position when stopping

## Architecture

```
gridbot/
├── core.py          # Main orchestrator
├── calculator.py    # Grid calculations
├── order_manager.py # Order lifecycle
├── position_tracker.py # Position & P&L
├── risk_manager.py  # Risk controls
├── config.py        # Configuration
├── persistence.py   # State storage
├── cli.py          # CLI interface
└── types.py        # Data structures
```

## Performance Metrics

The bot tracks:
- Total trades executed
- Win rate percentage
- Grid profit (from completed trades)
- Position profit (unrealized P&L)
- Total volume traded
- Fees paid
- ROI and Sharpe ratio
- Maximum drawdown

## Safety Features

1. **Pre-trade Validation**
   - Configuration validation
   - Balance checks
   - Market condition assessment

2. **Runtime Protection**
   - Circuit breakers
   - Consecutive loss limits
   - Position size limits

3. **Error Handling**
   - Automatic retry logic
   - Graceful degradation
   - State recovery

## Development

### Running Tests

```bash
python -m pytest tests/test_gridbot.py -v
```

### Example Usage

```python
from exchanges.bitunix import BitUnixExchange
from gridbot import GridBot, GridBotConfig, GridType, PositionDirection

# Create configuration
config = GridBotConfig().from_dict({
    'symbol': 'BTCUSDT',
    'grid_type': GridType.ARITHMETIC,
    'position_direction': PositionDirection.NEUTRAL,
    'upper_price': 45000,
    'lower_price': 42000,
    'grid_count': 20,
    'total_investment': 1000
})

# Initialize bot
exchange = BitUnixExchange()
bot = GridBot(exchange, config)

# Set callbacks
bot.on_grid_trade = lambda order: print(f"Trade: {order}")
bot.on_error = lambda error: print(f"Error: {error}")

# Start trading
bot.start()
```

## Best Practices

1. **Start Small** - Test with minimal investment first
2. **Monitor Actively** - Check bot status regularly
3. **Set Stop Loss** - Always use risk management
4. **Review Performance** - Analyze trade history
5. **Adjust Parameters** - Optimize based on market conditions

## Troubleshooting

### Bot Won't Start
- Check API keys are configured
- Verify sufficient balance
- Ensure price range is valid

### No Trades Executing
- Check if price is within grid range
- Verify orders are being placed
- Check exchange connectivity

### High Losses
- Review risk settings
- Check market volatility
- Consider wider grid spacing

## Disclaimer

Grid trading involves risk. This bot is provided as-is without warranty. Always test thoroughly and never invest more than you can afford to lose.