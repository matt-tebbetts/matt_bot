import asyncio
import aiomysql
import pandas as pd
import os
from dotenv import load_dotenv
import traceback
from typing import List, Dict, Any, Optional
import weakref
import atexit
import signal

lock = asyncio.Lock()
_pools = {}

# Global connection pool
_pool = None
_pool_refs = weakref.WeakSet()  # Track pool references for cleanup

# Register cleanup function to run at exit
def _cleanup_on_exit():
    """Cleanup function called at program exit"""
    import asyncio
    try:
        if _pool is not None:
            # Create a new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_force_close_pool())
                finally:
                    loop.close()
            else:
                # We have a running loop
                if loop.is_running():
                    # Schedule the cleanup
                    loop.create_task(_force_close_pool())
                else:
                    loop.run_until_complete(_force_close_pool())
    except Exception:
        pass  # Ignore cleanup errors during exit

def _signal_handler(signum, frame):
    """Handle termination signals"""
    try:
        _cleanup_on_exit()
    except Exception:
        pass
    # Call the default handler
    signal.default_int_handler(signum, frame)

# Register cleanup handlers
atexit.register(_cleanup_on_exit)
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

async def _force_close_pool():
    """Force close the connection pool"""
    global _pool
    if _pool is not None:
        try:
            _pool.close()
            await _pool.wait_closed()
        except Exception:
            pass  # Ignore errors during forced cleanup
        finally:
            _pool = None

# get sql config
async def get_db_config():
    # load env variables
    load_dotenv()

    # Retrieve environment variables (using SQL_ prefix to match existing .env)
    SQL_USER = os.getenv('SQL_USER')
    SQL_PASS = os.getenv('SQL_PASS')
    SQL_HOST = os.getenv('SQL_HOST')
    SQL_PORT = os.getenv('SQL_PORT', '3306')  # Default MySQL port
    SQL_DATA = os.getenv('SQL_DATA')

    # Check if all environment variables were found
    for var_name, var_value in [('SQL_USER', SQL_USER), ('SQL_PASS', SQL_PASS), 
                              ('SQL_HOST', SQL_HOST), ('SQL_DATA', SQL_DATA)]:
        if var_value is None:
            raise ValueError(f"Environment variable '{var_name}' not found.")

    db_config = {
        'host': SQL_HOST,
        'port': int(SQL_PORT),
        'user': SQL_USER,
        'password': SQL_PASS,
        'db': SQL_DATA,
        'charset': 'utf8mb4',              # Explicitly set charset
        'use_unicode': True,               # Enable Unicode support
        'connect_timeout': 10,             # 10 second connection timeout
        'autocommit': True,                # Enable autocommit
        'pool_recycle': 3600,              # Recycle connections after 1 hour
        'echo': False,                     # Disable SQL query logging
        'minsize': 1,                      # Minimum pool size
        'maxsize': 10,                     # Maximum pool size
        'init_command': "SET collation_connection = 'utf8mb4_0900_ai_ci'"  # Set connection collation to match database
    }

    return db_config

async def get_pool():
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        db_config = await get_db_config()
        _pool = await aiomysql.create_pool(**db_config)
        print(f"Connected to {db_config['host']}/{db_config['db']}")
    return _pool

async def execute_query(query: str, params: Optional[tuple] = None, max_retries: int = 3) -> List[Dict[str, Any]]:
    """Execute a SQL query and return the results with cleaned None values. Includes retry logic for connection issues."""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, params or ())
                    results = await cur.fetchall()
                    
                    # Clean None/NULL values and replace with "-"
                    cleaned_results = []
                    for row in results:
                        cleaned_row = {}
                        for key, value in row.items():
                            if value is None:
                                cleaned_row[key] = "-"
                            else:
                                cleaned_row[key] = value
                        cleaned_results.append(cleaned_row)
                    
                    return cleaned_results
                    
        except (aiomysql.Error, ConnectionError, OSError) as e:
            last_exception = e
            error_code = getattr(e, 'args', [None])[0] if hasattr(e, 'args') and e.args else None
            
            # Check if it's a connection-related error worth retrying
            connection_errors = [
                2006,  # MySQL server has gone away
                2013,  # Lost connection to MySQL server during query
                2055,  # Lost connection to MySQL server at 'reading initial communication packet'
            ]
            
            is_connection_error = (
                error_code in connection_errors or
                "Lost connection" in str(e) or
                "MySQL server has gone away" in str(e) or
                "Connection reset by peer" in str(e)
            )
            
            if is_connection_error and attempt < max_retries - 1:
                # Reset the pool to force new connections
                global _pool
                if _pool:
                    _pool.close()
                    await _pool.wait_closed()
                    _pool = None
                
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"[SQL] Connection error (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"[SQL] Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                continue
            else:
                # Not a connection error or max retries reached
                raise e
    
    # If we get here, all retries failed
    print(f"[SQL] All {max_retries} attempts failed. Last error: {last_exception}")
    raise last_exception

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
        try:
            _pool.close()
            await _pool.wait_closed()
        except Exception as e:
            # Log but don't raise to avoid blocking cleanup
            print(f"[SQL] Warning during pool closure: {e}")
        finally:
            _pool = None

