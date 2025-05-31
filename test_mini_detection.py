#!/usr/bin/env python3
"""
Simple test to manually trigger mini leader detection
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.functions.mini_warning import check_mini_leaders
from bot.functions.admin import read_json, write_json, direct_path_finder

async def test_mini_detection():
    print("=== MANUAL MINI LEADER TEST ===")
    print(f"Time: {datetime.now()}")
    
    # Check current leaders file
    leader_filepath = direct_path_finder('files', 'config', 'global_mini_leaders.json')
    current_leaders = read_json(leader_filepath, [])
    print(f"Current stored leaders: {current_leaders}")
    
    # Clear the file to force a detection
    print("Clearing leaders file to force detection...")
    write_json(leader_filepath, [])
    
    # Run the detection
    print("Running check_mini_leaders...")
    result = await check_mini_leaders()
    print(f"Result: {result}")
    
    # Check what's now in the file
    new_leaders = read_json(leader_filepath, [])
    print(f"New stored leaders: {new_leaders}")
    
    # Try running it again to see if it detects a change
    print("\nRunning again to test comparison logic...")
    result2 = await check_mini_leaders()
    print(f"Second run result: {result2}")

if __name__ == "__main__":
    asyncio.run(test_mini_detection()) 