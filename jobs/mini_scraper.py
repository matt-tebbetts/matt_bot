
## this should run on a completely separate process from the bot
## it should not be linked to Discord at all
## it should write the leaderboard to a file, and only write new records to sql

from jobs import send_df_to_sql

import pandas as pd
from datetime import datetime
import pytz
import json
import requests
from bs4 import BeautifulSoup
from bot_functions import get_mini_date, bot_print
from global_functions import get_current_time
import os
from config import NYT_COOKIE
import asyncio

current_mini_dt = get_mini_date().strftime("%Y-%m-%d")
import json
import re
import re
import json

NYT_COOKIE = os.getenv('NYT_COOKIE')

def scrape_mini_scores():
    leaderboard_url = 'https://www.nytimes.com/puzzles/leaderboards'
    response = requests.get(leaderboard_url, cookies={'NYT-S': NYT_COOKIE})
    if response.status_code != 200:
        print(f"Failed to fetch leaderboard. Status Code: {response.status_code}")
        return {}
    soup = BeautifulSoup(response.text, 'lxml')
    script_tag = soup.find('script', string=re.compile('window.data'))
    if script_tag:
        data_string = script_tag.string.split('=', 1)[1].strip()
        data = json.loads(data_string.rstrip(';'))
        scores = {entry['name']: entry['solveTime'] for entry in data.get('scoreList', []) if entry.get('solveTime')}
        return scores
    else:
        print("Script tag with data not found.")
    return {}

# save mini scores to file1
def save_new_scores_to_json(scores):

    # get today's mini path
    file_path = f"files/mini/{current_mini_dt}.json"

    # check if file exists, read existing data if it does
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            existing_scores = json.load(f)
    else:
        existing_scores = {}

    # initialize count of scores added
    new_scores_found = 0
    
    # add new scores (if any)
    for player, score in scores.items():
        if player not in existing_scores:
            added_ts = get_current_time()
            print(f"{added_ts}: New mini score of {score} from {player}!")
            existing_scores[player] = {
                "time": score,
                "added_ts": added_ts,
                "added_to_sql": False
                }
            new_scores_found += 1

    # print count of scores added
    if new_scores_found > 0:
        
        # create file if not exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # save updated scores to JSON
        with open(file_path, 'w') as f:
            json.dump(existing_scores, f, indent=4)

    return existing_scores

# save new scores to sql
async def save_new_scores_to_sql(existing_scores):

    # check for scores that haven't been added to SQL yet
    new_scores = {player: data for player, data in existing_scores.items() if not data['added_to_sql']}

    if len(new_scores) == 0:
        return

    else:
        # Prepare DataFrame for SQL
        df = pd.DataFrame(new_scores).transpose().reset_index()
        df.insert(0, 'game_date', current_mini_dt)
        df['added_ts'] = get_current_time()

        # set columns
        df.rename(columns={'index': 'player_id', 'name': 'player_id', 'time': 'game_time'}, inplace=True)
        df = df[['game_date', 'player_id', 'game_time', 'added_ts']]

        try:
            # Send to SQL
            await send_df_to_sql(df, 'mini_history')

            # If successful, mark these scores as added to SQL
            for player in new_scores.keys():
                bot_print(f"Successfully added score for: {player}")
                existing_scores[player]['added_to_sql'] = True

            # Save the updated scores back to JSON
            with open(f"files/mini/{current_mini_dt}.json", 'w') as f:
                json.dump(existing_scores, f, indent=4)

        except Exception as e:
            # Handle the exception (e.g., log it, send an alert, etc.)
            bot_print(f"An error occurred while sending data to SQL: {e}")
            # Do not update the JSON file if there was an error

# get mini
scores_raw = scrape_mini_scores()

# save new scores to file
scores_json = save_new_scores_to_json(scores_raw)

# save new scores to sql
asyncio.run(save_new_scores_to_sql(scores_json))
