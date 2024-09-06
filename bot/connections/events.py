import os
import discord
import importlib
from bot.connections.tasks import setup_tasks

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
        print("events.py: on_ready activated")

            # print confirmation
        print(f"events.py: logged in as {client.user}")
        for guild in client.guilds:
            print(f"events.py: connected to guild: {guild.name}")

        # load cogs
        try:
            print("events.py: running load_cogs")
            await load_cogs(client, tree)
            print("events.py: successfully ran load_cogs")
        except Exception as e:
            print(f"events.py: error in load_cogs: {e}")

        # sync commands
        print("events.py: running tree.sync")
        try:
            await tree.sync()
            commands = ", ".join([cmd.name for cmd in await tree.fetch_commands()])
            print("events.py: synced these commands:", commands)
        except Exception as e:
            print(f"events.py: error syncing commands: {e}")

        # start background tasks
        print("events.py: running setup_tasks")
        try:
            setup_tasks(client)
            print("events.py: successfully ran setup_tasks")
        except Exception as e:
            print(f"events.py: error starting background tasks: {e}")

    # on message
    @client.event
    async def on_message(message):
        print("events.py: on_message activated")
        if message.author == client.user:
            return
        print(f"events.py: message from {message.author}: {message.content}")
