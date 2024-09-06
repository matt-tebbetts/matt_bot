import os
import discord
from discord import app_commands
import asyncio
from bot.commands import setup_commands
from bot.events import setup_events

# setup
intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
token = os.getenv("MATT_BOT")

# config
setup_commands(tree)
setup_events(client, tree)

# connect
client.run(token)
