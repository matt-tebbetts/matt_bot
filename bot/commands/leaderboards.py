import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from bot.functions import get_df_from_sql
from datetime import datetime
import pandas as pd

class Leaderboards(commands.Cog):
    def __init__(self, client, tree):
        self.client = client
        self.tree = tree
        self.load_commands()

    def load_commands(self):
        games_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'files', 'games.json'))
        with open(games_file_path, 'r', encoding='utf-8') as file:
            games_data = json.load(file)

        for game_name, game_info in games_data.items():
            command_name = game_info["game_name"]
            command_description = f"Show {command_name.capitalize()} leaderboard"
            if not self.tree.get_command(command_name):
                self.create_command(command_name, command_description)

    def create_command(self, name, description):
        async def command(interaction: discord.Interaction):
            print(f"leaderboards.py: running {name}")
            await self.show_leaderboard(game=name, interaction=interaction)

        command.__name__ = name
        app_command = app_commands.Command(name=name, description=description, callback=command)
        self.tree.add_command(app_command)

    # leaderboard for any game
    async def show_leaderboard(client: discord.Client, interaction: discord.Interaction = None, guild: discord.Guild = None, game: str = None):
        # get the leaderboard
        query = f"SELECT game_rank as rnk, player, score FROM matt.leaderboards WHERE game_name = '{game}'"
        df = await get_df_from_sql(query)
        if df.empty:
            if interaction:
                await interaction.followup.send(f"No data available for {game} leaderboard.")
            print(f"leaderboards.py: no data for {game} leaderboard")
            return "No data available for this leaderboard."
        
        # format leaderboard
        df['rnk'] = df['rnk'].fillna(-1).astype(int).replace(-1, '-').astype(str)
        title = f"{game.capitalize()} Leaderboard"
        subtitle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        leaderboard = df.to_string(index=False)
        message = f"**{title}**\n*{subtitle}*\n```\n{leaderboard}\n```"
        
        # if called via command interaction, send the message as a reply
        if interaction:
            await interaction.followup.send(message)
            return

        # if called programmatically, send the message to the default channel
        if guild:
            # Read the config.json file to get the default_channel_id
            config_path = f"files/guilds/{guild.name}/config.json"
            try:
                with open(config_path, 'r') as config_file:
                    config = json.load(config_file)
                    channel_id = int(config.get("default_channel_id"))
                    channel = client.get_channel(channel_id)
                    if channel:
                        await channel.send(message)
                    else:
                        print(f"leaderboards.py: Channel ID '{channel_id}' not found in guild '{guild.name}'")
            except FileNotFoundError:
                print(f"leaderboards.py: config.json not found for guild '{guild.name}'")
            except json.JSONDecodeError:
                print(f"leaderboards.py: Error decoding config.json for guild '{guild.name}'")
            except ValueError:
                print(f"leaderboards.py: Invalid channel ID in config.json for guild '{guild.name}'")

async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically