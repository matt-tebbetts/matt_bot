import asyncio
import aiomysql
import pandas as pd
import os
from dotenv import load_dotenv
import random
import traceback
from typing import List, Dict, Any, Optional

lock = asyncio.Lock()
_pools = {}

# Global connection pool
_pool = None

# get sql config
async def get_db_config():
    # load env variables
    load_dotenv()

    # Retrieve environment variables
    SQL_USER = os.getenv('SQL_USER')
    SQL_PASS = os.getenv('SQL_PASS')
    SQL_HOST = os.getenv('SQL_HOST')
    SQL_PORT = os.getenv('SQL_PORT')
    SQL_DATA = os.getenv('SQL_DATA')

    # Check if all environment variables were found
    for var_name, var_value in [('SQL_USER', SQL_USER), ('SQL_PASS', SQL_PASS), 
                              ('SQL_HOST', SQL_HOST), ('SQL_PORT', SQL_PORT), 
                              ('SQL_DATA', SQL_DATA)]:
        if var_value is None:
            raise ValueError(f"Environment variable '{var_name}' not found.")

    db_config = {
        'host': SQL_HOST,
        'port': int(SQL_PORT),
        'user': SQL_USER,
        'password': SQL_PASS,
        'db': SQL_DATA,
        'connect_timeout': 10,  # 10 second connection timeout
        'autocommit': True,     # Enable autocommit
        'pool_recycle': 3600,   # Recycle connections after 1 hour
        'echo': False,          # Disable SQL query logging
        'minsize': 1,           # Minimum pool size
        'maxsize': 10           # Maximum pool size
    }

    return db_config

async def get_pool():
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        db_config = await get_db_config()
        _pool = await aiomysql.create_pool(**db_config)
        print(f"✓ Connected to {db_config['host']}/{db_config['db']}")
    return _pool

async def execute_query(query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """Execute a SQL query and return the results."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, params or ())
            return await cur.fetchall()

async def execute_many(query: str, params_list: List[tuple]) -> None:
    """Execute multiple SQL queries with different parameters."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(query, params_list)

async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None

async def send_df_to_sql(df, table_name, if_exists='append'):
    if df.empty:
        print(f"[SQL] Warning: Attempting to insert empty DataFrame into {table_name}")
        return

    try:
        async with lock:
            pool = await get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    if if_exists == 'replace':
                        await cur.execute(f"DELETE FROM {table_name}")
                        print(f"✓ Cleared existing data from {table_name}")

                    # Prepare the data
                    columns = df.columns.tolist()
                    placeholders = ', '.join(['%s'] * len(columns))
                    query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    
                    # Convert DataFrame to list of tuples, handling lists by converting to strings
                    data_tuples = []
                    for row in df.values:
                        processed_row = []
                        for value in row:
                            if isinstance(value, list):
                                processed_row.append(', '.join(str(x) for x in value))
                            else:
                                processed_row.append(value)
                        data_tuples.append(tuple(processed_row))
                    
                    # Execute the insert
                    await cur.executemany(query, data_tuples)
                    await conn.commit()
                    print(f"✓ Inserted {len(data_tuples)} rows into {table_name}")

    except Exception as e:
        print(f"[SQL] Failed to insert data into {table_name}: {str(e)}")
        raise