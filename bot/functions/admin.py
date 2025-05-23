import os
import json
import discord

# read json
def read_json(filepath, default_data=[]):

    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(filepath, 'w') as file:
            json.dump(default_data, file)
        return default_data

# write json
def write_json(filepath, data):
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w') as file:
        json.dump(data, file, indent=4)

# get default channel id
def get_default_channel_id(guild_name):
    config_path = f"files/guilds/{guild_name}/config.json"
    try:
        config = read_json(config_path)
        channel_id = config.get("default_channel_id")
        if channel_id is not None:
            return int(channel_id)
        else:
            print(f"admin.py: default_channel_id not found in config.json for guild '{guild_name}'")
    except FileNotFoundError:
        print(f"admin.py: config.json not found for guild '{guild_name}'")
    except json.JSONDecodeError:
        print(f"admin.py: Error decoding config.json for guild '{guild_name}'")
    except ValueError:
        print(f"admin.py: Invalid channel ID in config.json for guild '{guild_name}'")
    return None

async def update_guild_config(guild: discord.Guild):
    """Update the guild's config.json with current channel and user information."""
    config_path = f"files/guilds/{guild.name}/config.json"
    
    # Load existing config or create new
    config = read_json(config_path, {})
    
    # Update channels
    channels = []
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).read_messages:
            channels.append({
                "id": str(channel.id),
                "name": channel.name,
                "category": channel.category.name if channel.category else None
            })
    config["channels"] = channels
    
    # Update users
    users = []
    for member in guild.members:
        if not member.bot:
            users.append({
                "id": str(member.id),
                "name": member.name,
                "display_name": member.display_name,
                "nickname": member.nick if member.nick else None
            })
    config["users"] = users
    
    # Update games (if not already present)
    if "games" not in config:
        games_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'files', 'games.json'))
        if os.path.exists(games_file):
            with open(games_file, 'r', encoding='utf-8') as f:
                games_data = json.load(f)
                config["games"] = list(games_data.keys())
    
    # Save updated config
    write_json(config_path, config)
    return config

async def save_guild_config(guild: discord.Guild):
    """Save guild configuration including channel and user information."""
    config_path = f"files/guilds/{guild.name}/config.json"
    
    # Load existing config or create new
    config = read_json(config_path, {})
    
    # Update channels
    channels = []
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).read_messages:
            channels.append({
                "id": str(channel.id),
                "name": channel.name
            })
    config["channels"] = channels
    
    # Update users
    users = []
    for member in guild.members:
        if not member.bot:
            users.append({
                "id": str(member.id),
                "name": member.name,
                "display_name": member.display_name
            })
    config["users"] = users
    
    # Update games (if not already present)
    if "games" not in config:
        games_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'files', 'games.json'))
        if os.path.exists(games_file):
            with open(games_file, 'r', encoding='utf-8') as f:
                games_data = json.load(f)
                config["games"] = list(games_data.keys())
    
    # Save updated config
    write_json(config_path, config)
    return config

def direct_path_finder(*relative_path_parts: str) -> str:
    """
    Constructs an absolute path by joining the project root directory with the relative path parts.

    :param relative_path_parts: The parts of the relative path to join.
    :return: The absolute path.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.path.join(project_root, *relative_path_parts)