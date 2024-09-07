import os
import discord
import importlib
from bot.connections.tasks import setup_tasks
from bot.functions import save_message_detail
from bot.functions import process_game_score

# load cogs commands
async def load_cogs(client, tree):
    print("events.py: loading cogs...")
    cog_directory = './bot/commands'
    cog_files = [f for f in os.listdir(cog_directory) if f.endswith('.py') and f != '__init__.py']
    
    for filename in cog_files:
        module_name = f'bot.commands.{filename[:-3]}'
        print(f"events.py: importing module: {module_name}")
        module = importlib.import_module(module_name)
        if hasattr(module, 'setup'):
            print(f"events.py: setting up module: {module_name}")
            await module.setup(client, tree)
        print(f"events.py: loaded extension: {module_name}")

# Register event listeners
async def setup_events(client, tree):
    print("events.py: setup_events activated")

    # on ready
    @client.event
    async def on_ready():
        
        # print confirmation
        for guild in client.guilds:
            print(f"events.py: {client.user} connected to {guild.name}")

        # load cogs
        try:
            await load_cogs(client, tree)
            print("events.py: loaded commands via load_cogs")
        except Exception as e:
            print(f"events.py: error in load_cogs: {e}")

        # sync commands
        try:
            await tree.sync()
            commands = ", ".join([cmd.name for cmd in await tree.fetch_commands()])
            print(f"events.py: synced these commands:", commands)
        except Exception as e:
            print(f"events.py: error syncing commands: {e}")

        # start background tasks
        try:
            setup_tasks(client)
            print("events.py: successfully ran setup_tasks")
        except Exception as e:
            print(f"events.py: error starting background tasks: {e}")

    # on message
    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        print(f"events.py: message on channel {message.channel} from {message.author}")

        # save message
        try:
            save_message_detail(message)
        except Exception as e:
            print(f"events.py: error saving message detail: {e}")

        # save game scores
        try:
            await process_game_score(message)

            
        except Exception as e:
            print(f"events.py: error processing game score: {e}")