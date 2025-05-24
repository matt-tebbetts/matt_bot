import os
import discord
import importlib
from pprint import pformat
import pandas as pd
import json
from collections import OrderedDict
from bot.connections.config import BOT_NAME, SYSTEM_NAME
import re

# local imports
from bot.functions import save_message_detail
from bot.functions import process_game_score, is_game_score
from bot.connections.tasks import setup_tasks
from bot.connections.config import save_all_guild_configs
from bot.functions.message_history import initialize_message_history
from bot.functions.sql_helper import get_pool
from bot.functions.admin import direct_path_finder

async def analyze_guild_token_estimates(client):
    """Analyze message data and create token estimates for each guild and channel."""
    try:
        for guild in client.guilds:
            guild_name = guild.name
            messages_file = direct_path_finder('files', 'guilds', guild_name, 'messages.json')
            
            if not os.path.exists(messages_file):
                continue
            
            # Load messages
            with open(messages_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            if not messages:
                continue
            
            # Analyze by channel
            channel_stats = {}
            overall_min_date = None
            overall_max_date = None
            
            # Overall game score vs normal message stats
            overall_game_score_stats = {
                'message_count': 0,
                'total_characters': 0,
                'estimated_tokens': 0
            }
            overall_normal_stats = {
                'message_count': 0,
                'total_characters': 0,
                'estimated_tokens': 0
            }
            
            # Initialize statistics with more detailed breakdown
            stats = {
                'message_count': 0,
                'total_characters': 0,
                'estimated_tokens': 0,
                'emoji_count': 0,
                'mention_count': 0,
                'url_count': 0,
                'min_date': None,
                'max_date': None,
                'game_score_stats': {
                    'message_count': 0,
                    'total_characters': 0,
                    'estimated_tokens': 0
                },
                'normal_stats': {
                    'message_count': 0,
                    'total_characters': 0,
                    'estimated_tokens': 0
                },
                'message_type_breakdown': {
                    'regular': 0,
                    'bot_message': 0,
                    'interaction_response': 0,
                    'command': 0,
                    'possible_interaction': 0,
                    'system_message': 0
                },
                'interaction_commands': {},
                'bot_vs_human': {
                    'bot_messages': 0,
                    'human_messages': 0,
                    'bot_tokens': 0,
                    'human_tokens': 0
                }
            }
            
            for msg_id, msg in messages.items():
                channel = msg.get('channel_nm', 'unknown')
                content = msg.get('content', '')
                create_ts = msg.get('create_ts')
                is_game_score = msg.get('is_game_score', False)
                
                if channel not in channel_stats:
                    channel_stats[channel] = {
                        'message_count': 0,
                        'total_characters': 0,
                        'estimated_tokens': 0,
                        'emoji_count': 0,
                        'mention_count': 0,
                        'url_count': 0,
                        'min_date': None,
                        'max_date': None,
                        'game_score_stats': {
                            'message_count': 0,
                            'total_characters': 0,
                            'estimated_tokens': 0
                        },
                        'normal_stats': {
                            'message_count': 0,
                            'total_characters': 0,
                            'estimated_tokens': 0
                        },
                        'message_type_breakdown': {
                            'regular': 0,
                            'bot_message': 0,
                            'interaction_response': 0,
                            'command': 0,
                            'possible_interaction': 0,
                            'system_message': 0
                        },
                        'interaction_commands': {},
                        'bot_vs_human': {
                            'bot_messages': 0,
                            'human_messages': 0,
                            'bot_tokens': 0,
                            'human_tokens': 0
                        }
                    }
                
                stats = channel_stats[channel]
                stats['message_count'] += 1
                stats['total_characters'] += len(content)
                
                # Track dates for this channel
                if create_ts:
                    if stats['min_date'] is None or create_ts < stats['min_date']:
                        stats['min_date'] = create_ts
                    if stats['max_date'] is None or create_ts > stats['max_date']:
                        stats['max_date'] = create_ts
                    
                    # Track overall dates
                    if overall_min_date is None or create_ts < overall_min_date:
                        overall_min_date = create_ts
                    if overall_max_date is None or create_ts > overall_max_date:
                        overall_max_date = create_ts
                
                # Count emojis (Discord emojis and Unicode emojis)
                emoji_count = len(re.findall(r'<:[^>]+>', content))  # Discord custom emojis
                emoji_count += len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]', content))  # Unicode emojis
                stats['emoji_count'] += emoji_count
                
                # Count mentions and URLs
                stats['mention_count'] += len(re.findall(r'<@[!&]?\d+>', content))
                stats['url_count'] += len(re.findall(r'https?://[^\s]+', content))
                
                # Estimate tokens (rough approximation)
                base_tokens = len(content) / 4  # ~4 characters per token for normal text
                emoji_tokens = emoji_count * 2  # Each emoji is roughly 2-3 tokens
                mention_tokens = stats['mention_count'] * 3  # Mentions are a bit more complex
                url_tokens = stats['url_count'] * 10  # URLs can be quite token-heavy
                
                estimated_tokens = base_tokens + emoji_tokens + mention_tokens + url_tokens
                stats['estimated_tokens'] += estimated_tokens
                
                # Track game score vs normal message stats
                if is_game_score:
                    stats['game_score_stats']['message_count'] += 1
                    stats['game_score_stats']['total_characters'] += len(content)
                    stats['game_score_stats']['estimated_tokens'] += estimated_tokens
                    overall_game_score_stats['message_count'] += 1
                    overall_game_score_stats['total_characters'] += len(content)
                    overall_game_score_stats['estimated_tokens'] += estimated_tokens
                else:
                    stats['normal_stats']['message_count'] += 1
                    stats['normal_stats']['total_characters'] += len(content)
                    stats['normal_stats']['estimated_tokens'] += estimated_tokens
                    overall_normal_stats['message_count'] += 1
                    overall_normal_stats['total_characters'] += len(content)
                    overall_normal_stats['estimated_tokens'] += estimated_tokens
                
                # Analyze new message metadata fields
                message_type = msg.get('message_type', 'regular')
                author_is_bot = msg.get('author_is_bot', False)
                interaction_info = msg.get('interaction_info')
                
                # Track message types
                if message_type in stats['message_type_breakdown']:
                    stats['message_type_breakdown'][message_type] += 1
                else:
                    stats['message_type_breakdown']['other'] = stats['message_type_breakdown'].get('other', 0) + 1
                
                # Track interaction commands
                if interaction_info and interaction_info.get('command_name'):
                    command_name = interaction_info['command_name']
                    stats['interaction_commands'][command_name] = stats['interaction_commands'].get(command_name, 0) + 1
                
                # Track bot vs human statistics
                if author_is_bot:
                    stats['bot_vs_human']['bot_messages'] += 1
                    stats['bot_vs_human']['bot_tokens'] += estimated_tokens
                else:
                    stats['bot_vs_human']['human_messages'] += 1
                    stats['bot_vs_human']['human_tokens'] += estimated_tokens
            
            # Sort channels by estimated tokens (highest first)
            sorted_channels = sorted(channel_stats.items(), key=lambda x: x[1]['estimated_tokens'], reverse=True)
            
            # Calculate totals
            total_messages = sum(stats['message_count'] for stats in channel_stats.values())
            total_characters = sum(stats['total_characters'] for stats in channel_stats.values())
            total_tokens = sum(stats['estimated_tokens'] for stats in channel_stats.values())
            
            # Prepare results
            analysis_result = {
                'guild_name': guild_name,
                'analysis_timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                'totals': {
                    'total_messages': total_messages,
                    'total_characters': total_characters,
                    'estimated_total_tokens': int(total_tokens),
                    'total_channels': len(channel_stats),
                    'min_date': overall_min_date,
                    'max_date': overall_max_date,
                    'game_score_summary': {
                        'message_count': overall_game_score_stats['message_count'],
                        'total_characters': overall_game_score_stats['total_characters'],
                        'estimated_tokens': int(overall_game_score_stats['estimated_tokens']),
                        'avg_tokens_per_message': round(overall_game_score_stats['estimated_tokens'] / overall_game_score_stats['message_count'], 1) if overall_game_score_stats['message_count'] > 0 else 0
                    },
                    'normal_message_summary': {
                        'message_count': overall_normal_stats['message_count'],
                        'total_characters': overall_normal_stats['total_characters'],
                        'estimated_tokens': int(overall_normal_stats['estimated_tokens']),
                        'avg_tokens_per_message': round(overall_normal_stats['estimated_tokens'] / overall_normal_stats['message_count'], 1) if overall_normal_stats['message_count'] > 0 else 0
                    }
                },
                'channels': []
            }
            
            # Add channel details
            for channel_name, stats in sorted_channels:
                analysis_result['channels'].append({
                    'channel_name': channel_name,
                    'message_count': stats['message_count'],
                    'total_characters': stats['total_characters'],
                    'estimated_tokens': int(stats['estimated_tokens']),
                    'emoji_count': stats['emoji_count'],
                    'mention_count': stats['mention_count'],
                    'url_count': stats['url_count'],
                    'avg_tokens_per_message': round(stats['estimated_tokens'] / stats['message_count'], 1) if stats['message_count'] > 0 else 0,
                    'min_date': stats['min_date'],
                    'max_date': stats['max_date'],
                    'game_score_stats': {
                        'message_count': stats['game_score_stats']['message_count'],
                        'total_characters': stats['game_score_stats']['total_characters'],
                        'estimated_tokens': int(stats['game_score_stats']['estimated_tokens']),
                        'avg_tokens_per_message': round(stats['game_score_stats']['estimated_tokens'] / stats['game_score_stats']['message_count'], 1) if stats['game_score_stats']['message_count'] > 0 else 0
                    },
                    'normal_stats': {
                        'message_count': stats['normal_stats']['message_count'],
                        'total_characters': stats['normal_stats']['total_characters'],
                        'estimated_tokens': int(stats['normal_stats']['estimated_tokens']),
                        'avg_tokens_per_message': round(stats['normal_stats']['estimated_tokens'] / stats['normal_stats']['message_count'], 1) if stats['normal_stats']['message_count'] > 0 else 0
                    },
                    'message_type_breakdown': stats['message_type_breakdown'],
                    'interaction_commands': stats['interaction_commands'],
                    'bot_vs_human': {
                        'bot_messages': stats['bot_vs_human']['bot_messages'],
                        'human_messages': stats['bot_vs_human']['human_messages'],
                        'bot_tokens': int(stats['bot_vs_human']['bot_tokens']),
                        'human_tokens': int(stats['bot_vs_human']['human_tokens']),
                        'bot_percentage': round(stats['bot_vs_human']['bot_messages'] / stats['message_count'] * 100, 1) if stats['message_count'] > 0 else 0
                    }
                })
            
            # Save to file
            output_file = direct_path_finder('files', 'guilds', guild_name, 'token_estimates.json')
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2)
        
    except Exception as e:
        print(f"[ERROR] Token analysis failed: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

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
        
        # Run initial setup tasks in parallel
        print("\nRunning initial setup...")
        try:
            import asyncio
            await asyncio.gather(
                save_all_guild_configs(client),
                get_pool(),  # Start database connection early
                return_exceptions=True
            )
            print("✓ Initial setup completed")
        except Exception as e:
            print(f"[ERROR] Initial setup failed: {e}")
        
        # Initialize message history (can be time-consuming)
        print("\nInitializing message history...")
        try:
            await initialize_message_history(client, lookback_days=7)
        except Exception as e:
            print(f"[ERROR] Message history initialization failed: {e}")
        
        # Analyze token estimates for all guilds
        try:
            await analyze_guild_token_estimates(client)
        except Exception as e:
            print(f"[ERROR] Token analysis failed: {e}")
        
        # Load cogs and sync commands in parallel
        print("\nLoading modules and syncing commands...")
        try:
            import asyncio
            # Define sync task
            async def sync_commands():
                await tree.sync(guild=None)  # Global sync
                for guild in client.guilds:
                    await tree.sync(guild=guild)
                return len(client.guilds)
            
            # Run in parallel
            results = await asyncio.gather(
                load_cogs(client, tree),
                sync_commands(),
                return_exceptions=True
            )
            
            if not isinstance(results[1], Exception):
                print(f"✓ Commands synced to {results[1]} servers")
                
        except Exception as e:
            print(f"[ERROR] Module loading or command sync failed: {e}")
        
        # Start background tasks
        print("\nStarting background tasks...")
        try:
            setup_tasks(client, tree)
            print("✓ Background tasks started")
        except Exception as e:
            print(f"[ERROR] Background task setup failed: {e}")
        
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
