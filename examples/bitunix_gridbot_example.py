#!/usr/bin/env python3
"""BitUnix Grid Bot Example"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.bitunix import BitUnixExchange
from gridbot import GridBot, GridBotConfig, GridType, PositionDirection


def main():
    """Run BitUnix grid bot example"""
    print("=== BitUnix Grid Bot Example ===\n")
    
    # Initialize exchange
    exchange = BitUnixExchange()
    
    # Create configuration
    config_manager = GridBotConfig()
    
    # Example 1: Conservative BTC grid
    btc_config = config_manager.from_dict({
        'symbol': 'BTCUSDT',
        'grid_type': GridType.ARITHMETIC,
        'position_direction': PositionDirection.NEUTRAL,
        'upper_price': 45000,
        'lower_price': 42000,
        'grid_count': 20,
        'total_investment': 1000,
        'leverage': 1,
        'stop_loss': 40000,
        'max_drawdown_percentage': 10,
        'post_only': True
    })
    
    print("Configuration Summary:")
    print(f"Symbol: {btc_config.symbol}")
    print(f"Range: ${btc_config.lower_price} - ${btc_config.upper_price}")
    print(f"Grid Count: {btc_config.grid_count}")
    print(f"Grid Spacing: ${btc_config.grid_spacing:.2f}")
    print(f"Investment per Grid: ${btc_config.investment_per_grid:.2f}")
    print(f"Stop Loss: ${btc_config.stop_loss}")
    print()
    
    # Create grid bot
    bot = GridBot(exchange, btc_config, persistence_path="bitunix_btc_gridbot.db")
    
    # Set up callbacks
    def on_trade(order):
        print(f"✅ Trade: {order.side.value} {order.quantity} @ ${order.fill_price}")
    
    def on_state_change(state):
        print(f"📊 State: {state.value}")
    
    def on_error(error):
        print(f"❌ Error: {error}")
    
    bot.on_grid_trade = on_trade
    bot.on_state_change = on_state_change
    bot.on_error = on_error
    
    # Example 2: Get current market price and suggest parameters
    print("Fetching current market data...")
    
    def ticker_callback(status, data):
        if status == "success":
            for ticker in data:
                if ticker.symbol == "BTCUSDT":
                    current_price = ticker.lastPrice
                    print(f"Current BTC Price: ${current_price:.2f}")
                    
                    # Suggest grid parameters based on volatility
                    # (In real implementation, calculate actual volatility)
                    volatility = 5  # Example: 5% daily volatility
                    
                    suggested = bot.calculator.suggest_grid_parameters(current_price, volatility)
                    print(f"\nSuggested Parameters:")
                    print(f"  Lower Price: ${suggested['lower_price']}")
                    print(f"  Upper Price: ${suggested['upper_price']}")
                    print(f"  Grid Count: {suggested['grid_count']}")
                    print(f"  Grid Type: {suggested['grid_type'].value}")
                    break
    
    exchange.fetchTickers(ticker_callback)
    
    # Example 3: Dry run to show what orders would be placed
    print("\n\nDry Run - Orders that would be placed:")
    print("-" * 60)
    
    # Calculate grid levels
    grid_levels = bot.calculator.calculate_grid_levels(43500)  # Example current price
    
    # Show initial orders
    initial_orders = bot.calculator.get_initial_orders(grid_levels, 43500)
    
    buy_orders = [o for o in initial_orders if o.side.value == "BUY"]
    sell_orders = [o for o in initial_orders if o.side.value == "SELL"]
    
    print(f"\nBuy Orders ({len(buy_orders)}):")
    for order in sorted(buy_orders, key=lambda x: x.price, reverse=True)[:5]:
        print(f"  ${order.price:.2f} x {order.quantity:.3f}")
    if len(buy_orders) > 5:
        print(f"  ... and {len(buy_orders) - 5} more")
    
    print(f"\nSell Orders ({len(sell_orders)}):")
    for order in sorted(sell_orders, key=lambda x: x.price)[:5]:
        print(f"  ${order.price:.2f} x {order.quantity:.3f}")
    if len(sell_orders) > 5:
        print(f"  ... and {len(sell_orders) - 5} more")
    
    # Example 4: Risk calculations
    print("\n\nRisk Analysis:")
    print("-" * 60)
    
    # Maximum loss if stop loss is hit
    if btc_config.stop_loss:
        max_loss_pct = ((btc_config.lower_price - btc_config.stop_loss) / btc_config.lower_price) * 100
        max_loss_amount = btc_config.total_investment * (max_loss_pct / 100)
        print(f"Maximum Loss (if stop loss hit): ${max_loss_amount:.2f} ({max_loss_pct:.1f}%)")
    
    # Expected profit per grid trade
    fee_rate = 0.001  # 0.1%
    grid_profit_pct = ((btc_config.grid_spacing / btc_config.lower_price) * 100) - (2 * fee_rate * 100)
    grid_profit_amount = btc_config.investment_per_grid * (grid_profit_pct / 100)
    print(f"Expected Profit per Grid Trade: ${grid_profit_amount:.2f} ({grid_profit_pct:.2f}%)")
    
    # Break-even trades
    if btc_config.stop_loss and grid_profit_amount > 0:
        breakeven_trades = int(max_loss_amount / grid_profit_amount) + 1
        print(f"Trades needed to break even from stop loss: {breakeven_trades}")
    
    print("\n" + "=" * 60)
    print("This is a dry run example. To start the actual bot:")
    print("1. Ensure you have API keys configured")
    print("2. Review and adjust the configuration")
    print("3. Call bot.start() to begin trading")
    print("4. Monitor with bot.get_status()")
    print("5. Stop with bot.stop()")
    
    # Example 5: Show how to start the bot (commented out for safety)
    """
    # To actually start the bot:
    print("\nStarting Grid Bot...")
    bot.start()
    
    # Keep running until interrupted
    try:
        while bot.state == GridState.RUNNING:
            time.sleep(10)
            status = bot.get_status()
            print(f"Status: {status['statistics']['trades']} trades, "
                  f"${status['statistics']['total_profit']:.2f} profit")
    except KeyboardInterrupt:
        print("\nStopping bot...")
        bot.stop()
    """


if __name__ == "__main__":
    main()