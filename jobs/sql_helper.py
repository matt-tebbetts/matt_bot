
import asyncio
import aiomysql
import pandas as pd
import os

lock = asyncio.Lock()

# get sql config
async def get_db_config():

    # Retrieve environment variables
    SQLUSER = os.getenv('SQLUSER')
    SQLPASS = os.getenv('SQLPASS')
    SQLHOST = os.getenv('SQLHOST')
    SQLPORT = int(os.getenv('SQLPORT'))
    SQLDATA = os.getenv('SQLDATA')

    # Check if all environment variables were found
    for var in [SQLUSER, SQLPASS, SQLHOST, SQLPORT, SQLDATA]:
        if var is None:
            raise ValueError(f"Environment variable '{var}' not found.")

    db_config = {
        'host': SQLHOST,
        'port': SQLPORT,
        'user': SQLUSER,
        'password': SQLPASS,
        'db': SQLDATA
    }

    return db_config

# get df from sql query
async def get_df_from_sql(query, params=None):
    db_config = await get_db_config()
    attempts = 0
    while attempts < 3:
        try:
            conn = await aiomysql.connect(**db_config, loop=asyncio.get_running_loop())
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                result = await cursor.fetchall()
            conn.close()

            # return df
            return pd.DataFrame(result) if result else pd.DataFrame()
        
        except (asyncio.TimeoutError, aiomysql.OperationalError) as e:
            print(f"SQL Connection/Timeout Error: {e}")
            attempts += 1
            if attempts >= 3:
                print("Max attempts reached")
                raise e
            await asyncio.sleep(1)
        except Exception as e:
            raise e
    return pd.DataFrame()

# save df to sql table
async def send_df_to_sql(df, table_name, if_exists='append'):
    db_config = await get_db_config()
    async with lock:
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

        # Connect and execute
        async with aiomysql.create_pool(**db_config, loop=asyncio.get_running_loop()) as pool:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:

                    # If 'replace', delete existing data
                    if if_exists == 'replace':
                        await cur.execute(delete_query)

                    # If 'fail', check if the table is empty
                    elif if_exists == 'fail':
                        await cur.execute(check_query)
                        if await cur.fetchone():
                            raise ValueError(f"Table {table_name} is not empty. Aborting operation.")

                    # Execute the insert query
                    await cur.executemany(insert_query, data_tuples)
                    await conn.commit()
