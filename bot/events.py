import discord

# Define the on_ready event
async def on_ready(client: discord.Client):
    print(f'{client.user} has connected to Discord!')
    for guild in client.guilds:
        print(f"Connected to guild: {guild.name} (id: {guild.id})")
    
    # sync commands
    try:
        await client.tree.sync()  # Sync the command tree
        print("Synced commands:")
        commands = await client.tree.fetch_commands()
        for command in commands:
            print(f"- {command.name}: {command.description}")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Define the on_message event
async def on_message(client: discord.Client, message: discord.Message):
    if message.author == client.user:
        return
    print(f"Message from {message.author}: {message.content}")

# Register event listeners
def setup_events(client: discord.Client):
    client.event(on_ready)
    client.event(on_message)