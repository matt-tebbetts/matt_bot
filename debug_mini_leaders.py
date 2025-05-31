#!/usr/bin/env python3
"""
Debug script to test mini leader detection functionality
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root to the path so we can import bot modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.functions.sql_helper import execute_query, get_pool
from bot.functions.mini_warning import check_mini_leaders
from bot.functions.admin import read_json, direct_path_finder

async def debug_mini_leaders():
    """Debug the mini leader detection system"""
    
    print("=== DEBUGGING MINI LEADER DETECTION ===")
    
    # Test 1: Check if we can connect to the database
    print("\n1. Testing database connection...")
    try:
        pool = await get_pool()
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return
    
    # Test 2: Check what dates are available in mini_view
    print("\n2. Checking available dates in mini_view...")
    try:
        query = "SELECT DISTINCT game_date FROM matt.mini_view ORDER BY game_date DESC LIMIT 10"
        results = await execute_query(query)
        print(f"Available dates: {[r['game_date'] for r in results]}")
    except Exception as e:
        print(f"✗ Error getting dates: {e}")
        return
    
    # Test 3: Check what guilds are in the data
    print("\n3. Checking available guilds in mini_view...")
    try:
        query = "SELECT DISTINCT guild_nm FROM matt.mini_view"
        results = await execute_query(query)
        print(f"Available guilds: {[r['guild_nm'] for r in results]}")
    except Exception as e:
        print(f"✗ Error getting guilds: {e}")
    
    # Test 4: Check today's data (all guilds)
    print("\n4. Checking today's mini data (all guilds)...")
    try:
        query = """
            SELECT game_date, guild_nm, player_name, game_time, game_rank 
            FROM matt.mini_view 
            WHERE game_date = (SELECT MAX(game_date) FROM matt.mini_view)
            ORDER BY guild_nm, game_rank
        """
        results = await execute_query(query)
        if results:
            print(f"Today's data ({results[0]['game_date']}):")
            for r in results:
                print(f"  {r['guild_nm']} - #{r['game_rank']} {r['player_name']} ({r['game_time']})")
        else:
            print("No data found for today")
    except Exception as e:
        print(f"✗ Error getting today's data: {e}")
    
    # Test 5: Check the specific query used by check_mini_leaders
    print("\n5. Testing the exact query used by check_mini_leaders...")
    try:
        query = """
            select 
                player_name,
                game_time
            from matt.mini_view
            where game_date = (select max(game_date) from matt.mini_view)
            and game_rank = 1
            and guild_nm = 'Global'
        """
        results = await execute_query(query)
        print(f"Global leaders query result: {results}")
    except Exception as e:
        print(f"✗ Error with global leaders query: {e}")
    
    # Test 6: Check what's in the global_mini_leaders.json file
    print("\n6. Checking current global_mini_leaders.json file...")
    try:
        leader_filepath = direct_path_finder('files', 'config', 'global_mini_leaders.json')
        previous_leaders = read_json(leader_filepath)
        print(f"Current stored leaders: {previous_leaders}")
    except Exception as e:
        print(f"✗ Error reading leaders file: {e}")
    
    # Test 7: Run the actual check_mini_leaders function
    print("\n7. Running check_mini_leaders function...")
    try:
        result = await check_mini_leaders()
        print(f"check_mini_leaders returned: {result}")
    except Exception as e:
        print(f"✗ Error running check_mini_leaders: {e}")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(debug_mini_leaders()) 