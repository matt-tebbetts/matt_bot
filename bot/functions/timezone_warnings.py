import discord
import pandas as pd
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from bot.functions import execute_query
from bot.functions.admin import read_json, write_json, direct_path_finder
from bot.connections.logging_config import get_logger, log_exception

# Get logger for timezone warning functions
timezone_logger = get_logger('timezone_warnings')

# Common timezone mappings for users who might not specify full timezone names
TIMEZONE_MAPPINGS = {
    'EST': 'America/New_York',
    'EDT': 'America/New_York',
    'CST': 'America/Chicago', 
    'CDT': 'America/Chicago',
    'MST': 'America/Denver',
    'MDT': 'America/Denver',
    'PST': 'America/Los_Angeles',
    'PDT': 'America/Los_Angeles',
    'GMT': 'Europe/London',
    'UTC': 'UTC',
    'CET': 'Europe/Paris',
    'CEST': 'Europe/Paris',
    'JST': 'Asia/Tokyo',
    'AEST': 'Australia/Sydney',
    'AEDT': 'Australia/Sydney',
    # Add more as needed
}

def get_user_timezone_config_path() -> str:
    """Get the path to the user timezone configuration file."""
    return direct_path_finder('files', 'config', 'user_timezones.json')

def load_user_timezones() -> Dict[str, str]:
    """Load user timezone preferences from config file.
    
    Returns:
        Dictionary mapping discord_id -> timezone_string
    """
    config_path = get_user_timezone_config_path()
    config = read_json(config_path, {})
    return config.get('user_timezones', {})

def save_user_timezones(user_timezones: Dict[str, str]) -> None:
    """Save user timezone preferences to config file.
    
    Args:
        user_timezones: Dictionary mapping discord_id -> timezone_string
    """
    config_path = get_user_timezone_config_path()
    config = read_json(config_path, {})
    config['user_timezones'] = user_timezones
    config['last_updated'] = datetime.now().isoformat()
    write_json(config_path, config)

def normalize_timezone(timezone_str: str) -> Optional[str]:
    """Normalize timezone string to a valid pytz timezone.
    
    Args:
        timezone_str: User-provided timezone string
        
    Returns:
        Valid pytz timezone string or None if invalid
    """
    if not timezone_str:
        return None
        
    # Clean up the input
    timezone_str = timezone_str.strip()
    
    # Try direct mapping first
    if timezone_str in TIMEZONE_MAPPINGS:
        timezone_str = TIMEZONE_MAPPINGS[timezone_str]
    
    # Validate it's a real timezone
    try:
        pytz.timezone(timezone_str)
        return timezone_str
    except pytz.exceptions.UnknownTimeZoneError:
        timezone_logger.warning(f"Unknown timezone: {timezone_str}")
        return None

async def set_user_timezone(discord_id: int, timezone_str: str) -> bool:
    """Set timezone preference for a user.
    
    Args:
        discord_id: Discord user ID
        timezone_str: Timezone string (e.g., 'America/New_York', 'EST', etc.)
        
    Returns:
        True if successful, False if invalid timezone
    """
    normalized_tz = normalize_timezone(timezone_str)
    if not normalized_tz:
        return False
    
    user_timezones = load_user_timezones()
    user_timezones[str(discord_id)] = normalized_tz
    save_user_timezones(user_timezones)
    
    timezone_logger.info(f"Set timezone for user {discord_id}: {normalized_tz}")
    return True

async def get_user_timezone(discord_id: int, default_timezone: str = 'America/New_York') -> str:
    """Get timezone preference for a user.
    
    Args:
        discord_id: Discord user ID
        default_timezone: Default timezone if user hasn't set one
        
    Returns:
        Timezone string
    """
    user_timezones = load_user_timezones()
    return user_timezones.get(str(discord_id), default_timezone)

async def get_users_to_warn_by_timezone(target_hour: int = 12) -> List[Tuple[Dict, str]]:
    """Get users who need warnings, organized by timezone and filtered by target hour.
    
    Args:
        target_hour: Hour of day (0-23) to send warnings in user's local time
        
    Returns:
        List of (user_dict, timezone) tuples for users who should receive warnings now
    """
    try:
        timezone_logger.debug(f"Finding users to warn at target hour {target_hour}")
        
        # Get users who haven't completed the mini
        result = await execute_query("SELECT * FROM matt.mini_not_completed")
        if not result:
            timezone_logger.info("No users found to warn (all completed mini)")
            return []
        
        users_df = pd.DataFrame(result)
        user_timezones = load_user_timezones()
        current_utc = datetime.now(pytz.UTC)
        
        users_to_warn = []
        
        for _, user_row in users_df.iterrows():
            discord_id = user_row['discord_id_nbr']
            user_timezone_str = await get_user_timezone(discord_id)
            
            try:
                user_tz = pytz.timezone(user_timezone_str)
                user_local_time = current_utc.astimezone(user_tz)
                
                # Check if it's the target hour in their timezone (with 5-minute window)
                if user_local_time.hour == target_hour and user_local_time.minute <= 5:
                    user_dict = {
                        'name': user_row['player_name'],
                        'discord_id_nbr': discord_id
                    }
                    users_to_warn.append((user_dict, user_timezone_str))
                    timezone_logger.info(f"User {user_row['player_name']} ({discord_id}) needs warning - local time: {user_local_time.strftime('%H:%M %Z')}")
                
            except Exception as e:
                timezone_logger.error(f"Error processing timezone for user {discord_id}: {e}")
                # Fallback to default behavior for this user
                continue
        
        timezone_logger.info(f"Found {len(users_to_warn)} users to warn at hour {target_hour}")
        return users_to_warn
        
    except Exception as e:
        log_exception(timezone_logger, e, "finding users to warn by timezone")
        return []

async def get_next_warning_times(discord_id: int, target_hour: int = 12) -> Dict[str, str]:
    """Get the next warning time for a user in their timezone.
    
    Args:
        discord_id: Discord user ID
        target_hour: Target hour for warnings
        
    Returns:
        Dictionary with timing information
    """
    try:
        user_timezone_str = await get_user_timezone(discord_id)
        user_tz = pytz.timezone(user_timezone_str)
        current_utc = datetime.now(pytz.UTC)
        user_local_time = current_utc.astimezone(user_tz)
        
        # Calculate next warning time
        next_warning = user_local_time.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        if next_warning <= user_local_time:
            next_warning += timedelta(days=1)
        
        return {
            'user_timezone': user_timezone_str,
            'current_local_time': user_local_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'next_warning_time': next_warning.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'next_warning_utc': next_warning.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
    except Exception as e:
        log_exception(timezone_logger, e, f"getting next warning times for user {discord_id}")
        return {}

def get_common_timezones() -> List[str]:
    """Get a list of common timezone options for users to choose from."""
    return [
        'America/New_York',      # Eastern
        'America/Chicago',       # Central  
        'America/Denver',        # Mountain
        'America/Los_Angeles',   # Pacific
        'Europe/London',         # GMT/BST
        'Europe/Paris',          # CET/CEST
        'Europe/Amsterdam',      # Netherlands
        'Europe/Berlin',         # Germany
        'Asia/Tokyo',            # Japan
        'Asia/Shanghai',         # China
        'Australia/Sydney',      # Australia East
        'Australia/Perth',       # Australia West
        'UTC'                    # UTC
    ] 