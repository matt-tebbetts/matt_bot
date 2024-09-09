import json
import os
from discord import app_commands, Interaction
from discord.ext import commands
from bot.functions import get_df_from_sql
from datetime import datetime

class Leaderboards(commands.Cog):
    def __init__(self, client):
        self.client = client
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
        app_command = app_commands.Command(name=name, description=description)(command)
        self.client.tree.add_command(app_command)

    async def show_leaderboard(self, interaction: Interaction, game: str):
        await interaction.response.defer()
        query = f"SELECT game_rank as rnk, player, score FROM matt.leaderboards WHERE game_name = '{game}'"
        print(f"leaderboards.py: running show_leaderboard with query: {query}")
        df = await get_df_from_sql(query)
        print(f"leaderboards.py: got the data: {df}")
        if df.empty:
            await interaction.followup.send(f"No data available for {game} leaderboard.")
        else:
            print(f"leaderboards.py: building message")
            title = f"{game.capitalize()} Leaderboard"
            subtitle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            leaderboard = df.to_string(index=False)
            message = f"**{title}**\n*{subtitle}*\n```\n{leaderboard}\n```"
            print(f"leaderboards.py: Sending message: {message}")
            try:
                await interaction.followup.send(message)
                print("leaderboards.py: Message sent successfully.")
            except Exception as send_error:
                print(f"leaderboards.py: Error sending message: {send_error}")

async def setup(client, tree):
    leaderboards = Leaderboards(client)
    # No need to manually add commands here, they are added dynamically