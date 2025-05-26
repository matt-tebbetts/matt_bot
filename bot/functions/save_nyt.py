import argparse
import os
import json
from datetime import datetime, timedelta
import asyncio
import pytz

import requests
from dotenv import load_dotenv
from tqdm import tqdm
import pandas as pd

# Import our SQL helper
from sql_helper import send_df_to_sql, execute_query

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

    (("-t", "--type"), {"help": 'The type of puzzle data to fetch. Valid values are "daily", "bonus", "mini", or "all" (defaults to all)', "default": "all"}),
    (("--config-file",), {"help": "Path to users config JSON file", "default": "files/config/users.json"}),
    (("--historical",), {"help": "Fetch all available historical data (overrides start-date)", "action": "store_true"}),

    (("--date-range",), {"help": "Use specific date range instead of incremental mode (for backfills)", "action": "store_true"}),
    (("--csv-backup",), {"help": "Save CSV backups of each user's data as it's processed", "action": "store_true"})
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
    """Extract essential puzzle fields only from API detail response"""
    # Get nested sections
    calcs = detail.get("calcs", {})
    firsts = detail.get("firsts", {})
    
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
        "star": puzzle_data.get("star", None),
        
        # Key timestamps (converted to Eastern time)
        "opened_datetime": unix_to_eastern_datetime(firsts.get("opened", None)),
        "solved_datetime": unix_to_eastern_datetime(firsts.get("solved", None)),
        "min_guess_datetime": unix_to_eastern_datetime(detail.get("minGuessTime", None)),
        "final_commit_datetime": unix_to_eastern_datetime(detail.get("timestamp", None)),
        
        # System tracking
        "bot_added_ts": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return essential_record


async def get_player_last_commit(player_name):
    """Get the latest commit timestamp for a player from our database"""
    try:
        query = """
            SELECT MAX(final_commit_datetime) as last_commit
            FROM nyt_history 
            WHERE player_name = %s 
            AND final_commit_datetime IS NOT NULL
            AND final_commit_datetime != '-'
        """
        results = await execute_query(query, (player_name,))
        
        if results and results[0]['last_commit']:
            return results[0]['last_commit']
        return None
    except Exception as e:
        print(f"Warning: Could not fetch last commit for {player_name}: {e}")
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





def get_v3_puzzle_overview(puzzle_type, start_date, end_date, cookie):
    payload = {
        "publish_type": puzzle_type,
        "sort_order": "asc",
        "sort_by": "print_date",
        "date_start": start_date.strftime("%Y-%m-%d"),
        "date_end": end_date.strftime("%Y-%m-%d"),
    }

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


