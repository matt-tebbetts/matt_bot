import discord
from bot.functions import execute_query
from bot.functions.admin import read_json, write_json
from bot.functions.admin import direct_path_finder

# find users who haven't completed the mini
async def find_users_to_warn():
    df = await execute_query("SELECT * FROM matt.mini_not_completed")
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

    # get latest leaders
    query = """
        select 
            guild_nm,
            player_name,
            game_time
        from matt.mini_view
        where game_date = (select max(game_date) from matt.mini_view)
        and game_rank = 1
    """
    df = await execute_query(query)

    # get leaders by guild
    aggregated_df = df.groupby('guild_nm')['player_name'].apply(list).reset_index()
    new_leaders = aggregated_df.to_dict(orient='records')

    # loop through guilds and check for differences
    guild_differences = {}
    for guild in new_leaders:
        guild_name = guild['guild_nm']
        
        # skip global
        if guild_name == "Global":
            continue

        # get list of previous leaders
        leader_filepath = direct_path_finder('files', 'guilds', guild_name, 'leaders.json')
        previous_leaders = read_json(leader_filepath)

        # check if new leaders are different
        if set(guild['player_name']) != set(previous_leaders):
            write_json(leader_filepath, guild['player_name'])
            guild_differences[guild_name] = True
        else:
            guild_differences[guild_name] = False
    
    return guild_differences
