import json
import os
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ext import commands
from bot.functions.admin import direct_path_finder
import openai
from typing import Optional, Dict, List

class GPT(commands.Cog):
    def __init__(self, client, tree):
        self.client = client
        self.tree = tree
        self.load_command()
        
    def load_command(self):
        @self.tree.command(
            name="gpt",
            description="Ask ChatGPT a question or get context-aware responses about recent messages"
        )
        async def gpt_command(interaction: discord.Interaction, prompt: str):
            try:
                # Defer the response since this might take a moment
                await interaction.response.defer()
                
                # Get the guild's message history
                guild_name = interaction.guild.name
                messages_file = direct_path_finder('files', 'guilds', guild_name, 'messages.json')
                
                # Load messages
                with open(messages_file, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                
                # Check if the prompt is asking about recent messages
                if any(word in prompt.lower() for word in ['what', 'who', 'when', 'where', 'why', 'how']):
                    # Get recent messages (last 50 messages)
                    recent_messages = self.get_recent_messages(messages, limit=50)
                    
                    # Create context from recent messages
                    context = self.create_message_context(recent_messages)
                    
                    # Add context to the prompt
                    enhanced_prompt = f"""Recent messages in the channel:
{context}

User question: {prompt}

Please provide a helpful response, using the message context if relevant."""
                else:
                    enhanced_prompt = prompt
                
                # Get response from OpenAI
                response = await self.get_gpt_response(enhanced_prompt)
                
                # Send the response
                await interaction.followup.send(response)
                
            except Exception as e:
                print(f"Error in GPT command: {str(e)}")
                await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
    
    def get_recent_messages(self, messages: Dict, limit: int = 50) -> List[Dict]:
        """Get the most recent messages, sorted by timestamp."""
        # Convert messages to list and sort by timestamp
        message_list = list(messages.values())
        message_list.sort(key=lambda x: x['create_ts'], reverse=True)
        
        # Return the most recent messages
        return message_list[:limit]
    
    def create_message_context(self, messages: List[Dict]) -> str:
        """Create a readable context from recent messages."""
        context = []
        for msg in messages:
            # Skip bot messages and empty messages
            if msg['author_is_bot'] or not msg['content'].strip():
                continue
                
            # Format the message
            timestamp = datetime.strptime(msg['create_ts'], '%Y-%m-%d %H:%M:%S')
            formatted_time = timestamp.strftime('%I:%M %p')
            author = msg['author_nick'] or msg['author_nm']
            channel = msg['channel_nm']
            
            context.append(f"[{formatted_time}] {author} in #{channel}: {msg['content']}")
        
        return "\n".join(context)
    
    async def get_gpt_response(self, prompt: str) -> str:
        """Get a response from OpenAI's GPT model."""
        try:
            # Initialize OpenAI client
            client = openai.AsyncOpenAI()
            
            # Get response from GPT
            response = await client.chat.completions.create(
                model="gpt-4-turbo-preview",  # or your preferred model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that can answer questions and provide context-aware responses based on recent messages in a Discord channel."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error getting GPT response: {str(e)}")
            raise Exception(f"Failed to get response from GPT: {str(e)}")

async def setup(client, tree):
    gpt = GPT(client, tree)