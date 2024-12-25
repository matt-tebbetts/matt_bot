import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from bot.functions import get_df_from_sql
from bot.functions.admin import direct_path_finder
from datetime import datetime
import pandas as pd
from typing import Optional

class Leaderboards(commands.Cog):
    def __init__(self, client, tree):
        self.client = client
        self.tree = tree
        self.load_commands()

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
        async def command(interaction: discord.Interaction, date_range: app_commands.Choice[str]):
            print(f"leaderboards.py: running command '{name}' with date_range '{date_range.value}'")
            await self.show_leaderboard(game=name, interaction=interaction, date_range=date_range.value)

        # Define the list of date range options
        date_ranges = ["today", "this month", "last month", "this year", "all time"]

        # Create the choices using a list comprehension
        choices = [app_commands.Choice(name=option, value=option) for option in date_ranges]

        command.__name__ = name
        app_command = app_commands.Command(
            name=name,
            callback=command,
            choices=[app_commands.Choice(name=option, value=option) for option in date_ranges]
        )
        self.tree.add_command(app_command)

    # leaderboard for any game
    async def show_leaderboard(self, interaction: Optional[discord.Interaction] = None, game: str = None, date_range: Optional[str] = None) -> str:
        
        # Defer the interaction to give more time for processing
        if interaction and not interaction.response.is_done():
            # buy some time
            await interaction.response.defer()
            # respond to interaction, telling them it's loading
            await interaction.followup.send("Loading leaderboard...")

        # Determine the SQL file based on the date range
        if date_range and date_range.lower() == "this month":
            sql_file = 'leaderboard_this_month.sql'
        else:
            sql_file = 'leaderboard_today.sql'

        # Read the SQL query from the file
        sql_file_path = direct_path_finder('files', 'queries', sql_file)
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            query = file.read().format(game=game)

        # get the leaderboard
        df = await get_df_from_sql(query)

        if not df.empty:
            # format leaderboard
            leaderboard = df.to_string(index=False)
            df['rnk'] = df['rnk'].fillna(-1).astype(int).replace(-1, '-').astype(str)
            title = f"{game.capitalize()} Leaderboard"
            subtitle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"**{title}**\n*{subtitle}*\n```\n{leaderboard}\n```"
        else:
            message = f"No data available for {game} leaderboard."
        
        try:
            # if called via command interaction, send the message as a reply
            if isinstance(interaction, discord.Interaction):
                await interaction.followup.send(message)
                return None
            
            # if called programmatically, return the message
            return message
        
        except Exception as e:
            print(f"show_leaderboard: Exception occurred - {e}")
            raise

async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically