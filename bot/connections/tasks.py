import discord
from discord.ext import tasks
from datetime import datetime
import pandas as pd
import os
import json
import pytz

from bot.functions import find_users_to_warn
from bot.functions import send_df_to_sql, execute_query
from bot.functions import check_mini_leaders
from bot.functions import track_warning_attempt
from bot.functions import write_json
from bot.commands import Leaderboards
from bot.functions.admin import get_default_channel_id
from bot.functions.admin import direct_path_finder
from bot.connections.logging_config import get_task_logger, log_exception, log_asyncio_context

# Get task-specific loggers
mini_leaders_logger = get_task_logger('post_new_mini_leaders')
reset_leaders_logger = get_task_logger('reset_mini_leaders')
daily_summary_logger = get_task_logger('daily_mini_summary')
setup_logger = get_task_logger('setup_tasks')

# Removed redundant send_warning_loop - functionality moved to daily_mini_summary task

# task 1 - check for new mini leaders and post to discord
@tasks.loop(seconds=60)
async def post_new_mini_leaders(client: discord.Client, tree: discord.app_commands.CommandTree):
    try:
        now = datetime.now()
        mini_reset_hour = 18 if now.weekday() >= 5 else 22  # 6pm weekends, 10pm weekdays
        
        # Skip leader checks during mini expiration/reset window to avoid false positives
        if now.hour == mini_reset_hour and now.minute <= 9:
            mini_leaders_logger.debug(f"Skipping leader check during mini expiration window at {now}")
            return
        
        mini_leaders_logger.debug(f"Running mini leaders check at {now}")
        log_asyncio_context()
        
        # check for global leader changes (returns True/False instead of guild dict)
        mini_leaders_logger.debug("Calling check_mini_leaders()...")
        has_new_leader = await check_mini_leaders()
        mini_leaders_logger.debug(f"check_mini_leaders returned: {has_new_leader}")

        if not has_new_leader:
            mini_leaders_logger.debug("No new leader detected, task complete")
            return

        mini_leaders_logger.info("NEW MINI LEADER DETECTED! Processing announcement...")

        # Post to ALL connected guilds since mini leaderboard is now global
        connected_guilds = {guild.name for guild in client.guilds}
        mini_leaders_logger.info(f"Connected guilds: {connected_guilds}")
        
        for guild_name in connected_guilds:
            mini_leaders_logger.debug(f"Processing guild: {guild_name}")
            
            # Get the default channel ID
            channel_id = get_default_channel_id(guild_name)
            mini_leaders_logger.debug(f"Default channel ID for {guild_name}: {channel_id}")
            
            if not channel_id:
                mini_leaders_logger.warning(f"No default channel ID found for {guild_name}, skipping")
                continue

            basic_message = "There's a new mini leader!"
            channel = client.get_channel(channel_id)
            mini_leaders_logger.debug(f"Got channel object for {guild_name}: {channel}")
            
            if channel:
                try:
                    mini_leaders_logger.info(f"Sending announcement to {guild_name} in #{channel.name}")
                    await channel.send(basic_message)
                    
                    # Create leaderboard and send as image file
                    mini_leaders_logger.debug("Creating leaderboard image...")
                    leaderboards = Leaderboards(client, tree)
                    img_path = await leaderboards.show_leaderboard(game='mini')
                    
                    # Check if we got a valid file path (should end with .png and exist)
                    if (img_path and isinstance(img_path, str) and 
                        img_path.endswith('.png') and 
                        os.path.exists(img_path)):
                        mini_leaders_logger.info(f"Sending leaderboard image to {guild_name}: {img_path}")
                        await channel.send(file=discord.File(img_path))
                        mini_leaders_logger.info(f"Successfully posted mini leader announcement to {guild_name}")
                    else:
                        # Either got an error message or file doesn't exist
                        error_msg = img_path if isinstance(img_path, str) else "Unknown error generating leaderboard"
                        mini_leaders_logger.error(f"Failed to generate mini leaderboard for {guild_name}: {error_msg}")
                        await channel.send("Error: Could not generate mini leaderboard image")
                        
                except Exception as e:
                    log_exception(mini_leaders_logger, e, f"posting mini leader update to {guild_name}")
            else:
                mini_leaders_logger.error(f"Could not get channel object for channel ID {channel_id} in {guild_name}")
                    
    except Exception as e:
        log_exception(mini_leaders_logger, e, "post_new_mini_leaders task execution")

@post_new_mini_leaders.before_loop
async def before_post_new_mini_leaders():
    mini_leaders_logger.info("Mini leaders monitoring task starting...")

