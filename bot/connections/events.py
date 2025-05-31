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
from bot.connections.logging_config import get_logger, log_exception, log_asyncio_context

# Get loggers for different components
startup_logger = get_logger('startup')
events_logger = get_logger('events')
message_logger = get_logger('messages')

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
        log_exception(startup_logger, e, "token analysis")
        import traceback
        log_exception(startup_logger, traceback.format_exc(), "traceback")

# load cogs commands
async def load_cogs(client, tree):
    cog_directory = './bot/commands'
    cog_files = [f for f in os.listdir(cog_directory) if f.endswith('.py') and f != '__init__.py']
    
    for filename in cog_files:
        module_name = f'bot.commands.{filename[:-3]}'
        module = importlib.import_module(module_name)
        if hasattr(module, 'setup'):
            await module.setup(client, tree)
        log_asyncio_context()
        print(f"✓ Loaded {module_name}")

# Register event listeners
async def setup_events(client, tree):

    # on ready
    @client.event
    async def on_ready():
        startup_logger.info("="*60)
        startup_logger.info("BOT STARTUP SEQUENCE INITIATED")
        startup_logger.info("="*60)
        startup_logger.info(f"Logged in as {client.user.name} (ID: {client.user.id})")
        startup_logger.info(f"Connected to {len(client.guilds)} servers:")
        for guild in client.guilds:
            startup_logger.info(f"  └─ {guild.name} (ID: {guild.id}, {len(guild.members)} members)")
        
        log_asyncio_context()
        
        # Run initial setup tasks in parallel
        startup_logger.info("Running initial setup tasks...")
        try:
            import asyncio
            results = await asyncio.gather(
                save_all_guild_configs(client),
                get_pool(),  # Start database connection early
                return_exceptions=True
            )
            
            # Check results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    startup_logger.error(f"Initial setup task {i} failed: {result}")
                else:
                    startup_logger.debug(f"Initial setup task {i} completed successfully")
                    
            startup_logger.info("✓ Initial setup completed")
        except Exception as e:
            log_exception(startup_logger, e, "initial setup")
        
        # Initialize message history (can be time-consuming)
        startup_logger.info("Checking for missed messages...")
        try:
            await initialize_message_history(client, lookback_days=7)
            startup_logger.info("✓ Message history initialization completed")
        except Exception as e:
            log_exception(startup_logger, e, "message history initialization")
        
        # Analyze token estimates for all guilds
        startup_logger.info("Analyzing token estimates...")
        try:
            await analyze_guild_token_estimates(client)
            startup_logger.info("✓ Token analysis completed")
        except Exception as e:
            log_exception(startup_logger, e, "token analysis")
        
        # Load cogs and sync commands in parallel
        startup_logger.info("Loading modules and syncing commands...")
        try:
            import asyncio
            # Define sync task
            async def sync_commands():
                startup_logger.debug("Starting global command sync...")
                await tree.sync(guild=None)  # Global sync
                startup_logger.debug("Starting guild-specific command syncs...")
                for guild in client.guilds:
                    await tree.sync(guild=guild)
                    startup_logger.debug(f"Synced commands for {guild.name}")
                return len(client.guilds)
            
            # Run in parallel
            results = await asyncio.gather(
                load_cogs(client, tree),
                sync_commands(),
                return_exceptions=True
            )
            
            if isinstance(results[0], Exception):
                log_exception(startup_logger, results[0], "loading cogs")
            else:
                startup_logger.info("✓ Modules loaded successfully")
                
            if isinstance(results[1], Exception):
                log_exception(startup_logger, results[1], "syncing commands")
            else:
                startup_logger.info(f"✓ Commands synced to {results[1]} servers")
                
        except Exception as e:
            log_exception(startup_logger, e, "module loading or command sync")
        
        # Start background tasks
        startup_logger.info("Starting background tasks...")
        try:
            setup_tasks(client, tree)
            startup_logger.info("✓ Background tasks started successfully")
        except Exception as e:
            log_exception(startup_logger, e, "background task setup")
        
        startup_logger.info("="*60)
        startup_logger.info("🚀 BOT IS READY AND OPERATIONAL! 🚀")
        startup_logger.info("="*60)

    # on message
    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        # Check if it's a game score first
        try:
            is_score, game_name, game_info = is_game_score(message.content)
        except Exception as e:
            log_exception(message_logger, e, "checking if message is game score")
            is_score, game_name, game_info = False, None, None

        # log message
        try:
            if isinstance(message.channel, discord.Thread):
                channel_name = f"#{message.channel.parent.name} > {message.channel.name}"
            elif isinstance(message.channel, discord.TextChannel):
                channel_name = f"#{message.channel.name}"
            elif isinstance(message.channel, discord.GroupChannel):
                channel_name = f"Group DM: {message.channel.name or 'Unnamed'}"
            elif isinstance(message.channel, discord.DMChannel):
                channel_name = f"DM with {message.channel.recipient.name}"
            else:
                channel_name = "Unknown Channel"
            
            first_line = message.content.split('\n')[0]
            message_preview = first_line[:16] + "..." if len(first_line) > 16 else first_line
            game_info_text = f" [{game_name}]" if is_score else ""
            
            # Use different log levels for different message types
            if is_score:
                message_logger.info(f"🎮 {message.author.name} posted {game_name} score in {channel_name}: {message_preview}")
            else:
                message_logger.debug(f"💬 {message.author.name} posted in {channel_name}: {message_preview}")
                
        except Exception as e:
            log_exception(message_logger, e, "logging message details")

        # save message (with game score flag)
        try:
            save_message_detail(message)
        except Exception as e:
            log_exception(message_logger, e, "saving message detail")

        # process game score if it is one
        if not is_score:
            return

        try:
            message_logger.debug(f"Processing {game_name} score for {message.author.name}")
            score_result = await process_game_score(message, game_name, game_info)
            if not score_result:
                message_logger.debug(f"No score result returned for {game_name}")
                return

            message_logger.debug(f"Score processed successfully: {score_result}")

            # Load games configuration
            games_file_path = direct_path_finder('files', 'config', 'games.json')
            with open(games_file_path, 'r', encoding='utf-8') as f:
                games_config = json.load(f)
            game_config = games_config.get(score_result['game_name'], {})

            # Add reactions
            main_emoji = game_config.get('emoji', '✅')
            success = await smart_emoji_reaction(message, main_emoji)
            if not success:
                # Fallback to green checkmark
                try:
                    await smart_emoji_reaction(message, '✅')
                    message_logger.debug(f"Used fallback emoji for {game_name}")
                except Exception as e:
                    log_exception(message_logger, e, "adding fallback emoji reaction")
            else:
                message_logger.debug(f"Added main emoji {main_emoji} for {game_name}")
            
            # Add bonus reactions if any
            if game_bonuses := score_result.get('game_bonuses'):
                message_logger.debug(f"Processing bonuses: {game_bonuses}")
                for bonus in game_bonuses.split(', '):
                    if emoji_config := game_config.get('bonus_emojis', {}).get(bonus):
                        success = await smart_emoji_reaction_with_fallbacks(message, emoji_config)
                        if not success:
                            # Fallback to green checkmark for failed bonus emojis
                            try:
                                await smart_emoji_reaction(message, '✅')
                                message_logger.debug(f"Used fallback emoji for bonus {bonus}")
                            except Exception as e:
                                log_exception(message_logger, e, f"adding fallback emoji for bonus {bonus}")
                        else:
                            message_logger.debug(f"Added bonus emoji for {bonus}")
            
        except Exception as e:
            log_exception(message_logger, e, f"processing {game_name} game score")

