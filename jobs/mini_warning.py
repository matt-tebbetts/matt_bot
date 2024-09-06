import discord
from functions.sql_helper import get_df_from_sql

async def find_users_to_warn():
    df = await get_df_from_sql("SELECT * FROM matt.mini_not_completed")
    if df.empty:
        return []
    users_to_message = []
    for index, row in df.iterrows():
        users_to_message.append({
            'name': row['player_name'],
            'discord_id_nbr': row['discord_id_nbr']
        })
    return users_to_message