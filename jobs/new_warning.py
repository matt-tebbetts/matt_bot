import random
from datetime import datetime
import pytz
from functions import get_df_from_sql
import sys
import os

# Add the project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the send_dm function
from bot.connection import send_dm

async def send_mini_warning():
    df = await get_df_from_sql("SELECT * FROM matt.mini_not_completed")
    if df.empty:
        return print("No users to warn right now.")

    now = datetime.now(pytz.timezone('US/Eastern'))
    dm_count = 0
    users_messaged = []

    # Create series of short mini reminder messages
    """
    mini_reminder_phrases = [
        "it's Mini time. Don't forget.",
        "quick Mini break?",
        "done the Mini yet?",
        "the Mini is waiting for you!",
        "don't miss today's Mini!",
        "got a sec? Do the Mini?",
        "it's time for your Mini fix",
        "Mini challenge? Go for it!",
        "Mini done? If not, now's the time!",
        "there's still time to do today's Mini!",
        "you can still do the Mini today"
    ]
    """

    # Send each user a DM on Discord
    for index, row in df.iterrows():
        chosen_phrase = ['this is your reminder to complete the Mini!'] # random.choice(mini_reminder_phrases)

        # get user
        name = row['player_name']
        discord_user_id = row['discord_user_id']  # Assuming you have a Discord user ID stored

        # Construct the message
        message = f"Hey {name}, {chosen_phrase}"
        print(f"Sending DM to {name}...")

        # Send the DM via Discord
        await send_dm(discord_user_id, message)

        dm_count += 1
        users_messaged.append(name)

    print(f"Sent DM to the following {dm_count} user(s): {users_messaged}")
    return