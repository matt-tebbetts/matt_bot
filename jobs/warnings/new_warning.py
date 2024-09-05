import discord
from functions.sql_helper import get_df_from_sql

async def find_users_to_warn(client: discord.Client):
    print("Now we're in the find_users_to_warn function...")
    df = await get_df_from_sql("SELECT * FROM matt.mini_not_completed")
    if df.empty:
        return []

    users_to_message = []
    for index, row in df.iterrows():
        name = row['player_name']
        discord_user_id = row['discord_user_id']  # Assuming you have a Discord user ID stored

        users_to_message.append({
            'name': name,
            'discord_user_id': discord_user_id,
            'message': f"Hey {name}, this is your reminder to complete the Mini!"
        })

    print(f"Found {len(users_to_message)} users to message: {users_to_message}")
    return users_to_message