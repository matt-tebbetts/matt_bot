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

# Removed redundant send_warning_loop - functionality moved to daily_mini_summary task

# task 1 - check for new mini leaders and post to discord
@tasks.loop(seconds=60)
async def post_new_mini_leaders(client: discord.Client, tree: discord.app_commands.CommandTree):
    try:
        print(f"[DEBUG] Running post_new_mini_leaders task at {datetime.now()}")
        
        # check for global leader changes (returns True/False instead of guild dict)
        has_new_leader = await check_mini_leaders()
        print(f"[DEBUG] check_mini_leaders returned: {has_new_leader}")

        if not has_new_leader:
            print(f"[DEBUG] No new leader, exiting task")
            return

        # Post to ALL connected guilds since mini leaderboard is now global
        connected_guilds = {guild.name for guild in client.guilds}
        print(f"[DEBUG] Connected guilds: {connected_guilds}")
        
        for guild_name in connected_guilds:
            print(f"[DEBUG] Processing guild: {guild_name}")
            
            # Get the default channel ID
            channel_id = get_default_channel_id(guild_name)
            print(f"[DEBUG] Default channel ID for {guild_name}: {channel_id}")
            
            if not channel_id:
                print(f"[DEBUG] No default channel ID found for {guild_name}, skipping")
                continue

            basic_message = "There's a new mini leader!"
            channel = client.get_channel(channel_id)
            print(f"[DEBUG] Got channel object: {channel}")
            
            if channel:
                try:
                    print(f"[DEBUG] Sending message to {guild_name} in #{channel.name}")
                    await channel.send(basic_message)
                    
                    # Create leaderboard and send as image file
                    leaderboards = Leaderboards(client, tree)
                    img_path = await leaderboards.show_leaderboard(game='mini')
                    
                    # Check if we got a valid file path (should end with .png and exist)
                    if (img_path and isinstance(img_path, str) and 
                        img_path.endswith('.png') and 
                        os.path.exists(img_path)):
                        print(f"[DEBUG] Sending leaderboard image: {img_path}")
                        await channel.send(file=discord.File(img_path))
                    else:
                        # Either got an error message or file doesn't exist
                        error_msg = img_path if isinstance(img_path, str) else "Unknown error generating leaderboard"
                        print(f"[DEBUG] Failed to generate mini leaderboard for {guild_name}: {error_msg}")
                        await channel.send("Error: Could not generate mini leaderboard image")
                        
                except Exception as e:
                    print(f"[DEBUG] Error posting mini leader update to {guild_name}: {e}")
            else:
                print(f"[DEBUG] Could not get channel object for channel ID {channel_id} in {guild_name}")
                    
    except Exception as e:
        print(f"[DEBUG] Error in post_new_mini_leaders task: {e}")

# task 2 - reset leaders when mini resets
@tasks.loop(hours=1)
async def reset_mini_leaders(client: discord.Client):
    try:
        now = datetime.now()
        mini_reset_hour = 22 if now.weekday() >= 5 else 18
        
        if now.hour == mini_reset_hour and now.minute <= 1:  # reset window
            # Reset global mini leaders file (not per-guild anymore)
            leader_filepath = direct_path_finder('files', 'config', 'global_mini_leaders.json')
            write_json(leader_filepath, [])  # makes it an empty list
            print(f"Reset global mini leaders at {now}")

    except Exception as e:
        print(f"Error in reset_mini_leaders: {e}")

# task 3 - end of day mini summary and warnings
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
                
                # Check which users are in connected guilds to avoid unnecessary API calls
                guild_member_ids = {member.id for guild in client.guilds for member in guild.members}
                
                for user in users_to_warn:
                    if user['discord_id_nbr'] not in guild_member_ids:
                        print(f"Skipping DM to {user['name']} - not in any connected guilds")
                        continue
                        
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
    print(f"[DEBUG] Setting up tasks...")
    
    # Start the continuous monitoring task
    if post_new_mini_leaders.is_running():
        post_new_mini_leaders.stop()
    post_new_mini_leaders.start(client, tree)
    print(f"[DEBUG] Started post_new_mini_leaders task")

    # Start time-based tasks (they have their own time checks)
    if reset_mini_leaders.is_running():
        reset_mini_leaders.stop()
    reset_mini_leaders.start(client)
    print(f"[DEBUG] Started reset_mini_leaders task")
    
    if daily_mini_summary.is_running():
        daily_mini_summary.stop()
    daily_mini_summary.start(client, tree)
    print(f"[DEBUG] Started daily_mini_summary task")
    
    # Note: send_warning_loop is redundant with daily_mini_summary DM warnings
    # Removing it to avoid duplicate warning systems
