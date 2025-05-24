import json
import os
from datetime import datetime, timedelta
import discord
from discord import app_commands
from bot.functions.admin import direct_path_finder
import openai
from typing import Optional, Dict, List, Tuple
import pytz
import tiktoken
import re

class GPT:
    def __init__(self, client, tree):
        self.client = client
        self.tree = tree
        self.load_command()
        
        # Load prompts
        self.analysis_prompt_template = self._load_prompt('analysis_prompt.txt')
        self.analysis_system_prompt = self._load_prompt('analysis_system_prompt.txt')
        self.system_prompt_template = self._load_prompt('system_prompt.txt')
        self.summary_prompt_template = self._load_prompt('summary_prompt.txt')
        
        # Initialize tokenizer
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        
        # Load model costs
        self.model_costs = self._load_model_costs()
        
    def _load_model_costs(self) -> Dict:
        """Load model costs from gpt_models.json."""
        try:
            cost_file = direct_path_finder('files', 'gpt_models.json')
            with open(cost_file, 'r', encoding='utf-8') as f:
                return json.load(f)['models']
        except Exception as e:
            print(f"Error loading model costs: {str(e)}")
            return {}
        
    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(self.encoding.encode(text))
        
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost of a GPT request."""
        if model not in self.model_costs:
            return 0.0
            
        costs = self.model_costs[model]
        input_cost = (input_tokens / 1000) * costs['input_cost']
        output_cost = (output_tokens / 1000) * costs['output_cost']
        return input_cost + output_cost
        
    def _trim_messages_to_token_limit(self, messages: List[Dict], max_tokens: int = 7000) -> List[Dict]:
        """Trim messages to fit within token limit, keeping the most recent ones."""
        total_tokens = sum(self._count_tokens(msg["content"]) for msg in messages)
        
        if total_tokens <= max_tokens:
            return messages
            
        # Always keep the system prompt and user's question
        system_prompt = messages[0]
        user_question = messages[-1]
        
        # Get message history (everything in between)
        message_history = messages[1:-1]
        
        # Calculate tokens for system prompt and user question
        base_tokens = self._count_tokens(system_prompt["content"]) + self._count_tokens(user_question["content"])
        remaining_tokens = max_tokens - base_tokens
        
        # Start with most recent messages and work backwards
        trimmed_history = []
        current_tokens = 0
        
        for msg in reversed(message_history):
            msg_tokens = self._count_tokens(msg["content"])
            if current_tokens + msg_tokens <= remaining_tokens:
                trimmed_history.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        # Reconstruct the messages list
        return [system_prompt] + trimmed_history + [user_question]
        
    def _load_prompt(self, filename: str) -> str:
        """Load a prompt template from file."""
        prompt_path = direct_path_finder('files', 'gpt', filename)
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading prompt {filename}: {str(e)}")
            return ""
        
    def load_command(self):
        async def gpt_command(interaction: discord.Interaction, prompt: str):
            print(f"/gpt called by {interaction.user.name} in {interaction.guild.name}")
            try:
                await interaction.response.defer()
                
                # First, analyze if this prompt needs message context
                needs_context, analysis, filter_params = await self.analyze_prompt(
                    prompt=prompt,
                    guild_name=interaction.guild.name,
                    current_channel=interaction.channel.name
                )
                
                # Get the final response
                if needs_context:
                    # Load messages if needed
                    guild_name = interaction.guild.name
                    messages_file = direct_path_finder('files', 'guilds', guild_name, 'messages.json')
                    with open(messages_file, 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                    
                    # Get response with context
                    response, input_tokens, output_tokens = await self.get_gpt_response(
                        prompt=prompt,
                        system_prompt="You are a helpful assistant that analyzes Discord conversations. Use the provided message history to answer the user's question about the conversation.",
                        messages_data=messages,
                        filter_params=filter_params
                    )
                    message_count = len(messages)
                else:
                    # Get regular response
                    response, input_tokens, output_tokens = await self.get_gpt_response(
                        prompt=prompt,
                        filter_params=filter_params  # Pass filter_params even without context
                    )
                    message_count = 0
                
                # Calculate total tokens and cost
                total_tokens = input_tokens + output_tokens
                cost = self._calculate_cost("gpt-4", input_tokens, output_tokens)
                
                # Log the analysis and response
                self.log_prompt_analysis(
                    interaction=interaction,
                    prompt=prompt,
                    needs_context=needs_context,
                    analysis=analysis,
                    final_response=response,
                    message_count=message_count,
                    filter_params=filter_params,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost
                )
                
                # Get user's display name
                user_display = interaction.user.display_name
                
                # Add token count and cost to response
                token_info = f"\n\n[Tokens: {input_tokens} in, {output_tokens} out, {total_tokens} total | Cost: ${cost:.4f}]"
                await interaction.followup.send(f"**{user_display}:** {prompt}\n\n**ChatGPT:** {response}{token_info}")
                
            except Exception as e:
                await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

        gpt_command.__name__ = "gpt"
        app_command = app_commands.Command(
            name="gpt",
            callback=gpt_command,
            description="Ask ChatGPT a question or about recent conversations"
        )
        self.tree.add_command(app_command)
    
    async def analyze_prompt(self, prompt: str, guild_name: str, current_channel: str) -> Tuple[bool, str, Dict]:
        """Analyze if the prompt needs message context and what filtering to apply.
        Returns (needs_context, analysis, filter_params)"""
        try:
            client = openai.AsyncOpenAI()
            
            # Get guild config to know available channels
            config_path = direct_path_finder('files', 'guilds', guild_name, 'config.json')
            guild_config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    guild_config = json.load(f)
            
            # Get list of available channels
            available_channels = [ch['name'] for ch in guild_config.get('channels', [])]
            channels_info = f"Available channels: {', '.join(available_channels)}"
            
            # Format the analysis prompt with the user's prompt and channel info
            analysis_prompt = self.analysis_prompt_template.format(
                prompt=prompt,
                channels_info=channels_info
            )

            response = await client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for better analysis
                messages=[
                    {"role": "system", "content": self.analysis_system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            analysis_result = json.loads(response.choices[0].message.content)
            needs_context = analysis_result["needs_context"]
            analysis = analysis_result["explanation"]
            filter_params = analysis_result["filter_params"]
            
            # Ensure required fields are set
            filter_params['guild_name'] = guild_name
            
            # If channels were suggested by GPT, use those
            if filter_params.get('channels'):
                # Validate that suggested channels exist
                valid_channels = [ch for ch in filter_params['channels'] if ch in available_channels]
                if valid_channels:
                    filter_params['channels'] = valid_channels
                    filter_params['current_channel'] = valid_channels[0]  # Use first valid channel as current
                else:
                    # If no valid channels were suggested, default to current
                    filter_params['channels'] = [current_channel]
                    filter_params['current_channel'] = current_channel
            else:
                # Default to current channel if no channels suggested
                filter_params['channels'] = [current_channel]
                filter_params['current_channel'] = current_channel
            
            return needs_context, analysis, filter_params
            
        except Exception as e:
            # For conversation-related queries, default to using context
            conversation_keywords = ['summarize', 'conversation', 'messages', 'chat', 'discussion', 'talk']
            prompt_lower = prompt.lower()
            
            # Check if the prompt is about conversations
            is_conversation_query = any(keyword in prompt_lower for keyword in conversation_keywords)
            
            # Default to using context for conversation queries
            needs_context = is_conversation_query
            
            return needs_context, f"Error in analysis: {str(e)}", {
                'guild_name': guild_name,
                'current_channel': current_channel,
                'channels': [current_channel]
            }
    
    def filter_messages(self, messages: Dict, filter_params: Dict) -> Dict:
        """Filter messages based on the provided parameters."""
        if not filter_params:
            return messages

        filtered_messages = {}
        current_time = datetime.now(pytz.timezone('US/Eastern'))
        cutoff_time = current_time - timedelta(days=7)  # Only include last 7 days
        
        # First pass: basic validation and date filtering
        for msg_id, msg in messages.items():
            # Skip if message doesn't have required fields
            if not all(k in msg for k in ['create_ts', 'channel_nm', 'author_nm', 'content', 'author_nick']):
                continue
                
            # Apply date filter (last 7 days)
            try:
                msg_time = datetime.strptime(msg['create_ts'], '%Y-%m-%d %H:%M:%S')
                msg_time = pytz.timezone('US/Eastern').localize(msg_time)
                if msg_time < cutoff_time:
                    continue
            except Exception:
                continue
            
            filtered_messages[msg_id] = msg
        
        # Sort by timestamp (most recent first)
        sorted_msgs = sorted(
            filtered_messages.values(),
            key=lambda x: datetime.strptime(x['create_ts'], '%Y-%m-%d %H:%M:%S'),
            reverse=True
        )
        
        # Keep as many messages as possible within token limit
        filtered_messages = {}
        current_tokens = 0
        max_tokens = 6000  # Leave room for system prompt and response
        
        for msg in sorted_msgs:
            # Estimate tokens for this message (author + content)
            msg_tokens = self._count_tokens(f"{msg['author_nick']}: {msg['content']}")
            
            # If adding this message would exceed token limit, stop
            if current_tokens + msg_tokens > max_tokens:
                break
                
            # Find the original message ID and add to filtered messages
            for msg_id, original_msg in messages.items():
                if (original_msg['create_ts'] == msg['create_ts'] and 
                    original_msg['content'] == msg['content'] and 
                    original_msg['author_nick'] == msg['author_nick']):
                    filtered_messages[msg_id] = msg
                    current_tokens += msg_tokens
                    break
            
        return filtered_messages

    def log_prompt_analysis(self, interaction: discord.Interaction, prompt: str, needs_context: bool, analysis: str, final_response: str = None, message_count: int = 0, filter_params: Dict = None, input_tokens: int = 0, output_tokens: int = 0, total_tokens: int = 0, cost: float = 0.0):
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
                    "model_used": "gpt-4",
                    "has_messages": needs_context,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost
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
    
    async def get_gpt_response(self, prompt: str, system_prompt: str = None, messages_data: Dict = None, filter_params: Dict = None) -> Tuple[str, int, int]:
        """Get a response from OpenAI's GPT model.
        Returns (response, input_tokens, output_tokens)"""
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
            
            # Prepare guild info
            guild_info = ""
            if guild_config:
                guild_info = f"""Name: {guild_config['guild_name']}
