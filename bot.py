import os
import discord
import asyncio

# Create a bot instance with the required intents
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)
token = os.getenv("MATT_BOT")

# example
@tree.command(name="hello", description="Says hello")
async def hello(interaction: discord.Interaction):

    # get user details
    user = interaction.user
    msg = f"Hello, {user.mention}!"

    await interaction.response.send_message(msg)

# Event to sync the slash commands with Discord
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

async def main():
    async with bot:
        await bot.start(token)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Bot has been stopped manually.")
# Run the bot

bot.run(token)
