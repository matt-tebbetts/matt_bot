import os
import re
import json
import pandas as pd
from datetime import datetime
import pytz
from bot.functions import send_df_to_sql
from typing import Tuple
from bot.functions.admin import direct_path_finder
from bot.functions.save_messages import is_game_score

async def process_game_score(message, game_name=None, game_info=None):
    """Process and save a game score if the message contains one."""
    # If game info wasn't provided, check if it's a game score
    if game_name is None or game_info is None:
        is_score, game_name, game_info = is_game_score(message.content)
        if not is_score:
            return None
            
    # send for processing
    try:
        score_info = get_score_info(message.content, game_name, game_info)
    except Exception as e:
        return None

    # get basic info
    basic_info = {
        'added_ts': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'game_date': message.created_at.astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d"),
        'game_name': game_name,
        'user_name': message.author.name
    }

    # combine basic info and score info
    game_score_to_add = {**basic_info, **score_info}

    # prepare for database
    game_score_to_add.setdefault('game_bonuses', None)
    game_score_to_add['source_desc'] = 'discord'
    
    columns_order = [
        'added_ts', 'user_name', 'game_name', 'game_score',
        'game_date', 'game_detail', 'game_bonuses', 'source_desc'
    ]

    # Reorder the dictionary
    ordered_game_score = {col: game_score_to_add[col] for col in columns_order}

    # Create DataFrame with specified column order
    df = pd.DataFrame([ordered_game_score])

    try:
        await send_df_to_sql(df, 'games.game_history', if_exists='append')
    except Exception as e:
        print(f"save_scores.py: error sending score to sql: {e}")

    # send back for further processing
    return ordered_game_score

def get_score_info(message, game_name, game_info):
    game_processors = {
        "connections": process_connections,
        "crosswordle": process_crosswordle,
        "boxoffice": process_boxoffice,
        "travle": process_travle,
        "worldle": process_worldle,
        "wordle": process_wordle,
        "octordle": process_octordle,
        "octordle_rescue": process_octordle,
        "octordle_sequence": process_octordle,
        "timeguessr": process_timeguessr,
        "factle": process_factle,
        "factle_sports": process_factle,
        "actorle": process_actorle
    }

    # Check if the game has a specific processor
    if game_name in game_processors:
        try:
            return game_processors[game_name](message)
        except Exception as e:
            raise

def process_connections(message):
    # analyze line squares
    lines = message.strip().split("\n")
    
    # Count guesses and completed lines
    guesses_taken = len([line for line in lines if any(emoji in line for emoji in ["🟨", "🟩", "🟦", "🟪"])])
    completed_lines = 0
    for line in lines[1:]:
        if len(set(line)) == 1 and line.strip() != "":
            completed_lines += 1

    # calculate score and bonuses (true/false if they got the bonus)
    score = f"{guesses_taken}/7" if completed_lines == 4 else "X/7"
    
    # get bonuses
    got_rainbow_first = len(set(lines[2])) == 4
    got_purple_first = lines[2].count("🟪") == 4
    got_lost = completed_lines < 4

    # make list of bonuses
    bonuses = []
    if got_rainbow_first:
        bonuses.append('rainbow_first')
    if got_purple_first:
        bonuses.append('purple_first')
    if got_lost:
        bonuses.append('lost')
    
    # Convert bonuses list to a comma-separated string (consistent with other games)
    bonuses_str = ', '.join(bonuses) if bonuses else None
    
    # get game detail
    game_detail = lines[1].strip()

    # return dictionary of all info
    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonuses_str
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
    bonus = "under_30" if total_seconds < 30 else None

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
    if movies_guessed > 0:
        bonus = f'guessed_{movies_guessed}'
    
    # return dictionary
    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonus
    }
    return score_info