Channels: {', '.join([ch['name'] for ch in guild_config['channels']])}
Users: {', '.join([u['display_name'] for u in guild_config['users']])}"""
            
            # Get current channel
            current_channel = filter_params.get('current_channel', 'unknown')
            
            # Check if this is a conversation summary request
            is_summary_request = any(keyword in prompt.lower() for keyword in ['summarize', 'summary', 'what happened', 'what was said'])
            
            # Use appropriate system prompt
            if is_summary_request and messages_data:
                custom_system_prompt = self.summary_prompt_template
            else:
                custom_system_prompt = system_prompt if system_prompt else ""
            
            # Format the system prompt
            base_system_prompt = self.system_prompt_template.format(
                guild_info=guild_info,
                current_channel=current_channel,
                custom_prompt=custom_system_prompt
            )
            
            # Prepare messages for the API call
            messages = [
                {"role": "system", "content": base_system_prompt}
            ]
            
            # If we have message data, filter and format efficiently
            if messages_data:
                filtered_messages = self.filter_messages(messages_data, filter_params)
                
                # Sort messages by timestamp
                sorted_messages = sorted(
                    filtered_messages.values(),
                    key=lambda x: datetime.strptime(x['create_ts'], '%Y-%m-%d %H:%M:%S')
                )
                
                # Format messages efficiently
                formatted_messages = []
                for msg in sorted_messages:
                    if msg['content'].strip():  # Only include non-empty messages
                        # More compact format for messages
                        formatted_msg = f"{msg['author_nick']}: {msg['content']}"
                        formatted_messages.append(formatted_msg)
                
                # Convert to a more compact format
                message_text = "\n".join(formatted_messages)
                
                # Add message history as a separate message
                messages.append({
                    "role": "system",
                    "content": f"Here is the message history to analyze:\n\n{message_text}"
                })
            
            # Add the user's prompt
            messages.append({"role": "user", "content": prompt})
            
            # Count input tokens
            input_tokens = sum(self._count_tokens(msg["content"]) for msg in messages)
            
            # If we're still over the limit, use the trim function as a fallback
            if input_tokens > 7000:
                messages = self._trim_messages_to_token_limit(messages)
                input_tokens = sum(self._count_tokens(msg["content"]) for msg in messages)
            
            response = await client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for better responses
                messages=messages,
                max_tokens=1000 if is_summary_request else 500,  # Allow longer responses for summaries
                temperature=0.7
            )
            
            # Get output tokens
            output_tokens = self._count_tokens(response.choices[0].message.content)
            
            return response.choices[0].message.content, input_tokens, output_tokens
            
        except Exception as e:
            raise Exception(f"Failed to get response from GPT: {str(e)}")

async def setup(client, tree):
    gpt = GPT(client, tree)