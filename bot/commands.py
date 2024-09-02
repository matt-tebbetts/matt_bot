import discord

async def hello(interaction: discord.Interaction):
    user = interaction.user
    msg = f"Hello, {user.mention}!"
    await interaction.response.send_message(msg)
