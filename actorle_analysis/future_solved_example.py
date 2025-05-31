#!/usr/bin/env python3
"""
Conceptual example of how the solved Actorle data would work

This shows how you could have both 'puzzle' and 'solved' records for the same game_date,
with revealed movie titles and actor information.
"""

import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path for bot imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.functions.sql_helper import execute_query, send_df_to_sql
import pandas as pd

async def create_actor_table():
    """Create a separate table for storing revealed actor information"""
    
    create_actor_table_sql = """
    CREATE TABLE IF NOT EXISTS actorle_actors (
        game_date DATE PRIMARY KEY,
        game_number INT,
        actor_name VARCHAR(255) NOT NULL,
        actor_birth_year INT,
        actor_country VARCHAR(100),
        difficulty_level VARCHAR(20),
        solution_revealed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        INDEX idx_actor_name (actor_name),
        INDEX idx_game_number (game_number)
    );
    """
    
    try:
        await execute_query(create_actor_table_sql)
        print("✅ Successfully created actorle_actors table")
        
        # Show structure
        result = await execute_query("DESCRIBE actorle_actors")
        print("\n📋 Actor table structure:")
        for row in result:
            print(f"   {row['Field']}: {row['Type']} {row['Extra']}")
            
    except Exception as e:
        print(f"❌ Error creating actor table: {e}")

def example_solved_data():
    """Example of what solved data would look like"""
    
    print("\n🎯 EXAMPLE: How solved data would be structured")
    print("="*60)
    
    # Example solved movie data (same IDs but with 'solved' status)
    solved_movies = [
        {
            'id': '20250531_01',
            'game_date': '2025-05-31',
            'game_number': 6504,
            'game_status': 'solved',  # Changed from 'puzzle'
            'year': 1967,
            'title': 'Cool Hand Luke',  # Revealed title (no more ×××)
            'genres': 'DRAMA; CRIME',
            'rating': 5.4
        },
        {
            'id': '20250531_02', 
            'game_date': '2025-05-31',
            'game_number': 6504,
            'game_status': 'solved',
            'year': 1968,
            'title': 'Rosemary\'s Baby',  # Revealed title
            'genres': 'DRAMA; HORROR; THRILLER',
            'rating': 5.6
        },
        # ... more solved movies
    ]
    
    print("📽️ Solved movie data example:")
    for movie in solved_movies[:2]:
        print(f"   {movie['id']} - {movie['game_status']} - {movie['year']} - {movie['title']} - {movie['rating']}/10")
    
    # Example actor data
    actor_data = {
        'game_date': '2025-05-31',
        'game_number': 6504,
        'actor_name': 'Paul Newman',  # Revealed actor name
        'actor_birth_year': 1925,
        'actor_country': 'USA',
        'difficulty_level': 'Medium'
    }
    
    print(f"\n🎭 Revealed actor data example:")
    print(f"   Game #{actor_data['game_number']} ({actor_data['game_date']})")
    print(f"   Actor: {actor_data['actor_name']} (born {actor_data['actor_birth_year']}, {actor_data['actor_country']})")
    print(f"   Difficulty: {actor_data['difficulty_level']}")
    
    print(f"\n💡 WORKFLOW CONCEPT:")
    print("="*25)
    print("   1. Daily scraper runs → saves 'puzzle' data with censored titles")
    print("   2. Solution scraper/solver runs → saves 'solved' data with real titles")
    print("   3. Actor data saved to separate actorle_actors table")
    print("   4. Both datasets coexist for the same game_date")
    print("   5. Query by game_status to get puzzle vs solved data")
    
    print(f"\n🔍 EXAMPLE QUERIES:")
    print("="*20)
    print("   # Get puzzle data for a date:")
    print("   SELECT * FROM actorle_history WHERE game_date = '2025-05-31' AND game_status = 'puzzle'")
    print()
    print("   # Get solved data for a date:")
    print("   SELECT * FROM actorle_history WHERE game_date = '2025-05-31' AND game_status = 'solved'")
    print()
    print("   # Get actor info for a date:")
    print("   SELECT * FROM actorle_actors WHERE game_date = '2025-05-31'")
    print()
    print("   # Compare puzzle vs solved for same movie:")
    print("   SELECT p.title as puzzle_title, s.title as solved_title, p.year")
    print("   FROM actorle_history p JOIN actorle_history s")
    print("   ON p.game_date = s.game_date AND p.year = s.year")
    print("   WHERE p.game_status = 'puzzle' AND s.game_status = 'solved'")

async def main():
    """Main function to demonstrate the concept"""
    print("🚀 ACTORLE SOLVED DATA CONCEPT")
    print("="*40)
    
    # Create the actor table
    await create_actor_table()
    
    # Show the concept
    example_solved_data()
    
    print(f"\n📋 CURRENT STATUS:")
    print("="*20)
    print("   ✅ Puzzle data collection: IMPLEMENTED")
    print("   ✅ Database structure: READY for both puzzle and solved data")
    print("   🔄 Solution extraction: TO BE IMPLEMENTED")
    print("   🔄 Actor table: CREATED (ready for data)")

if __name__ == "__main__":
    asyncio.run(main()) 