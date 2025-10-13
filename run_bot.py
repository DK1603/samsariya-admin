#!/usr/bin/env python3
"""
Launcher script for Samsariya Admin Bot
Run this from the root directory: python run_bot.py
"""

import sys
import os
import asyncio

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.main import main

if __name__ == "__main__":
    asyncio.run(main())