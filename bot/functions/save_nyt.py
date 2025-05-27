import argparse
import os
import json
from datetime import datetime, timedelta
import asyncio
import pytz
import time

import requests
from dotenv import load_dotenv
from tqdm import tqdm
import pandas as pd
from dateutil.relativedelta import relativedelta

# Import our SQL helper
from sql_helper import send_df_to_sql, execute_query, close_pool

load_dotenv()

API_ROOT = "http://www.nytimes.com/svc/crosswords"
PUZZLE_INFO = API_ROOT + "/v3/puzzles.json"
PUZZLE_DETAIL = API_ROOT + "/v6/game/"
DATE_FORMAT = "%Y-%m-%d"

# Configure argument parser efficiently
parser = argparse.ArgumentParser(description="Fetch NYT Crossword stats for multiple users")

# Define arguments in a clean data structure
arguments = [
    (("-u", "--user"), {"help": "Specific user to fetch data for (by player_name). If not specified, fetches for all active users"}),
    (("-s", "--start-date"), {"help": "The first date to pull from, inclusive (defaults to 7 days ago)", "default": datetime.strftime(datetime.now() - timedelta(days=7), DATE_FORMAT)}),
    (("-e", "--end-date"), {"help": "The last date to pull from, inclusive (defaults to today)", "default": datetime.strftime(datetime.now(), DATE_FORMAT)}),

    (("-t", "--type"), {"help": 'The type of puzzle data to fetch. Valid values are "daily", "mini", or "all" (defaults to all)', "default": "all"}),
    (("--config-file",), {"help": "Path to users config JSON file", "default": "files/config/users.json"}),
    (("--date-range",), {"help": "Use specific date range instead of incremental mode (for backfills)", "action": "store_true"}),
    (("--historical",), {"help": "Historical backfill mode: process data month-by-month backwards from latest missing data to start-date", "action": "store_true"}),

]

# Add arguments to parser
for arg_names, arg_config in arguments:
    parser.add_argument(*arg_names, **arg_config)


def unix_to_eastern_datetime(unix_timestamp):
    """Convert Unix timestamp to Eastern timezone datetime string"""
    if unix_timestamp is None:
        return None
    
    # Create timezone objects
    utc = pytz.UTC
    eastern = pytz.timezone('US/Eastern')
    
    # Convert Unix timestamp to UTC datetime, then to Eastern
    utc_dt = datetime.fromtimestamp(unix_timestamp, tz=utc)
    eastern_dt = utc_dt.astimezone(eastern)
    
    # Return as readable string
    return eastern_dt.strftime('%Y-%m-%d %H:%M:%S %Z')


def convert_star_to_boolean(star_value):
    """Convert star value to boolean for database storage"""
    if star_value is None:
        return None
    
    # Handle various star representations
    if isinstance(star_value, str):
        star_lower = star_value.lower()
        if star_lower in ['gold', 'true', '1']:
            return True
        elif star_lower in ['false', '0', 'none', '']:
            return False
        else:
            return None  # Unknown value
    elif isinstance(star_value, bool):
        return star_value
    elif isinstance(star_value, (int, float)):
        return bool(star_value)
    else:
        return None


