import discord
from discord import app_commands

# Define and register slash commands
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hey, {interaction.user}!")

def setup_commands(tree: app_commands.CommandTree):
    tree.add_command(
        app_commands.Command(name="hello", description="Say hello!", callback=hello)
    )
