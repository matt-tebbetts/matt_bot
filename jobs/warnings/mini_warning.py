import asyncio
import smtplib
import json
import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import pytz
import random
from functions import send_df_to_sql
import pandas as pd

# Add the project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions.sql_helper import get_df_from_sql

# load environment variables
load_dotenv()
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

async def send_sms(name, number, carrier, message):

    # Determine user's full SMS carrier gateway email address
    with open('config/sms_carriers.json', 'r') as file:
        carrier_emails = json.load(file)
    carrier_gateway_template = carrier_emails[carrier]["sms_email"]
    recipient_email = f"{number}@{carrier_gateway_template.replace('number', number)}"
    print(f"Texting reminder to {name} ({recipient_email})...")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASS)
            response = server.sendmail(GMAIL_USER, recipient_email, message)
            
            if response == {}:
                print("Message handed off to SMTP server successfully.")
            else:
                print(f"Failed to deliver to some recipients: {response}")

    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

async def log_sms_sent(player_name, phone_nbr, carrier, message):
    # Prepare the data to be logged
    log_data = pd.DataFrame([{
        'player_name': player_name,
        'phone_nbr': phone_nbr,
        'carrier': carrier,
        'message': message,
        'sent_at': datetime.now(pytz.timezone('US/Eastern'))
    }])

    # Insert the log into the sms_reminders table
    await send_df_to_sql(log_data, 'sms_reminders', if_exists='append')

async def send_mini_warning():

    # find users who have not yet completed the mini
    df = await get_df_from_sql("SELECT * FROM matt.mini_not_completed")
    if df.empty:
        return print("No users to warn right now.")

    now = datetime.now(pytz.timezone('US/Eastern'))
    text_count = 0
    users_texted = []

    # send each user a text
    for index, row in df.iterrows():

        # create series of short mini reminder messages
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

        # pick random message
        chosen_phrase = random.choice(mini_reminder_phrases)

        name = row['player_name']
        number = row['phone_nbr']
        carrier = row['phone_carr_cd']
        message = f"Hey {name}, {chosen_phrase}"
        print(f"Sending text to {name}...")

        await send_sms(name, number, carrier, message)

        text_count += 1
        users_texted += [name]

        # Log the sent SMS in the sms_reminders table
        await log_sms_sent(name, number, carrier, message)

    print(f"Texted the following {text_count} user(s): {users_texted}")
    return

async def main():
    await send_mini_warning()

if __name__ == "__main__":
    asyncio.run(main())