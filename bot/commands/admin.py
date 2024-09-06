from discord import app_commands, Interaction
from discord.ext import commands

class Admin:
    print("admin.py: running __init__")
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="ban", description="Ban a user")
    async def ban(self, interaction: Interaction, user: str):
        print(f"admin.py: Ban command invoked for user: {user}")
        await interaction.response.send_message(f"User {user} has been banned.")

    @app_commands.command(name="unban", description="Unban a user")
    async def unban(self, interaction: Interaction, user: str):
        print(f"admin.py: Unban command invoked for user: {user}")
        await interaction.response.send_message(f"User {user} has been unbanned.")

async def setup(client, tree):
    print("admin.py: setup activated")
    admin = Admin(client)
    tree.add_command(admin.ban)
    tree.add_command(admin.unban)
    print("admin.py: Admin commands added to tree")