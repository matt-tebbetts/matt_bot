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
        print(f"Logged in as {client.user.name} (ID: {client.user.id})")
        print(f"Connected to {len(client.guilds)} servers:")
        for guild in client.guilds:
            print(f"- {guild.name} (ID: {guild.id})")
        
        print("\n[DEBUG] Starting to save guild configs...")
        await save_all_guild_configs(client)
        print("[DEBUG] Finished saving guild configs")
        
        print("\n[DEBUG] Starting to initialize message history...")
        try:
            await initialize_message_history(client, lookback_days=7)  # Only look back 7 days during testing
            print("[DEBUG] Successfully initialized message history")
        except Exception as e:
            print(f"[DEBUG] Error initializing message history: {e}")
        
        print("\n[DEBUG] Starting to load cogs...")
        try:
            await load_cogs(client, tree)
            print("[DEBUG] Successfully loaded all cogs")
        except Exception as e:
            print(f"[DEBUG] Error loading cogs: {e}")
        print("[DEBUG] Finished loading cogs")
        
        print("\n[DEBUG] Starting to sync commands...")
        try:
            # Sync globally
            await tree.sync(guild=None)
            print("[DEBUG] Successfully synced commands globally")
            
            # Also sync to each guild
            for guild in client.guilds:
                await tree.sync(guild=guild)
                print(f"[DEBUG] Synced commands to {guild.name}")
        except Exception as e:
            print(f"[DEBUG] Error syncing commands: {e}")
        print("[DEBUG] Finished syncing commands")
        
        print("\n[DEBUG] Starting to connect to database...")
        try:
            await get_pool()
            print("[DEBUG] Successfully connected to database")
        except Exception as e:
            print(f"[DEBUG] Error connecting to database: {e}")
        print("[DEBUG] Finished database connection")
        
        print("\n[DEBUG] Starting background tasks...")
        try:
            setup_tasks(client, tree)
            print("[DEBUG] Successfully started background tasks")
        except Exception as e:
            print(f"[DEBUG] Error starting background tasks: {e}")
        print("[DEBUG] Finished starting background tasks")
        
        print("\n=== Bot is ready! ===")

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
            if isinstance(message.channel, discord.Thread):
                channel_name = f"#{message.channel.parent.name} > {message.channel.name}"
            elif isinstance(message.channel, discord.TextChannel):
                channel_name = f"#{message.channel.name}"
            else:
                channel_name = "DM"
            
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