@post_new_mini_leaders.after_loop
async def after_post_new_mini_leaders():
    if post_new_mini_leaders.is_being_cancelled():
        mini_leaders_logger.warning("Mini leaders monitoring task was cancelled")
    else:
        mini_leaders_logger.error("Mini leaders monitoring task stopped unexpectedly")

# task 2 - reset leaders when mini resets
@tasks.loop(minutes=10)
async def reset_mini_leaders(client: discord.Client):
    try:
        now = datetime.now()
        mini_reset_hour = 18 if now.weekday() >= 5 else 22  # Fixed: 6pm weekends, 10pm weekdays
        
        reset_leaders_logger.debug(f"Reset check at {now} - reset hour is {mini_reset_hour}")
        
        if now.hour == mini_reset_hour and now.minute <= 1:  # reset window
            reset_leaders_logger.info(f"MINI RESET TIME! Resetting global mini leaders at {now}")
            
            # Reset global mini leaders file (not per-guild anymore)
            leader_filepath = direct_path_finder('files', 'config', 'global_mini_leaders.json')
            write_json(leader_filepath, [])  # makes it an empty list
            reset_leaders_logger.info(f"Successfully reset global mini leaders file: {leader_filepath}")
        else:
            reset_leaders_logger.debug(f"Not reset time - current: {now.hour}:{now.minute:02d}, reset: {mini_reset_hour}:00-01")

    except Exception as e:
        log_exception(reset_leaders_logger, e, "reset_mini_leaders task execution")

@reset_mini_leaders.before_loop
async def before_reset_mini_leaders():
    reset_leaders_logger.info("Mini leaders reset task starting...")
    
@reset_mini_leaders.after_loop
async def after_reset_mini_leaders():
    if reset_mini_leaders.is_being_cancelled():
        reset_leaders_logger.warning("Mini leaders reset task was cancelled")
    else:
        reset_leaders_logger.error("Mini leaders reset task stopped unexpectedly")

# task 3 - end of day mini summary and simple warning system
@tasks.loop(minutes=10)
async def daily_mini_summary(client: discord.Client, tree: discord.app_commands.CommandTree):
    try:
        now = datetime.now()
        mini_reset_hour = 18 if now.weekday() >= 5 else 22  # 6pm weekends, 10pm weekdays
        
        daily_summary_logger.info(f"Daily summary check at {now} - mini expires at {mini_reset_hour}:00")
        
        # Check if it's mini expiration time (within 10 minute window)
        if now.hour == mini_reset_hour and now.minute <= 9:
            daily_summary_logger.info(f"MINI EXPIRATION TIME! Processing warnings and leaderboard at {now}")
            
            # 1. Send warnings to users who haven't completed the mini
            try:
                users_needing_warnings = await find_users_to_warn()
                daily_summary_logger.info(f"Found {len(users_needing_warnings)} users who need warnings")
                
                # Get users who have already been warned today to avoid duplicates
                today = datetime.now().strftime('%Y-%m-%d')
                already_warned_query = """
                    SELECT DISTINCT discord_id_nbr 
                    FROM games.mini_warning_history 
                    WHERE warning_date = %s AND success = 1
                """
                already_warned_result = await execute_query(already_warned_query, (today,))
                already_warned_ids = {row['discord_id_nbr'] for row in already_warned_result}
                daily_summary_logger.info(f"Found {len(already_warned_ids)} users already warned today")
                
                # Get all guild member IDs to check if users are in connected guilds
                guild_member_ids = {member.id for guild in client.guilds for member in guild.members}
                
                for user in users_needing_warnings:
                    user_id = user['discord_id_nbr']
                    user_name = user.get('name', 'Unknown')
                    
                    # Skip if already warned today
                    if user_id in already_warned_ids:
                        daily_summary_logger.debug(f"Skipping {user_name} - already warned today")
                        continue
                    
                    # Only send DM if user is in a connected guild
                    if user_id not in guild_member_ids:
                        daily_summary_logger.debug(f"Skipping DM to {user_name} - not in any connected guilds")
                        await track_warning_attempt(
                            player_name=user_name,
                            discord_id_nbr=user_id,
                            success=False,
                            error_message="User not in any connected guilds"
                        )
                        continue
                    
                    try:
                        # Send DM warning
                        discord_user = await client.fetch_user(user_id)
                        warning_text = f"🕛 **Mini reminder!** The mini crossword expires soon and you haven't completed it yet!"
                        
                        await discord_user.send(warning_text)
                        daily_summary_logger.info(f"Sent mini warning DM to {user_name} ({user_id})")
                        
                        # Track successful warning
                        await track_warning_attempt(
                            player_name=user_name,
                            discord_id_nbr=user_id,
                            success=True
                        )
                        
                    except Exception as e:
                        log_exception(daily_summary_logger, e, f"sending DM to {user_name}")
                        
                        # Track failed warning
                        await track_warning_attempt(
                            player_name=user_name,
                            discord_id_nbr=user_id,
                            success=False,
                            error_message=str(e)
                        )
                        
            except Exception as e:
                log_exception(daily_summary_logger, e, "processing mini warnings")
            
            # 2. Post final mini leaderboard to all connected guilds
            try:
                connected_guilds = {guild.name for guild in client.guilds}
                daily_summary_logger.info(f"Posting final mini leaderboard to {len(connected_guilds)} guilds")
                
                for guild_name in connected_guilds:
                    channel_id = get_default_channel_id(guild_name)
                    if not channel_id:
                        daily_summary_logger.warning(f"No default channel ID for {guild_name}")
                        continue
                    
                    channel = client.get_channel(channel_id)
                    if not channel:
                        daily_summary_logger.error(f"Could not get channel object for channel ID {channel_id} in {guild_name}")
                        continue
                    
                    try:
                        # Send final results message
                        summary_msg = "🏁 **Final Mini Results for Today!**"
                        await channel.send(summary_msg)
                        
                        # Generate and send leaderboard image
                        leaderboards = Leaderboards(client, tree)
                        img_path = await leaderboards.show_leaderboard(game='mini')
                        
                        if (img_path and isinstance(img_path, str) and 
                            img_path.endswith('.png') and 
                            os.path.exists(img_path)):
                            await channel.send(file=discord.File(img_path))
                            daily_summary_logger.info(f"Successfully posted final mini leaderboard to {guild_name}")
                        else:
                            error_msg = img_path if isinstance(img_path, str) else "Unknown error"
                            daily_summary_logger.error(f"Failed to generate leaderboard for {guild_name}: {error_msg}")
                            await channel.send("Error: Could not generate mini leaderboard image")
                            
                    except Exception as e:
                        log_exception(daily_summary_logger, e, f"posting final mini leaderboard to {guild_name}")
                        
            except Exception as e:
                log_exception(daily_summary_logger, e, "posting final mini leaderboards")
                
        else:
            daily_summary_logger.debug(f"Not mini expiration time - current: {now.hour}:{now.minute:02d}, expires at: {mini_reset_hour}:00")
                            
    except Exception as e:
        log_exception(daily_summary_logger, e, "daily_mini_summary task execution")

