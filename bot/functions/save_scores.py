import panadas as pd
from datetime import datetime
import pytz
from bot.functions import send_df_to_sql

# add discord scores to database when people paste them to discord chat
async def add_score(game_name, game_date, discord_id, msg_txt):
    # get date and time
    now = datetime.now(pytz.timezone('US/Eastern'))
    added_ts = now.strftime("%Y-%m-%d %H:%M:%S")

    # set these up
    game_name = game_name
    game_score = None
    game_dtl = None
    metric_01 = None
    metric_02 = None # game completed yes/no
    metric_03 = None

    # find game_score from message details
    score_details = await extract_score(msg_txt, game_name)
    game_score = score_details.get('score')
    bonuses = score_details.get('bonuses')

    # game detail for certain games
    if game_name == 'boxoffice':
        game_dtl = msg_txt.strip().split("\n")[1] # movie date
        metric_01 = msg_txt.count("✅") # movies guessed
    elif game_name.lower() == 'connections':
        lines = msg_txt.strip().split("\n")
        metric_01 = 1 if lines[2].count("🟪") == 4 else 0

    # put into dataframe
    my_cols = ['game_date', 'game_name', 'game_score', 'added_ts', 'discord_id', 'game_dtl', 'metric_01', 'metric_02', 'metric_03']
    my_data = [[game_date, game_name, game_score, added_ts, discord_id, game_dtl, metric_01, metric_02, metric_03]]
    df = pd.DataFrame(data=my_data, columns=my_cols)

    # send to sql using new function
    await send_df_to_sql(df, 'game_history', if_exists='append')

    msg_back = f"Added Score: {game_date}, {game_name}, {discord_id}, {game_score}"
    bot_print(msg_back)

    return {'message': msg_back, 'bonuses': bonuses}

async def process_game_score(message, game_prefixes, game_prefix_dict, emoji_map, add_score):
    msg_text = str(message.content)
    
    for game_prefix in game_prefixes:
        if msg_text.lower().startswith(game_prefix.lower()):
            # Find game name from prefix
            game_name = next((key for key, value in game_prefix_dict.items() if value.lower() == game_prefix.lower()), None)
            if not game_name:
                return

            # Get message detail
            game_date = datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")

            # Get discord name
            author = message.author.name
            user_id = author[:-2] if author.endswith("#0") else author

            # Get score and bonuses (as dictionary)
            response = await add_score(game_name, game_date, user_id, msg_text)

            # React with proper emoji(s)
            emoji = emoji_map.get(game_prefix.lower(), '✅')
            await message.add_reaction(emoji)

            if response.get('bonuses', {}).get('rainbow_bonus'):
                await message.add_reaction('🌈')
            if response.get('bonuses', {}).get('purple_bonus'):
                await message.add_reaction('🟪')

            break