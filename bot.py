import os
from dotenv import load_dotenv
import asyncio
import discord
from discord import app_commands
from bot.connections.events import setup_events

# setup
intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# load env
load_dotenv()
token = os.getenv("MATT_BOT")
print(f"Token loaded: {token is not None}")

# main
async def main():
    print("Starting main function")

    # config
    await setup_events(client, tree)
    print("Events setup complete")

    # connect
    await client.start(token)
    print("Bot started")

# run the bot
asyncio.run(main())

