#!/usr/bin/env python3

import requests
import sys
sys.path.append('bot/functions')
from save_nyt import load_users_config

def test_api_limits():
    users = load_users_config('files/config/users.json')
    cookie = users[0]['nyt_s_cookie']
    API_ROOT = 'http://www.nytimes.com/svc/crosswords'
    PUZZLE_INFO = API_ROOT + '/v3/puzzles.json'

    # Test different date ranges
    tests = [
        ('Last 30 days', '2025-04-26', '2025-05-26'),
        ('Last 60 days', '2025-03-27', '2025-05-26'), 
        ('Last 90 days', '2025-02-25', '2025-05-26'),
        ('Jan 1 to May 26', '2025-01-01', '2025-05-26'),
        ('All of 2024', '2024-01-01', '2024-12-31')
    ]

    for name, start, end in tests:
        payload = {
            'publish_type': 'daily',
            'sort_order': 'asc', 
            'sort_by': 'print_date',
            'date_start': start,
            'date_end': end
        }
        
        print(f"Testing {name} ({start} to {end})...")
        resp = requests.get(PUZZLE_INFO, params=payload, cookies={'NYT-S': cookie})
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', [])
            dates = [p.get('print_date') for p in results if p.get('print_date')]
            
            print(f'  Results: {len(results)} puzzles')
            if dates:
                print(f'  Actual range: {min(dates)} to {max(dates)}')
            print()
        else:
            print(f'  ERROR {resp.status_code}: {resp.text}')
            print()

if __name__ == "__main__":
    test_api_limits() 