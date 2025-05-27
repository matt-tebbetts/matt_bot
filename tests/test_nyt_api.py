#!/usr/bin/env python3

import requests
import json
import sys
sys.path.append('bot/functions')
from save_nyt import load_users_config

API_ROOT = "http://www.nytimes.com/svc/crosswords"
PUZZLE_INFO = API_ROOT + "/v3/puzzles.json"

def test_api_requirements():
    """Test what parameters the NYT API actually requires"""
    
    # Load user config to get a cookie
    users = load_users_config('files/config/users.json')
    if not users:
        print("No users found!")
        return
    
    cookie = users[0]['nyt_s_cookie']
    
    print("Testing NYT API parameter requirements...")
    
    # Test 1: With date parameters (current method)
    print("\n1. Testing WITH date parameters:")
    payload_with_dates = {
        "publish_type": "daily",
        "sort_order": "asc",
        "sort_by": "print_date",
        "date_start": "2025-05-20",
        "date_end": "2025-05-26",
    }
    
    try:
        resp = requests.get(PUZZLE_INFO, params=payload_with_dates, cookies={"NYT-S": cookie})
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            puzzle_count = len(data.get("results", []))
            print(f"  Puzzles found: {puzzle_count}")
        else:
            print(f"  Error: {resp.text}")
    except Exception as e:
        print(f"  Exception: {e}")
    
    # Test 2: Without date parameters
    print("\n2. Testing WITHOUT date parameters:")
    payload_no_dates = {
        "publish_type": "daily",
        "sort_order": "asc",
        "sort_by": "print_date",
    }
    
    try:
        resp = requests.get(PUZZLE_INFO, params=payload_no_dates, cookies={"NYT-S": cookie})
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            puzzle_count = len(data.get("results", []))
            print(f"  Puzzles found: {puzzle_count}")
            if puzzle_count > 0:
                print("  SUCCESS: API works without date parameters!")
                # Show date range of results
                results = data.get("results", [])
                dates = [p.get("print_date") for p in results if p.get("print_date")]
                if dates:
                    print(f"  Date range: {min(dates)} to {max(dates)}")
        else:
            print(f"  Error: {resp.text}")
    except Exception as e:
        print(f"  Exception: {e}")
    
    # Test 3: Minimal parameters
    print("\n3. Testing with MINIMAL parameters:")
    payload_minimal = {
        "publish_type": "daily",
    }
    
    try:
        resp = requests.get(PUZZLE_INFO, params=payload_minimal, cookies={"NYT-S": cookie})
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            puzzle_count = len(data.get("results", []))
            print(f"  Puzzles found: {puzzle_count}")
        else:
            print(f"  Error: {resp.text}")
    except Exception as e:
        print(f"  Exception: {e}")

if __name__ == "__main__":
    test_api_requirements() 