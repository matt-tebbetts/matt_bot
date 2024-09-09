import os
import discord
import importlib
from bot.connections.tasks import setup_tasks
from bot.functions import save_message_detail
from bot.functions import process_game_score
from pprint import pformat
import pandas as pd
import json

# load cogs commands
async def load_cogs(client, tree):
    cog_directory = './bot/commands'
    cog_files = [f for f in os.listdir(cog_directory) if f.endswith('.py') and f != '__init__.py']
    
    for filename in cog_files:
        module_name = f'bot.commands.{filename[:-3]}'
        module = importlib.import_module(module_name)
        if hasattr(module, 'setup'):
            await module.setup(client, tree)
        print(f"events.py: loaded {module_name}")

# Register event listeners
async def setup_events(client, tree):

    # on ready
    @client.event
    async def on_ready():
        
        # print confirmation
        for guild in client.guilds:
            print(f"events.py: {client.user} connected to {guild.name}")

        # load cogs
        try:
            await load_cogs(client, tree)
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
            print("events.py: started tasks")
        except Exception as e:
            print(f"events.py: error starting tasks: {e}")

    # on message
    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        # save message
        try:
            save_message_detail(message)
        except Exception as e:
            print(f"events.py: error saving message detail: {e}")

        # save game scores
        try:
            print(f"events.py: processing game score...")
            score_result = await process_game_score(message) 
            if score_result:
                confirmation_message = f"events.py: saved {score_result}"
                print(confirmation_message)

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
