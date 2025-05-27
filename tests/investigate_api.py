#!/usr/bin/env python3

import json
import sys
import requests
from datetime import datetime, timedelta

# Add the bot functions to path
sys.path.append('bot/functions')
from save_nyt import get_v3_puzzle_overview, get_v3_puzzle_detail, load_users_config

def examine_api_response():
    """Capture and examine raw API responses to find checks/reveals data"""
    
    # Load user config
    users = load_users_config('files/config/users.json')
    if not users:
        print("No users found!")
        return
    
    user = users[0]  # Use first user
    cookie = user['nyt_s_cookie']
    
    # Get recent puzzles
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)
    
    print(f"Examining NYT API responses for puzzle data...")
    print(f"User: {user['player_name']}")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Get puzzle overview
    print("\n1. Getting puzzle overview...")
    overview = get_v3_puzzle_overview("daily", start_date, end_date, cookie)
    
    if not overview:
        print("No puzzles found!")
        return
    
    # Get detail for first puzzle
    puzzle = overview[0]
    puzzle_id = puzzle['puzzle_id']
    print(f"\n2. Getting detailed data for puzzle {puzzle_id}...")
    
    detail = get_v3_puzzle_detail(puzzle_id, cookie)
    
    # Save raw response to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"raw_nyt_response_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(detail, f, indent=2)
    
    print(f"✓ Raw API response saved to: {filename}")
    
    # Examine structure
    print(f"\n3. Examining structure...")
    print(f"Top-level keys: {list(detail.keys())}")
    
    if 'calcs' in detail:
        print(f"calcs keys: {list(detail['calcs'].keys())}")
    
    if 'board' in detail:
        board = detail['board']
        print(f"board keys: {list(board.keys())}")
        
        if 'cells' in board:
            cells = board['cells']
            print(f"Total cells: {len(cells)}")
            
            # Look for different cell types
            cell_types = {}
            for i, cell in enumerate(cells):
                if isinstance(cell, dict):
                    keys = tuple(sorted(cell.keys()))
                    if keys not in cell_types:
                        cell_types[keys] = []
                    cell_types[keys].append(i)
            
            print(f"\nDifferent cell structures found:")
            for keys, indices in cell_types.items():
                print(f"  {keys}: {len(indices)} cells")
                # Show first example
                example_idx = indices[0]
                print(f"    Example (cell {example_idx}): {cells[example_idx]}")
    
    # Look for any field that might contain check/reveal counts
    print(f"\n4. Searching for potential checks/reveals fields...")
    def search_for_keywords(obj, path=""):
        findings = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if any(keyword in key.lower() for keyword in ['check', 'reveal', 'hint', 'cheat']):
                    findings.append(f"  {current_path}: {value}")
                findings.extend(search_for_keywords(value, current_path))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                findings.extend(search_for_keywords(item, f"{path}[{i}]"))
        return findings
    
    findings = search_for_keywords(detail)
    if findings:
        print("Found potential check/reveal related fields:")
        for finding in findings:
            print(finding)
    else:
        print("No obvious check/reveal fields found in this puzzle")
        print("This might be a puzzle where no checks/reveals were used")
    
    print(f"\n💡 Next steps:")
    print(f"1. Look at the saved file: {filename}")
    print(f"2. Try to find a puzzle where you know checks/reveals were used")
    print(f"3. Compare the structures to see what differs")

if __name__ == "__main__":
    examine_api_response() 