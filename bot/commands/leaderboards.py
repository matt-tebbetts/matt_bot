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
from typing import Optional, Tuple
# Import the actorle scraper function
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
from actorle_analysis.actorle_scraper import get_actorle_game_info, ActorleScraper

class Leaderboards(commands.Cog):
    _commands_loaded = False  # Class variable to track if commands are already loaded
    
    def __init__(self, client, tree):
        self.client = client
        self.tree = tree
        # Only load commands if they haven't been loaded yet
        if not Leaderboards._commands_loaded:
            self.load_commands()
            self.add_actorle_summary_command()
            Leaderboards._commands_loaded = True

    # this calls create_command for each game name in the games.json configuration
    def load_commands(self):
        games_file_path = direct_path_finder('files', 'config', 'games.json')
        with open(games_file_path, 'r', encoding='utf-8') as file:
            games_data = json.load(file)
            # print(f"Loaded games data: {games_data}")  # Commented out to reduce noise

        commands_created = 0
        for game_name, game_info in games_data.items():
            command_name = game_info["game_name"]
            # Special description for my_scores command
            if command_name == "my_scores":
                command_description = "Show your personal scores for a specific date (default: today)"
            else:
                command_description = f"Show {command_name.capitalize()} leaderboard"
            
            if not self.tree.get_command(command_name):
                self.create_command(command_name, command_description)
                commands_created += 1
        
        if commands_created > 0:
            print(f"✓ Created {commands_created} leaderboard commands")
        else:
            print("✓ All leaderboard commands already exist")

    # this creates a leaderboard command for each game so you can call /mini or /octordle
    def create_command(self, name, description):
        async def command(interaction: discord.Interaction,
                         timeframe: str = "today"):
            print(f"/{name} called by {interaction.user.name} in {interaction.guild.name}")
            try:
                # Defer the response immediately
                await interaction.response.defer()
                
                # Get the leaderboard
                try:
                    img_path = await self.show_leaderboard(game=name, interaction=interaction, timeframe=timeframe)
                    
                    # Send the image file
                    if os.path.exists(img_path):
                        await interaction.followup.send(file=discord.File(img_path))
                    else:
                        await interaction.followup.send(f"Error: Could not find leaderboard image at {img_path}")
                except Exception as e:
                    await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
                
            except Exception as e:
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
                    else:
                        await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
                except Exception as followup_error:
                    pass

        command.__name__ = name
        app_command = app_commands.Command(
            name=name,
            callback=command,
            description=description
        )
        app_command = app_commands.describe(timeframe="Date or timeframe (today, yesterday, this month, last month, this year, all time, or custom date like 2024-01-15)")(app_command)
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

    def parse_timeframe_or_date(self, timeframe_input: str) -> Tuple[datetime, datetime]:
        """Parse timeframe input - handles both predefined timeframes and custom dates."""
        # Normalize input
        input_lower = timeframe_input.lower().strip()
        
        # Handle predefined timeframes
        predefined_timeframes = ["today", "yesterday", "this month", "last month", "this year", "all time"]
        if input_lower in predefined_timeframes:
            return self.get_date_range(input_lower)
        
        # Try to parse as custom date - multiple formats
        date_formats = [
            '%Y-%m-%d',      # 2024-01-15
            '%m/%d/%Y',      # 1/15/2024  
            '%m-%d-%Y',      # 1-15-2024
            '%B %d %Y',      # January 15 2024
            '%b %d %Y',      # Jan 15 2024
            '%Y/%m/%d',      # 2024/01/15
            '%d-%m-%Y',      # 15-01-2024
            '%m/%d',         # 1/15 (current year)
            '%m-%d',         # 1-15 (current year)
        ]
        
        current_year = datetime.now().year
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(timeframe_input.strip(), fmt).date()
                # For formats without year, assume current year
                if parsed_date.year == 1900:  # strptime default year
                    parsed_date = parsed_date.replace(year=current_year)
                return parsed_date, parsed_date
            except ValueError:
                continue
        
        # If nothing works, default to today and raise a warning
        print(f"Warning: Could not parse '{timeframe_input}', defaulting to today")
        today = datetime.now().date()
        return today, today

    # leaderboard for any game
    async def show_leaderboard(self, interaction: Optional[discord.Interaction] = None, game: str = None, 
                             timeframe: Optional[str] = 'today') -> str:
        try:
            # Parse timeframe or custom date
            start_date, end_date = self.parse_timeframe_or_date(timeframe)
            
            # Special case for my_scores command
            if game == "my_scores":
                # For my_scores, we need to use the daily_myscores.sql query
                # and pass member_nm (discord username) and game_date as parameters
                sql_file = "daily_myscores.sql"
                if interaction:
                    # Get the discord username from the interaction
                    member_nm = interaction.user.name
                    params = [member_nm, start_date]
                else:
                    # If no interaction provided, we can't determine the user
                    raise ValueError("my_scores command requires user interaction to determine discord username")
            
            # Special case for winners - always use daily_winners.sql but show 2 weeks of games
            elif game == "winners" and timeframe.lower() in ["today", "yesterday"]:
                sql_file = "daily_winners.sql"
                params = [start_date]
            # Determine if we need daily scores or aggregate stats for other games
            elif timeframe.lower() in ["today", "yesterday"] or start_date == end_date:
                # Use daily scores query for single days
                sql_file = "daily_games.sql"
                params = [start_date, game]
            else:
                # Use aggregate stats query for date ranges
                sql_file = "game_aggregate_stats.sql"
                params = [start_date, end_date, game]

            # Check if the SQL file exists
            sql_file_path = direct_path_finder('files', 'queries', 'active', sql_file)
            if not os.path.exists(sql_file_path):
                error_message = f"Error: SQL file '{sql_file}' not found."
                print(error_message)
                return error_message

            # Read the SQL query from the file
            with open(sql_file_path, 'r', encoding='utf-8') as file:
                query = file.read()

            # Get the leaderboard
            try:
                result = await execute_query(query, params)
                df = pd.DataFrame(result)
                
                # Clean any NaN values that might have been introduced during DataFrame processing
                df = df.fillna("-")
                
                # Also clean any string representations of None/nan
                df = df.replace(['None', 'nan', 'NaN', 'null', 'NULL'], "-")
                
            except Exception as e:
                print(f"Error executing query: {str(e)}")
                return f"Error executing query: {str(e)}"

            # Check if DataFrame is empty
            if df.empty:
                print(f"No data found for {game}")
                return f"No data available for {game}"

            # Create and return the image
            try:
                # Get game detail from the first row if available - check both 'detail' and 'game_detail' columns
                game_detail = None
                detail_column = None
                
                if 'detail' in df.columns and not df.empty:
                    game_detail = df['detail'].iloc[0]
                    detail_column = 'detail'
                elif 'game_detail' in df.columns and not df.empty:
                    game_detail = df['game_detail'].iloc[0]
                    detail_column = 'game_detail'
                
                # Drop the detail column before creating the image
                if detail_column:
                    df = df.drop(columns=[detail_column])
                
                # Customize title for my_scores
                if game == "my_scores" and interaction:
                    title = f"{interaction.user.display_name}'s Scores"
                    subtitle = f"Date: {start_date}"
                else:
                    title = f"{game} Leaderboard"
                    subtitle = game_detail if game_detail else "Leaderboard"
                
                img_path = df_to_image(
                    df, 
                    "files/images/leaderboard.png", 
                    title,
                    img_subtitle=subtitle
                )
                if not os.path.exists(img_path):
                    raise FileNotFoundError(f"Image file was not created at {img_path}")
                return img_path
            except Exception as e:
                print(f"Error in image creation process: {str(e)}")
                raise Exception(f"Failed to create leaderboard image: {str(e)}")

        except Exception as e:
            error_message = f"Error showing leaderboard: {str(e)}"
            print(error_message)
            raise Exception(error_message)

    # Add the actorle_summary command
    def add_actorle_summary_command(self):
        async def actorle_summary_command(interaction: discord.Interaction):
            print(f"/actorle_summary called by {interaction.user.name} in {interaction.guild.name}")
            try:
                # Defer the response immediately
                await interaction.response.defer()
                
                # Run the actorle scraper
                try:
                    await interaction.followup.send("🎭 Scraping Actorle data...", ephemeral=True)
                    
                    # Create scraper instance and get movie data
                    scraper = ActorleScraper(headless=True)
                    try:
                        # Use the new caching system - will check cache first
                        movies = scraper.get_movie_data()
                        
                        if not movies:
                            await interaction.followup.send("❌ No movie data found", ephemeral=True)
                            return
                        
                        # Use the new method for Discord-optimized movie display
                        df_display = scraper.get_movies_for_discord(movies)
                        
                        if df_display.empty:
                            await interaction.followup.send("❌ No movie data to display", ephemeral=True)
                            return
                        
                        # Create the image
                        title = "🎭 Daily Actorle Movies"
                        subtitle = f"Sorted by Best Rating First - {datetime.now().strftime('%Y-%m-%d')}"
                        
                        img_path = df_to_image(
                            df_display, 
                            "files/images/actorle_summary.png", 
                            title,
                            img_subtitle=subtitle
                        )
                        
                        # Send the image file
                        if os.path.exists(img_path):
                            await interaction.followup.send(file=discord.File(img_path))
                        else:
                            await interaction.followup.send(f"Error: Could not find summary image at {img_path}")
                            
                    finally:
                        scraper.close()
                        
                except Exception as e:
                    await interaction.followup.send(f"Error running Actorle scraper: {str(e)}", ephemeral=True)
                
            except Exception as e:
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
                    else:
                        await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
                except Exception as followup_error:
                    pass

        # Create the app command
        actorle_summary_command.__name__ = "actorle_summary"
        app_command = app_commands.Command(
            name="actorle_summary",
            callback=actorle_summary_command,
            description="Get today's Actorle movie list sorted by best rating first"
        )
        
        # Only add if it doesn't already exist
        if not self.tree.get_command("actorle_summary"):
            self.tree.add_command(app_command)
            print("✓ Added actorle_summary command")

async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically