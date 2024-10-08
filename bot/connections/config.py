import os
import json
import discord

async def save_guild_config(guild: discord.Guild):
    guild_info = {
        "guild_id": guild.id,
        "guild_name": guild.name,
        "channels": [],
        "members": [],
        "default_channel_id": None
    }

    # Gather channel information
    for channel in guild.text_channels:
        channel_info = {
            "channel_id": channel.id,
            "channel_name": channel.name,
            "is_default_channel": False
        }
        guild_info["channels"].append(channel_info)

        # Set default channel based on criteria
        if channel.name in ["game-scores", "crossword-corner"]:
            guild_info["default_channel_id"] = channel.id
            channel_info["is_default_channel"] = True

    # Gather member information
    for member in guild.members:
        member_info = {
            "user_id": member.id,
            "user_name": member.name
        }
        guild_info["members"].append(member_info)

    # Save to config.json
    guild_dir = os.path.join("files", "guilds", guild.name)
    os.makedirs(guild_dir, exist_ok=True)
    config_path = os.path.join(guild_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(guild_info, f, indent=4)

async def save_all_guild_configs(client: discord.Client):
    for guild in client.guilds:
        await save_guild_config(guild)