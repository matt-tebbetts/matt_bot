#!/usr/bin/env python3
"""
Verify the actorle_detail table data
"""

import asyncio
import sys
import os

# Add parent directory to path for bot imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.functions.sql_helper import execute_query

async def verify_data():
    try:
        # Check count by date and status
        result = await execute_query("""
            SELECT COUNT(*) as count, game_date, game_status
            FROM actorle_history 
            GROUP BY game_date, game_status
            ORDER BY game_date DESC, game_status 
            LIMIT 10
        """)
        
        print("📊 Data in actorle_history table:")
        for row in result:
            print(f"   {row['game_date']} ({row['game_status']}): {row['count']} movies")
        
        # Check total records
        total = await execute_query("SELECT COUNT(*) as total FROM actorle_history")
        print(f"\n📈 Total records: {total[0]['total']}")
        
        # Check sample records with new game_status field
        sample = await execute_query("""
            SELECT id, game_date, game_number, game_status, year, title, rating 
            FROM actorle_history 
            ORDER BY year ASC 
            LIMIT 5
        """)
        
        print("\n🆔 Sample records (by year):")
        for row in sample:
            title_short = row['title'][:25] + '...' if len(str(row['title'])) > 25 else row['title']
            game_num = f"Game #{row['game_number']}" if row['game_number'] else "No game #"
            print(f"   {row['id']} - {row['game_date']} - {game_num} - {row['game_status']} - {row['year']} - {title_short} - {row['rating']}/10")
            
        # Check top-rated movies
        top_rated = await execute_query("""
            SELECT id, game_date, game_status, year, title, rating 
            FROM actorle_history 
            ORDER BY rating DESC 
            LIMIT 3
        """)
        
        print("\n⭐ Top rated movies:")
        for row in top_rated:
            title_short = row['title'][:25] + '...' if len(str(row['title'])) > 25 else row['title']
            print(f"   {row['id']} - {row['game_status']} - {row['year']} - {title_short} - {row['rating']}/10")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_data()) 