async def process_user_data(user, start_date, end_date, puzzle_type, use_date_range=False):
    """Process NYT crossword data for a single user and return the results"""
    print(f"\nProcessing data for {user['player_name']}...")
    
    cookie = user['nyt_s_cookie']
    
    days_between = (end_date - start_date).days
    batches = (days_between // 100) + 1

    print(f"Getting stats from {start_date.strftime(DATE_FORMAT)} until {end_date.strftime(DATE_FORMAT)} in {batches} batches")

    if end_date - start_date > timedelta(days=100):
        batch_end = start_date + timedelta(days=100)
    else:
        batch_end = end_date
    batch_start = start_date

    puzzle_overview = []

    for batch in (pbar := tqdm(range(batches), desc=f"{user['player_name']} - Fetching overview")):
        pbar.set_description(f"{user['player_name']} - Start date: {batch_start}")
        batch_overview = get_v3_puzzle_overview(
            puzzle_type=puzzle_type,
            start_date=batch_start,
            end_date=batch_end,
            cookie=cookie,
        )
        puzzle_overview.extend(batch_overview)
        batch_start = batch_start + timedelta(days=100)
        batch_end = batch_end + timedelta(days=100)

    # Get baseline for incremental mode (default behavior)
    last_commit_str = None
    
    if not use_date_range:
        # Default incremental mode
        print(f"Checking last commit for {user['player_name']}...")
        last_commit_str = await get_player_last_commit(user['player_name'])
        if last_commit_str:
            print(f"Last recorded commit: {last_commit_str}")
        else:
            print("No previous commits found for this user")
    else:
        print(f"Date range mode: checking all puzzles in range")

    print(f"\nGetting puzzle solve times for {user['player_name']}\n")

    # Convert puzzles to streamlined structure
    essential_puzzles = []
    skipped_count = 0
    
    for puzzle in tqdm(puzzle_overview, desc=f"{user['player_name']} - Puzzle details"):
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

    if not use_date_range and skipped_count > 0:
        print(f"Incremental mode: skipped {skipped_count} unchanged puzzles, processed {len(essential_puzzles)} updates")

    print(f"{len(essential_puzzles)} records processed for {user['player_name']}")
    return essential_puzzles





def save_csv_backup(puzzles_data, user_name, puzzle_type, backup_dir="files/nyt_backups"):
    """Save puzzle data to CSV as backup"""
    try:
        if not puzzles_data:
            return None
            
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nyt_{user_name}_{puzzle_type}_{timestamp}.csv"
        filepath = os.path.join(backup_dir, filename)
        
        # Save to CSV
        df = pd.DataFrame(puzzles_data)
        df.to_csv(filepath, index=False)
        
        print(f"✓ CSV backup saved: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"Warning: Could not save CSV backup: {e}")
        return None


async def save_to_sql(puzzles_data, table_name="nyt_history"):
    """Save puzzle data to SQL database using existing sql_helper patterns"""
    try:
        # Convert to DataFrame
        df = pd.DataFrame(puzzles_data)
        
        if df.empty:
            print("No puzzle data to save to SQL")
            return
            
        print(f"Preparing to save {len(df)} records to SQL table '{table_name}'")
        
        # Use existing sql_helper function with UPSERT to avoid duplicates
        await send_df_to_sql(df, table_name, if_exists='upsert', unique_key='record_id')
        
        print(f"✓ Successfully saved {len(df)} records to SQL table '{table_name}'")
        
    except Exception as e:
        print(f"Error saving to SQL: {e}")
        raise


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
    
    # Handle date range options  
    if args.historical:
        # For historical backfill, start from 2014 when NYT crosswords went digital
        start_date = datetime(2014, 1, 1)
        print(f"Historical mode: fetching all data since {start_date.strftime(DATE_FORMAT)}")
    elif args.date_range:
        # Use custom date range
        start_date = datetime.strptime(args.start_date, DATE_FORMAT)
        print(f"Date range mode: {start_date.strftime(DATE_FORMAT)} to {args.end_date}")
    else:
        # Default: Incremental mode - check if any users have existing data
        print("Incremental mode (default): checking for existing data...")
        
        # Check if any users have previous commits
        any_existing_data = False
        for user in users:
            last_commit = await get_player_last_commit(user['player_name'])
            if last_commit:
                any_existing_data = True
                break
        
        if any_existing_data:
            # Some users have data, use 365-day window to catch any old modifications
            start_date = datetime.now() - timedelta(days=365)
            print(f"Found existing data - scanning last 365 days for modifications")
        else:
            # No previous data found, do full historical backfill
            start_date = datetime(2014, 1, 1)
            print(f"No existing data found - doing full historical backfill from {start_date.strftime(DATE_FORMAT)}")
    
    end_date = datetime.strptime(args.end_date, DATE_FORMAT)
    
    # Determine which puzzle types to fetch
    if args.type == "all":
        puzzle_types_to_fetch = ["daily", "mini", "bonus"]
        print("Fetching ALL puzzle types: daily, mini, and bonus")
    else:
        puzzle_types_to_fetch = [args.type]
        print(f"Fetching {args.type} puzzles only")
    
    # Track progress
    total_records = 0
    completed_tasks = []
    failed_tasks = []
    
    # Process each puzzle type and user combination
    for puzzle_type in puzzle_types_to_fetch:
        print(f"\n{'='*50}")
        print(f"PROCESSING {puzzle_type.upper()} PUZZLES")
        print(f"{'='*50}")
        
        for user in users:
            task_name = f"{user['player_name']} - {puzzle_type}"
            
            try:
                print(f"\n[{task_name}] Starting...")
                
                # Process user data
                puzzles_data = await process_user_data(user, start_date, end_date, puzzle_type, args.date_range)
                
                if puzzles_data:
                    # Save CSV backup if requested
                    if args.csv_backup:
                        save_csv_backup(puzzles_data, user['player_name'], puzzle_type)
                    
                    # Save to SQL immediately
                    print(f"[{task_name}] Saving {len(puzzles_data)} records to SQL...")
                    await save_to_sql(puzzles_data)
                    
                    total_records += len(puzzles_data)
                    completed_tasks.append(f"{task_name}: {len(puzzles_data)} records")
                    print(f"✓ [{task_name}] Complete - {len(puzzles_data)} records saved")
                else:
                    completed_tasks.append(f"{task_name}: 0 records (no new data)")
                    print(f"✓ [{task_name}] Complete - no new data to save")
                    
            except Exception as e:
                error_msg = f"{task_name}: {str(e)}"
                failed_tasks.append(error_msg)
                print(f"✗ [{task_name}] FAILED: {e}")
                print(f"   Continuing with other users...")
    
    # Show final summary
    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    print(f"{'='*60}")
    
    print(f"\n📊 SUMMARY:")
    print(f"  • Total records processed: {total_records}")
    print(f"  • Completed tasks: {len(completed_tasks)}")
    print(f"  • Failed tasks: {len(failed_tasks)}")
    
    if completed_tasks:
        print(f"\n✓ COMPLETED:")
        for task in completed_tasks:
            print(f"  • {task}")
    
    if failed_tasks:
        print(f"\n✗ FAILED:")
        for task in failed_tasks:
            print(f"  • {task}")
        print(f"\nNote: Failed tasks did not prevent other users from being processed.")
    
    # Show mode information
    mode_info = ""
    if args.historical:
        mode_info = " (historical backfill)"
    elif args.date_range:
        mode_info = " (date range mode)"
    else:
        mode_info = " (incremental mode - only modified puzzles)"
    
    backup_info = " with CSV backups" if args.csv_backup else ""
    
    print(f"\n🎯 RESULT: Processed {total_records} total records across {len(puzzle_types_to_fetch)} puzzle types for {len(users)} users{mode_info}{backup_info}.")


if __name__ == "__main__":
    asyncio.run(main()) 