async def send_df_to_sql(df, table_name, if_exists='append', unique_key=None):
    if df.empty:
        return

    try:
        async with lock:
            pool = await get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    if if_exists == 'replace':
                        await cur.execute(f"DELETE FROM {table_name}")

                    # Clean DataFrame: replace NaN values with None (which becomes SQL NULL)
                    df_cleaned = df.copy()
                    
                    # Replace pandas NaN values with None
                    df_cleaned = df_cleaned.where(pd.notnull(df_cleaned), None)
                    
                    # Also replace string representations of nan/null with None
                    df_cleaned = df_cleaned.replace(['nan', 'NaN', 'null', 'NULL', 'None'], None)
                    
                    # Replace numpy nan and float('nan') with None
                    import numpy as np
                    df_cleaned = df_cleaned.replace([np.nan, float('nan')], None)

                    # Prepare the data
                    columns = df_cleaned.columns.tolist()
                    placeholders = ', '.join(['%s'] * len(columns))
                    
                    # Convert DataFrame to list of tuples, handling lists by converting to strings
                    data_tuples = []
                    for row in df_cleaned.values:
                        processed_row = []
                        for value in row:
                            if isinstance(value, list):
                                processed_row.append(', '.join(str(x) for x in value))
                            else:
                                # Additional NaN cleaning at the individual value level
                                if pd.isna(value):
                                    processed_row.append(None)
                                elif str(value).lower() in ['nan', 'none', 'null']:
                                    processed_row.append(None)
                                else:
                                    processed_row.append(value)
                        data_tuples.append(tuple(processed_row))
                    
                    # Final cleanup: ensure no remaining NaN values
                    cleaned_tuples = []
                    for row in data_tuples:
                        cleaned_row = []
                        for value in row:
                            if pd.isna(value) or (isinstance(value, float) and str(value).lower() == 'nan'):
                                cleaned_row.append(None)
                            else:
                                cleaned_row.append(value)
                        cleaned_tuples.append(tuple(cleaned_row))
                    data_tuples = cleaned_tuples
                    
                    # Handle different insert modes
                    if if_exists == 'upsert' and unique_key:
                        # Use INSERT ... ON DUPLICATE KEY UPDATE for MySQL with alias syntax
                        update_clauses = [f"{col} = new_values.{col}" for col in columns if col != unique_key]
                        query = f"""
                            INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders}) AS new_values
                            ON DUPLICATE KEY UPDATE {', '.join(update_clauses)}
                        """
                        await cur.executemany(query, data_tuples)
                    else:
                        # Standard append mode
                        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                        await cur.executemany(query, data_tuples)
                    
                    await conn.commit()

    except Exception as e:
        print(f"[SQL] Failed to insert data into {table_name}: {str(e)}")
        raise 

class DatabaseManager:
    """Context manager for database operations that ensures proper cleanup"""
    
    def __init__(self):
        self.pool = None
        self.local_loop = None
        self.created_loop = False
        
    async def __aenter__(self):
        self.pool = await get_pool()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Don't close the global pool here, just ensure any local resources are cleaned
        pass
    
    def __enter__(self):
        # Synchronous context manager entry
        try:
            loop = asyncio.get_running_loop()
            self.local_loop = loop
        except RuntimeError:
            # No running loop, create one
            self.local_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.local_loop)
            self.created_loop = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up if we created the loop
        if self.created_loop and self.local_loop:
            try:
                # Ensure pool is closed before closing loop
                self.local_loop.run_until_complete(close_pool())
            except Exception:
                pass  # Ignore cleanup errors
            finally:
                try:
                    self.local_loop.close()
                except Exception:
                    pass
                self.local_loop = None
    
    async def execute_query(self, query: str, params: Optional[tuple] = None, max_retries: int = 3):
        """Execute query within this context"""
        return await execute_query(query, params, max_retries)
    
    async def send_df_to_sql(self, df, table_name, if_exists='append', unique_key=None):
        """Send DataFrame to SQL within this context"""
        return await send_df_to_sql(df, table_name, if_exists, unique_key)
    
    def run_async(self, coro):
        """Run an async operation within this context"""
        if self.local_loop and not self.local_loop.is_running():
            return self.local_loop.run_until_complete(coro)
        else:
            # If loop is already running, we can't use run_until_complete
            raise RuntimeError("Cannot run async operation in already running loop context") 