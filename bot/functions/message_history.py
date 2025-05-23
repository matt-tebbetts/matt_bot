import json
import os
from typing import Dict, List, Tuple
from bot.functions.admin import direct_path_finder
from bot.functions.save_scores import is_game_score, process_game_score

async def collect_recent_messages(channel) -> Tuple[int, int]:
    """Collect recent messages from a channel and save any new ones to messages.json.
    Returns tuple of (new_messages_count, game_scores_count)"""
    try:
        # Get the messages file path
        guild_name = channel.guild.name
        messages_file = direct_path_finder('files', 'guilds', guild_name, 'messages.json')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(messages_file), exist_ok=True)
        
        # Load existing messages
        existing_messages = {}
        if os.path.exists(messages_file):
            with open(messages_file, 'r', encoding='utf-8') as f:
                existing_messages = json.load(f)
        
        # Get recent messages from Discord
        new_messages = {}
        game_score_count = 0
        async for message in channel.history(limit=100):  # Can adjust limit up to 2000
            # Skip if we already have this message
            if str(message.id) in existing_messages:
                continue
                
            # Skip bot messages and empty messages
            if message.author.bot or not message.content.strip():
                continue
            
            # Add new message
            new_messages[str(message.id)] = {
                "content": message.content,
                "author_nm": message.author.name,
                "author_nick": message.author.display_name,
                "channel_nm": channel.name,
                "create_ts": message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }

            # Check if it's a game score before processing
            is_score, game_name, game_info = is_game_score(message.content)
            if is_score:
                try:
                    score_result = await process_game_score(message)
                    if score_result:
                        game_score_count += 1
                        
                        # Add confirmation emoji
                        confirmation_emoji = game_info.get('emoji', '✅')
                        await message.add_reaction(confirmation_emoji)

                        # Add bonus emojis if any
                        game_bonuses = score_result.get('game_bonuses')
                        if game_bonuses:
                            bonus_emojis = game_info.get('bonus_emojis', {})
                            bonuses_list = game_bonuses.split(', ')
                            for bonus in bonuses_list:
                                if bonus in bonus_emojis:
                                    await message.add_reaction(bonus_emojis[bonus])
                except Exception as e:
                    print(f"[ERROR] Error processing game score: {str(e)}")
        
        # Save new messages if any were found
        if new_messages:
            existing_messages.update(new_messages)
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump(existing_messages, f, indent=2)
            
        return len(new_messages), game_score_count
            
    except Exception as e:
        print(f"[ERROR] Error collecting messages: {str(e)}")
        return 0, 0

async def initialize_message_history(client) -> None:
    """Initialize message history collection for all channels the bot can see."""
    try:
        print("\n[DEBUG] Starting message history initialization...")
        total_messages = 0
        total_scores = 0
        
        for guild in client.guilds:
            print(f"[DEBUG] Processing guild: {guild.name}")
            for channel in guild.text_channels:
                # Skip channels the bot can't read
                if not channel.permissions_for(guild.me).read_messages:
                    print(f"[DEBUG] Skipping channel {channel.name} - no read permissions")
                    continue
                    
                print(f"[DEBUG] Collecting messages from {channel.name}")
                messages, scores = await collect_recent_messages(channel)
                total_messages += messages
                total_scores += scores
                print(f"[DEBUG] Collected {messages} messages and {scores} scores from {channel.name}")
        
        if total_messages > 0:
            print(f"✓ Saved {total_messages} historical messages including {total_scores} game scores")
        else:
            print("✓ No new messages to save")
        
    except Exception as e:
        print(f"[ERROR] Error initializing message history: {str(e)}")
        print(f"[ERROR] Full error details: {str(e.__class__.__name__)}: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}") 