#!/usr/bin/env python3
"""Test grid bot run directly"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gridbot import GridBot, GridBotConfig
from exchanges.bitunix import BitUnixExchange

# Set auto-resume
os.environ['GRIDBOT_AUTO_RESUME'] = 'true'

# Load config
config_manager = GridBotConfig()
config = config_manager.load_from_file('btc_long_50grid_config.json')

# Initialize exchange
exchange = BitUnixExchange()

print(f"\nInitializing Grid Bot on BITUNIX...")
print(f"Symbol: {config.symbol}")
print(f"Grid Count: {config.grid_count}")
print(f"Position: {config.position_direction.value}")

# Initialize bot
bot = GridBot(exchange, config)

# Start bot
print("\nStarting Grid Bot...")
bot.start()

# Keep running
try:
    import time
    while bot.state == bot.state.RUNNING:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nStopping bot...")
    bot.stop()