import discord
import pandas as pd
from bot.functions import execute_query
from bot.functions.admin import read_json, write_json
from bot.functions.admin import direct_path_finder
from bot.connections.logging_config import get_logger, log_exception

# Get logger for mini warning functions
mini_warning_logger = get_logger('mini_warning')

# find users who haven't completed the mini
async def find_users_to_warn():
    try:
        mini_warning_logger.debug("Finding users to warn...")
        result = await execute_query("SELECT * FROM matt.mini_not_completed")
        df = pd.DataFrame(result)
        
        if df.empty:
            mini_warning_logger.info("No users found to warn (all completed mini)")
            return []
        
        users_to_message = []
        for index, row in df.iterrows():
            users_to_message.append({
                'name': row['player_name'],
                'discord_id_nbr': row['discord_id_nbr']
            })
        
        mini_warning_logger.info(f"Found {len(users_to_message)} users to warn: {[u['name'] for u in users_to_message]}")
        return users_to_message
        
    except Exception as e:
        log_exception(mini_warning_logger, e, "finding users to warn")
        return []

# check mini leaders
async def check_mini_leaders():
    try:
        mini_warning_logger.debug("Starting mini leaders check...")
        
        # get latest global leaders - now checking global leaderboard instead of per-guild
        query = """
            select 
                player_name,
                game_time
            from matt.mini_view
            where game_date = (select max(game_date) from matt.mini_view)
            and game_rank = 1
            and guild_nm = 'Global'
        """
        
        mini_warning_logger.debug(f"Executing query: {query}")
        result = await execute_query(query)
        mini_warning_logger.debug(f"Query returned {len(result)} rows: {result}")
        
        # Convert result to DataFrame
        df = pd.DataFrame(result)
        
        # Check if we have any data
        if df.empty:
            mini_warning_logger.info("No mini leaders found for today - no data available")
            return False

        # get current leaders (global list)
        new_leaders = sorted(df['player_name'].tolist())
        mini_warning_logger.info(f"New leaders from database: {new_leaders}")

        # get list of previous global leaders
        leader_filepath = direct_path_finder('files', 'config', 'global_mini_leaders.json')
        mini_warning_logger.debug(f"Reading previous leaders from: {leader_filepath}")
        
        previous_leaders = read_json(leader_filepath)
        if previous_leaders is None:
            previous_leaders = []
        
        mini_warning_logger.info(f"Previous leaders from file: {previous_leaders}")
        
        # check if new leaders are different
        if new_leaders != sorted(previous_leaders):
            mini_warning_logger.info(f"🏆 NEW MINI LEADERS DETECTED! {new_leaders} (was: {previous_leaders})")
            write_json(leader_filepath, new_leaders)
            mini_warning_logger.debug(f"Updated leaders file: {leader_filepath}")
            return True
        else:
            mini_warning_logger.debug(f"No change in leaders: {new_leaders}")
            return False
            
    except Exception as e:
        log_exception(mini_warning_logger, e, "checking mini leaders")
        return False
