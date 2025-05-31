import discord
from discord import app_commands
from bot.functions.timezone_warnings import (
    set_user_timezone, 
    get_user_timezone, 
    get_next_warning_times,
    get_common_timezones,
    normalize_timezone
)
from bot.connections.logging_config import get_logger, log_exception

# Get logger for timezone commands
timezone_commands_logger = get_logger('timezone_commands')

class TimezoneCommands:
    def __init__(self, client: discord.Client, tree: app_commands.CommandTree):
        self.client = client
        self.tree = tree

    @app_commands.command(name="set_timezone", description="Set your timezone for mini crossword warnings")
    @app_commands.describe(timezone="Your timezone (e.g., America/New_York, EST, Europe/Amsterdam)")
    async def set_timezone(self, interaction: discord.Interaction, timezone: str):
        """Set user's timezone preference for mini warnings."""
        try:
            user_id = interaction.user.id
            success = await set_user_timezone(user_id, timezone)
            
            if success:
                normalized_tz = normalize_timezone(timezone)
                warning_info = await get_next_warning_times(user_id, target_hour=12)
                
                embed = discord.Embed(
                    title="✅ Timezone Set Successfully!",
                    description=f"Your timezone has been set to **{normalized_tz}**",
                    color=0x00ff00
                )
                
                if warning_info:
                    embed.add_field(
                        name="Current Local Time",
                        value=warning_info['current_local_time'],
                        inline=False
                    )
                    embed.add_field(
                        name="Next Mini Warning",
                        value=f"12:00 PM in your timezone\n({warning_info['next_warning_time']})",
                        inline=False
                    )
                
                embed.set_footer(text="You'll now receive mini warnings at 12:00 PM in your local time!")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                timezone_commands_logger.info(f"User {interaction.user.name} ({user_id}) set timezone to {normalized_tz}")
                
            else:
                embed = discord.Embed(
                    title="❌ Invalid Timezone",
                    description=f"'{timezone}' is not a valid timezone.",
                    color=0xff0000
                )
                
                common_timezones = get_common_timezones()
                timezone_list = "\n".join([f"• {tz}" for tz in common_timezones[:10]])
                
                embed.add_field(
                    name="Common Timezones",
                    value=timezone_list,
                    inline=False
                )
                
                embed.add_field(
                    name="Examples",
                    value="• America/New_York (Eastern)\n• Europe/Amsterdam (Netherlands)\n• Asia/Tokyo (Japan)",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                timezone_commands_logger.warning(f"User {interaction.user.name} ({user_id}) tried invalid timezone: {timezone}")
                
        except Exception as e:
            log_exception(timezone_commands_logger, e, f"setting timezone for user {interaction.user.id}")
            await interaction.response.send_message(
                "❌ An error occurred while setting your timezone. Please try again.",
                ephemeral=True
            )

    @app_commands.command(name="my_timezone", description="View your current timezone and next warning time")
    async def my_timezone(self, interaction: discord.Interaction):
        """Show user's current timezone and next warning time."""
        try:
            user_id = interaction.user.id
            current_timezone = await get_user_timezone(user_id)
            warning_info = await get_next_warning_times(user_id, target_hour=12)
            
            embed = discord.Embed(
                title="🕐 Your Timezone Settings",
                color=0x0099ff
            )
            
            embed.add_field(
                name="Current Timezone",
                value=current_timezone,
                inline=False
            )
            
            if warning_info:
                embed.add_field(
                    name="Your Current Local Time",
                    value=warning_info['current_local_time'],
                    inline=False
                )
                embed.add_field(
                    name="Next Mini Warning",
                    value=f"12:00 PM in your timezone\n({warning_info['next_warning_time']})",
                    inline=False
                )
            
            embed.set_footer(text="Use /set_timezone to change your timezone preference")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            timezone_commands_logger.info(f"User {interaction.user.name} ({user_id}) checked their timezone")
            
        except Exception as e:
            log_exception(timezone_commands_logger, e, f"getting timezone for user {interaction.user.id}")
            await interaction.response.send_message(
                "❌ An error occurred while getting your timezone. Please try again.",
                ephemeral=True
            )

    @app_commands.command(name="timezones", description="List common timezone options")
    async def list_timezones(self, interaction: discord.Interaction):
        """List common timezone options for users."""
        try:
            common_timezones = get_common_timezones()
            
            embed = discord.Embed(
                title="🌍 Common Timezone Options",
                description="Here are some common timezone options you can use with `/set_timezone`:",
                color=0x0099ff
            )
            
            # Split into regions
            americas = [tz for tz in common_timezones if tz.startswith('America/')]
            europe = [tz for tz in common_timezones if tz.startswith('Europe/')]
            asia = [tz for tz in common_timezones if tz.startswith('Asia/')]
            australia = [tz for tz in common_timezones if tz.startswith('Australia/')]
            
            if americas:
                embed.add_field(
                    name="🇺🇸 Americas",
                    value="\n".join([f"• {tz}" for tz in americas]),
                    inline=True
                )
            
            if europe:
                embed.add_field(
                    name="🇪🇺 Europe",
                    value="\n".join([f"• {tz}" for tz in europe]),
                    inline=True
                )
            
            if asia:
                embed.add_field(
                    name="🇯🇵 Asia",
                    value="\n".join([f"• {tz}" for tz in asia]),
                    inline=True
                )
            
            if australia:
                embed.add_field(
                    name="🇦🇺 Australia",
                    value="\n".join([f"• {tz}" for tz in australia]),
                    inline=True
                )
            
            embed.add_field(
                name="Short Forms Also Accepted",
                value="• EST, EDT, CST, CDT, MST, MDT, PST, PDT\n• GMT, UTC, CET, CEST, JST",
                inline=False
            )
            
            embed.set_footer(text="Example: /set_timezone America/New_York")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            timezone_commands_logger.info(f"User {interaction.user.name} ({interaction.user.id}) requested timezone list")
            
        except Exception as e:
            log_exception(timezone_commands_logger, e, f"listing timezones for user {interaction.user.id}")
            await interaction.response.send_message(
                "❌ An error occurred while listing timezones. Please try again.",
                ephemeral=True
            )

async def setup(client: discord.Client, tree: app_commands.CommandTree):
    """Setup function to register timezone commands."""
    timezone_cmd = TimezoneCommands(client, tree)
    
    tree.add_command(timezone_cmd.set_timezone)
    tree.add_command(timezone_cmd.my_timezone)
    tree.add_command(timezone_cmd.list_timezones)
    
    timezone_commands_logger.info("Timezone commands registered successfully") 