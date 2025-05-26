import argparse
import os
import json
from csv import DictWriter
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from tqdm import tqdm

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
    (("-t", "--type"), {"help": 'The type of puzzle data to fetch. Valid values are "daily", "bonus", and "mini" (defaults to daily)', "default": "daily"}),
    (("--config-file",), {"help": "Path to users config JSON file", "default": "files/config/users.json"}),
    (("--historical",), {"help": "Fetch all available historical data (overrides start-date)", "action": "store_true"}),
    (("--overwrite",), {"help": "Overwrite existing files (default: True)", "action": "store_true", "default": True})
]

# Add arguments to parser
for arg_names, arg_config in arguments:
    parser.add_argument(*arg_names, **arg_config)


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
    """Extract and compute all puzzle fields from API detail response with organized structure"""
    # Get nested sections
    calcs = detail.get("calcs", {})
    firsts = detail.get("firsts", {})
    
    # Create organized structure
    date_obj = datetime.strptime(print_date, DATE_FORMAT)
    puzzle_id = puzzle_data.get("puzzle_id", "unknown")
    
    organized_record = {
        # Unique identifier and key info
        "record_id": f"{player_name}_{print_date}_{puzzle_data.get('publish_type', 'unknown').lower()}",
        "player_name": player_name,
        "print_date": print_date,
        "puzzle_type": puzzle_data.get("publish_type", "unknown"),
        
        # Basic puzzle info (alphabetical)
        "puzzle_info": {
            "author": puzzle_data.get("author", None),
            "editor": puzzle_data.get("editor", None),
            "format_type": puzzle_data.get("format_type", None),
            "puzzle_id": puzzle_id,
            "title": puzzle_data.get("title", None),
            "version": puzzle_data.get("version", None)
        },
        
        # Date and timing context
        "date_info": {
            "day_of_week_integer": int(date_obj.strftime('%w')),
            "day_of_week_name": date_obj.strftime('%A'),
            "print_date": print_date
        },
        
        # Performance and completion metrics
        "performance": {
            "eligible": calcs.get("eligible", None),
            "percent_filled": puzzle_data.get("percent_filled", None),
            "percent_filled_detail": calcs.get("percentFilled", None),
            "solved": puzzle_data.get("solved", None),
            "solved_detail": calcs.get("solved", None),
            "solving_seconds": calcs.get("secondsSpentSolving", None),
            "star": puzzle_data.get("star", None)
        },
        
        # Timestamps (all timing data)
        "timestamps": {
            "detail_timestamp": detail.get("timestamp", None),
            "last_solve_timestamp": detail.get("lastSolve", None),
            "min_guess_time": detail.get("minGuessTime", None),
            "opened_timestamp": firsts.get("opened", None),
            "solved_timestamp": firsts.get("solved", None)
        },
        
        # Technical/system fields
        "technical": {
            "last_commit_id": detail.get("lastCommitID", None),
            "user_id": detail.get("userID", None)
        }
    }
    
    return organized_record


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

    # Convert puzzles to organized structure
    organized_puzzles = []
    for puzzle in tqdm(puzzle_overview, desc=f"{user['player_name']} - Puzzle details"):
        try:
            detail = get_v3_puzzle_detail(puzzle_id=puzzle["puzzle_id"], cookie=cookie)
            # Extract all fields using helper function with organized structure
            organized_record = extract_puzzle_fields(detail, user['player_name'], puzzle["print_date"], puzzle)
            organized_puzzles.append(organized_record)
            
        except Exception as e:
            print(f"Error processing puzzle {puzzle['puzzle_id']}: {e}")
            # Set defaults for error cases using helper function
            default_record = extract_puzzle_fields({}, user['player_name'], puzzle["print_date"], puzzle)
            organized_puzzles.append(default_record)


    # Add organized puzzles to the master collection (we only do JSON now)
    if master_data is not None:
        master_data['puzzles'].extend(organized_puzzles)
    
    print(f"{len(organized_puzzles)} records processed for {user['player_name']}")
    return len(organized_puzzles)


def save_master_json(master_data, output_dir, puzzle_types_processed):
    """Save the consolidated master JSON file with smart merging"""
    os.makedirs(output_dir, exist_ok=True)
    
    master_file = os.path.join(output_dir, "nyt_crossword_data.json")
    current_time = datetime.now().isoformat()
    
    # Load existing master data if it exists
    existing_puzzles = []
    existing_metadata = {}
    if os.path.exists(master_file):
        print(f"Loading existing master JSON for merge: {master_file}")
        try:
            with open(master_file, "r") as f:
                existing_data = json.load(f)
                existing_puzzles = existing_data.get("puzzles", [])
                existing_metadata = existing_data.get("metadata", {})
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load existing master JSON ({e}), creating new file")
            existing_puzzles = []
            existing_metadata = {}
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
    
    # Convert back to list, sorted by player_name, then puzzle_type, then date
    final_puzzles = sorted(merged_puzzles.values(), 
                          key=lambda x: (x.get('player_name', ''), x.get('puzzle_type', ''), x.get('print_date', '')))
    
    print(f"Master merge stats: {new_count} new puzzles, {updated_count} updated puzzles, {len(final_puzzles)} total")
    
    # Get stats using helper function
    player_stats, puzzle_type_stats = get_stats_summary(final_puzzles)
    
    # Create comprehensive master JSON structure
    json_data = {
        "metadata": {
            "description": "NYT Crossword data for all players and puzzle types",
            "total_puzzles": len(final_puzzles),
            "players": list(player_stats.keys()),
            "puzzle_types": list(puzzle_type_stats.keys()),
            "stats_by_player": player_stats,
            "stats_by_puzzle_type": puzzle_type_stats,
            "last_run_stats": {
                "new_puzzles": new_count,
                "updated_puzzles": updated_count,
                "puzzle_types_processed": puzzle_types_processed,
                "generated_at": current_time
            },
            "created_at": existing_metadata.get("created_at", current_time),
            "last_updated": current_time,
            "data_structure": {
                "record_id": "Unique identifier: {player_name}_{print_date}_{puzzle_type}",
                "player_name": "Player identifier",
                "print_date": "Puzzle publication date (YYYY-MM-DD)",
                "puzzle_type": "Type of puzzle (daily, mini, bonus)",
                "puzzle_info": "Basic puzzle metadata (author, editor, title, etc.)",
                "date_info": "Date context (day of week info)",
                "performance": "Solving metrics (time, completion, stars)",
                "timestamps": "All timing data",
                "technical": "System/API technical fields"
            }
        },
        "puzzles": final_puzzles
    }
    
    with open(master_file, "w") as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Master JSON saved: {master_file}")
    return master_file


if __name__ == "__main__":
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
    
    # Only JSON output now - collect all data first then save master file
    master_data = {"puzzles": []}
    puzzle_types_processed = [args.type]
    
    for user in users:
        try:
            records = process_user_data(user, start_date, end_date, args.type, args.output_dir, master_data)
            total_records += records
        except Exception as e:
            print(f"Error processing user {user['player_name']}: {e}")
    
    # Save the master JSON file
    if master_data["puzzles"]:
        master_file = save_master_json(master_data, args.output_dir, puzzle_types_processed)
        print(f"\nMaster JSON created: {master_file}")
    else:
        print("\nNo puzzle data found to save.")
    
    print(f"\nComplete! Processed {total_records} total records for {len(users)} users.") 