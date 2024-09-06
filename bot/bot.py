import os
import discord
from discord import app_commands
import asyncio
from bot.connections.events import setup_events

# setup
intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
token = os.getenv("MATT_BOT")

# main
async def main():

    # config
    await setup_events(client, tree)

    # connect
    await client.start(token)

# run the bot
asyncio.run(main())
