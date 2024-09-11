import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from bot.functions import get_df_from_sql
from datetime import datetime
import pandas as pd

# build leaderboard commands
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
            self.create_command(command_name, command_description)

    def create_command(self, name, description):
        async def command(interaction: discord.Interaction):
            print(f"leaderboards.py: running {name}")
            await self.show_leaderboard(interaction, name)

        command.__name__ = name
        app_command = app_commands.Command(name=name, description=description, callback=command)
        self.tree.add_command(app_command)
        print(f"leaderboards.py: added command {name}")

    # leaderboard for any game
    async def show_leaderboard(interaction: discord.Interaction = None, 
                               game: str = None
                               ):
        
        # if they called the command directly, acknowledge to avoid timeout
        if interaction:
            await interaction.response.defer()
        
        # get the leaderboard
        query = f"SELECT game_rank as rnk, player, score FROM matt.leaderboards WHERE game_name = '{game}'"
        df = await get_df_from_sql(query)
        if df.empty:
            await interaction.followup.send(f"No data available for {game} leaderboard.")
            print(f"leaderboards.py: no data for {game} leaderboard")
            return
        
        # format leaderboard
        df['rnk'] = df['rnk'].fillna(-1).astype(int).replace(-1, '-').astype(str)
        title = f"{game.capitalize()} Leaderboard"
        subtitle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        leaderboard = df.to_string(index=False)
        message = f"**{title}**\n*{subtitle}*\n```\n{leaderboard}\n```"
        
        # if they called the command directly, send it as reply
        if interaction:
            await interaction.followup.send(message)
            return

        # if not interaction, just return the leaderboard as a string
        return message
    
async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically