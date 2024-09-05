import os
import discord
import asyncio
from bot.events import setup_events

# bot setup
client = discord.Client(intents=discord.Intents.all())
tree = discord.app_commands.CommandTree(client)
token = os.getenv("MATT_BOT")

# event listeners setup
setup_events(client)

# connect to discord
asyncio.run(client.start(token))  # Directly start the bot
