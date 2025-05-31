#!/usr/bin/env python3
"""
Setup script to create the actorle_detail table in the database
"""

import sys
import os
import asyncio

# Add parent directory to path for bot imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from bot.functions.sql_helper import execute_query
    
    async def setup_table():
        """Create the actorle_detail table"""
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS actorle_history (
            id VARCHAR(12) PRIMARY KEY,
            game_date DATE NOT NULL,
            game_number INT,
            game_status VARCHAR(20) NOT NULL DEFAULT 'puzzle',
            year INT NOT NULL,
            title TEXT,
            genres TEXT,
            rating DECIMAL(3,1),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Add indexes for efficient queries
            INDEX idx_game_date (game_date),
            INDEX idx_game_status (game_status),
            INDEX idx_year (year),
            INDEX idx_rating (rating),
            INDEX idx_game_number (game_number)
        );
        """
        
        try:
            await execute_query(create_table_sql)
            print("✅ Successfully created actorle_history table")
            
            # Check if table exists and show structure
            check_sql = "DESCRIBE actorle_history"
            result = await execute_query(check_sql)
            
            print("\n📋 Table structure:")
            for row in result:
                print(f"   {row['Field']}: {row['Type']} {row['Extra']}")
                
        except Exception as e:
            print(f"❌ Error creating table: {e}")
    
    def main():
        """Main function"""
        print("🗄️  Setting up actorle_detail database table...")
        asyncio.run(setup_table())

    if __name__ == "__main__":
        main()

except ImportError:
    print("❌ Database dependencies not available")
    print("   Run this script from the bot environment with database access")
    sys.exit(1) 