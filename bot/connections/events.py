import os
import discord
import importlib
from pprint import pformat
import pandas as pd
import json
from collections import OrderedDict
from bot.connections.config import BOT_NAME, SYSTEM_NAME

# local imports
from bot.functions import save_message_detail
from bot.functions import process_game_score, is_game_score
from bot.connections.tasks import setup_tasks
from bot.connections.config import save_all_guild_configs
from bot.functions.message_history import initialize_message_history
from bot.functions.sql_helper import get_pool

# load cogs commands
async def load_cogs(client, tree):
    cog_directory = './bot/commands'
    cog_files = [f for f in os.listdir(cog_directory) if f.endswith('.py') and f != '__init__.py']
    
    for filename in cog_files:
        module_name = f'bot.commands.{filename[:-3]}'
        module = importlib.import_module(module_name)
        if hasattr(module, 'setup'):
            await module.setup(client, tree)
        print(f"✓ Loaded {module_name}")

# Register event listeners
async def setup_events(client, tree):

    # on ready
    @client.event
    async def on_ready():
        print("\n=== Bot Startup Sequence ===")
        print()
        print(f"✓ Running *{BOT_NAME}* on {SYSTEM_NAME}")

        # print guild connections
        for guild in client.guilds:
            print(f"✓ Connected to {guild.name}")
        
        # Save guild configs
        await save_all_guild_configs(client)
        print("✓ Saved guild configs")

        # Initialize message history
        try:
            await initialize_message_history(client, lookback_days=7)  # Only look back 7 days during testing
        except Exception as e:
            print(f"✗ Error initializing message history: {e}")

        # load cogs
        try:
            await load_cogs(client, tree)
        except Exception as e:
            print(f"✗ Error loading command modules: {e}")

        # sync commands
        try:
            # Sync globally
            await tree.sync(guild=None)
            
            # Also sync to each guild
            for guild in client.guilds:
                await tree.sync(guild=guild)
                print(f"✓ Synced commands to {guild.name}")

        except Exception as e:
            print(f"✗ Error syncing commands: {e}")

        # Establish SQL connection
        try:
            await get_pool()
        except Exception as e:
            print(f"✗ Error connecting to database: {e}")

        # start background tasks
        try:
            setup_tasks(client, tree)
            print(f"✓ Started background tasks")
        except Exception as e:
            print(f"✗ Error starting background tasks: {e}")

        print("\n=== Bot is ready! ===\n")

    # on message
    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        # Check if it's a game score first
        try:
            is_score, game_name, game_info = is_game_score(message.content)
        except Exception as e:
            print(f"events.py: error checking game score: {e}")
            is_score, game_name, game_info = False, None, None

        # log message
        try:
            channel_name = f"#{message.channel.name}" if isinstance(message.channel, discord.TextChannel) else "DM"
            first_line = message.content.split('\n')[0]
            message_preview = first_line[:16] + "..." if len(first_line) > 16 else first_line
            game_info_text = f" [{game_name}]" if is_score else ""
            print(f"User {message.author.name} posted in {channel_name}: {message_preview}{game_info_text}")
        except Exception as e:
            print(f"events.py: error logging message: {e}")

        # save message (with game score flag)
        try:
            save_message_detail(message)
        except Exception as e:
            print(f"events.py: error saving message detail: {e}")

        # process game score if it is one
        if not is_score:
            return

        try:
            score_result = await process_game_score(message, game_name, game_info)
            if not score_result:
                return

            # Load games configuration
            with open('files/games.json', 'r', encoding='utf-8') as f:
                games_config = json.load(f)
            game_config = games_config.get(score_result['game_name'], {})

            # Add reactions
            await message.add_reaction(game_config.get('emoji', '✅'))
            
            # Add bonus reactions if any
            if game_bonuses := score_result.get('game_bonuses'):
                for bonus in game_bonuses.split(', '):
                    if emoji := game_config.get('bonus_emojis', {}).get(bonus):
                        await message.add_reaction(emoji)
            
        except Exception as e:
            print(f"events.py: Error processing game score: {str(e)}")
