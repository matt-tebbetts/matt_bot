import os
import discord
import asyncio
from bot.commands import hello

# bot setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
token = os.getenv("MATT_BOT")

# command setup
tree = discord.app_commands.CommandTree(client)
tree.command(name="hello", description="Says hello")(hello)

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

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
