import json
import os
from datetime import datetime, timedelta
import discord
from discord import app_commands
from bot.functions.admin import direct_path_finder
import openai
from typing import Optional, Dict, List, Tuple
import pytz

class GPT:
    def __init__(self, client, tree):
        self.client = client
        self.tree = tree
        self.load_command()
        
    def load_command(self):
        async def gpt_command(interaction: discord.Interaction, prompt: str):
            print(f"/gpt called by {interaction.user.name} in {interaction.guild.name}")
            try:
                await interaction.response.defer()
                
                # First, analyze if this prompt needs message context
                needs_context, analysis, filter_params = await self.analyze_prompt(prompt)
                
                # Get the final response
                if needs_context:
                    # Load messages if needed
                    guild_name = interaction.guild.name
                    messages_file = direct_path_finder('files', 'guilds', guild_name, 'messages.json')
                    with open(messages_file, 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                    
                    # Get response with context
                    response = await self.get_gpt_response(
                        prompt=prompt,
                        system_prompt="You are a helpful assistant that analyzes Discord conversations. Use the provided message history to answer the user's question about the conversation.",
                        messages_data=messages,
                        filter_params=filter_params
                    )
                    message_count = len(messages)
                else:
                    # Get regular response
                    response = await self.get_gpt_response(
                        prompt=prompt,
                        filter_params=filter_params  # Pass filter_params even without context
                    )
                    message_count = 0
                
                # Log the analysis and response
                self.log_prompt_analysis(
                    interaction=interaction,
                    prompt=prompt,
                    needs_context=needs_context,
                    analysis=analysis,
                    final_response=response,
                    message_count=message_count,
                    filter_params=filter_params
                )
                
                # Get user's display name
                user_display = interaction.user.display_name
                
                await interaction.followup.send(f"**{user_display}:** {prompt}\n\n**ChatGPT:** {response}")
                
            except Exception as e:
                await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

        gpt_command.__name__ = "gpt"
        app_command = app_commands.Command(
            name="gpt",
            callback=gpt_command,
            description="Ask ChatGPT a question or about recent conversations"
        )
        self.tree.add_command(app_command)
    
    async def analyze_prompt(self, prompt: str) -> Tuple[bool, str, Dict]:
        """Analyze if the prompt needs message context and what filtering to apply.
        Returns (needs_context, analysis, filter_params)"""
        try:
            client = openai.AsyncOpenAI()
            
            analysis_prompt = """Someone just called my custom /gpt command on Discord, and I need your help to identify:
1. Whether this prompt needs Discord message context
2. What specific context filtering would be most relevant

For example:
- If they ask "what did John say about the movie yesterday?", we need messages from yesterday mentioning John and movies
- If they ask "summarize the recent discussion about games", we need recent messages about games
- If they ask "what's the most active channel?", we need message counts per channel
- If they ask "what was discussed last Tuesday?", we need messages from that specific date
- If they ask about something in "this channel", we need messages from the current channel
- If they ask about specific users or content, we need messages mentioning those users or containing that content
- If they ask about games or scores, we need messages related to those games

Please respond in this exact JSON format:
{
    "needs_context": true/false,
    "explanation": "brief explanation of why",
    "filter_params": {
        "channels": ["channel1", "channel2"] or null,
        "users": ["user1", "user2"] or null,
        "date_range": {
            "type": "relative" or "specific",
            "value": "last_hour/last_day/last_week/all" or "2024-05-23",
            "end_date": "2024-05-24" or null  # Only for specific ranges
        },
        "keywords": ["word1", "word2"] or null,
        "guild_name": "name of the guild"  # This is required
    }
}

User's prompt: """ + prompt

            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes prompts to determine if they need Discord message context and what filtering to apply."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=300,  # Shorter response needed as this just returns a structured analysis JSON
                temperature=0.3  # Lower temperature for more consistent, structured responses
            )
            
            analysis_result = json.loads(response.choices[0].message.content)
            needs_context = analysis_result["needs_context"]
            analysis = analysis_result["explanation"]
            filter_params = analysis_result["filter_params"]
            
            # Ensure guild_name is set
            if not filter_params.get('guild_name'):
                raise ValueError("GPT analysis must include guild_name in filter_params")
            
            return needs_context, analysis, filter_params
            
        except Exception as e:
            return False, f"Error in analysis: {str(e)}", {}
    
    def filter_messages(self, messages: Dict, filter_params: Dict) -> Dict:
        """Filter messages based on the provided parameters."""
        if not filter_params:
            return messages

        filtered_messages = {}
        current_time = datetime.now(pytz.timezone('US/Eastern'))
        
        for msg_id, msg in messages.items():
            # Skip if message doesn't have required fields
            if not all(k in msg for k in ['create_ts', 'channel_nm', 'author_nm', 'content']):
                continue
                
            # Apply channel filter
            if filter_params.get('channels') and msg['channel_nm'] not in filter_params['channels']:
                continue
                
            # Apply user filter
            if filter_params.get('users') and msg['author_nm'] not in filter_params['users']:
                continue
                
            # Apply date range filter
            if filter_params.get('date_range'):
                try:
                    msg_time = datetime.strptime(msg['create_ts'], '%Y-%m-%d %H:%M:%S')
                    msg_time = pytz.timezone('US/Eastern').localize(msg_time)
                    
                    date_range = filter_params['date_range']
                    
                    if date_range['type'] == 'relative':
                        time_diff = current_time - msg_time
                        if date_range['value'] == 'last_hour' and time_diff.total_seconds() > 3600:
                            continue
                        elif date_range['value'] == 'last_day' and time_diff.total_seconds() > 86400:
                            continue
                        elif date_range['value'] == 'last_week' and time_diff.total_seconds() > 604800:
                            continue
                    elif date_range['type'] == 'specific':
                        try:
                            msg_date = msg_time.date()
                            start_date = datetime.strptime(date_range['value'], '%Y-%m-%d').date()
                            if date_range.get('end_date'):
                                end_date = datetime.strptime(date_range['end_date'], '%Y-%m-%d').date()
                                if not (start_date <= msg_date <= end_date):
                                    continue
                            elif msg_date != start_date:
                                continue
                        except ValueError:
                            continue
                except Exception:
                    continue
            
            # Apply keyword filter
            if filter_params.get('keywords'):
                content_lower = msg['content'].lower()
                if not any(keyword.lower() in content_lower for keyword in filter_params['keywords']):
                    continue
            
            filtered_messages[msg_id] = msg
            
        return filtered_messages

    def log_prompt_analysis(self, interaction: discord.Interaction, prompt: str, needs_context: bool, analysis: str, final_response: str = None, message_count: int = 0, filter_params: Dict = None):
        """Log the prompt analysis to a JSON file."""
        try:
            # Get guild-specific path
            guild_name = interaction.guild.name
            log_file = direct_path_finder('files', 'guilds', guild_name, 'gpt_history.json')
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # Load existing logs or create new
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Add new log entry
            new_entry = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "user": {
                    "name": interaction.user.name,
                    "id": str(interaction.user.id),
                    "nickname": interaction.user.nick if hasattr(interaction.user, 'nick') else None,
                    "display_name": interaction.user.display_name
                },
                "guild": {
                    "name": interaction.guild.name,
                    "id": str(interaction.guild.id)
                },
                "channel": {
                    "name": interaction.channel.name,
                    "id": str(interaction.channel.id)
                },
                "message_id": str(interaction.message.id) if interaction.message else None,
                "prompt": prompt,
                "needs_context": needs_context,
                "analysis": analysis,
                "final_response": final_response,
                "context_info": {
                    "message_count": message_count,
                    "model_used": "gpt-3.5-turbo",
                    "has_messages": needs_context
                },
                "interaction_id": str(interaction.id),
                "filter_params": filter_params
            }
            
            logs.append(new_entry)
            
            # Save updated logs
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            print(f"[ERROR] Error logging prompt analysis: {str(e)}")
            print(f"[ERROR] Full error details: {str(e.__class__.__name__)}: {str(e)}")
    
    async def get_gpt_response(self, prompt: str, system_prompt: str = None, messages_data: Dict = None, filter_params: Dict = None) -> str:
        """Get a response from OpenAI's GPT model."""
        try:
            client = openai.AsyncOpenAI()
            
            # Get guild config for context
            guild_name = filter_params.get('guild_name') if filter_params else None
            if not guild_name:
                raise ValueError("Guild name is required for GPT responses")
                
            config_path = direct_path_finder('files', 'guilds', guild_name, 'config.json')
            guild_config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    guild_config = json.load(f)
            
            # Prepare base system prompt with guild context
            base_system_prompt = system_prompt or """You are Matt_Bot, a Discord bot powered by ChatGPT that can answer questions about this Discord server or about anything in the world. Keep your answers short and sweet. Be as direct as possible. Don't praise the prompt or add unnecessary commentary.

As a Discord bot, you have direct access to server metadata through config.json which contains information about channels and users. You can also access message history through messages.json when needed. The process works in two steps:
1. First, your prompt is analyzed to determine if it needs message context and what filters to apply
2. Then, you receive the relevant context (server info, message history if needed) to provide an informed response

When users ask about the server, channels, or users, you MUST use the config data provided in your context. Do not say you don't have access to this information - you do! The config data is provided in your system prompt.

For example, if someone asks about channels or users, you should list them from the config data provided in your context. Do not say you can't access this information or that you need message history to answer these questions.

Remember that you are a Discord bot - you can reference your own capabilities and access to server data when relevant, but keep responses concise and focused on what the user asked."""
            
            # Always add guild context
            if guild_config:
                context = f"""\n\nSERVER INFORMATION:
Server Name: {guild_config['guild_name']}

Available Channels:
{', '.join([ch['name'] for ch in guild_config['channels']])}

Known Users:
{', '.join([f"{u['display_name']} ({u['name']})" for u in guild_config['users']])}

This information is from your config.json file. You MUST use this information when asked about the server, channels, or users."""
                base_system_prompt += context
            
            # Prepare messages for the API call
            messages = [
                {"role": "system", "content": base_system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # If we have message data, filter and format efficiently
            if messages_data:
                filtered_messages = self.filter_messages(messages_data, filter_params)
                
                # Format messages efficiently
                formatted_messages = []
                for msg in filtered_messages.values():
                    # Only include essential fields
                    formatted_msg = {
                        "author": msg['author_nm'],
                        "channel": msg['channel_nm'],
                        "time": msg['create_ts'],
                        "content": msg['content']
                    }
                    formatted_messages.append(formatted_msg)
                
                # Sort by timestamp
                formatted_messages.sort(key=lambda x: x['time'])
                
                # Convert to a more compact format
                message_text = "\n".join([
                    f"[{msg['time']}] {msg['author']} in #{msg['channel']}: {msg['content']}"
                    for msg in formatted_messages
                ])
                
                # Add message history to system prompt
                messages[0]["content"] += f"\n\nHere are the relevant messages to analyze:\n{message_text}"
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using GPT-3.5 Turbo for cost efficiency
                messages=messages,
                max_tokens=500,  # Reduced to ~375-500 words to stay well within Discord's 2000 character limit
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"Failed to get response from GPT: {str(e)}")

async def setup(client, tree):
    gpt = GPT(client, tree)