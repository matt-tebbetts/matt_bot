import os
from dotenv import load_dotenv
import asyncio
import discord
from discord import app_commands
from bot.connections.events import setup_events
from bot.connections.config import BOT_TOKEN, DEBUG_MODE
from bot.connections.logging_config import setup_logging, get_logger, log_exception, log_asyncio_context

# Setup logging first
logger = setup_logging(debug_mode=DEBUG_MODE)
main_logger = get_logger('main')

# setup
intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# main
async def main():
    try:
        main_logger.info("Starting bot initialization...")
        log_asyncio_context()
        
        # config
        main_logger.info("Setting up events and handlers...")
        await setup_events(client, tree)

        # connect
        main_logger.info(f"Connecting to Discord with token ending in ...{BOT_TOKEN[-4:] if BOT_TOKEN else 'NONE'}")
        await client.start(BOT_TOKEN)
        main_logger.info("Bot started successfully")
        
    except Exception as e:
        log_exception(main_logger, e, "main bot startup")
        main_logger.critical("Bot startup failed, exiting...")
        raise

# run the bot
if __name__ == "__main__":
    try:
        main_logger.info("="*50)
        main_logger.info("MATT BOT STARTING UP")
        main_logger.info("="*50)
        asyncio.run(main())
    except KeyboardInterrupt:
        main_logger.info("Bot shutdown requested by user")
    except Exception as e:
        log_exception(main_logger, e, "bot main execution")
        main_logger.critical("Bot crashed during execution")
    finally:
        main_logger.info("Bot execution finished")

