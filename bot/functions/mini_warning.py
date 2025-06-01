import discord
import pandas as pd
from datetime import datetime
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

async def track_warning_attempt(player_name: str, discord_id_nbr: int, success: bool, error_message: str = None, warning_type: str = 'daily_reminder'):
    """
    Track a warning attempt in the mini_warning_history table.
    
    Args:
        player_name: The player's display name
        discord_id_nbr: The Discord user ID
        success: Whether the warning was sent successfully
        error_message: Error message if the warning failed
        warning_type: Type of warning (default: 'daily_reminder')
    """
    try:
        warning_date = datetime.now().strftime('%Y-%m-%d')
        
        # Insert or update warning attempt
        query = """
        INSERT INTO games.mini_warning_history 
        (warning_date, player_name, discord_id_nbr, warning_sent, success, error_message, warning_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        warning_timestamp = CURRENT_TIMESTAMP,
        warning_sent = VALUES(warning_sent),
        success = VALUES(success),
        error_message = VALUES(error_message)
        """
        
        await execute_query(query, (
            warning_date,
            player_name,
            discord_id_nbr,
            True,  # warning_sent = True (we attempted it)
            success,
            error_message,
            warning_type
        ))
        
        mini_warning_logger.debug(f"Tracked warning attempt for {player_name} ({discord_id_nbr}): success={success}")
        
    except Exception as e:
        log_exception(mini_warning_logger, e, f"tracking warning attempt for {player_name}")

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

        # compare lists (order matters!)
        if sorted(new_leaders) != sorted(previous_leaders):
            mini_warning_logger.info(f"LEADER CHANGE DETECTED! Old: {previous_leaders}, New: {new_leaders}")
            
            # Save the new leaders to file
            write_json(leader_filepath, new_leaders)
            mini_warning_logger.info(f"Updated global leaders file with: {new_leaders}")
            
            return True  # Signal that there's a new leader
        else:
            mini_warning_logger.debug("No leader change detected")
            return False  # No change

    except Exception as e:
        log_exception(mini_warning_logger, e, "checking mini leaders")
        return False
