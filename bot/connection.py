import os
import discord
from discord.ext import tasks
import asyncio
from jobs.warnings.new_warning import find_users_to_warn  # Import the function

# bot setup
intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
token = os.getenv("MATT_BOT")

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

    # start task
    send_warning_loop.start()

## tasks
@tasks.loop(hours=1)
async def send_warning_loop():
    print("Checking and sending Mini warnings...")
    users_to_warn = await find_users_to_warn(client)
    
    results = []

    for user in users_to_warn:
        try:
            await send_dm(user['discord_id_nbr'], f'Hi {user["name"]}, this is your reminder to complete the Mini!')
            results.append({'user': user['name'], 'status': 'Message sent'})
        except discord.Forbidden:
            results.append({'user': user['name'], 'status': 'Not in guild'})
        except Exception as e:
            results.append({'user': user['name'], 'status': f'Error: {e}'})

    print("Summary of actions taken:")
    for result in results:
        print(f"- {result['user']}: {result['status']}")

@send_warning_loop.before_loop
async def before_send_warning_loop():
    await client.wait_until_ready()
## /tasks

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    print(f"Message from {message.author}: {message.content}")

async def send_dm(user_id: int, message: str):
    user = await client.fetch_user(user_id)
    if user:
        await user.send(message)
        print(f"Message sent to user {user.name}")

async def main():
    async with client:
        await client.start(token)

def run_bot():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot has been stopped manually.")