def process_travle(message):
    lines = message.split('\n')
    full_line = lines[0] if lines else None
    score = None
    game_detail = None
    
    if full_line:
        # Extract just the game identifier (e.g., "#travle #892")
        game_match = re.search(r'#travle #\d+', full_line)
        if game_match:
            game_detail = game_match.group(0)
        
        # Check for loss pattern "(X away)"
        away_match = re.search(r'\((\d+) away\)', full_line)
        if away_match:
            # It's a loss - use X to indicate failure (like other games)
            score = "X"
        else:
            # Regular win/attempt - extract score like "+2" or "+0"
            score_match = re.search(r'\+(\d+)', full_line)
            if score_match:
                score = f"+{score_match.group(1)}"

    # Check for bonuses
    bonuses = []
    if "Perfect" in full_line:
        bonuses.append("perfect")
    if "hint" in full_line:
        bonuses.append("hint")
    # Check for loss: either "(X away)" pattern or red squares in message
    if "(away)" in full_line or "🟥" in message:
        bonuses.append("lost")

    # Convert bonuses list to a comma-separated string
    bonuses_str = ', '.join(bonuses) if bonuses else None

    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonuses_str
    }
    return score_info

def process_octordle(message):
    score = int(message.split('\n')[-1].split(' ')[1])
    game_detail = message.split('\n')[0]
    
    # Calculate bonuses based on game type
    wordles_failed = message.count('🟥')
    wordles_guessed = 8 - wordles_failed
    bonuses_list = []
    
    # bonus check
    if wordles_failed > 0:
        bonuses_list.append("failed_any")

    if "Rescue" in game_detail and score == 9:
        bonuses_list.append("bonus_9")

    if "Rescue" not in game_detail and score <= 52:
        bonuses_list.append("under_52")

    # convert to string
    bonuses = ', '.join(bonuses_list) if bonuses_list else None

    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonuses
    }
    return score_info

def process_worldle(message):
    
    pattern = re.compile(r'(\d{1,2}|\?|X)/\d{1,2}')
    match = pattern.search(message)
    score = None
    bonus = None
    if match:
        score = match.group(0)
        if score.startswith('1/'):
            bonus = 'first_guess'

    # Extract game detail
    detail_pattern = re.compile(r'#Worldle #\d+')
    detail_match = detail_pattern.search(message)
    game_detail = detail_match.group(0) if detail_match else None

    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonus
    }
    return score_info

def process_timeguessr(message):
    lines = message.split('\n')
    game_detail = None
    score = None
    bonus = None

    if lines:
        # Extract game detail
        parts = lines[0].split()
        if len(parts) >= 2:
            game_detail = ' '.join(parts[:2])

        # Extract score
        score_match = re.search(r'(\d{1,3}(?:,\d{3})*)/\d{1,3}(?:,\d{3})*', lines[0])
        if score_match:
            score = score_match.group(1).replace(',', '')
            bonus = 'over_40k' if int(score) > 40000 else None

    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonus
    }
    return score_info

def process_factle(message):
    lines = message.split('\n')
    game_detail = lines[1] if len(lines) > 1 else None
    score = None
    bonus = None

    if len(lines) > 3:
        guesses_taken = len(lines) - 3
        emoji_line = lines[-2].strip()
        if emoji_line == "🐸" * 5:
            score = f"{guesses_taken}/5"
            print(f"Score: {score}")
            if guesses_taken == 1:
                bonus = "perfect"
            elif guesses_taken == 2:
                bonus = "impressive"
        else:
            score = "X/5"
            bonus = "lost"

    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonus
    }
    return score_info

def process_actorle(message):
    # Extract game detail (e.g., "Actorle #1164")
    game_detail = message.split('\n')[0].strip()
    
    # Extract score (e.g., "2/6")
    score_match = re.search(r'(\d+|\?|X)/\d+', message)
    score = score_match.group(0) if score_match else None
    
    # Calculate bonuses
    bonus = None
    if score:
        if score.startswith('1/'):
            bonus = 'single_guess'
        elif score.startswith('2/') or score.startswith('3/'):
            bonus = 'under_3'
    
    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': bonus
    }
    return score_info

def process_wordle(message):
    lines = message.split('\n')
    game_detail = lines[0] if lines else None  # e.g., "Wordle 1,234 3/6"
    
    # Extract score (e.g., "3/6" or "X/6")
    score_match = re.search(r'(\d+|X)/6', message)
    score = score_match.group(0) if score_match else None
    
    score_info = {
        'game_score': score,
        'game_detail': game_detail,
        'game_bonuses': None
    }
    return score_info
