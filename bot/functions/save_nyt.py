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
from sql_helper import send_df_to_sql

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
    (("-s", "--start-date"), {"help": "The first date to pull from, inclusive (defaults to 2 days ago)", "default": datetime.strftime(datetime.now() - timedelta(days=2), DATE_FORMAT)}),
    (("-e", "--end-date"), {"help": "The last date to pull from, inclusive (defaults to today)", "default": datetime.strftime(datetime.now(), DATE_FORMAT)}),
    (("-o", "--output-dir"), {"help": "The directory to write output files to", "default": "files/nyt_stats"}),
    (("-t", "--type"), {"help": 'The type of puzzle data to fetch. Valid values are "daily", "bonus", "mini", or "all" (defaults to all)', "default": "all"}),
    (("--config-file",), {"help": "Path to users config JSON file", "default": "files/config/users.json"}),
    (("--historical",), {"help": "Fetch all available historical data (overrides start-date)", "action": "store_true"}),
    (("--sql",), {"help": "Save data to SQL database", "action": "store_true"}),
    (("--json-only",), {"help": "Save JSON only (skip SQL)", "action": "store_true"})
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
        
        # System tracking
        "last_updated": datetime.now().isoformat(),
        "added_ts": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return essential_record


def get_stats_summary(puzzles_list):
    """Generate statistics summary from a list of puzzles"""
    player_stats = {}
    puzzle_type_stats = {}
    
    for puzzle in puzzles_list:
        player = puzzle.get('player_name', 'Unknown')
        ptype = puzzle.get('puzzle_type', 'Unknown')
        
        player_stats[player] = player_stats.get(player, 0) + 1
        puzzle_type_stats[ptype] = puzzle_type_stats.get(ptype, 0) + 1
    
    return player_stats, puzzle_type_stats


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


def process_user_data(user, start_date, end_date, puzzle_type, output_dir, master_data=None):
    """Process NYT crossword data for a single user"""
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

    print(f"\nGetting puzzle solve times for {user['player_name']}\n")

    # Convert puzzles to streamlined structure
    essential_puzzles = []
    for puzzle in tqdm(puzzle_overview, desc=f"{user['player_name']} - Puzzle details"):
        try:
            detail = get_v3_puzzle_detail(puzzle_id=puzzle["puzzle_id"], cookie=cookie)
            # Extract essential fields only
            essential_record = extract_puzzle_fields(detail, user['player_name'], puzzle["print_date"], puzzle)
            essential_puzzles.append(essential_record)
            
        except Exception as e:
            print(f"Error processing puzzle {puzzle['puzzle_id']}: {e}")
            # Set defaults for error cases using helper function
            default_record = extract_puzzle_fields({}, user['player_name'], puzzle["print_date"], puzzle)
            essential_puzzles.append(default_record)

    # Add essential puzzles to the master collection
    if master_data is not None:
        master_data['puzzles'].extend(essential_puzzles)
    
    print(f"{len(essential_puzzles)} records processed for {user['player_name']}")
    return len(essential_puzzles)


