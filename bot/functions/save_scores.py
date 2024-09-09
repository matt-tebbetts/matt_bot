import os
import re
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

    # if it's a game score, parse it and add to database
    for game_name, game_info in games_data.items():
        if "prefix" in game_info and message.content.startswith(game_info["prefix"]):
            
            # send for processing
            game_name = game_info["game_name"].lower()
            score_info = get_score_info(message.content, game_name, game_info)
            basic_info = {
                'added_ts': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'game_date': message.created_at.astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d"),
                'game_name': game_name,
                'user_name': message.author.name
            }

            # combine basic info and score info
            game_score_to_add = {**basic_info, **score_info}

            # prepare for database
            df_copy = game_score_to_add.copy()
            df_copy['game_bonuses'] = json.dumps(df_copy['game_bonuses']) if df_copy['game_bonuses'] else None
            df_copy['source_desc'] = 'discord'
            columns_order = [
                'added_ts', 'user_name', 'game_name', 'game_score',
                'game_date', 'game_detail', 'game_bonuses', 'source_desc'
            ]

            # Create DataFrame with specified column order
            df = pd.DataFrame([df_copy], columns=columns_order)

            try:
                await send_df_to_sql(df, 'games.game_history', if_exists='append')
            except Exception as e:
                print(f"save_scores.py: error sending score to sql: {e}")

            # send back for further processing
            return game_score_to_add

    # else it's not a game score
    return None

def get_score_info(message, game_name, game_info):
    game_processors = {
        "connections": process_connections,
        "crosswordle": process_crosswordle,
        "boxoffice": process_boxoffice,
        "travle": process_travle,
        "worldle": process_worldle,
        "octordle": process_octordle,
        "octordle_rescue": process_octordle,
        "octordle_sequence": process_octordle
    }

    # Check if the game has a specific processor
    if game_name in game_processors:
        return game_processors[game_name](message)

    # Default processing based on scoring type
    if game_info["scoring_type"] == "guesses":
        pattern = re.compile(r'(\d{1,2}|\?|X)/\d{1,2}')
    elif game_info["scoring_type"] == "points":
        pattern = re.compile(r'(\d{1,3}(?:,\d{3})*)(?=/)')
    elif game_info["scoring_type"] == "timed":
        pattern = re.compile(r'\d{1,2}:\d{2}')
    else:
        pattern = None

    # get score
    score = None
    if pattern:
        match = pattern.search(message)
        if match:
            score = match.group(0)

    score_info = {
        'game_score': score,
        'game_detail': None,
        'game_bonuses': None
    }
    return score_info

def process_connections(message):
    
    # analyze line squares
        lines = message.strip().split("\n")
        guesses_taken = len([line for line in lines if any(emoji in line for emoji in ["🟨", "🟩", "🟦", "🟪"])])
        completed_lines = 0
        for line in lines[1:]:
            if len(set(line)) == 1 and line.strip() != "":
                completed_lines += 1

        # calculate score and bonuses (true/false if they got the bonus)
        score = f"{guesses_taken}/7" if completed_lines == 4 else "X/7"
        got_rainbow_first = len(set(lines[2])) == 4
        got_purple_second = lines[3].count("🟪") == 4
        bonuses = {'rainbow_first': got_rainbow_first, 'purple_second': got_purple_second}
        game_detail = lines[1].strip()

        # return dictionary of all info
        score_info = {
            'game_score': score,
            'game_detail': game_detail,
            'game_bonuses': bonuses
        }
        return score_info

def process_crosswordle(message):

    game_detail = ' '.join(message.split()[:3]).rstrip(':')  # "Daily Crosswordle 961"
    match = re.search(r"(\d+)m\s*(\d+)s|(\d+)s", message)
    if match:
        if match.group(3):  # Seconds only
            minutes, seconds = 0, int(match.group(3))
        else:  # Minutes and seconds
            minutes, seconds = int(match.group(1)), int(match.group(2))
        score = f"{minutes}:{str(seconds).zfill(2)}"
        total_seconds = minutes * 60 + seconds
    
    # if under 30 seconds, give bonus
    bonus = {"under_30": True} if total_seconds < 30 else {}
    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonus
    }
    return score_info

def process_boxoffice(message):
    pattern = re.compile(r'🏆\s*(\d+)')
    match = pattern.search(message)
    score = match.group(1) if match else None
    game_detail = message.strip().split("\n")[1] # movie date

    # calculate bonuses
    movies_guessed = message.count("✅")
    bonuses = {}
    if movies_guessed > 0:
        bonuses[f'guessed_{movies_guessed}'] = True
    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonuses
    }
    return score_info

def process_travle(message):
    parts = message.split()
    score = parts[2] if len(parts) > 2 else None
    game_detail = parts[1] if len(parts) > 1 else None
    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': None
    }
    return score_info

def process_octordle(message):
    score = int(message.split('\n')[-1].split(' ')[1])
    game_detail = message.split('\n')[0]
    
    # Calculate bonuses based on game type
    wordles_failed = message.count('🟥')
    wordles_guessed = 8 - wordles_failed
    bonuses = {}
    if "Rescue" in game_detail:
        if wordles_guessed < 8:
            bonuses[f"under_8"] = True
        if wordles_guessed == 8:
            bonuses[f"saved_8"] = True
        if score == 9:
            bonuses[f"bonus_9"] = True
    else:
        # Find the highest number of words guessed
        for i in range(8, 0, -1):  # Check from 8 down to 1
            if str(i) in message or f"{i}️" in message:
                bonuses[f"guessed_{i}"] = True
                break  # Exit the loop after finding the highest number
        if score <= 52:
            bonuses["under_52"] = True

    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonuses
    }
    return score_info

def process_worldle(message):
    pattern = re.compile(r'(\d{1,2}|\?|X)/\d{1,2}')
    match = pattern.search(message)
    if match:
        score = match.group(0)
        bonuses = {'first_guess': score.startswith('1/')}
    else:
        score = None
        bonuses = None

    # Extract game detail
    detail_pattern = re.compile(r'#Worldle #\d+')
    detail_match = detail_pattern.search(message)
    game_detail = detail_match.group(0) if detail_match else None

    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonuses
    }
    return score_info