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

async def get_pool():
    global pool
    if pool is None:
        db_config = await get_db_config()
        pool = await aiomysql.create_pool(**db_config, loop=asyncio.get_running_loop())
        print(f"[SQL] Connection pool initialized (host: {db_config['host']}, db: {db_config['db']})")
    return pool

# get df from sql query
async def get_df_from_sql(query, params=None):
    attempts = 0
    max_attempts = 3
    base_delay = 1  # Start with 1 second delay

    # Log the query being executed (without sensitive data)
    query_type = query.strip().split()[0].upper()
    print(f"[SQL] Executing {query_type} query")

    while attempts < max_attempts:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    try:
                        await cursor.execute(query, params)
                        result = await cursor.fetchall()
                        df = pd.DataFrame(result) if result else pd.DataFrame()
                        print(f"[SQL] Query returned {len(df)} rows")
                        return df
                    except Exception as e:
                        print(f"[SQL] Query execution failed: {str(e)}")
                        print(f"[SQL] Query: {query[:100]}...")  # Log first 100 chars of query
                        if params:
                            print(f"[SQL] Params: {params}")
                        raise e

        except (asyncio.TimeoutError, aiomysql.OperationalError) as e:
            attempts += 1
            if attempts >= max_attempts:
                print(f"[SQL] Connection failed after {max_attempts} attempts: {str(e)}")
                print(f"[SQL] Last error traceback:\n{traceback.format_exc()}")
                raise e
            
            # Exponential backoff with jitter
            delay = base_delay * (2 ** (attempts - 1)) + (random.random() * 0.1)
            print(f"[SQL] Connection attempt {attempts}/{max_attempts} failed. Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)
            
        except Exception as e:
            print(f"[SQL] Unexpected error: {str(e)}")
            print(f"[SQL] Error traceback:\n{traceback.format_exc()}")
            raise e

    return pd.DataFrame()

# save df to sql table
async def send_df_to_sql(df, table_name, if_exists='append'):
    if df.empty:
        print(f"[SQL] Warning: Attempting to insert empty DataFrame into {table_name}")
        return

    # Convert DataFrame to tuples
    data_tuples = [tuple(x) for x in df.to_numpy()]

    # Construct SQL query for inserting data
    cols = ', '.join(df.columns)
    placeholders = ', '.join(['%s'] * len(df.columns))
    insert_query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"

    # Handle the 'if_exists' cases
    if if_exists == 'replace':
        delete_query = f"DELETE FROM {table_name}"
    elif if_exists == 'fail':
        check_query = f"SELECT 1 FROM {table_name} LIMIT 1"

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # If 'replace', delete existing data
                if if_exists == 'replace':
                    await cur.execute(delete_query)
                    print(f"[SQL] Cleared existing data from {table_name}")

                # If 'fail', check if the table is empty
                elif if_exists == 'fail':
                    await cur.execute(check_query)
                    if await cur.fetchone():
                        raise ValueError(f"Table {table_name} is not empty. Aborting operation.")

                # Execute the insert query
                await cur.executemany(insert_query, data_tuples)
                await conn.commit()
                print(f"[SQL] Successfully inserted {len(data_tuples)} rows into {table_name}")
                print(f"[SQL] Columns: {', '.join(df.columns)}")
            except Exception as e:
                print(f"[SQL] Failed to insert data into {table_name}: {str(e)}")
                print(f"[SQL] Error traceback:\n{traceback.format_exc()}")
                raise e