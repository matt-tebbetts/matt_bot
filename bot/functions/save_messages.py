import re
import json
import os
import pytz
import discord
from typing import Tuple, Dict, Any, List
from bot.functions.admin import direct_path_finder

def save_message_detail(message: discord.Message) -> None:
    """
    Save message details to a JSON file.
    
    Args:
        message: A discord.Message object containing the message to save
    """
    if not isinstance(message, discord.Message):
        raise TypeError(f"Expected discord.Message object, got {type(message)}")
    
    # Find URLs
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
    
    # Check for GIFs or other attachments
    attachments = [attachment.url for attachment in message.attachments]
    urls.extend(attachments)

    # get message timestamps
    msg_crt = message.created_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")
    msg_edt = None
    if message.edited_at is not None:
        msg_edt = message.edited_at.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S")

    # Structure data
    message_data: Dict[str, Any] = {
        "id": message.id,
        "content": message.content,
        "create_ts": msg_crt,
        "edit_ts": msg_edt,
        "length": len(message.content),
        "author_id": message.author.id,
        "author_nm": message.author.name,
        "author_nick": message.author.display_name,
        "channel_id": message.channel.id,
        "channel_nm": message.channel.name,
        "has_attachments": bool(message.attachments),
        "has_links": bool(urls),
        "has_mentions": bool(message.mentions),
        "list_of_attachment_types": [attachment.content_type for attachment in message.attachments],
        "list_of_links": urls,
        "list_of_mentioned": [str(user.name) for user in message.mentions]
    }

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
