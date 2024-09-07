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
        if "prefix" in game_info and message.startswith(game_info["prefix"]):
            game_name = game_info["name"]
            print(f"save_scores.py: this is a game score for: {game_name}")
            
            # send for processing
            result = get_score_info(message, game_name, game_info)

            # message the user, confirming the result
            msg = f"""
                Thanks {message.author.mention}!
                Your score has been saved for {game_name}.
                Here are the details:
                {result}
            """
            await message.channel.send(msg)

def get_score_info(message, game_name, game_info):

    # get score_info (score, bonuses, and game detail)
    if game_name == "connections":
        score_info = process_connections(message)
    elif game_name == 'crosswordle':
        score_info = process_crosswordle(message)
    elif game_name == 'boxoffice':
        score_info = process_boxoffice(message)
    elif game_name == 'travle':
        score_info = process_travle(message)
    elif game_name == 'octordle' or game_name == 'octordle_sequence' or game_name == 'octordle_rescue':
        score_info = process_octordle(message)
    else:
        if game_info["scoring_type"] == "guesses":
            pattern = re.compile(r'(\d{1,2}|\?|X)/\d{1,2}')
        elif game_info["scoring_type"] == "points":
            pattern = re.compile(r'(\d{1,3}(?:,\d{3})*)(?=/)') 
        elif game_info["scoring_type"] == "timed":
            pattern = re.compile(r'\d{1,2}:\d{2}')
        match = pattern.search(message)
        if match:           
            score = match.group(0)
        score_info = {
            'score': score,
            'game_detail': None
        }
    
        # get basic info
    
    # combine into final_info
    result = {
        'added_ts': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'game_date': message.created_at.astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d"),
        'user_id': message.author.id,
        'user_name': message.author.name,
        'game_name': game_name,
        'game_info': game_info,
        'score': score_info['score'],
        'game_detail': score_info['game_detail'],
        'bonuses': score_info['bonuses']
    }

    print(f"save_scores.py: result is {result}")
    return result  

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
        bonuses = {'rainbow': got_rainbow_first, 'purple': got_purple_second}
        game_detail = lines[1].strip()

        # return dictionary of all info
        score_info = {
            'score': score,
            'bonuses': bonuses,
            'game_detail': game_detail
        }
        return score_info

def process_crosswordle(message):

    parts = message.split()
    game_detail = ' '.join(parts[:3])  # "Daily Crosswordle 961"
    match = re.search(r"(\d+)m\s*(\d+)s|(\d+)s", message)
    if match:
        if match.group(3):  # Seconds only
            minutes, seconds = 0, int(match.group(3))
        else:  # Minutes and seconds
            minutes, seconds = int(match.group(1)), int(match.group(2))
        score = f"{minutes}:{str(seconds).zfill(2)}"
        total_seconds = minutes * 60 + seconds
    
    # if under 30 seconds, give bonus
    bonuses = {"under_30": True} if total_seconds < 30 else {}
    score_info = {
        'score': score,
        'game_detail': game_detail,
        'bonuses': bonuses
    }
    return score_info

def process_boxoffice(message):
    pattern = re.compile(r'🏆\s*(\d+)')
    match = pattern.search(message)
    score = match.group(1) if match else None
    game_detail = message.strip().split("\n")[1] # movie date

    # calculate bonuses
    guessed_1 = message.count("✅") == 1
    guessed_2 = message.count("✅") == 2
    guessed_3 = message.count("✅") == 3
    guessed_4 = message.count("✅") == 4
    guessed_5 = message.count("✅") == 5
    bonuses = {
        'guessed_1': guessed_1,
        'guessed_2': guessed_2,
        'guessed_3': guessed_3,
        'guessed_4': guessed_4,
        'guessed_5': guessed_5,
        'guessed_all': guessed_5
    }
    score_info = {
        'score': score,
        'bonuses': bonuses,
        'game_detail': game_detail,
    }
    return score_info

def process_travle(message):
    parts = message.split()
    score = parts[2] if len(parts) > 2 else None
    game_detail = parts[1] if len(parts) > 1 else None
    score_info = {
        'score': score,
        'game_detail': game_detail
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
        for i in range(1, 9):
            if str(i) in message or f"{i}️" in message:
                bonuses[f"guessed_{i}"] = True
        if score <= 52:
            bonuses["under_52"] = True

    score_info = {
        'score': score,
        'bonuses': bonuses,
        'game_detail': game_detail
    }
    return score_info
