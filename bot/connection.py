import os
import discord
import asyncio

# bot setup
intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
token = os.getenv("MATT_BOT")

# first command
@tree.command(name="hello", description="Says hello")
async def hello(interaction: discord.Interaction):
    print(f"activated the hello command!")
    await interaction.response.send_message("Hello!")

@client.event
async def on_ready():

    # Print the bot's name and guilds
    print(f'{client.user} has connected to Discord!')

    for guild in client.guilds:
        print(f"Connected to guild: {guild.name} (id: {guild.id})")

    # sync commands
    try:
        await tree.sync()
        print("Synced commands:")
        commands = await tree.fetch_commands()  # if you use fetch_commands()
        for command in commands:
            print(f"- {command.name}: {command.description}")

    except Exception as e:
        print(f"Error syncing commands: {e}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    print(f"Message from {message.author}: {message.content}")

async def main():
    async with client:
        await client.start(token)

def run_bot():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot has been stopped manually.")
