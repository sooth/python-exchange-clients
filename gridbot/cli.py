"""Grid Bot Command Line Interface"""

import argparse
import sys
import os
import time
import threading
from typing import Optional
from datetime import datetime

from exchanges.bitunix import BitUnixExchange
from exchanges.lmex import LMEXExchange
from .core import GridBot
from .config import GridBotConfig
from .types import GridState


class GridBotCLI:
    """Command line interface for Grid Bot"""
    
    def __init__(self):
        self.bot: Optional[GridBot] = None
        self.config_manager = GridBotConfig()
        self.running = False
        
    def run(self):
        """Run the CLI"""
        parser = argparse.ArgumentParser(description="Grid Bot Trading System")
        
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        
        # Start command
        start_parser = subparsers.add_parser('start', help='Start grid bot')
        start_parser.add_argument('--config', '-c', help='Configuration file path')
        start_parser.add_argument('--exchange', '-e', choices=['bitunix', 'lmex'], 
                                default='bitunix', help='Exchange to use')
        start_parser.add_argument('--wizard', '-w', action='store_true', 
                                help='Use configuration wizard')
        start_parser.add_argument('--resume', '-r', action='store_true',
                                help='Resume with existing positions/orders')
        start_parser.add_argument('--auto-resume', '-a', action='store_true',
                                help='Automatically resume with existing positions/orders')
        
        # Stop command
        subparsers.add_parser('stop', help='Stop grid bot')
        
        # Status command
        subparsers.add_parser('status', help='Show bot status')
        
        # Monitor command
        subparsers.add_parser('monitor', help='Monitor bot in real-time')
        
        # History command
        history_parser = subparsers.add_parser('history', help='Show trade history')
        history_parser.add_argument('--limit', '-l', type=int, default=10, 
                                  help='Number of trades to show')
        
        # Export command
        export_parser = subparsers.add_parser('export', help='Export bot data')
        export_parser.add_argument('output', help='Output file path')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        # Execute command
        command_method = getattr(self, f'cmd_{args.command}', None)
        if command_method:
            command_method(args)
        else:
            print(f"Unknown command: {args.command}")
    
    def cmd_start(self, args):
        """Start the grid bot"""
        if self.bot and self.bot.state == GridState.RUNNING:
            print("Grid bot is already running")
            return
        
        # Set auto-resume environment variable if requested
        if args.auto_resume or args.resume:
            os.environ['GRIDBOT_AUTO_RESUME'] = 'true'
        
        # Load or create configuration
        print(f"DEBUG: args.config = {args.config}")
        print(f"DEBUG: args.wizard = {args.wizard}")
        
        if args.config:
            print(f"Loading config from: {args.config}")
            config = self.config_manager.load_from_file(args.config)
        elif args.wizard:
            config = self.config_manager.create_from_wizard()
        else:
            print("Please provide a configuration file with --config or use --wizard")
            return
        
        # Initialize exchange
        if args.exchange == 'bitunix':
            exchange = BitUnixExchange()
        else:
            exchange = LMEXExchange()
        
        print(f"\nInitializing Grid Bot on {args.exchange.upper()}...")
        
        # Create bot
        persistence_path = f"gridbot_{config.symbol}_{args.exchange}.db"
        self.bot = GridBot(exchange, config, persistence_path)
        
        # Set up callbacks
        self.bot.on_grid_trade = self._on_grid_trade
        self.bot.on_state_change = self._on_state_change
        self.bot.on_error = self._on_error
        
        # Start bot
        self.bot.start()
        
        # Keep running
        self.running = True
        self._run_interactive_mode()
    
    def cmd_stop(self, args):
        """Stop the grid bot"""
        if not self.bot:
            print("No bot is running")
            return
        
        self.bot.stop()
        self.running = False
    
    def cmd_status(self, args):
        """Show bot status"""
        if not self.bot:
            print("No bot is running")
            return
        
        status = self.bot.get_status()
        self._print_status(status)
    
    def cmd_monitor(self, args):
        """Monitor bot in real-time"""
        if not self.bot:
            print("No bot is running")
            return
        
        print("Monitoring Grid Bot (Press Ctrl+C to stop)...")
        print("-" * 80)
        
        try:
            while True:
                # Clear screen
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Print header
                print(f"Grid Bot Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 80)
                
                # Get and print status
                status = self.bot.get_status()
                self._print_status(status)
                
                # Print recent trades
                recent_trades = self.bot.position_tracker.get_recent_trades(5)
                if recent_trades:
                    print("\nRecent Trades:")
                    print("-" * 80)
                    for trade in recent_trades:
                        completed_time = datetime.fromtimestamp(trade.completed_at).strftime('%H:%M:%S')
                        print(f"{completed_time} | Buy: ${trade.buy_order.fill_price:.2f} → "
                              f"Sell: ${trade.sell_order.fill_price:.2f} | "
                              f"Profit: ${trade.profit:.2f} ({trade.profit_percentage:.2f}%)")
                
                print("\nPress Ctrl+C to stop monitoring...")
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\nStopped monitoring")
    
    def cmd_history(self, args):
        """Show trade history"""
        if not self.bot:
            print("No bot is running")
            return
        
        trades = self.bot.position_tracker.get_recent_trades(args.limit)
        
        if not trades:
            print("No trades yet")
            return
        
        print(f"\nLast {len(trades)} trades:")
        print("-" * 80)
        print(f"{'Time':^20} | {'Buy Price':^10} | {'Sell Price':^10} | "
              f"{'Quantity':^10} | {'Profit':^10} | {'Profit %':^10}")
        print("-" * 80)
        
        for trade in trades:
            completed_time = datetime.fromtimestamp(trade.completed_at).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{completed_time:^20} | ${trade.buy_order.fill_price:^9.2f} | "
                  f"${trade.sell_order.fill_price:^9.2f} | "
                  f"{trade.buy_order.quantity:^10.3f} | "
                  f"${trade.profit:^9.2f} | {trade.profit_percentage:^9.2f}%")
        
        # Summary
        total_profit = sum(t.profit for t in trades)
        avg_profit = total_profit / len(trades) if trades else 0
        print("-" * 80)
        print(f"Total Profit: ${total_profit:.2f} | Average: ${avg_profit:.2f}")
    
    def cmd_export(self, args):
        """Export bot data"""
        if not self.bot:
            print("No bot is running")
            return
        
        if self.bot.persistence:
            self.bot.persistence.export_to_json(self.bot.config.symbol, args.output)
        else:
            print("No persistence configured")
    
    def _run_interactive_mode(self):
        """Run interactive mode while bot is running"""
        print("\nGrid Bot is running. Available commands:")
        print("  status - Show current status")
        print("  pause  - Pause the bot")
        print("  resume - Resume the bot")
        print("  stop   - Stop the bot")
        print("  quit   - Stop and exit")
        print("")
        
        while self.running:
            try:
                command = input("> ").strip().lower()
                
                if command == "status":
                    status = self.bot.get_status()
                    self._print_status(status)
                
                elif command == "pause":
                    self.bot.pause()
                
                elif command == "resume":
                    self.bot.resume()
                
                elif command == "stop" or command == "quit":
                    self.bot.stop()
                    self.running = False
                
                elif command == "":
                    continue
                
                else:
                    print(f"Unknown command: {command}")
                
            except KeyboardInterrupt:
                print("\nStopping bot...")
                self.bot.stop()
                self.running = False
            except EOFError:
                # Handle Ctrl+D
                self.running = False
    
    def _print_status(self, status: dict):
        """Print formatted status"""
        print(f"\n=== Grid Bot Status ===")
        print(f"State: {status['state'].upper()}")
        print(f"Symbol: {status['config']['symbol']}")
        print(f"Range: {status['config']['range']}")
        print(f"Grids: {status['config']['grids']}")
        print(f"Investment: ${status['config']['investment']}")
        
        print(f"\nPosition:")
        pos = status['position']
        print(f"  Size: {pos['size']} ({pos['side']})")
        print(f"  Entry: ${pos['entry_price']:.2f}")
        print(f"  Current: ${pos['current_price']:.2f}")
        print(f"  Unrealized P&L: ${pos['unrealized_pnl']:.2f} ({pos['pnl_percentage']:.2f}%)")
        print(f"  Realized P&L: ${pos['realized_pnl']:.2f}")
        
        print(f"\nOrders:")
        orders = status['orders']
        print(f"  Total: {orders['total_orders']}")
        print(f"  Buy: {orders['buy_orders']} (${orders['buy_value']:.2f})")
        print(f"  Sell: {orders['sell_orders']} (${orders['sell_value']:.2f})")
        
        print(f"\nStatistics:")
        stats = status['statistics']
        print(f"  Trades: {stats['trades']}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Total Profit: ${stats['total_profit']:.2f}")
        print(f"  Uptime: {stats['uptime_hours']:.1f} hours")
        
        if status['risk']['risk_triggered']:
            print(f"\n⚠️  RISK ALERT: {status['risk']['risk_reason']}")
    
    def _on_grid_trade(self, order):
        """Callback for grid trades"""
        print(f"\n✅ Trade executed: {order.side.value} {order.quantity} @ ${order.fill_price}")
    
    def _on_state_change(self, state):
        """Callback for state changes"""
        print(f"\n📊 State changed to: {state.value}")
    
    def _on_error(self, error):
        """Callback for errors"""
        print(f"\n❌ Error: {error}")


def main():
    """Main entry point"""
    cli = GridBotCLI()
    cli.run()


if __name__ == "__main__":
    main()