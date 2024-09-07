import os
import json
import pandas as pd
from datetime import datetime
import pytz
from bot.functions import send_df_to_sql

async def process_game_score(message):
    
    # load games.json
    games_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'files', 'games.json'))
    with open(games_file_path, 'r') as file:
        games_data = json.load(file)

    # determine if this message is a game score
    for game_name, game_info in games_data.items():
        if "prefix" in game_info and message.startswith(game_info["prefix"]):
            
            # Process the game score
            return await parse_specific_game_score(message, game_name, game_info)
    
    # If we get here, it's not a game score
    return None

async def parse_specific_game_score(message, game_name, game_info):
    # Process the specific game score here
    scoring_type = game_info.get("scoring_type")
    bonuses = game_info.get("bonuses", {})
    
    # ... rest of your game processing logic ...

    # parse game_info to prepare for sql
    added_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    game_date = message.created_at.astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")
    user_id = message.author.id

    # determine all emojis to react with
    bonuses = game_info.get("bonuses", {})
    emojis_to_react_with = []
    for bonus_key, bonus_emoji in bonuses.items():
        if response.get('bonuses', {}).get(bonus_key):
            emojis_to_react_with += bonus_emoji
    return emojis_to_react_with

process_game_score()
