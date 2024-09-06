from discord import app_commands, Interaction
from discord.ext import commands
from functions.sql_helper import get_df_from_sql

class Leaderboards(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Leaderboards cog loaded")

    @app_commands.command(name="mini", description="Show Mini leaderboard")
    async def mini(self, interaction: Interaction):
        await self.show_leaderboard(interaction, "mini")

    @app_commands.command(name="octordle", description="Show Octordle leaderboard")
    async def octordle(self, interaction: Interaction):
        await self.show_leaderboard(interaction, "octordle")

    @app_commands.command(name="wordle", description="Show Wordle leaderboard")
    async def wordle(self, interaction: Interaction):
        await self.show_leaderboard(interaction, "wordle")

    async def show_leaderboard(self, interaction: Interaction, game: str):
        await interaction.response.defer()
        query = f"SELECT * FROM matt.{game}_leaderboard"
        df = await get_df_from_sql(query)
        if df.empty:
            await interaction.followup.send(f"No data available for {game} leaderboard.")
        else:
            leaderboard = df.to_string(index=False)
            await interaction.followup.send(f"```\n{leaderboard}\n```")

async def setup(client, tree):
    print("Setting up Leaderboards commands")
    leaderboards = Leaderboards(client)
    tree.add_command(leaderboards.mini)
    tree.add_command(leaderboards.octordle)
    tree.add_command(leaderboards.wordle)
    print("Leaderboards commands added to tree")