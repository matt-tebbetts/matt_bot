import discord
from discord.ext import tasks
from datetime import datetime
import pandas as pd

from bot.functions import find_users_to_warn
from bot.functions import send_df_to_sql, get_df_from_sql
from bot.functions import check_mini_leaders
from bot.functions import write_json
from bot.commands.leaderboards import Leaderboards

# task 1 - check for users who haven't completed the mini
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

# task 2 - check for new mini leaders and post to discord
@tasks.loop(seconds=60)
async def post_new_mini_leaders(client: discord.Client, tree: discord.app_commands.CommandTree):
    
    # check for leader changes
    guild_differences = await check_mini_leaders()
    for guild_name, has_new_leader in guild_differences.items():
        if has_new_leader:
            message = f"New mini leader for {guild_name}!"
            print(f"tasks.py: {message}")

            # Find the guild object
            guild = discord.utils.get(client.guilds, name=guild_name)
            if guild:
                try:
                    # Create an instance of Leaderboards and call post_leaderboard
                    print(f"tasks.py: attempting to create Leaderboards instance")
                    leaderboards = Leaderboards(client, tree)
                    print(f"tasks.py: attempting to run post_leaderboard for {guild_name}")
                    await leaderboards.post_leaderboard(game='mini', guild=guild)
                    print(f"tasks.py: finished running post_leaderboard for {guild_name}")
                except Exception as e:
                    print(f"tasks.py: error in post_leaderboard: {e}")
            else:
                print(f"tasks.py: Guild {guild_name} not found")

# task 3 - reset leaders when mini resets
@tasks.loop(hours=1)
async def reset_mini_leaders(client: discord.Client):
    now = datetime.now()
    mini_reset_hour = 22 if now.weekday() >= 5 else 18
    if now.hour == mini_reset_hour and now.minute <= 1: # reset window
        for guild in client.guilds:
            leader_filepath = f"files/guilds/{guild.name}/leaders.json"
            write_json(leader_filepath, []) # makes it an empty list

def setup_tasks(client: discord.Client, tree: discord.app_commands.CommandTree):
    send_warning_loop.start(client)
    post_new_mini_leaders.start(client, tree)
    reset_mini_leaders.start(client)

