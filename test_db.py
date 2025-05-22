import asyncio
from bot.functions.sql_helper import execute_query, close_pool

async def main():
    try:
        # Test connection and get tables
        print("Testing database connection...")
        tables = await execute_query("SHOW TABLES")
        print("\nAvailable tables:")
        for table in tables:
            print(f"- {list(table.values())[0]}")
            
        # Test views
        print("\nChecking views...")
        views = await execute_query("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
        print("\nAvailable views:")
        for view in views:
            print(f"- {list(view.values())[0]}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main()) 