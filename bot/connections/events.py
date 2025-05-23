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
from bot.functions import process_game_score
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

        # log message
        try:
            channel_name = f"#{message.channel.name}" if isinstance(message.channel, discord.TextChannel) else "DM"
            message_preview = message.content[:32] + "..." if len(message.content) > 32 else message.content
            print(f"User {message.author.name} posted in {channel_name}: {message_preview}")
        except Exception as e:
            print(f"events.py: error logging message: {e}")

        # save message
        try:
            save_message_detail(message)
        except Exception as e:
            print(f"events.py: error saving message detail: {e}")

        # save game scores
        try:
            is_score, game_name, game_info = is_game_score(message.content)
            print(f"Message from {message.author.name}: {'✓' if is_score else '✗'} Game score detection")
            if is_score:
                print(f"  Detected game: {game_name}")
            
            score_result = await process_game_score(message)
            if score_result:
                columns_order = [
                    'added_ts', 'user_name', 'game_name', 'game_score',
                    'game_date', 'game_detail', 'game_bonuses', 'source_desc'
                ]
                
                # Load games configuration
                with open('files/games.json', 'r', encoding='utf-8') as f:
                    games_config = json.load(f)
                game_config = games_config.get(score_result['game_name'], {})

                # React with confirmation emoji
                confirmation_emoji = game_config.get('emoji', '✅')  # Default to green checkmark
                await message.add_reaction(confirmation_emoji)

                # check for bonuses
                game_bonuses = score_result.get('game_bonuses')
                if game_bonuses:
                    bonus_emojis = game_config.get('bonus_emojis', {})
                    bonuses_list = game_bonuses.split(', ')
                    for bonus in bonuses_list:
                        if bonus in bonus_emojis:
                            await message.add_reaction(bonus_emojis[bonus])
                return 
            
        except Exception as e:
            print(f"events.py: Error processing game score: {str(e)}")
