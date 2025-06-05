import discord
from discord import app_commands
import json
import os
from datetime import datetime
import pytz
from typing import Optional
from bot.functions.admin import direct_path_finder
from bot.connections.logging_config import get_logger, log_exception

timezone_logger = get_logger('timezone')

class Timezone:
    def __init__(self, client, tree):
        self.client = client
        self.tree = tree
        self.load_command()
        
    def load_command(self):
        async def timezone_command(
            interaction: discord.Interaction,
            hour: int = 12,
            timezone: str = "US/Eastern"
        ):
            timezone_logger.info(f"/set_mini_warning_time called by {interaction.user.name}")
            
            try:
                # Validate hour (0-23)
                if not 0 <= hour <= 23:
                    await interaction.response.send_message(
                        "❌ Hour must be between 0 and 23 (24-hour format)", 
                        ephemeral=True
                    )
                    return
                
                # Validate timezone
                try:
                    pytz.timezone(timezone)
                except pytz.exceptions.UnknownTimeZoneError:
                    await interaction.response.send_message(
                        f"❌ Invalid timezone '{timezone}'. Please use a valid timezone like 'US/Eastern', 'US/Pacific', 'UTC', etc.", 
                        ephemeral=True
                    )
                    return
                
                # Load or create users.json
                users_file_path = direct_path_finder('files', 'config', 'users.json')
                
                users_data = {}
                if os.path.exists(users_file_path):
                    with open(users_file_path, 'r', encoding='utf-8') as f:
                        users_data = json.load(f)
                
                # Update user data
                user_id = str(interaction.user.id)
                if user_id not in users_data:
                    users_data[user_id] = {}
                
                users_data[user_id].update({
                    "id": interaction.user.id,
                    "name": interaction.user.name,
                    "display_name": interaction.user.display_name,
                    "warning_hour": hour,
                    "timezone": timezone,
                    "updated_at": datetime.now().isoformat(),
                    "_comment": f"{interaction.user.display_name} ({interaction.user.name})"
                })
                
                # Save updated users.json
                with open(users_file_path, 'w', encoding='utf-8') as f:
                    json.dump(users_data, f, indent=2)
                
                # Convert hour to 12-hour format for display
                display_hour = hour
                ampm = "AM"
                if hour == 0:
                    display_hour = 12
                elif hour == 12:
                    ampm = "PM"
                elif hour > 12:
                    display_hour = hour - 12
                    ampm = "PM"
                
                timezone_logger.info(f"Updated timezone settings for {interaction.user.name}: {hour}:00 {timezone}")
                
                await interaction.response.send_message(
                    f"✅ Your mini warning time has been set to **{display_hour}:00 {ampm} {timezone}**",
                    ephemeral=True
                )
                
            except Exception as e:
                log_exception(timezone_logger, e, f"setting timezone for {interaction.user.name}")
                await interaction.response.send_message(
                    "❌ An error occurred while setting your timezone. Please try again.",
                    ephemeral=True
                )

        timezone_command.__name__ = "set_mini_warning_time"
        app_command = app_commands.Command(
            name="set_mini_warning_time",
            callback=timezone_command,
            description="Set your preferred time and timezone for mini warnings"
        )
        
        # Add parameter descriptions
        app_command = app_commands.describe(
            hour="Hour to receive warnings (0-23, default: 12 for 12pm)",
            timezone="Your timezone (default: US/Eastern). Examples: US/Pacific, UTC, Europe/London"
        )(app_command)
        
        self.tree.add_command(app_command)

async def setup(client, tree):
    timezone_cmd = Timezone(client, tree) 