from discord import app_commands, Interaction
from discord.ext import commands
from bot.functions import get_df_from_sql
from datetime import datetime

class Leaderboards(commands.Cog):
    print("leaderboards.py: running __init__")
    def __init__(self, client):
        self.client = client

    async def on_ready(self):
        print("leaderboards.py: successfully ran on_ready")

    @app_commands.command(name="mini", description="Show Mini leaderboard")
    async def mini(self, interaction: Interaction):
        print("leaderboards.py: running mini")
        await self.show_leaderboard(interaction, "mini")

    @app_commands.command(name="octordle", description="Show Octordle leaderboard")
    async def octordle(self, interaction: Interaction):
        print("leaderboards.py: running octordle")
        await self.show_leaderboard(interaction, "octordle")

    @app_commands.command(name="wordle", description="Show Wordle leaderboard")
    async def wordle(self, interaction: Interaction):
        print("leaderboards.py: running wordle")
        await self.show_leaderboard(interaction, "wordle")

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
    print("leaderboards.py: Setting up Leaderboards commands")
    leaderboards = Leaderboards(client)
    tree.add_command(leaderboards.mini)
    tree.add_command(leaderboards.octordle)
    tree.add_command(leaderboards.wordle)
    print("leaderboards.py: Leaderboards commands added to tree")