import json
import os
from discord import app_commands, Interaction
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
            self.create_command(command_name, command_description)

    def create_command(self, name, description):
        async def command(interaction: Interaction):
            print(f"leaderboards.py: running {name}")
            await self.show_leaderboard(interaction, name)

        command.__name__ = name
        app_command = app_commands.Command(name=name, description=description, callback=command)
        self.tree.add_command(app_command)
        print(f"leaderboards.py: added command {name}")

    async def show_leaderboard(self, interaction: Interaction, game: str):
        await interaction.response.defer()
        query = f"SELECT game_rank as rnk, player, score FROM matt.leaderboards WHERE game_name = '{game}'"
        df = await get_df_from_sql(query)
        if df.empty:
            await interaction.followup.send(f"No data available for {game} leaderboard.")
        else:
            # Convert numeric ranks to integers and replace NaN values with '-'
            df['rnk'] = df['rnk'].fillna(-1).astype(int).replace(-1, '-').astype(str)
            title = f"{game.capitalize()} Leaderboard"
            subtitle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            leaderboard = df.to_string(index=False)
            message = f"**{title}**\n*{subtitle}*\n```\n{leaderboard}\n```"
            try:
                await interaction.followup.send(message)
                print(f"leaderboards.py: returned {game} leaderboard")
            except Exception as send_error:
                print(f"leaderboards.py: Error sending message: {send_error}")

async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically