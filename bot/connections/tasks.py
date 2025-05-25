import discord
from discord.ext import tasks
from datetime import datetime
import pandas as pd
import os

from bot.functions import find_users_to_warn
from bot.functions import send_df_to_sql, execute_query
from bot.functions import check_mini_leaders
from bot.functions import write_json
from bot.commands import Leaderboards
from bot.functions.admin import get_default_channel_id
from bot.functions.admin import direct_path_finder

# task 1 - check for users who haven't completed the mini
@tasks.loop(hours=1)
async def send_warning_loop(client: discord.Client):
    
    # Skip on startup - wait for first scheduled run
    if send_warning_loop.current_loop == 0:
        print("Skipping warning loop on startup - will run on schedule")
        return
    
    # see if anyone needs a warning
    users_to_warn = await find_users_to_warn()
    if len(users_to_warn) == 0:
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
    try:
        # check for leader changes
        guild_differences = await check_mini_leaders()

        # Filter guild_differences to include only connected guilds
        connected_guilds = {guild.name for guild in client.guilds}
        filtered_guild_differences = {guild_name: has_new_leader for guild_name, has_new_leader in guild_differences.items() if guild_name in connected_guilds}

        for guild_name, has_new_leader in filtered_guild_differences.items():

            if not has_new_leader:
                continue

            # Get the default channel ID
            channel_id = get_default_channel_id(guild_name)
            if not channel_id:
                continue

            basic_message = "There's a new mini leader!"
            channel = client.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(basic_message)
                    # Create leaderboard and send as image file
                    leaderboards = Leaderboards(client, tree)
                    img_path = await leaderboards.show_leaderboard(game='mini')
                    
                    # Check if we got a valid file path (should end with .png and exist)
                    if (img_path and isinstance(img_path, str) and 
                        img_path.endswith('.png') and 
                        os.path.exists(img_path)):
                        await channel.send(file=discord.File(img_path))
                    else:
                        # Either got an error message or file doesn't exist
                        error_msg = img_path if isinstance(img_path, str) else "Unknown error generating leaderboard"
                        print(f"Failed to generate mini leaderboard for {guild_name}: {error_msg}")
                        await channel.send("Error: Could not generate mini leaderboard image")
                        
                except Exception as e:
                    print(f"Error posting mini leader update to {guild_name}: {e}")
                    
    except Exception as e:
        print(f"Error in post_new_mini_leaders task: {e}")

# task 3 - reset leaders when mini resets
@tasks.loop(hours=1)
async def reset_mini_leaders(client: discord.Client):
    try:
        now = datetime.now()
        mini_reset_hour = 22 if now.weekday() >= 5 else 18
        
        if now.hour == mini_reset_hour and now.minute <= 1:  # reset window
            for guild in client.guilds:
                leader_filepath = direct_path_finder('files', 'guilds', guild.name, 'leaders.json')
                write_json(leader_filepath, [])  # makes it an empty list

    except Exception as e:
        print(f"Error in reset_mini_leaders: {e}")

# task 4 - end of day mini summary and warnings
@tasks.loop(hours=1)
async def daily_mini_summary(client: discord.Client, tree: discord.app_commands.CommandTree):
    try:
        now = datetime.now()
        mini_reset_hour = 18 if now.weekday() >= 5 else 22  # 6pm weekends, 10pm weekdays
        warning_hour = mini_reset_hour - 2  # 2 hours before expiration
        
        # Send DM warnings 2 hours before mini expires (once per day)
        if now.hour == warning_hour and now.minute <= 5:  # 5 minute window
            users_to_warn = await find_users_to_warn()
            if users_to_warn:
                warning_text = "⏰ **Mini reminder!** Only 2 hours left to complete today's mini crossword!"
                
                for user in users_to_warn:
                    try:
                        # Get user by discord ID and send DM
                        discord_user = await client.fetch_user(user['discord_id_nbr'])
                        await discord_user.send(warning_text)
                        print(f"Sent mini warning DM to {user['name']}")
                    except Exception as e:
                        print(f"Failed to send mini warning DM to {user['name']}: {e}")
        
        # Send end-of-day summary to channels when mini resets
        elif now.hour == mini_reset_hour and now.minute <= 5:  # 5 minute window
            connected_guilds = {guild.name for guild in client.guilds}
            for guild_name in connected_guilds:
                channel_id = get_default_channel_id(guild_name)
                if channel_id:
                    channel = client.get_channel(channel_id)
                    if channel:
                        summary_msg = "🏁 **Final Mini Results for Today!**"
                        try:
                            await channel.send(summary_msg)
                            # Show final leaderboard
                            leaderboards = Leaderboards(client, tree)
                            img_path = await leaderboards.show_leaderboard(game='mini')
                            if (img_path and isinstance(img_path, str) and 
                                img_path.endswith('.png') and 
                                os.path.exists(img_path)):
                                await channel.send(file=discord.File(img_path))
                            else:
                                print(f"Failed to generate daily mini summary leaderboard for {guild_name}: {img_path}")
                        except Exception as e:
                            print(f"Error sending daily mini summary to {guild_name}: {e}")
                            
    except Exception as e:
        print(f"Error in daily_mini_summary task: {e}")

def setup_tasks(client: discord.Client, tree: discord.app_commands.CommandTree):
    # Start the continuous monitoring task
    if post_new_mini_leaders.is_running():
        post_new_mini_leaders.stop()
    post_new_mini_leaders.start(client, tree)

    # Start time-based tasks (they have their own time checks)
    if reset_mini_leaders.is_running():
        reset_mini_leaders.stop()
    reset_mini_leaders.start(client)
    
    if daily_mini_summary.is_running():
        daily_mini_summary.stop()
    daily_mini_summary.start(client, tree)
    
    # Note: send_warning_loop is redundant with daily_mini_summary DM warnings
    # Removing it to avoid duplicate warning systems
