import os
from dotenv import load_dotenv
import asyncio
import discord
from discord import app_commands
from bot.connections.events import setup_events
from bot.connections.config import BOT_TOKEN

# setup
intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# main
async def main():

    # config
    await setup_events(client, tree)

    # connect
    await client.start(BOT_TOKEN)
    print("Bot started")

# run the bot
asyncio.run(main())

