import asyncio
import aiomysql
import pandas as pd
import os
from dotenv import load_dotenv
import random
import traceback

lock = asyncio.Lock()
pool = None

# get sql config
async def get_db_config():
    # load env variables
    load_dotenv()

    # Retrieve environment variables
    SQLUSER = os.getenv('SQLUSER')
    SQLPASS = os.getenv('SQLPASS')
    SQLHOST = os.getenv('SQLHOST')
    SQLPORT = os.getenv('SQLPORT')
    SQLDATA = os.getenv('SQLDATA')

    # Check if all environment variables were found
    for var_name, var_value in [('SQLUSER', SQLUSER), ('SQLPASS', SQLPASS), ('SQLHOST', SQLHOST), ('SQLPORT', SQLPORT), ('SQLDATA', SQLDATA)]:
        if var_value is None:
            raise ValueError(f"Environment variable '{var_name}' not found.")

    db_config = {
        'host': SQLHOST,
        'port': int(SQLPORT),
        'user': SQLUSER,
        'password': SQLPASS,
        'db': SQLDATA,
        'connect_timeout': 10,  # 10 second connection timeout
        'autocommit': True,     # Enable autocommit
        'pool_recycle': 3600,   # Recycle connections after 1 hour
        'echo': False,          # Disable SQL query logging
        'minsize': 1,           # Minimum pool size
        'maxsize': 10           # Maximum pool size
    }

    return db_config

async def get_connection():
    global pool
    if pool is None:
        db_config = await get_db_config()
        print(f"[SQL] Initializing connection pool to {db_config['host']}/{db_config['db']}")
        pool = await aiomysql.create_pool(**db_config)

async def execute_query(query, params=None, max_attempts=3):
    attempts = 0
    delay = 1.0  # Initial delay in seconds
    
    while attempts < max_attempts:
        try:
            async with lock:
                await get_connection()
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        query_type = "SELECT" if query.strip().upper().startswith("SELECT") else "INSERT/UPDATE"
                        if params:
                            await cur.execute(query, params)
                        else:
                            await cur.execute(query)
                        
                        if query_type == "SELECT":
                            columns = [desc[0] for desc in cur.description]
                            rows = await cur.fetchall()
                            df = pd.DataFrame(rows, columns=columns)
                            return df
                        else:
                            await conn.commit()
                            return None
                            
        except aiomysql.OperationalError as e:
            attempts += 1
            if attempts == max_attempts:
                print(f"[SQL] Connection failed after {max_attempts} attempts: {str(e)}")
                raise
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
            
        except Exception as e:
            print(f"[SQL] Query execution failed: {str(e)}")
            if params:
                print(f"[SQL] Query: {query[:100]}... Params: {params}")
            raise

async def send_df_to_sql(df, table_name, if_exists='append'):
    if df.empty:
        print(f"[SQL] Warning: Attempting to insert empty DataFrame into {table_name}")
        return

    try:
        async with lock:
            await get_connection()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    if if_exists == 'replace':
                        await cur.execute(f"DELETE FROM {table_name}")
                        print(f"[SQL] Cleared existing data from {table_name}")

                    # Prepare the data
                    columns = df.columns.tolist()
                    placeholders = ', '.join(['%s'] * len(columns))
                    query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    
                    # Convert DataFrame to list of tuples
                    data_tuples = [tuple(x) for x in df.values]
                    
                    # Execute the insert
                    await cur.executemany(query, data_tuples)
                    await conn.commit()
                    print(f"[SQL] Inserted {len(data_tuples)} rows into {table_name}")

    except Exception as e:
        print(f"[SQL] Failed to insert data into {table_name}: {str(e)}")
        raise