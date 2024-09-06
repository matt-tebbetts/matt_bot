import os
import discord
import importlib
from bot.tasks import setup_tasks

# load cogs commands
async def load_cogs(client, tree):
    print("Loading cogs...")
    cog_directory = './bot/commands'
    cog_files = [f for f in os.listdir(cog_directory) if f.endswith('.py') and f != '__init__.py']
    
    for filename in cog_files:
        module_name = f'bot.commands.{filename[:-3]}'
        print(f"Importing module: {module_name}")
        module = importlib.import_module(module_name)
        if hasattr(module, 'setup'):
            print(f"Setting up module: {module_name}")
            await module.setup(client, tree)
        print(f"Loaded extension: {module_name}")

# Register event listeners
async def setup_events(client, tree):
    print("setup_events activated")

    # on ready
    @client.event
    async def on_ready():
        print("on_ready activated")

        # print confirmation
        print(f"Logged in as {client.user}")
        for guild in client.guilds:
            print(f"Connected to guild: {guild.name}")

        # load cogs
        try:
            print("loading cogs")
            await load_cogs(client, tree)
            print("cogs loaded")
        except Exception as e:
            print(f"Error loading cogs: {e}")

        # sync commands
        print("syncing commands")
        try:
            await tree.sync()
            print("Synced commands:")
            commands = await tree.fetch_commands()
            for command in commands:
                print(f"-- {command.name}: {command.description}")
        except Exception as e:
            print(f"Error syncing commands: {e}")

        # start background tasks
        print("starting background tasks")
        try:
            setup_tasks(client)
            print("background tasks started")
        except Exception as e:
            print(f"Error starting background tasks: {e}")

    # on message
    @client.event
    async def on_message(message):
        print("on_message activated")
        if message.author == client.user:
            return
        print(f"Message from {message.author}: {message.content}")
