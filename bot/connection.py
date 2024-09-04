import os
import discord
import asyncio

# bot setup
intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
token = os.getenv("MATT_BOT")

async def send_dm(user_id: int, message: str):
    user = await client.fetch_user(user_id)
    if user:
        try:
            await user.send(message)
            print(f"Message sent to user {user.name}")
        except Exception as e:
            print(f"Failed to send message: {e}")

# Example command to trigger DM sending
@tree.command(name="senddm", description="Send a direct message to a user")
async def send_dm_command(interaction: discord.Interaction, 
                          user_id: int, message: str):
    await send_dm(user_id, message)
    await interaction.response.send_message(f"DM sent to user {user_id}")

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