def save_master_json(master_data, output_dir, puzzle_types_processed):
    """Save the consolidated master JSON file with smart merging"""
    os.makedirs(output_dir, exist_ok=True)
    
    master_file = os.path.join(output_dir, "nyt_crossword_data.json")
    current_time = datetime.now().isoformat()
    
    # Load existing master data if it exists
    existing_puzzles = []
    if os.path.exists(master_file):
        print(f"Loading existing master JSON for merge: {master_file}")
        try:
            with open(master_file, "r") as f:
                existing_data = json.load(f)
                # Handle both old format (with metadata) and new format (just array)
                if isinstance(existing_data, dict) and "puzzles" in existing_data:
                    existing_puzzles = existing_data["puzzles"]
                elif isinstance(existing_data, list):
                    existing_puzzles = existing_data
                else:
                    existing_puzzles = []
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load existing master JSON ({e}), creating new file")
            existing_puzzles = []
    else:
        print(f"Creating new master JSON: {master_file}")
    
    # Merge logic: use the record_id as the unique key
    merged_puzzles = {}
    
    # Add existing puzzles to dict
    for puzzle in existing_puzzles:
        key = puzzle.get('record_id', f"unknown_{puzzle.get('print_date', '')}")
        merged_puzzles[key] = puzzle
    
    # Add/overwrite with new puzzles (newer data wins)
    new_count = 0
    updated_count = 0
    for puzzle in master_data['puzzles']:
        key = puzzle.get('record_id', f"unknown_{puzzle.get('print_date', '')}")
        if key in merged_puzzles:
            updated_count += 1
        else:
            new_count += 1
        # Always use new data (it's more recent)
        puzzle['last_updated'] = current_time
        merged_puzzles[key] = puzzle
    
    # Convert back to list, sorted by date, puzzle_type, then player
    final_puzzles = sorted(merged_puzzles.values(), 
                          key=lambda x: (x.get('print_date', ''), x.get('puzzle_type', ''), x.get('player_name', '')))
    
    print(f"Master merge stats: {new_count} new puzzles, {updated_count} updated puzzles, {len(final_puzzles)} total")
    
    # Get stats using helper function
    player_stats, puzzle_type_stats = get_stats_summary(final_puzzles)
    
    # Create streamlined master JSON structure (no metadata)
    json_data = final_puzzles
    
    with open(master_file, "w") as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Master JSON saved: {master_file}")
    return master_file


async def save_to_sql(puzzles_data, table_name="nyt_history"):
    """Save puzzle data to SQL database using existing sql_helper patterns"""
    try:
        # Convert to DataFrame
        df = pd.DataFrame(puzzles_data)
        
        if df.empty:
            print("No puzzle data to save to SQL")
            return
            
        print(f"Preparing to save {len(df)} records to SQL table '{table_name}'")
        
        # Use existing sql_helper function
        await send_df_to_sql(df, table_name, if_exists='append')
        
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
    
    # Handle historical option
    if args.historical:
        # For historical backfill, start from 2014 when NYT crosswords went digital
        start_date = datetime(2014, 1, 1)
        print(f"Historical mode: fetching all data since {start_date.strftime(DATE_FORMAT)}")
    else:
        start_date = datetime.strptime(args.start_date, DATE_FORMAT)
    
    end_date = datetime.strptime(args.end_date, DATE_FORMAT)
    
    total_records = 0
    
    # Determine which puzzle types to fetch
    if args.type == "all":
        puzzle_types_to_fetch = ["daily", "mini", "bonus"]
        print("Fetching ALL puzzle types: daily, mini, and bonus")
    else:
        puzzle_types_to_fetch = [args.type]
        print(f"Fetching {args.type} puzzles only")
    
    # Collect all data first
    master_data = {"puzzles": []}
    puzzle_types_processed = []
    
    for puzzle_type in puzzle_types_to_fetch:
        print(f"\n{'='*50}")
        print(f"PROCESSING {puzzle_type.upper()} PUZZLES")
        print(f"{'='*50}")
        
        puzzle_types_processed.append(puzzle_type)
        
        for user in users:
            try:
                records = process_user_data(user, start_date, end_date, puzzle_type, args.output_dir, master_data)
                total_records += records
                print(f"  → {records} {puzzle_type} records for {user['player_name']}")
            except Exception as e:
                print(f"Error processing {puzzle_type} puzzles for user {user['player_name']}: {e}")
    
    # Save outputs
    if master_data["puzzles"]:
        # Always save JSON unless explicitly skipped
        if not args.sql or args.json_only:
            master_file = save_master_json(master_data, args.output_dir, puzzle_types_processed)
            print(f"\nMaster JSON created: {master_file}")
        
        # Save to SQL if requested
        if args.sql and not args.json_only:
            print(f"\nSaving {len(master_data['puzzles'])} records to SQL...")
            await save_to_sql(master_data['puzzles'])
        
    else:
        print("\nNo puzzle data found to save.")
    
    output_methods = []
    if not args.sql or args.json_only:
        output_methods.append("JSON")
    if args.sql and not args.json_only:
        output_methods.append("SQL")
    
    print(f"\nComplete! Processed {total_records} total records across {len(puzzle_types_processed)} puzzle types for {len(users)} users.")
    print(f"Output methods: {', '.join(output_methods) if output_methods else 'None'}")


if __name__ == "__main__":
    asyncio.run(main()) 