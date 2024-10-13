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

        # this creates the static leaderboard commands
        for game_name, game_info in games_data.items():
            command_name = game_info["game_name"]
            command_description = f"Show {command_name.capitalize()} leaderboard"
            existing_command = self.tree.get_command(command_name)
            if existing_command:
                self.tree.remove_command(existing_command)
            self.create_command(command_name, command_description)

        # this creates the dynamic commands for the views
        views = {
            "my_scores": "Show your scores for today",
            "winners": "Show winners for today"
            # Add more views here as needed
        }

        for command_name, description in views.items():
            print(f"leaderboards.py: processing command {command_name}")  # Debug statement
            existing_command = self.tree.get_command(command_name)
            if existing_command:
                self.tree.remove_command(existing_command)
            self.create_dynamic_command(command_name, description)

    def create_command(self, name, description):
        async def command(interaction: discord.Interaction):
            print(f"leaderboards.py: running command '{name}'")
            await self.show_leaderboard(game=name, interaction=interaction)

        command.__name__ = name
        app_command = app_commands.Command(name=name, description=description, callback=command)
        self.tree.add_command(app_command)

    def create_dynamic_command(self, name, description):
        async def dynamic_command(interaction: discord.Interaction):
            print(f"leaderboards.py: running {name} for {interaction.user.name}")
            await self.show_view_data(view_name=name, interaction=interaction)

        dynamic_command.__name__ = name
        app_command = app_commands.Command(name=name, description=description, callback=dynamic_command)
        self.tree.add_command(app_command)
        print(f"leaderboards.py: added command {name}")  # Debug statement

    async def get_view_data(self, view_name: str, discord_name: str = None):
        print(f"leaderboards.py: entered get_view_data with view_name={view_name}, discord_name={discord_name}")  # Debug statement

        if view_name == "my_scores":
            query = f"SELECT game, score, rnk FROM games.my_scores WHERE discord_nm = '{discord_name}'"
        
        if view_name == "winners":
            query = f"SELECT game, winner, score, players FROM games.winners_today"

        df = await get_df_from_sql(query)

        if df.empty:
            print(f"leaderboards.py: no data in {view_name} for {discord_name if discord_name else 'view'}")
            return f"No data available for {view_name.replace('_', ' ')}."

        # format data
        df.rename(columns={"rnk": "rank"}, inplace=True)
        title = f"{view_name.replace('_', ' ').capitalize()}"
        subtitle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = df.to_string(index=False)
        data_as_string = f"**{title}**\n*{subtitle}*\n```\n{data}\n```"
        return data_as_string

    async def show_view_data(self, view_name: str, interaction: discord.Interaction):
        await interaction.response.defer()
        data_as_string = await self.get_view_data(view_name, interaction.user.name)
        await interaction.followup.send(data_as_string)

    async def show_leaderboard(self, game: str = None, interaction: discord.Interaction = None):
        print(f"leaderboards.py: entered show_leaderboard with game {game}")

        if interaction:
            await interaction.response.defer()

        # get the leaderboard
        query = f"SELECT rnk, player, score FROM games.leaderboard_today WHERE game = '{game}'"
        df = await get_df_from_sql(query)
        print(f"leaderboards.py: fetched data for {game} leaderboard")

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
            if interaction:
                await interaction.followup.send(message)
                print(f"leaderboards.py: sent leaderboard message for {game}")

            # if called programmatically, return the message
            print(f"leaderboards.py: returning leaderboard message for {game}")
            return message
        
        except Exception as e:
            print(f"show_leaderboard: Exception occurred - {e}")
            raise


async def setup(client, tree):
    leaderboards = Leaderboards(client, tree)
    # No need to manually add commands here, they are added dynamically