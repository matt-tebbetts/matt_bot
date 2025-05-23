import json
import os
from typing import Dict, List, Tuple
from bot.functions.admin import direct_path_finder
from bot.functions.save_messages import is_game_score
from datetime import datetime, timedelta
import pytz

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
        "message_count": 0,
        "game_score_count": 0
    }

def save_metadata(guild_name: str, metadata: Dict):
    """Save metadata about message history collection."""
    metadata_path = get_metadata_path(guild_name)
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

async def collect_recent_messages(channel, oldest_ts: str = None, lookback_days: int = 7) -> Tuple[int, int]:
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
        
        # If we have an oldest timestamp, only fetch messages after that
        if oldest_ts:
            after = datetime.strptime(oldest_ts, '%Y-%m-%d %H:%M:%S')
            after = pytz.timezone('US/Eastern').localize(after)
        else:
            # Default to lookback_days ago if no timestamp provided
            after = datetime.now(pytz.timezone('US/Eastern')) - timedelta(days=lookback_days)
        
        async for message in channel.history(after=after, limit=None):
            # Skip if message already exists
            if str(message.id) in existing_messages:
                continue
                
            # Save message
            new_messages[str(message.id)] = {
                "id": message.id,
                "content": message.content,
                "create_ts": message.created_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S"),
                "edit_ts": message.edited_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S") if message.edited_at else None,
                "bot_added_ts": datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S"),
                "length": len(message.content),
                "author_id": message.author.id,
                "author_nm": message.author.name,
                "author_nick": message.author.display_name,
                "channel_id": message.channel.id,
                "channel_nm": message.channel.name,
                "has_attachments": bool(message.attachments),
                "has_links": bool(message.embeds),
                "has_mentions": bool(message.mentions),
                "is_game_score": is_game_score(message.content)[0]
            }
            
            # Check for game scores
            if is_game_score(message.content)[0]:
                game_score_count += 1
        
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
            oldest_ts = metadata.get("oldest_message_ts")
            
            for channel in guild.text_channels:
                # Skip channels the bot can't read
                if not channel.permissions_for(guild.me).read_messages:
                    continue
                    
                messages, scores = await collect_recent_messages(channel, oldest_ts, lookback_days)
                guild_messages += messages
                guild_scores += scores
            
            # Update metadata
            metadata["last_initialized"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            metadata["message_count"] = guild_messages
            metadata["game_score_count"] = guild_scores
            
            # If we collected new messages, update the oldest timestamp
            if guild_messages > 0:
                messages_file = direct_path_finder('files', 'guilds', guild.name, 'messages.json')
                if os.path.exists(messages_file):
                    with open(messages_file, 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                        if messages:
                            oldest_ts = min(msg["create_ts"] for msg in messages.values())
                            metadata["oldest_message_ts"] = oldest_ts
            
            save_metadata(guild.name, metadata)
            
            total_messages += guild_messages
            total_scores += guild_scores
        
        if total_messages > 0:
            print(f"✓ Saved {total_messages} historical messages")
            if total_scores > 0:
                print(f"✓ Saved {total_scores} game scores to SQL")
        
    except Exception as e:
        print(f"[ERROR] Error initializing message history: {str(e)}")
        print(f"[ERROR] Full error details: {str(e.__class__.__name__)}: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}") 