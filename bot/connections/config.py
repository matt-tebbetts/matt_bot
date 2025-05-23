import os
import json
import discord
import platform
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Platform-specific configurations
IS_MAC = platform.system() == 'Darwin'
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

# Bot token configuration
BOT_TOKEN = os.getenv("MATT_BOT") if IS_LINUX else os.getenv("TEST_BOT")
BOT_NAME = "Matt_Bot" if IS_LINUX else "Test_Bot"
SYSTEM_NAME = platform.system()

# Font configuration
FONT_PATHS = {
    'Windows': 'C:/Windows/Fonts/arial.ttf',
    'Darwin': '/Library/Fonts/Arial.ttf',  # macOS
    'Linux': '/usr/share/fonts/truetype/ARIAL.TTF'
}
FONT_PATH = FONT_PATHS.get(platform.system(), FONT_PATHS['Linux'])

async def save_guild_config(guild: discord.Guild):
    guild_info = {
        "guild_id": str(guild.id),
        "guild_name": guild.name,
        "channels": [],
        "users": [],
        "default_channel_id": None
    }

    # Gather channel information
    for channel in guild.text_channels:
        channel_info = {
            "id": str(channel.id),
            "name": channel.name,
            "category": channel.category.name if channel.category else None,
            "position": channel.position
        }
        guild_info["channels"].append(channel_info)

        # Set default channel based on criteria
        if channel.name in ["game-scores", "crossword-corner"]:
            guild_info["default_channel_id"] = str(channel.id)

    # Gather user information
    for member in guild.members:
        if not member.bot:
            user_info = {
                "id": str(member.id),
                "name": member.name,
                "display_name": member.display_name,
                "nickname": member.nick if member.nick else None,
                "joined_at": member.joined_at.strftime('%Y-%m-%d %H:%M:%S') if member.joined_at else None,
                "roles": [{"id": str(role.id), "name": role.name} for role in member.roles if role.name != "@everyone"],
                "is_owner": member.id == guild.owner_id,
                "is_admin": member.guild_permissions.administrator
            }
            guild_info["users"].append(user_info)

    # Save to config.json
    guild_dir = os.path.join("files", "guilds", guild.name)
    os.makedirs(guild_dir, exist_ok=True)
    config_path = os.path.join(guild_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(guild_info, f, indent=4)

async def save_all_guild_configs(client: discord.Client):
    for guild in client.guilds:
        await save_guild_config(guild)