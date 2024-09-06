import discord
from bot.tasks import setup_tasks

# Register event listeners
def setup_events(client, tree):

    # on ready
    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        for guild in client.guilds:
            print(f"Connected to guild: {guild.name}")

        # sync commands
        try:
            await tree.sync()
            print("Synced commands:")
            commands = await tree.fetch_commands()
            for command in commands:
                print(f"-- {command.name}: {command.description}")
        except Exception as e:
            print(f"Error syncing commands: {e}")

        # start background tasks
        setup_tasks(client)

    # on message
    @client.event
    async def on_message(message):
        print("on_message activated")
        if message.author == client.user:
            return
        print(f"Message from {message.author}: {message.content}")
