import re
import json
import os
import pytz
import discord
from typing import Tuple, Dict, Any, List
from bot.functions.admin import direct_path_finder
from datetime import datetime

def save_message_detail(message: discord.Message) -> None:
    """
    Save message details to a JSON file with comprehensive metadata.
    
    Args:
        message: A discord.Message object containing the message to save
    """
    if not isinstance(message, discord.Message):
        raise TypeError(f"Expected discord.Message object, got {type(message)}")
    
    # Find URLs in content
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
    
    # Process attachments
    attachments = []
    attachment_urls = []
    for attachment in message.attachments:
        attachment_urls.append(attachment.url)
        attachments.append({
            "filename": attachment.filename,
            "content_type": attachment.content_type,
            "size": attachment.size,
            "url": attachment.url
        })
    urls.extend(attachment_urls)

    # Process embeds
    embed_info = []
    for embed in message.embeds:
        embed_data = {
            "type": embed.type,
            "title": embed.title,
            "description": embed.description,
            "url": embed.url,
            "color": embed.color.value if embed.color else None,
            "has_image": bool(embed.image),
            "has_video": bool(embed.video),
            "has_thumbnail": bool(embed.thumbnail)
        }
        embed_info.append(embed_data)

    # Process reactions
    reaction_info = []
    for reaction in message.reactions:
        reaction_info.append({
            "emoji": str(reaction.emoji),
            "count": reaction.count,
            "me": reaction.me
        })

    # Get message timestamps
    msg_crt = message.created_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")
    msg_edt = None
    if message.edited_at is not None:
        msg_edt = message.edited_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

    # Determine message type and context
    message_type = "regular"
    interaction_info = {}
    command_info = {}
    
    # Check if this is an interaction (slash command, button, etc.)
    if hasattr(message, 'interaction_metadata') and message.interaction_metadata:
        message_type = "interaction_response"
        interaction_info = {
            "interaction_id": message.interaction_metadata.id,
            "interaction_type": message.interaction_metadata.type.name if message.interaction_metadata.type else None,
            "command_name": message.interaction_metadata.name,
            "user": {
                "id": message.interaction_metadata.user.id,
                "name": message.interaction_metadata.user.name,
                "display_name": message.interaction_metadata.user.display_name
            }
        }
    # Fallback to old interaction attribute for compatibility
    elif hasattr(message, 'interaction') and message.interaction:
        message_type = "interaction_response"
        interaction_info = {
            "interaction_id": message.interaction.id,
            "interaction_type": message.interaction.type.name if message.interaction.type else None,
            "command_name": message.interaction.name,
            "user": {
                "id": message.interaction.user.id,
                "name": message.interaction.user.name,
                "display_name": message.interaction.user.display_name
            }
        }
    
    # Check if this is likely a command (starts with prefix or is from bot with empty content + attachments)
    elif message.content.startswith(('/', '!', '?')):
        message_type = "command"
        command_parts = message.content.split()
        if command_parts:
            command_info = {
                "command": command_parts[0],
                "args": command_parts[1:] if len(command_parts) > 1 else []            }
    
    # Check if this looks like a slash command result (empty content but has attachments/embeds)
    elif message.content == "" and (message.attachments or message.embeds):
        message_type = "possible_interaction"
    
    # Check if this is a bot message
    elif message.author.bot:
        message_type = "bot_message"
    
    # Check if this is a system message
    elif message.type != discord.MessageType.default:
        message_type = "system_message"
        interaction_info["system_type"] = message.type.name

    # Reply information
    reply_info = {}
    if message.reference:
        reply_info = {
            "replied_to_message_id": message.reference.message_id,
            "replied_to_channel_id": message.reference.channel_id,
            "replied_to_guild_id": message.reference.guild_id
        }

    # Thread information
    thread_info = {}
    if isinstance(message.channel, discord.Thread):
        thread_info = {
            "thread_id": message.channel.id,
            "thread_name": message.channel.name,
            "parent_channel_id": message.channel.parent.id if message.channel.parent else None,
            "parent_channel_name": message.channel.parent.name if message.channel.parent else None,
            "thread_owner_id": message.channel.owner_id,
            "thread_created_at": message.channel.created_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S") if message.channel.created_at else None
        }

    # Check if this is a game score
    is_score, game_name, game_info = is_game_score(message.content)

    # Structure comprehensive message data
    message_data: Dict[str, Any] = {
        "id": message.id,
        "content": message.content,
        "create_ts": msg_crt,
        "edit_ts": msg_edt,
        "bot_added_ts": pytz.timezone('US/Eastern').localize(datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
        "length": len(message.content),
        
        # Author information
        "author_id": message.author.id,
        "author_nm": message.author.name,
        "author_nick": message.author.display_name,
        "author_is_bot": message.author.bot,
        
        # Channel information
        "channel_id": message.channel.id,
        "channel_nm": getattr(message.channel, 'name', 'DM') if hasattr(message.channel, 'name') else 'DM',
        "channel_type": type(message.channel).__name__,
        
        # Message type and context
        "message_type": message_type,
        "system_message_type": message.type.name if message.type != discord.MessageType.default else None,
        
        # Content analysis
        "has_attachments": bool(message.attachments),
        "has_embeds": bool(message.embeds),
        "has_links": bool(urls),
        "has_mentions": bool(message.mentions),
        "has_reactions": bool(message.reactions),
        "has_reply": bool(message.reference),
        "is_pinned": message.pinned,
        "is_game_score": is_score,
        
        # Detailed information
        "attachments": attachments,
        "embeds": embed_info,
        "reactions": reaction_info,
        "mentioned_users": [{"id": user.id, "name": user.name, "display_name": user.display_name} for user in message.mentions],
        "mentioned_roles": [{"id": role.id, "name": role.name} for role in message.role_mentions],
        "mentioned_channels": [{"id": channel.id, "name": channel.name} for channel in message.channel_mentions],
        
        # Legacy fields for compatibility
        "list_of_attachment_types": [attachment.content_type for attachment in message.attachments],
        "list_of_links": urls,
        "list_of_mentioned": [str(user.name) for user in message.mentions],
        
        # Context information
        "interaction_info": interaction_info if interaction_info else None,
        "command_info": command_info if command_info else None,
        "reply_info": reply_info if reply_info else None,
        "thread_info": thread_info if thread_info else None,
        
        # Game information
        "game_name": game_name if is_score else None,
        "game_info": game_info if is_score else None
    }

    # Handle DM messages (no guild)
    if message.guild is None:
        # For DM messages, we can either skip them or store them separately
        # For now, let's skip DM messages since the bot structure expects guild-based storage
        print(f"Skipping DM message from {message.author.name}: {message.content[:50]}...")
        return

    # set file path
    file_path = direct_path_finder('files', 'guilds', message.guild.name, 'messages.json')

    # read existing messages (if any)
    messages: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            content = file.read()
            if content:  # Check if the file is not empty
                try:
                    messages = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    messages = {}
    else:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # add new message to existing messages
    messages[str(message.id)] = message_data  # Convert ID to string for JSON compatibility

    # write updated messages back to the file
    with open(file_path, 'w') as file:
        json.dump(messages, file, indent=4)

def is_game_score(message_content: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Check if a message contains a game score by checking against game prefixes.
    
    Args:
        message_content: The content of the message to check
        
    Returns:
        A tuple containing:
        - bool: Whether the message is a game score
        - str: The game name if it is a score, None otherwise
        - dict: The game info if it is a score, None otherwise
    """
    # Load games configuration
    games_file_path = direct_path_finder('files', 'games.json')
    with open(games_file_path, 'r', encoding='utf-8') as file:
        games_data: Dict[str, Dict[str, Any]] = json.load(file)

    # check if message matches any game prefix
    for game_name, game_info in games_data.items():
        if "prefix" in game_info:
            prefix = game_info["prefix"]
            if message_content.startswith(prefix):
                return True, game_info["game_name"].lower(), game_info

    return False, None, None
