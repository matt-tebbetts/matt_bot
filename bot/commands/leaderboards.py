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

        print("leaderboards.py: show_leaderboard called")

        # Check if interaction is provided
        if interaction:
            # describe the interaction
            print(f"leaderboards.py: interaction is {interaction} called by {interaction.user} and game is {game} and date_range is {date_range}")
        else:
            # If not called via interaction, print alternative details
            print(f"leaderboards.py: called without interaction, game is {game} and date_range is {date_range}")

        # Defer the interaction to give more time for processing
        if interaction and not interaction.response.is_done():
            # buy some time
            await interaction.response.defer()

        # Determine the SQL file and parameters to use, based on the game and date range
        if game == "winners":
            if date_range and date_range.lower() == "this month":
                sql_file = 'winners_this_month.sql'
            else:
                sql_file = 'winners_today.sql'
            params = ()  # No parameters needed for winners
        elif game == "my_scores":
            if date_range and date_range.lower() == "this month":
                sql_file = 'my_scores_this_month.sql'
            else:
                sql_file = 'my_scores_today.sql'
            params = (interaction.user.name,)
        else:
            if date_range and date_range.lower() == "this month":
                sql_file = 'leaderboard_this_month.sql'
            else:
                sql_file = 'leaderboard_today.sql'
            params = (game,)  # Use the game name as the parameter

        # Construct the full path to the SQL file
        print(f"leaderboards.py: sql_file is {sql_file}")
        sql_file_path = direct_path_finder('files', 'queries', sql_file)

        # Check if the SQL file exists
        if not os.path.exists(sql_file_path):
            error_message = f"Error: SQL file '{sql_file}' not found."
            print(error_message)
            if interaction:
                await interaction.followup.send(error_message)
            return error_message

        # Read the SQL query from the file
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            query = file.read()

        # Debugging print statements
        print(f"Executing SQL Query for game: {game}")

        # get the leaderboard
        df = await get_df_from_sql(query, params)

        # Check if DataFrame is empty
        if df.empty:
            print(f"No data returned for game: {game}")
        else:
            print(f"Data retrieved for game: {game}")
            print(f"DataFrame Shape: {df.shape}")

        if not df.empty:
            print("DataFrame is not empty, proceeding to format leaderboard.")
            
            # format leaderboard
            print("Converting DataFrame to image...")
            
            try:
                # Create image filepath - using a single file that gets overwritten
                img_dir = direct_path_finder('files', 'images')
                os.makedirs(img_dir, exist_ok=True)  # Create directory if it doesn't exist
                img_filepath = os.path.join(img_dir, 'leaderboard.png')
                
                # Convert DataFrame to image
                img_path = df_to_image(
                    df=df,
                    img_filepath=img_filepath,
                    img_title=f"{game.capitalize()} Leaderboard",
                    img_subtitle=f"{date_range.capitalize()}"
                )
                
                print(f"leaderboards.py: image created at {img_path}")
                
                # Send the image
                if interaction:
                    print("Sending image via interaction followup...")
                    await interaction.followup.send(file=discord.File(img_path))
                    print("Image sent successfully via interaction.")
                    return None
                
                # if called programmatically, return the image path
                print("Returning image path programmatically.")
                return img_path

            except Exception as e:
                error_message = f"Error generating leaderboard image: {str(e)}"
                print(error_message)
                # Fallback to text-based leaderboard
                leaderboard = df.to_string(index=False)
                message = f"{game.capitalize()} Leaderboard\n{date_range.capitalize()}\n```\n{leaderboard}\n```"
                
                if interaction:
                    await interaction.followup.send(message)
                return message
        
        else:
            message = f"No data available for {game} leaderboard."

        print(f"leaderboards.py: now going to try to send message")
        try:
            # if called via command interaction, send the message as a reply
            if interaction:
                print("Sending message via interaction followup...")
                await interaction.followup.send(message)
                print("Message sent successfully via interaction.")
                return None
            
            # if called programmatically, return the message
            print("Returning message programmatically.")
            return message
        
        except Exception as e:
            print(f"show_leaderboard: Exception occurred - {e}")
            raise

async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically