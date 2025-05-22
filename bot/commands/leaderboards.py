import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from bot.functions import execute_query
from bot.functions.admin import direct_path_finder
from bot.functions.df_to_image import df_to_image
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, Literal, Tuple

class Leaderboards(commands.Cog):
    def __init__(self, client, tree):
        self.client = client
        self.tree = tree
        self.load_commands()

    # this calls create_command for each game name in the games.json configuration
    def load_commands(self):
        games_file_path = direct_path_finder('files', 'games.json')
        print(f"Loading commands from: {games_file_path}")
        with open(games_file_path, 'r', encoding='utf-8') as file:
            games_data = json.load(file)
            # print(f"Loaded games data: {games_data}")  # Commented out to reduce noise

        for game_name, game_info in games_data.items():
            command_name = game_info["game_name"]
            command_description = f"Show {command_name.capitalize()} leaderboard"
            print(f"Registering command: {command_name}")
            if not self.tree.get_command(command_name):
                self.create_command(command_name, command_description)
                print(f"Successfully registered command: {command_name}")
            else:
                print(f"Command {command_name} already exists")

    # this creates a leaderboard command for each game so you can call /mini or /octordle
    def create_command(self, name, description):
        async def command(interaction: discord.Interaction,
                         timeframe: Literal["today", "yesterday", "this month", "last month", "this year", "all time"] = "today"):
            print(f"leaderboards.py: running command '{name}' with timeframe '{timeframe}'")
            try:
                # Defer the response immediately
                await interaction.response.defer()
                print("Response deferred successfully")
                
                # Get the leaderboard
                img_path = await self.show_leaderboard(game=name, interaction=interaction, timeframe=timeframe)
                
                # Send the image file
                if os.path.exists(img_path):
                    await interaction.followup.send(file=discord.File(img_path))
                else:
                    await interaction.followup.send(f"Error: Could not find leaderboard image at {img_path}")
                print("Command completed successfully")
                
            except Exception as e:
                print(f"Error in command {name}: {str(e)}")
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
                    else:
                        await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
                except Exception as followup_error:
                    print(f"Error sending error message: {str(followup_error)}")

        command.__name__ = name
        app_command = app_commands.Command(
            name=name,
            callback=command,
            description=description
        )
        self.tree.add_command(app_command)

    def get_date_range(self, timeframe: str) -> Tuple[datetime, datetime]:
        today = datetime.now().date()
        
        if timeframe == "today":
            return today, today
        elif timeframe == "yesterday":
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif timeframe == "this month":
            start = today.replace(day=1)
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            return start, end
        elif timeframe == "last month":
            if today.month == 1:
                start = today.replace(year=today.year - 1, month=12, day=1)
            else:
                start = today.replace(month=today.month - 1, day=1)
            end = today.replace(day=1) - timedelta(days=1)
            return start, end
        elif timeframe == "this year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
            return start, end
        else:  # all time
            return datetime(2020, 1, 1).date(), today

    # leaderboard for any game
    async def show_leaderboard(self, interaction: Optional[discord.Interaction] = None, game: str = None, 
                             timeframe: Optional[str] = 'today') -> str:
        try:
            # Get date range
            start_date, end_date = self.get_date_range(timeframe)
            print(f"Date range: {start_date} to {end_date}")
            
            # Determine if we need daily scores or aggregate stats
            if timeframe in ["today", "yesterday"]:
                # Use daily scores query
                sql_file = "game_daily_scores.sql"
                params = [start_date, game]
            else:
                # Use aggregate stats query
                sql_file = "game_aggregate_stats.sql"
                params = [start_date, end_date, game]

            sql_file_path = direct_path_finder('files', 'queries', 'active', sql_file)
            print(f"Looking for SQL file at: {sql_file_path}")
            print(f"File exists: {os.path.exists(sql_file_path)}")

            # Check if the SQL file exists
            if not os.path.exists(sql_file_path):
                error_message = f"Error: SQL file '{sql_file}' not found."
                print(error_message)
                return error_message

            # Read the SQL query from the file
            print(f"Reading SQL query from file...")
            with open(sql_file_path, 'r', encoding='utf-8') as file:
                query = file.read()
            print(f"SQL query read successfully")

            # Get the leaderboard
            print(f"Executing query with params: {params}")
            try:
                result = await execute_query(query, params)
                df = pd.DataFrame(result)
                print(f"Query executed successfully, got {len(df)} rows")
                print(f"DataFrame columns: {df.columns.tolist()}")
                print(f"DataFrame head:\n{df.head()}")
            except Exception as e:
                print(f"Error executing query: {str(e)}")
                return f"Error executing query: {str(e)}"

            # Check if DataFrame is empty
            if df.empty:
                print(f"No data found for {game}")
                return f"No data available for {game}"

            # Create and return the image
            try:
                print(f"Starting to create image from DataFrame...")
                img_path = df_to_image(df, f"files/images/{game}_leaderboard.png", f"{game} Leaderboard")
                print(f"Image created successfully at {img_path}")
                return img_path
            except Exception as e:
                print(f"Error in image creation process: {str(e)}")
                return f"Error creating leaderboard image: {str(e)}"

        except Exception as e:
            error_message = f"Error showing leaderboard: {str(e)}"
            print(error_message)
            return error_message

async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically