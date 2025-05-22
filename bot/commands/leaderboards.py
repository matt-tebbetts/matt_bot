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
                         timeframe: Literal["today", "yesterday", "this month", "last month", "this year", "all time"] = "today",
                         specific_date: Optional[str] = None):
            print(f"leaderboards.py: running command '{name}' with timeframe '{timeframe}'")
            if specific_date:
                print(f"leaderboards.py: using specific date '{specific_date}'")
            await self.show_leaderboard(game=name, interaction=interaction, timeframe=timeframe, specific_date=specific_date)

        command.__name__ = name
        app_command = app_commands.Command(
            name=name,
            callback=command,
            description=description
        )
        self.tree.add_command(app_command)

    def get_date_range(self, timeframe: str, specific_date: Optional[str] = None) -> Tuple[datetime, datetime]:
        today = datetime.now().date()
        
        # If specific date is provided, use that instead of timeframe
        if specific_date:
            try:
                target_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
                return target_date, target_date
            except ValueError:
                raise ValueError("Invalid date format. Please use YYYY-MM-DD")

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
                             timeframe: Optional[str] = 'today', specific_date: Optional[str] = None) -> str:
        try:
            # Determine if this is an interaction or a programmatic call
            if interaction:
                await interaction.response.defer()
                user = interaction.user
            else:
                user = None

            # Get date range
            start_date, end_date = self.get_date_range(timeframe, specific_date)
            
            # Determine if we need daily scores or aggregate stats
            if timeframe in ["today", "yesterday"] or specific_date:
                # Use daily scores query
                sql_file = "game_daily_scores.sql"
                params = [start_date, game]
            else:
                # Use aggregate stats query
                sql_file = "game_aggregate_stats.sql"
                params = [start_date, end_date, game]

            sql_file_path = direct_path_finder('files', 'queries', 'active', sql_file)

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
            df = await execute_query(query, params)

            # Check if DataFrame is empty
            if df.empty:
                if interaction:
                    await interaction.followup.send(f"No data available for {game}")
                return f"No data available for {game}"

            # Format the leaderboard based on query type
            if timeframe == "today":
                leaderboard = self.format_daily_leaderboard(df, game)
            else:
                leaderboard = self.format_aggregate_leaderboard(df, game, timeframe)

            # Handle the response based on whether it's an interaction or programmatic call
            if interaction:
                # Try to create and send an image first
                try:
                    img_path = df_to_image(df, f"{game} Leaderboard")
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

    def format_daily_leaderboard(self, df: pd.DataFrame, game: str) -> str:
        # Format for daily scores
        lines = [f"**{game.capitalize()} Leaderboard - {df['game_date'].iloc[0].strftime('%Y-%m-%d')}**"]
        for _, row in df.iterrows():
            lines.append(f"{row['game_rank']}. {row['player_name']}: {row['game_score']} ({row['seconds']}s)")
        return "\n".join(lines)

    def format_aggregate_leaderboard(self, df: pd.DataFrame, game: str, timeframe: str) -> str:
        # Format for aggregate stats
        lines = [f"**{game.capitalize()} Leaderboard - {timeframe.title()}**"]
        for _, row in df.iterrows():
            lines.append(
                f"{row['rank']}. {row['player_name']}: "
                f"{row['total_points']} pts, "
                f"{row['games_played']} games, "
                f"avg {row['avg_seconds']}s, "
                f"best {row['best_time']}s, "
                f"{row['wins']} wins"
            )
        return "\n".join(lines)

async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically