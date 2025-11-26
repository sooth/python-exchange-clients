#!/usr/bin/env python3
"""
Quick start script for running the Grid Bot

Usage:
    python run_gridbot.py              # Interactive wizard
    python run_gridbot.py config.json  # Use config file
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gridbot.cli import main

if __name__ == "__main__":
    # Don't override sys.argv - let the CLI handle arguments properly
    main()