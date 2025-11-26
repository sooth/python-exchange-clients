#!/usr/bin/env python3
import sys
print(f"sys.argv: {sys.argv}")

from gridbot.cli import GridBotCLI
cli = GridBotCLI()

# Override run to debug
original_run = cli.run

def debug_run():
    print("=== CLI RUN DEBUG ===")
    import argparse
    parser = argparse.ArgumentParser(description="Grid Bot Trading System")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start grid bot')
    start_parser.add_argument('--config', '-c', help='Configuration file path')
    start_parser.add_argument('--wizard', '-w', action='store_true', help='Use configuration wizard')
    start_parser.add_argument('--resume', '-r', action='store_true', help='Resume')
    
    print(f"About to parse args: {sys.argv[1:]}")
    args = parser.parse_args(sys.argv[1:])
    print(f"Parsed args: {args}")
    print(f"Command: {args.command}")
    print(f"Config: {getattr(args, 'config', 'NOT SET')}")
    print(f"Wizard: {getattr(args, 'wizard', 'NOT SET')}")
    print(f"Resume: {getattr(args, 'resume', 'NOT SET')}")

cli.run = debug_run
cli.run()