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
        print(f"leaderboards.py: added command {name}")

    async def get_leaderboard(self, game: str):
        query = f"SELECT game_rank as rnk, player, score FROM matt.leaderboards WHERE game_name = '{game}'"
        df = await get_df_from_sql(query)
        if df.empty:
            print(f"leaderboards.py: no data for {game} leaderboard")
            return "No data available for this leaderboard."
        
        # format leaderboard
        df['rnk'] = df['rnk'].fillna(-1).astype(int).replace(-1, '-').astype(str)
        title = f"{game.capitalize()} Leaderboard"
        subtitle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        leaderboard = df.to_string(index=False)
        leaderboard_as_string = f"**{title}**\n*{subtitle}*\n```\n{leaderboard}\n```"
        return leaderboard_as_string

    # send leaderboard to discord
    async def show_leaderboard(self, game: str = None,
                               interaction: discord.Interaction = None, 
                               guild: discord.Guild = None):
        print(f"leaderboards.py: entered show_leaderboard for {guild.name} with game {game}")

        if interaction:
            await interaction.response.defer()

        leaderboard_as_string = await self.get_leaderboard(game)
        print(f"leaderboards.py: got leaderboard string for {game}")

        if guild:
            print(f"leaderboards.py: sending leaderboard to default channel for {guild.name}")
            config_path = f"files/guilds/{guild.name}/config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                default_channel_id = config.get('default_channel_id')
                if default_channel_id:
                    channel = guild.get_channel(default_channel_id)
                    if channel:
                        print(f"Posting leaderboard to {channel.name} in {guild.name}")
                        await channel.send(leaderboard_as_string)
                        return
                    else:
                        print(f"Channel with ID {default_channel_id} not found in {guild.name}")
                else:
                    print(f"No default_channel_id found in config for {guild.name}")
            else:
                print(f"Config file not found for {guild.name}")

        # if they called the command directly, send it as reply
        if interaction:
            await interaction.followup.send(leaderboard_as_string)

async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically