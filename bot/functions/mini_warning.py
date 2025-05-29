import discord
import pandas as pd
from bot.functions import execute_query
from bot.functions.admin import read_json, write_json
from bot.functions.admin import direct_path_finder

# find users who haven't completed the mini
async def find_users_to_warn():
    result = await execute_query("SELECT * FROM matt.mini_not_completed")
    df = pd.DataFrame(result)
    
    if df.empty:
        return []
    
    users_to_message = []
    for index, row in df.iterrows():
        users_to_message.append({
            'name': row['player_name'],
            'discord_id_nbr': row['discord_id_nbr']
        })
    return users_to_message

# check mini leaders
async def check_mini_leaders():
    # get latest global leaders - now checking global leaderboard instead of per-guild
    query = """
        select 
            player_name,
            game_time
        from matt.mini_view
        where game_date = (select max(game_date) from matt.mini_view)
        and game_rank = 1
        and guild_nm = 'Global'
    """
    result = await execute_query(query)
    
    # Convert result to DataFrame
    df = pd.DataFrame(result)
    
    # Check if we have any data
    if df.empty:
        print("No mini leaders found for today")
        return False

    # get current leaders (global list)
    new_leaders = sorted(df['player_name'].tolist())

    # get list of previous global leaders
    leader_filepath = direct_path_finder('files', 'config', 'global_mini_leaders.json')
    previous_leaders = read_json(leader_filepath)
    if previous_leaders is None:
        previous_leaders = []
    
    # check if new leaders are different
    if new_leaders != sorted(previous_leaders):
        write_json(leader_filepath, new_leaders)
        print(f"New mini leaders detected: {new_leaders} (was: {previous_leaders})")
        return True
    else:
        return False
