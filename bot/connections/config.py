import os
import json
import discord
import platform
from dotenv import load_dotenv
from bot.functions.admin import direct_path_finder

# Load environment variables
load_dotenv()

# Debug configuration
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Platform-specific configurations
IS_MAC = platform.system() == 'Darwin'
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

# Bot token configuration
if IS_LINUX:
    BOT_TOKEN = os.getenv("MATT_BOT")
    BOT_NAME = "Matt_Bot"
else:
    BOT_TOKEN = os.getenv("TEST_BOT")
    BOT_NAME = "Test_Bot"

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
        user_info = {
            "id": str(member.id),
            "name": member.name,
            "display_name": member.display_name,
            "bot": member.bot,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None
        }
        guild_info["users"].append(user_info)

    # Save to file
    config_file = direct_path_finder('files', 'guilds', guild.name, 'config.json')
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(guild_info, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved config for {guild.name} ({len(guild_info['channels'])} channels, {len(guild_info['users'])} users)")

async def save_all_guild_configs(client: discord.Client):
    for guild in client.guilds:
        try:
            await save_guild_config(guild)
        except Exception as e:
            print(f"[ERROR] Failed to save config for {guild.name}: {e}")