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
from bot.functions.timezone_warnings import get_users_to_warn_by_timezone
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
        mini_leaders_logger.debug(f"Running mini leaders check at {datetime.now()}")
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
        mini_reset_hour = 22 if now.weekday() >= 5 else 18
        
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

# task 3 - end of day mini summary and timezone-based warnings
@tasks.loop(minutes=10)
async def daily_mini_summary(client: discord.Client, tree: discord.app_commands.CommandTree):
    try:
        now = datetime.now()
        mini_reset_hour = 18 if now.weekday() >= 5 else 22  # 6pm weekends, 10pm weekdays
        
        daily_summary_logger.debug(f"Daily summary check at {now} - reset: {mini_reset_hour}")
        
        # Check for users who need timezone-based warnings (12PM in their local time)
        users_to_warn = await get_users_to_warn_by_timezone(target_hour=12)
        if users_to_warn:
            daily_summary_logger.info(f"TIMEZONE WARNINGS! Found {len(users_to_warn)} users to warn at their local 12PM")
            
            # Check which users are in connected guilds to avoid unnecessary API calls
            guild_member_ids = {member.id for guild in client.guilds for member in guild.members}
            
            for user_data, user_timezone in users_to_warn:
                user = user_data
                if user['discord_id_nbr'] not in guild_member_ids:
                    daily_summary_logger.debug(f"Skipping DM to {user['name']} - not in any connected guilds")
                    continue
                    
                try:
                    # Get user by discord ID and send personalized DM
                    discord_user = await client.fetch_user(user['discord_id_nbr'])
                    warning_text = f"🕛 **Mini reminder!** It's 12:00 PM in your timezone ({user_timezone}) - time to do today's mini crossword!"
                    
                    await discord_user.send(warning_text)
                    daily_summary_logger.info(f"Sent timezone-based mini warning DM to {user['name']} ({user['discord_id_nbr']}) in {user_timezone}")
                except Exception as e:
                    log_exception(daily_summary_logger, e, f"sending timezone-based DM to {user['name']}")
        
        # Send end-of-day summary to channels when mini resets
        if now.hour == mini_reset_hour and now.minute <= 5:  # 5 minute window
            daily_summary_logger.info(f"MINI SUMMARY TIME! Sending end-of-day summaries at {now}")
            
            connected_guilds = {guild.name for guild in client.guilds}
            for guild_name in connected_guilds:
                channel_id = get_default_channel_id(guild_name)
                if channel_id:
                    channel = client.get_channel(channel_id)
                    if channel:
                        summary_msg = "🏁 **Final Mini Results for Today!**"
                        try:
                            daily_summary_logger.info(f"Sending daily summary to {guild_name}")
                            await channel.send(summary_msg)
                            # Show final leaderboard
                            leaderboards = Leaderboards(client, tree)
                            img_path = await leaderboards.show_leaderboard(game='mini')
                            if (img_path and isinstance(img_path, str) and 
                                img_path.endswith('.png') and 
                                os.path.exists(img_path)):
                                await channel.send(file=discord.File(img_path))
                                daily_summary_logger.info(f"Successfully sent daily summary to {guild_name}")
                            else:
                                daily_summary_logger.error(f"Failed to generate daily mini summary leaderboard for {guild_name}: {img_path}")
                        except Exception as e:
                            log_exception(daily_summary_logger, e, f"sending daily mini summary to {guild_name}")
                else:
                    daily_summary_logger.warning(f"No default channel ID for {guild_name}")
        else:
            daily_summary_logger.debug(f"Not summary time - current: {now.hour}:{now.minute:02d}")
                            
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
