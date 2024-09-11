import discord
from discord.ext import tasks
from datetime import datetime
import pandas as pd

from bot.functions import find_users_to_warn, send_df_to_sql
from bot.functions import check_mini_leaders

@tasks.loop(hours=1)
async def send_warning_loop(client: discord.Client):
    
    # see if anyone needs a warning
    users_to_warn = await find_users_to_warn()
    if len(users_to_warn) == 0:
        print("tasks.py: No users to warn about the Mini right now")
        return
    
    # send warning to each user
    warning_text = "this is your reminder to complete the Mini!"
    warning_data = []
    guild_member_ids = {member.id for guild in client.guilds for member in guild.members}
    for user in users_to_warn:
        if user['discord_id_nbr'] not in guild_member_ids:
            status = 'Failed'
            error_msg = 'Bot not in user\'s guild(s)'
            msg = 'Did not attempt to send warning'
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

@tasks.loop(seconds=10)
async def check_mini(client: discord.Client):

    # check for leader changes
    guild_differences = await check_mini_leaders()
    for guild_name, has_new_leader in guild_differences.items():
        if has_new_leader:
            message = f"New mini leader for {guild_name}!"
            await post_mini(guild_name=guild_name, msg=message)

    # reset after cutoff_hour
    now = get_now()
    if now.hour == get_cutoff_hour() and now.minute == 0 and now.second < 10:
        for guild in client.guilds:
            guild_name = guild.name
            leader_filepath = f"files/guilds/{guild_name}/leaders.json"
            write_json(leader_filepath, []) # makes it an empty list


def setup_tasks(client: discord.Client):
    send_warning_loop.start(client)