@daily_mini_summary.before_loop
async def before_daily_mini_summary():
    daily_summary_logger.info("Daily mini summary task starting...")
    
@daily_mini_summary.after_loop
async def after_daily_mini_summary():
    if daily_mini_summary.is_being_cancelled():
        daily_summary_logger.warning("Daily mini summary task was cancelled")
    else:
        daily_summary_logger.error("Daily mini summary task stopped unexpectedly")

def setup_tasks(client: discord.Client, tree: discord.app_commands.CommandTree):
    setup_logger.info("="*40)
    setup_logger.info("SETTING UP BACKGROUND TASKS")
    setup_logger.info("="*40)
    
    try:
        # Start the continuous monitoring task
        if post_new_mini_leaders.is_running():
            setup_logger.warning("post_new_mini_leaders already running, stopping first")
            post_new_mini_leaders.stop()
        
        post_new_mini_leaders.start(client, tree)
        setup_logger.info("✓ Started post_new_mini_leaders task (60 second interval)")

        # Start time-based tasks (they have their own time checks)
        if reset_mini_leaders.is_running():
            setup_logger.warning("reset_mini_leaders already running, stopping first")
            reset_mini_leaders.stop()
            
        reset_mini_leaders.start(client)
        setup_logger.info("✓ Started reset_mini_leaders task (every 10 minutes)")
        
        if daily_mini_summary.is_running():
            setup_logger.warning("daily_mini_summary already running, stopping first")
            daily_mini_summary.stop()
            
        daily_mini_summary.start(client, tree)
        setup_logger.info("✓ Started daily_mini_summary task (every 10 minutes)")
        
        setup_logger.info("="*40)
        setup_logger.info("ALL BACKGROUND TASKS STARTED SUCCESSFULLY")
        setup_logger.info("="*40)
        
    except Exception as e:
        log_exception(setup_logger, e, "setting up background tasks")
        setup_logger.critical("FAILED TO START BACKGROUND TASKS!")
        raise
