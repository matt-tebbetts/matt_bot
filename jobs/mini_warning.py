from contextlib import asynccontextmanager
from sql_helper import get_df_from_sql
import asyncio
import smtplib
import json
import os

# load environment variables
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

 # gmail connection
@asynccontextmanager
async def smtp_server_connection():
    server = smtplib.SMTP("smtp.gmail.com", 587)
    try:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        yield server
    finally:
        server.quit()

async def send_sms(name, number, carrier, message):

    # determine user's full sms carrier gateway email address
    with open('files/config/sms_carriers.json', 'r') as file:
        carrier_emails = json.load(file)
    carrier_gateway_template = carrier_emails[carrier]["sms_email"]
    carrier_gateway = carrier_gateway_template.replace("number", number)
    recipient_email = f"{number}@{carrier_gateway}"
    print(f"Texting reminder to {name} ({recipient_email})...")

    try:
        async with smtp_server_connection() as server:
            server.sendmail(GMAIL_USER, recipient_email, message)
        print("Message sent successfully.")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

async def send_mini_warning():

    # find users who have not yet completed the mini
    df = await get_df_from_sql("SELECT * FROM matt.mini_not_completed")

    if df.empty:
        return print("No users found who have not completed the mini.")

    text_count = 0
    users_texted = []
    for index, row in df.iterrows():

        # if they want the text message, send it
        if row['wants_text'] == 1 and row['phone_nbr'] and row['phone_carr_cd']:

            # while testing, only send to Matt
            if row['player_name'] != "Matt":
                continue

            await send_sms(
                    name=row['player_name'],
                    number=row['phone_nbr'],
                    carrier=row['phone_carr_cd'],
                    message=f"Hey {row['player_name']}, there is still time to do the Mini today!"
                    )
            text_count += 1
            users_texted += [row['player_name']]
    
    print(f"Texted the following {text_count} users: {users_texted}")
    return

async def main():
    await send_mini_warning()

if __name__ == "__main__":
    asyncio.run(main())