def load_users_config(config_file):
    """Load user configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return [user for user in config['users'] if user.get('active', True)]
    except FileNotFoundError:
        print(f"Config file {config_file} not found!")
        return []
    except json.JSONDecodeError:
        print(f"Invalid JSON in config file {config_file}!")
        return []


def extract_puzzle_fields(detail, player_name, print_date, puzzle_data):
    """
    Extract essential puzzle fields from API detail response
    
    NEW FEATURES (addressing design flaws):
    1. ✅ Extracts checks/reveals data from board.cells for cheat detection
    2. ✅ Per-user date ranges instead of arbitrary 365-day global window  
    3. ✅ Eliminates confusing global vs individual user logic
    """
    # Get nested sections
    calcs = detail.get("calcs", {})
    firsts = detail.get("firsts", {})
    board = detail.get("board", {})
    
    # Calculate checks and reveals from board data
    # ✅ FOUND IT! Cells can have 'revealed': true and 'checked': true flags
    checks_used = 0
    reveals_used = 0
    
    if board and "cells" in board:
        cells = board["cells"]
        for cell in cells:
            if isinstance(cell, dict):
                # Count revealed cells
                if cell.get("revealed", False):
                    reveals_used += 1
                # Count checked cells (similar pattern expected)
                if cell.get("checked", False):
                    checks_used += 1
    
    # Create streamlined structure with only essential fields
    puzzle_id = puzzle_data.get("puzzle_id", "unknown")
    
    essential_record = {
        # Core identifiers
        "record_id": f"{print_date}_{puzzle_data.get('publish_type', 'unknown').lower()}_{player_name}",
        "player_name": player_name,
        "print_date": print_date,
        "puzzle_type": puzzle_data.get("publish_type", "unknown"),
        
        # Puzzle info (keeping the useful ones)
        "author": puzzle_data.get("author", None),
        "title": puzzle_data.get("title", None),
        "puzzle_id": puzzle_id,
        
        # Core performance metrics
        "solved": calcs.get("solved", puzzle_data.get("solved", None)),
        "solving_seconds": calcs.get("secondsSpentSolving", None),
        "percent_filled": calcs.get("percentFilled", puzzle_data.get("percent_filled", None)),
        "eligible": calcs.get("eligible", None),
        "star": convert_star_to_boolean(puzzle_data.get("star", None)),
        "checks_used": checks_used,
        "reveals_used": reveals_used, 
        "clean_solve": (checks_used == 0 and reveals_used == 0),
        
        # Key timestamps (converted to Eastern time)
        "opened_datetime": unix_to_eastern_datetime(firsts.get("opened", None)),
        "solved_datetime": unix_to_eastern_datetime(firsts.get("solved", None)),
        "min_guess_datetime": unix_to_eastern_datetime(detail.get("minGuessTime", None)),
        "final_commit_datetime": unix_to_eastern_datetime(detail.get("timestamp", None)),
        
        # System tracking
        "bot_added_ts": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return essential_record


async def get_player_last_commit(player_name, puzzle_type):
    """Get the latest commit timestamp for a player from our database for specific puzzle type"""
    try:
        query = """
            SELECT MAX(final_commit_datetime) as last_commit
            FROM nyt_history 
            WHERE player_name = %s 
            AND puzzle_type = %s
            AND final_commit_datetime IS NOT NULL
            AND final_commit_datetime != '-'
        """
        results = await execute_query(query, (player_name, puzzle_type))
        
        if results and results[0]['last_commit']:
            return results[0]['last_commit']
        return None
    except Exception as e:
        print(f"Warning: Could not fetch last commit for {player_name} - {puzzle_type}: {e}")
        return None





def puzzle_modified_since_last_check(api_timestamp, last_commit_str):
    """Check if puzzle was modified since player's last recorded commit"""
    if not last_commit_str or not api_timestamp:
        return True  # No baseline or API timestamp, update to be safe
    
    try:
        # Convert API timestamp to Eastern datetime string
        api_datetime_str = unix_to_eastern_datetime(api_timestamp)
        if not api_datetime_str:
            return True  # Can't parse API timestamp, update to be safe
            
        # Compare timestamps - if API timestamp is newer than our last check, update
        return api_datetime_str > last_commit_str
    except Exception:
        return True  # Any parsing error, update to be safe





def get_v3_puzzle_overview(puzzle_type, cookie, start_date=None, end_date=None):
    payload = {
        "publish_type": puzzle_type,
        "sort_order": "asc",
        "sort_by": "print_date",
    }
    
    # Add date parameters only if specified (for --date-range mode)
    if start_date and end_date:
        payload["date_start"] = start_date.strftime("%Y-%m-%d")
        payload["date_end"] = end_date.strftime("%Y-%m-%d")

    overview_resp = requests.get(PUZZLE_INFO, params=payload, cookies={"NYT-S": cookie})

    overview_resp.raise_for_status()
    puzzle_info = overview_resp.json().get("results")
    return puzzle_info


def get_v3_puzzle_detail(puzzle_id, cookie):
    puzzle_resp = requests.get(
        f"{PUZZLE_DETAIL}/{puzzle_id}.json", cookies={"NYT-S": cookie}
    )

    puzzle_resp.raise_for_status()
    puzzle_detail = puzzle_resp.json()  # Return full response, not just calcs

    return puzzle_detail


