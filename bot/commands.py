import discord

# Define and register slash commands
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hey, {interaction.user}!")

def setup_commands(tree: discord.app_commands.CommandTree):
    tree.add_command(
        discord.app_commands.Command(name="hello", description="Say hello!", callback=hello)
    )