async def smart_emoji_reaction(message, emoji_str):
    """
    Intelligently add emoji reaction with fallbacks.
    Handles Unicode, custom emojis, and provides fallbacks.
    """
    try:
        # Handle DMs (no guild)
        if message.guild is None:
            # In DMs, can only use Unicode emojis
            if not (emoji_str.startswith('<:') or emoji_str.startswith(':')):
                await message.add_reaction(emoji_str)
                return True
            else:
                print(f"Cannot use custom emoji '{emoji_str}' in DM")
                return False
        
        # Handle full custom Discord emoji format (<:name:id>)
        if emoji_str.startswith('<:') and emoji_str.endswith('>'):
            await message.add_reaction(emoji_str)
            return True
            
        # Handle shorthand custom Discord emoji format (:name:)
        elif emoji_str.startswith(':') and emoji_str.endswith(':') and len(emoji_str) > 2:
            emoji_name = emoji_str[1:-1]  # Remove the colons
            
            # First try to find in guild
            custom_emoji = discord.utils.get(message.guild.emojis, name=emoji_name)
            if custom_emoji:
                await message.add_reaction(custom_emoji)
                return True
                
            # If not found, check guild config for available emojis
            try:
                guild_config_path = direct_path_finder('files', 'guilds', message.guild.name, 'config.json')
                if os.path.exists(guild_config_path):
                    with open(guild_config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        custom_emojis = config.get('custom_emojis', {})
                        if emoji_name in custom_emojis:
                            emoji_data = custom_emojis[emoji_name]
                            # Check if emoji is available
                            if emoji_data.get('available', True):
                                full_emoji = emoji_data['full_format']
                                await message.add_reaction(full_emoji)
                                return True
                            else:
                                print(f"Custom emoji '{emoji_name}' is not available in guild '{message.guild.name}'")
                                return False
            except Exception as e:
                print(f"Error checking guild config for emoji: {e}")
                
            # Emoji not found in this guild
            print(f"Custom emoji '{emoji_name}' not available in guild '{message.guild.name}'")
            return False
            
        else:
            # Regular Unicode emoji
            await message.add_reaction(emoji_str)
            return True
            
    except Exception as e:
        print(f"Failed to add emoji reaction '{emoji_str}' in guild '{message.guild.name if message.guild else 'DM'}': {e}")
        return False

async def smart_emoji_reaction_with_fallbacks(message, emoji_config):
    """
    Enhanced emoji reaction with intelligent fallback system.
    Supports both simple string emojis and complex fallback configurations.
    """
    try:
        # Handle simple string emoji (backward compatibility)
        if isinstance(emoji_config, str):
            return await smart_emoji_reaction(message, emoji_config)
        
        # Handle complex fallback configuration
        if isinstance(emoji_config, dict):
            # Try primary emoji first
            if 'primary' in emoji_config:
                success = await smart_emoji_reaction(message, emoji_config['primary'])
                if success:
                    print(f"✓ Used primary emoji: {emoji_config['primary']}")
                    return True
                else:
                    print(f"✗ Primary emoji failed: {emoji_config['primary']}")
            
            # Try fallback emoji
            if 'fallback' in emoji_config:
                success = await smart_emoji_reaction(message, emoji_config['fallback'])
                if success:
                    print(f"✓ Used fallback emoji: {emoji_config['fallback']}")
                    return True
                else:
                    print(f"✗ Fallback emoji failed: {emoji_config['fallback']}")
            
            # Universal hardcoded backup - green checkmark
            success = await smart_emoji_reaction(message, '✅')
            if success:
                print(f"✓ Used universal backup emoji: ✅")
                return True
            else:
                print(f"✗ Even universal backup emoji failed: ✅")
        
        # If all else fails (this should be extremely rare)
        print(f"✗ All emoji options failed for config: {emoji_config}")
        return False
        
    except Exception as e:
        print(f"Error in smart_emoji_reaction_with_fallbacks: {e}")
        return False
