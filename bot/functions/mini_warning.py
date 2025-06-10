import discord
import pandas as pd
from datetime import datetime, timedelta
from bot.functions import execute_query
from bot.functions.admin import read_json, write_json
from bot.functions.admin import direct_path_finder
from bot.connections.logging_config import get_logger, log_exception

# Get logger for mini warning functions
mini_warning_logger = get_logger('mini_warning')

def get_current_mini_date():
    """
    Calculate the current mini date based on reset times:
    - Mini resets at 6pm on weekends (Saturday/Sunday)  
    - Mini resets at 10pm on weekdays
    
    If current time is after today's reset time, we're on tomorrow's mini.
    If current time is before today's reset time, we're still on today's mini.
    """
    now = datetime.now()
    
    # Determine reset hour for today
    # Saturday = 5, Sunday = 6, so weekday() >= 5 means weekend
    mini_reset_hour = 18 if now.weekday() >= 5 else 22  # 6pm weekends, 10pm weekdays
    
    # If we've passed today's reset time, we're on tomorrow's mini
    if now.hour >= mini_reset_hour:
        mini_date = (now + timedelta(days=1)).date()
    else:
        # If we haven't reached today's reset time, we're still on today's mini
        mini_date = now.date()
    
    return mini_date

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
        # Get the current mini date (accounts for reset times)
        current_mini_date = get_current_mini_date()
        
        # get latest global leaders - now using proper mini date instead of max(game_date)
        query = """
            select 
                player_name,
                game_time
            from matt.mini_view
            where game_date = %s
            and game_rank = 1
            and guild_nm = 'Global'
        """
        
        result = await execute_query(query, (current_mini_date,))
        
        # Convert result to DataFrame
        df = pd.DataFrame(result)
        
        # Check if we have any data
        if df.empty:
            return False

        # get current leaders (global list)
        new_leaders = sorted(df['player_name'].tolist())

        # get list of previous global leaders
        leader_filepath = direct_path_finder('files', 'config', 'global_mini_leaders.json')
        
        previous_leaders = read_json(leader_filepath)
        if previous_leaders is None:
            previous_leaders = []

        # compare lists (order matters!)
        if sorted(new_leaders) != sorted(previous_leaders):
            mini_warning_logger.info(f"LEADER CHANGE DETECTED! Old: {previous_leaders}, New: {new_leaders}")
            
            # Save the new leaders to file
            write_json(leader_filepath, new_leaders)
            mini_warning_logger.info(f"Updated global leaders file with: {new_leaders}")
            
            return True  # Signal that there's a new leader
        else:
            return False  # No change

    except Exception as e:
        log_exception(mini_warning_logger, e, "checking mini leaders")
        return False
