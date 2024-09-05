import os
import discord
import asyncio
from bot.commands import setup_commands
from bot.events import setup_events
from bot.tasks import setup_tasks

# setup
client = discord.Client(intents=discord.Intents.all())
tree = discord.app_commands.CommandTree(client)
token = os.getenv("MATT_BOT")

# config
setup_events(client)
setup_commands(tree)
setup_tasks(client)

# connect
asyncio.run(client.start(token))
