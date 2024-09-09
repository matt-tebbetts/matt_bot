import discord
from discord.ext import tasks
from bot.functions import find_users_to_warn, send_df_to_sql
from datetime import datetime
import pandas as pd

@tasks.loop(hours=1)
async def send_warning_loop(client: discord.Client):
    users_to_warn = await find_users_to_warn()  # Fetch users who need a warning
    if len(users_to_warn) == 0:
        print("tasks.py: No users to warn about the Mini right now")
        return
    
    # send warning to each user
    print(f"tasks.py: Need to warn {len(users_to_warn)} users")
    warning_text = "this is your reminder to complete the Mini!"
    warning_data = []

    # Collect all members from all guilds
    guild_member_ids = {member.id for guild in client.guilds for member in guild.members}
    print(f"tasks.py: bot is currently connected to these users: {guild_member_ids}")
    
    print(f"tasks.py: users to warn: {users_to_warn}")
    for user in users_to_warn:
        if user['discord_id_nbr'] not in guild_member_ids:
            print(f"tasks.py: User {user['name']} ({user['discord_id_nbr']}) not in any of this bot's guilds")
            status = 'Failed'
            error_msg = 'Bot not in user\'s guild(s)'
            msg = 'Did not attempt to send warning'
            print(f"tasks.py: {msg}")
        else:
            try:
                discord_id = await client.fetch_user(user['discord_id_nbr'])
                msg = f'Hi {user["name"]}, {warning_text}'
                await discord_id.send(msg)
                print(f"tasks.py: sent warning to {user['name']}")
                status = 'Sent'
                error_msg = ''
            except Exception as e:
                status = 'Failed'
                error_msg = str(e)

        # combine warning metadata
        warning_data.append({
            'warning_dttm': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_name': user['name'],
            'platform': 'discord',
            'message_status': status,
            'message_error': error_msg,
            'message_text': msg
        })

    # save warning metadata
    df = pd.DataFrame(warning_data)
    await send_df_to_sql(df, 'games.mini_warning_history', if_exists='append')

def setup_tasks(client: discord.Client):
    send_warning_loop.start(client)
