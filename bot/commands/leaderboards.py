import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from bot.functions import get_df_from_sql
from datetime import datetime

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

        # Add the new /my_scores command
        if not self.tree.get_command("my_scores"):
            self.create_my_scores_command()

    def create_command(self, name, description):
        async def command(interaction: discord.Interaction):
            print(f"leaderboards.py: running command '{name}'")
            await self.show_leaderboard(game=name, interaction=interaction)

        command.__name__ = name
        app_command = app_commands.Command(name=name, description=description, callback=command)
        self.tree.add_command(app_command)

    def create_my_scores_command(self):
        async def my_scores_command(interaction: discord.Interaction):
            print(f"leaderboards.py: running my_scores for {interaction.user.name}")
            await self.show_my_scores(interaction=interaction)

        my_scores_command.__name__ = "my_scores"
        app_command = app_commands.Command(name="my_scores", description="Show your scores", callback=my_scores_command)
        self.tree.add_command(app_command)
        print(f"leaderboards.py: added command my_scores")

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

    async def get_my_scores(self, discord_name: str):
        query = f"SELECT * FROM games.my_scores WHERE discord_nm = '{discord_name}'"
        df = await get_df_from_sql(query)
        if df.empty:
            print(f"leaderboards.py: no data for {discord_name} in my_scores")
            return "No data available for your scores."

        # format my_scores
        title = f"{discord_name}'s Scores"
        subtitle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        my_scores = df.to_string(index=False)
        my_scores_as_string = f"**{title}**\n*{subtitle}*\n```\n{my_scores}\n```"
        return my_scores_as_string

    async def show_leaderboard(self, game: str = None,
                               interaction: discord.Interaction = None, 
                               guild: discord.Guild = None):
        print(f"leaderboards.py: entered show_leaderboard for {guild.name} with game {game}")

        if interaction:
            await interaction.response.defer()
            # respond to interaction, telling them it's loading
            await interaction.followup.send("Loading leaderboard...")

        # get the leaderboard
        query = f"SELECT game_rank as rnk, player, score FROM matt.leaderboards WHERE game_name = '{game}'"
        df = await get_df_from_sql(query)

        if not df.empty:
            # format leaderboard
            df['rnk'] = df['rnk'].fillna(-1).astype(int).replace(-1, '-').astype(str)
            title = f"{game.capitalize()} Leaderboard"
            subtitle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            leaderboard = df.to_string(index=False)
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

    async def show_my_scores(self, interaction: discord.Interaction):
        print(f"leaderboards.py: entered show_my_scores for {interaction.user.name}")

        await interaction.response.defer()

        my_scores_as_string = await self.get_my_scores(interaction.user.name)
        print(f"leaderboards.py: got my_scores string for {interaction.user.name}")

        await interaction.followup.send(my_scores_as_string)

async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically