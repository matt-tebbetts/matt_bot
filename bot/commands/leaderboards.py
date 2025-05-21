import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from bot.functions import get_df_from_sql
from bot.functions.admin import direct_path_finder
from bot.functions.df_to_image import df_to_image
from datetime import datetime
import pandas as pd
from typing import Optional, Literal

list_of_date_ranges = ["today", "this month", "last month", "this year", "all time"]

class Leaderboards(commands.Cog):
    def __init__(self, client, tree):
        self.client = client
        self.tree = tree
        self.load_commands()

    # this calls create_command for each game name in the games.json configuration
    def load_commands(self):
        games_file_path = direct_path_finder('files', 'games.json')
        with open(games_file_path, 'r', encoding='utf-8') as file:
            games_data = json.load(file)

        for game_name, game_info in games_data.items():
            command_name = game_info["game_name"]
            command_description = f"Show {command_name.capitalize()} leaderboard"
            if not self.tree.get_command(command_name):
                self.create_command(command_name, command_description)

    # this creates a leaderboard command for each game so you can call /mini or /octordle
    def create_command(self, name, description):
        async def command(interaction: discord.Interaction,
                          date_range: Literal["today", "this month", "last month", "this year", "all time"]):
            print(f"leaderboards.py: running command '{name}' with date_range '{date_range}'")
            await self.show_leaderboard(game=name, interaction=interaction, date_range=date_range)

        command.__name__ = name
        app_command = app_commands.Command(
            name=name,
            callback=command,
            description=description
        )
        self.tree.add_command(app_command)

    # leaderboard for any game
    async def show_leaderboard(self, interaction: Optional[discord.Interaction] = None, game: str = None, date_range: Optional[str] = 'today') -> str:
        try:
            # Determine if this is an interaction or a programmatic call
            if interaction:
                await interaction.response.defer()
                user = interaction.user
            else:
                user = None

            # Get the appropriate SQL file based on date_range
            sql_file = f"leaderboard_{date_range}.sql"
            sql_file_path = os.path.join("files", "queries", sql_file)

            # Check if the SQL file exists
            if not os.path.exists(sql_file_path):
                error_message = f"Error: SQL file '{sql_file}' not found."
                if interaction:
                    await interaction.followup.send(error_message)
                return error_message

            # Read the SQL query from the file
            with open(sql_file_path, 'r', encoding='utf-8') as file:
                query = file.read()

            # Get the leaderboard
            params = [game] if game else None
            df = await get_df_from_sql(query, params)

            # Check if DataFrame is empty
            if df.empty:
                if interaction:
                    await interaction.followup.send(f"No data available for {game}")
                return f"No data available for {game}"

            # Format the leaderboard
            if date_range == 'today':
                leaderboard = format_today_leaderboard(df, game)
            elif date_range == 'this_month':
                leaderboard = format_monthly_leaderboard(df, game)
            else:
                leaderboard = format_leaderboard(df, game)

            # Handle the response based on whether it's an interaction or programmatic call
            if interaction:
                # Try to create and send an image first
                try:
                    img_path = create_leaderboard_image(leaderboard, game)
                    await interaction.followup.send(file=discord.File(img_path))
                    return img_path
                except Exception as e:
                    # If image creation fails, send as text
                    await interaction.followup.send(leaderboard)
                    return leaderboard
            else:
                return leaderboard

        except Exception as e:
            error_message = f"Error showing leaderboard: {str(e)}"
            if interaction:
                await interaction.followup.send(error_message)
            return error_message

async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically