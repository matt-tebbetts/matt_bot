import json
import os
from typing import Dict, List, Tuple
from bot.functions.admin import direct_path_finder
from bot.functions.save_messages import is_game_score
from bot.functions.save_scores import process_game_score
from bot.functions import execute_query
from bot.connections.config import DEBUG_MODE
from datetime import datetime, timedelta
import pytz
import discord

def get_metadata_path(guild_name: str) -> str:
    """Get the path to the metadata file for a guild."""
    return direct_path_finder('files', 'guilds', guild_name, 'history_tracker.json')

def load_metadata(guild_name: str) -> Dict:
    """Load metadata about message history collection."""
    metadata_path = get_metadata_path(guild_name)
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "last_initialized": None,
        "oldest_message_ts": None,
        "latest_message_ts": None,
        "message_count": 0,
        "game_score_count": 0
    }

def save_metadata(guild_name: str, metadata: Dict):
    """Save metadata about message history collection."""
    metadata_path = get_metadata_path(guild_name)
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

async def collect_recent_messages(channel, latest_ts: str = None, lookback_days: int = 7) -> Tuple[int, int]:
    """Collect recent messages from a channel and save any new ones to messages.json.
    Returns tuple of (new_messages_count, game_scores_count)"""
    try:
        # Get the messages file path
        guild_name = channel.guild.name
        messages_file = direct_path_finder('files', 'guilds', guild_name, 'messages.json')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(messages_file), exist_ok=True)
        
        # Load existing messages
        existing_messages = {}
        if os.path.exists(messages_file):
            with open(messages_file, 'r', encoding='utf-8') as f:
                existing_messages = json.load(f)
        
        # Get recent messages from Discord
        new_messages = {}
        game_score_count = 0
        
        # If we have a latest timestamp, only fetch messages after that
        # Otherwise, fall back to lookback_days
        if latest_ts:
            after = datetime.strptime(latest_ts, '%Y-%m-%d %H:%M:%S')
            after = pytz.timezone('US/Eastern').localize(after)
        else:
            # Default to lookback_days ago if no latest timestamp provided
            after = datetime.now(pytz.timezone('US/Eastern')) - timedelta(days=lookback_days)
        
        msg_count = 0
        async for message in channel.history(after=after, limit=None):
            msg_count += 1
            
            # Skip if message already exists
            if str(message.id) in existing_messages:
                continue
                
            # Check for game scores first (we'll use this for both metadata and processing)
            is_score, game_name, game_info = is_game_score(message.content)
            
            # Save message with enhanced metadata structure
            new_messages[str(message.id)] = {
                "id": message.id,
                "content": message.content,
                "create_ts": message.created_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S"),
                "edit_ts": message.edited_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S") if message.edited_at else None,
                "bot_added_ts": datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S"),
                "length": len(message.content),
                
                # Author information
                "author_id": message.author.id,
                "author_nm": message.author.name,
                "author_nick": message.author.display_name,
                "author_is_bot": message.author.bot,
                
                # Channel information
                "channel_id": message.channel.id,
                "channel_nm": message.channel.name,
                "channel_type": type(message.channel).__name__,
                
                # Message type detection
                "message_type": "bot_message" if message.author.bot else ("interaction_response" if getattr(message, 'interaction_metadata', None) else ("command" if message.content.startswith(('/', '!', '?')) else ("possible_interaction" if message.content == "" and (message.attachments or message.embeds) else "regular"))),
                "system_message_type": message.type.name if message.type != discord.MessageType.default else None,
                
                # Content analysis
                "has_attachments": bool(message.attachments),
                "has_embeds": bool(message.embeds),
                "has_links": bool(message.embeds),  # Using embeds as proxy for links
                "has_mentions": bool(message.mentions),
                "has_reactions": bool(message.reactions),
                "has_reply": bool(message.reference),
                "is_pinned": message.pinned,
                "is_game_score": is_score,
                
                # Legacy compatibility fields
                "list_of_attachment_types": [attachment.content_type for attachment in message.attachments],
                "list_of_links": [],  # Would need URL parsing which we skip for bulk collection
                "list_of_mentioned": [str(user.name) for user in message.mentions],
                
                # Enhanced fields (simplified for bulk collection)
                "attachments": [{"filename": att.filename, "content_type": att.content_type, "size": att.size} for att in message.attachments],
                "interaction_info": {
                    "interaction_id": getattr(message.interaction_metadata, 'id', None),
                    "command_name": getattr(message.interaction_metadata, 'name', None),
                    "user_id": getattr(message.interaction_metadata.user, 'id', None) if hasattr(message.interaction_metadata, 'user') else None
                } if getattr(message, 'interaction_metadata', None) else None,
                "reply_info": {
                    "replied_to_message_id": message.reference.message_id
                } if message.reference else None,
                "thread_info": {
                    "thread_name": message.channel.name,
                    "parent_channel_id": message.channel.parent.id if hasattr(message.channel, 'parent') and message.channel.parent else None
                } if isinstance(message.channel, discord.Thread) else None
            }
            
            # Process game scores
            if is_score:
                game_score_count += 1
                
                # Check if this score already exists in the database
                try:
                    check_query = """
                        SELECT COUNT(*) as count
                        FROM games.game_history 
                        WHERE user_name = %s 
                        AND game_name = %s 
                        AND game_date = %s
                    """
                    game_date = message.created_at.astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")
                    result = await execute_query(check_query, [message.author.name, game_name, game_date])
                    
                    # If score doesn't exist, process it
                    if result[0]['count'] == 0:
                        try:
                            # Process and save the game score
                            score_result = await process_game_score(message, game_name, game_info)
                            
                            if score_result:
                                # Load games configuration for emoji reactions
                                games_file_path = direct_path_finder('files', 'config', 'games.json')
                                with open(games_file_path, 'r', encoding='utf-8') as f:
                                    games_config = json.load(f)
                                game_config = games_config.get(game_name, {})
                                
                                # Add main emoji reaction
                                if 'emoji' in game_config:
                                    try:
                                        await message.add_reaction(game_config['emoji'])
                                    except:
                                        pass  # Ignore reaction errors
                                
                                # Add bonus reactions if any
                                if game_bonuses := score_result.get('game_bonuses'):
                                    for bonus in game_bonuses.split(', '):
                                        if emoji := game_config.get('bonus_emojis', {}).get(bonus):
                                            try:
                                                await message.add_reaction(emoji)
                                            except:
                                                pass  # Ignore reaction errors
                        except Exception as e:
                            print(f"[WARNING] Error processing historical game score: {e}")
                except Exception as e:
                    print(f"[WARNING] Error checking existing game score: {e}")
        
        # Only show output for channels that actually had new messages
        # if len(new_messages) > 0:
        #     print(f"✓ {channel.name}: {len(new_messages)} new messages")
        # elif DEBUG_MODE:
        #     # In debug mode, show all channels processed
        #     print(f"✓ {channel.name}: 0 new messages ({msg_count} total checked)")
        
        # Update messages file
        existing_messages.update(new_messages)
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(existing_messages, f, indent=2)
        
        return len(new_messages), game_score_count
        
    except Exception as e:
        print(f"[ERROR] Error collecting messages from {channel.name}: {str(e)}")
        return 0, 0

async def initialize_message_history(client, lookback_days: int = 7) -> None:
    """Initialize message history collection for all channels the bot can see.
    
    Args:
        client: The Discord client instance
        lookback_days: Number of days to look back for messages (default: 7)
    """
    try:
        total_messages = 0
        total_scores = 0
        
        for guild in client.guilds:
            # Load metadata
            metadata = load_metadata(guild.name)
            
            # Check if we need to run initialization
            if metadata["last_initialized"]:
                last_init = datetime.strptime(metadata["last_initialized"], '%Y-%m-%d %H:%M:%S')
                if datetime.now() - last_init < timedelta(hours=4):
                    print(f"✓ Skipped message history initialization for {guild.name}")
                    continue
            
            guild_messages = 0
            guild_scores = 0
            latest_ts = metadata.get("latest_message_ts")
            
            for channel in guild.text_channels:
                # Skip channels the bot can't read
                if not channel.permissions_for(guild.me).read_messages:
                    continue
                    
                messages, scores = await collect_recent_messages(channel, latest_ts, lookback_days)
                guild_messages += messages
                guild_scores += scores
            
            # Update metadata
            metadata["last_initialized"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            metadata["message_count"] = guild_messages
            metadata["game_score_count"] = guild_scores
            
            # Update both oldest and latest timestamps based on the messages we have
            messages_file = direct_path_finder('files', 'guilds', guild.name, 'messages.json')
            if os.path.exists(messages_file):
                with open(messages_file, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                    if messages:
                        timestamps = [msg["create_ts"] for msg in messages.values()]
                        metadata["oldest_message_ts"] = min(timestamps)
                        metadata["latest_message_ts"] = max(timestamps)
            
            save_metadata(guild.name, metadata)
            
            total_messages += guild_messages
            total_scores += guild_scores
        
        if total_messages > 0:
            print(f"✓ Saved {total_messages} historical messages")
            if total_scores > 0:
                print(f"✓ Saved {total_scores} game scores to SQL")
        
    except Exception as e:
        print(f"[ERROR] Error checking for missed messages: {str(e)}")
        print(f"[ERROR] Full error details: {str(e.__class__.__name__)}: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}") 