async def process_user_data(user, puzzle_type, start_date=None, end_date=None, use_date_range=False):
    """Process NYT crossword data for a single user and return the results"""
    mode = "date range" if use_date_range else "incremental"
    print(f"Processing {user['player_name']} ({mode} mode)")
    
    cookie = user['nyt_s_cookie']
    
    # Get puzzles based on mode
    if use_date_range and start_date and end_date:
        # Date range mode - use specified dates, no commit filtering
        puzzle_overview = get_v3_puzzle_overview(
            puzzle_type=puzzle_type,
            cookie=cookie,
            start_date=start_date,
            end_date=end_date,
        )
    else:
        # Incremental mode - scan last 7 days, then filter by commit timestamp
        from datetime import datetime, timedelta
        today = datetime.now()
        seven_days_ago = today - timedelta(days=7)
        puzzle_overview = get_v3_puzzle_overview(
            puzzle_type=puzzle_type,
            cookie=cookie,
            start_date=seven_days_ago,
            end_date=today,
        )

    # Get baseline for incremental mode only
    if not use_date_range:
        last_commit_str = await get_player_last_commit(user['player_name'], puzzle_type)
    else:
        last_commit_str = None  # Date range mode - process all puzzles found

    # Convert puzzles to streamlined structure
    essential_puzzles = []
    skipped_count = 0
    
    for puzzle in tqdm(puzzle_overview, desc=f"Checking {user['player_name']} {puzzle_type} puzzles", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"):
        try:
            # Get detail first to check timestamp
            detail = get_v3_puzzle_detail(puzzle_id=puzzle["puzzle_id"], cookie=cookie)
            api_timestamp = detail.get("timestamp", None)
            
            # Check if we should skip this puzzle (incremental mode only)
            if not use_date_range and last_commit_str:
                # Skip if puzzle hasn't been modified since our last recorded commit
                if not puzzle_modified_since_last_check(api_timestamp, last_commit_str):
                    skipped_count += 1
                    continue
            
            # Extract essential fields only
            essential_record = extract_puzzle_fields(detail, user['player_name'], puzzle["print_date"], puzzle)
            essential_puzzles.append(essential_record)
            
        except Exception as e:
            print(f"Error processing puzzle {puzzle['puzzle_id']}: {e}")
            # Set defaults for error cases using helper function
            default_record = extract_puzzle_fields({}, user['player_name'], puzzle["print_date"], puzzle)
            essential_puzzles.append(default_record)

    return essential_puzzles











async def save_to_sql(puzzles_data, table_name="nyt_history"):
    """Save puzzle data to SQL database using existing sql_helper patterns"""
    try:
        df = pd.DataFrame(puzzles_data)
        
        if df.empty:
            return
        
        await send_df_to_sql(df, table_name, if_exists='upsert', unique_key='record_id')
        
    except Exception as e:
        print(f"Error saving to SQL: {e}")
        raise


async def get_user_latest_date(player_name, puzzle_type):
    """Get the latest puzzle date for a user, or None if no data exists."""
    try:
        query = """
            SELECT MAX(print_date) as latest_date
            FROM nyt_history 
            WHERE player_name = %s AND puzzle_type = %s
        """
        results = await execute_query(query, (player_name, puzzle_type))
        
        if results and results[0]['latest_date']:
            return results[0]['latest_date']
        return None
    except Exception as e:
        print(f"Warning: Could not fetch latest date for {player_name} - {puzzle_type}: {e}")
        return None


def get_month_range(year, month):
    """Get start and end dates for a given year/month."""
    start_date = datetime(year, month, 1)
    end_date = start_date + relativedelta(months=1) - timedelta(days=1)
    return start_date, end_date


async def process_historical_backfill(users, puzzle_types, start_year):
    """Process historical data month-by-month backwards for each user."""
    total_records = 0
    completed_tasks = []
    failed_tasks = []
    
    for puzzle_type in puzzle_types:
        print(f"\n=== {puzzle_type.upper()} HISTORICAL BACKFILL ===")
        
        for user in users:
            print(f"\nProcessing {user['player_name']} - {puzzle_type}")
            
            # Find where to start for this user
            latest_date_str = await get_user_latest_date(user['player_name'], puzzle_type)
            
            if latest_date_str:
                latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d')
                start_month = latest_date.month
                start_year_actual = latest_date.year
                print(f"  User has data through {latest_date_str}, starting from there")
            else:
                start_month = datetime.now().month
                start_year_actual = datetime.now().year
                print(f"  User has no data, starting from current month")
            
            current_year = start_year_actual
            current_month = start_month
            user_total = 0
            
            # Process month by month backwards
            while current_year >= start_year:
                # Skip the first month if user already has data
                if current_year == start_year_actual and latest_date_str:
                    current_month -= 1
                    if current_month == 0:
                        current_month = 12
                        current_year -= 1
                        continue
                
                try:
                    # Get month date range
                    month_start, month_end = get_month_range(current_year, current_month)
                    
                    print(f"  Processing {current_year}-{current_month:02d} ({month_start.strftime('%Y-%m-%d')} to {month_end.strftime('%Y-%m-%d')})")
                    
                    # Process this month's data using existing function
                    puzzles_data = await process_user_data(
                        user, puzzle_type, 
                        start_date=month_start, 
                        end_date=month_end, 
                        use_date_range=True
                    )
                    
                    if puzzles_data:
                        await save_to_sql(puzzles_data)
                        user_total += len(puzzles_data)
                        print(f"    Saved {len(puzzles_data)} puzzles")
                    else:
                        print(f"    No puzzles found")
                    
                    # Small delay to be nice to the API
                    if puzzles_data:
                        time.sleep(1)
                        
                except Exception as e:
                    error_msg = f"{user['player_name']} - {puzzle_type} - {current_year}-{current_month:02d}: {str(e)}"
                    failed_tasks.append(error_msg)
                    print(f"    Error: {e}")
                
                # Move to previous month
                current_month -= 1
                if current_month == 0:
                    current_month = 12
                    current_year -= 1
            
            # Summary for this user
            task_name = f"{user['player_name']} - {puzzle_type}"
            if user_total > 0:
                completed_tasks.append(f"{task_name}: {user_total} records")
                total_records += user_total
                print(f"  Completed {task_name}: {user_total} total records")
            else:
                completed_tasks.append(f"{task_name}: 0 records")
                print(f"  Completed {task_name}: no new data")
    
    return total_records, completed_tasks, failed_tasks


async def main():
    args = parser.parse_args()
    
    # Load user configuration
    users = load_users_config(args.config_file)
    
    if not users:
        print("No active users found in configuration!")
        exit(1)
    
    # Filter to specific user if requested
    if args.user:
        users = [user for user in users if user['player_name'].lower() == args.user.lower()]
        if not users:
            print(f"User '{args.user}' not found in configuration!")
            exit(1)
    
    if args.type == "all":
        puzzle_types_to_fetch = ["daily", "mini"]
    else:
        puzzle_types_to_fetch = [args.type]
    
    # Historical backfill mode
    if args.historical:
        start_year = int(args.start_date.split('-')[0])  # Extract year from start_date
        print(f"Starting historical backfill from {start_year} to present")
        print(f"Processing {len(users)} users for {', '.join(puzzle_types_to_fetch)} puzzles")
        
        total_records, completed_tasks, failed_tasks = await process_historical_backfill(
            users, puzzle_types_to_fetch, start_year
        )
    
    # Regular incremental or date-range mode
    else:
        if args.date_range:
            global_start_date = datetime.strptime(args.start_date, DATE_FORMAT)
            global_end_date = datetime.strptime(args.end_date, DATE_FORMAT)
            use_global_dates = True
        else:
            use_global_dates = False
            global_start_date = None
            global_end_date = datetime.strptime(args.end_date, DATE_FORMAT)
        
        # Track progress
        total_records = 0
        completed_tasks = []
        failed_tasks = []
        
        for puzzle_type in puzzle_types_to_fetch:
            print(f"\n=== {puzzle_type.upper()} PUZZLES ===")
            
            for user in users:
                task_name = f"{user['player_name']} - {puzzle_type}"
                
                try:
                    if use_global_dates:
                        puzzles_data = await process_user_data(user, puzzle_type, global_start_date, global_end_date, args.date_range)
                    else:
                        puzzles_data = await process_user_data(user, puzzle_type, use_date_range=args.date_range)
                    
                    if puzzles_data:
                        await save_to_sql(puzzles_data)
                        
                        total_records += len(puzzles_data)
                        completed_tasks.append(f"{task_name}: {len(puzzles_data)} records")
                        print(f"{task_name}: {len(puzzles_data)} records saved")
                    else:
                        completed_tasks.append(f"{task_name}: 0 records")
                        print(f"{task_name}: no new data")
                        
                except Exception as e:
                    error_msg = f"{task_name}: {str(e)}"
                    failed_tasks.append(error_msg)
                    print(f"{task_name} failed: {e}")
    
    # Final summary
    print(f"\nProcessing complete:")
    print(f"Total records: {total_records}")
    print(f"Completed: {len(completed_tasks)}")
    print(f"Failed: {len(failed_tasks)}")
    
    if failed_tasks:
        print("Failed tasks:")
        for task in failed_tasks:
            print(f"  {task}")
    
    try:
        await close_pool()
    except Exception as e:
        print(f"Connection cleanup warning: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 