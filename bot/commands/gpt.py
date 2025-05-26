import json
import os
from datetime import datetime
import discord
from discord import app_commands
from bot.functions.admin import direct_path_finder
from bot.connections.config import DEBUG_MODE, BOT_NAME, SYSTEM_NAME
import openai
from typing import Dict, List, Tuple
import tiktoken
import re

class GPT:
    def __init__(self, client, tree):
        self.client = client
        self.tree = tree
        self.load_command()
        
        # Load prompts
        self.system_prompt_template = self._load_prompt('system_prompt.txt')
        
        # Initialize tokenizer
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        
        # Load model costs
        self.model_costs = self._load_model_costs()
        
    def _load_model_costs(self) -> Dict:
        """Load model costs from gpt_models.json."""
        try:
            cost_file = direct_path_finder('files', 'gpt', 'gpt_models.json')
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
        total_cost = input_cost + output_cost
        # Round up to nearest penny
        return round(total_cost + 0.005, 2)
        
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
            
            # Temporary disable - return early with message
            await interaction.response.send_message("Sorry, this command is temporarily disabled because I'm a stupid, idiotic robot who can't do basic text analysis. 🔧", ephemeral=False)
            return
            
            try:
                await interaction.response.defer()
                
                # Always load messages and provide context
                guild_name = interaction.guild.name
                
                # Simple filter params
                filter_params = {
                    'guild_name': guild_name,
                    'current_channel': interaction.channel.name
                }
                
                # Get response with context
                response, input_tokens, output_tokens, message_count, request_id = await self.get_gpt_response(
                    prompt=prompt,
                    filter_params=filter_params,
                    interaction=interaction
                )
                
                # Calculate total tokens and cost
                total_tokens = input_tokens + output_tokens
                cost = self._calculate_cost("gpt-4", input_tokens, output_tokens)
                
                # Log the response
                self.log_prompt_analysis(
                    interaction=interaction,
                    message_count=message_count,
                    filter_params=filter_params,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    request_id=request_id
                )
                
                # Get user's display name
                user_display = interaction.user.display_name
                
                # Load daily totals from history file
                history_file = direct_path_finder('files', 'gpt', 'gpt_history.json')
                daily_tokens = 0
                daily_cost = 0.0
                if os.path.exists(history_file):
                    with open(history_file, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                        current_date = datetime.now().strftime('%Y-%m-%d')
                        for log in logs:
                            if log.get('timestamp', '').startswith(current_date):
                                daily_tokens += log.get('context_info', {}).get('total_tokens', 0)
                                daily_cost += log.get('context_info', {}).get('cost', 0.0)
                
                # Round up daily cost to nearest penny
                daily_cost = round(daily_cost + 0.005, 2)
                
                # Add token count, cost, and daily totals to response
                token_info = f"\n\n[Tokens: {input_tokens} in, {output_tokens} out, {total_tokens} total | Cost: ${cost:.2f}]\n[Today: {daily_tokens} tokens, ${daily_cost:.2f}]"
                full_response = f"**{user_display}:** {prompt}\n\n**ChatGPT:** {response}{token_info}"

                # Discord message length limit
                MAX_DISCORD_MESSAGE_LENGTH = 2000
                if len(full_response) > MAX_DISCORD_MESSAGE_LENGTH:
                    full_response = full_response[:MAX_DISCORD_MESSAGE_LENGTH - 20] + "\n...[truncated]"
                await interaction.followup.send(full_response)
                
            except Exception as e:
                await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

        gpt_command.__name__ = "gpt"
        app_command = app_commands.Command(
            name="gpt",
            callback=gpt_command,
            description="Ask ChatGPT a question or about recent conversations"
        )
        self.tree.add_command(app_command)
    
    def filter_messages(self, messages: Dict, exclude_channel_names: List[str] = None) -> Dict:
        """
        Basic filter for messages:
        - Excludes specified channels (e.g., 'bot-test').
        - Excludes messages flagged as game scores.
        - Excludes messages without essential fields.
        """
        if exclude_channel_names is None:
            exclude_channel_names = ['bot-test']

        filtered_messages = {}
        total_messages = len(messages)
        excluded_channels = 0
        excluded_game_scores = 0
        excluded_missing_fields = 0
        
        for msg_id, msg in messages.items():
            # Check for required fields
            required_fields = ['create_ts', 'channel_nm', 'author_nm', 'content', 'author_nick', 'is_game_score']
            if not all(k in msg for k in required_fields):
                excluded_missing_fields += 1
                continue
                
            # Exclude bot-test and other specified channels
            channel_name = msg.get('channel_nm', '')
            if channel_name in exclude_channel_names:
                excluded_channels += 1
                continue
                
            # Exclude game scores
            if msg.get('is_game_score', False):
                excluded_game_scores += 1
                continue
                
            # Message passed all filters
            filtered_messages[msg_id] = msg
        
        # Debug output
        remaining_messages = len(filtered_messages)
        if DEBUG_MODE:
            print(f"[DEBUG] Message filtering results:")
            print(f"[DEBUG]   Total messages: {total_messages}")
            print(f"[DEBUG]   Excluded channels: {excluded_channels} (channels: {exclude_channel_names})")
            print(f"[DEBUG]   Excluded game scores: {excluded_game_scores}")
            print(f"[DEBUG]   Excluded missing fields: {excluded_missing_fields}")
            print(f"[DEBUG]   Remaining messages: {remaining_messages}")
        
        return filtered_messages

    async def _prepare_gpt_messages_from_file(self, guild_name: str, max_total_messages_to_consider: int = 10000, messages_per_channel_target: int = 100, min_messages_per_active_channel: int = 10) -> Tuple[str, int]:
        """
        Loads messages from messages.json, filters them, selects a balanced set
        from active channels, formats them, and saves to messages.txt.

        Returns:
            - Path to the messages.txt file.
            - Count of messages included.
        """
        messages_json_path = direct_path_finder('files', 'guilds', guild_name, 'messages.json')
        if not os.path.exists(messages_json_path):
            return "", 0

        with open(messages_json_path, 'r', encoding='utf-8') as f:
            all_messages_data = json.load(f)

        # Apply centralized filtering (removes game scores, bot-test, etc.)
        filtered_messages = self.filter_messages(all_messages_data)
        
        # Show filtering summary
        total_original = len(all_messages_data)
        total_filtered = len(filtered_messages)
        excluded_count = total_original - total_filtered
        # if excluded_count > 0:
        #     print(f"[FILTER] Excluded {excluded_count} messages ({total_filtered} remaining from {total_original} total)")

        # Identify channels with recent activity and count messages
        channel_message_counts = {}
        channel_recent_messages = {} 
        
        # Sort all filtered messages by timestamp to easily get recent ones
        sorted_filtered_messages = sorted(
            filtered_messages.values(),
            key=lambda x: datetime.strptime(x['create_ts'], '%Y-%m-%d %H:%M:%S'),
            reverse=True
        )
        
        # Limit to a large pool of recent messages to make processing faster
        recent_messages_pool = sorted_filtered_messages[:max_total_messages_to_consider]

        for msg in recent_messages_pool:
            channel_nm = msg['channel_nm']
            if channel_nm not in channel_message_counts:
                channel_message_counts[channel_nm] = 0
                channel_recent_messages[channel_nm] = []
            channel_message_counts[channel_nm] += 1
            channel_recent_messages[channel_nm].append(msg)

        # Sort channels by message count (most popular first)
        # Only consider channels that have at least min_messages_per_active_channel
        active_channels_sorted = sorted(
            [ch for ch, count in channel_message_counts.items() if count >= min_messages_per_active_channel],
            key=lambda ch: channel_message_counts[ch],
            reverse=True
        )

        # Format messages into messages.txt
        guild_dir = direct_path_finder('files', 'guilds', guild_name)
        os.makedirs(guild_dir, exist_ok=True)
        messages_txt_path = os.path.join(guild_dir, 'messages.txt')

        total_messages_written = 0
        with open(messages_txt_path, 'w', encoding='utf-8') as f:
            f.write("=== CONVERSATION HISTORY ===\n\n")
            
            for channel_nm in active_channels_sorted:
                # Get the latest messages_per_channel_target messages for this channel, ensure chronological order.
                # channel_recent_messages[channel_nm] contains messages sorted most recent first.
                messages_for_this_channel = list(reversed(channel_recent_messages[channel_nm][:messages_per_channel_target]))
                
                if not messages_for_this_channel:
                    continue

                f.write(f"#{channel_nm}:\n")
                
                for msg in messages_for_this_channel:
                    author_display = msg.get('author_nick') or msg.get('author_nm', 'UnknownUser')
                    content = msg.get('content', '').strip()
                    
                    # Truncate Matt_Bot responses to keep conversation flow
                    if author_display == BOT_NAME: 
                        # Completely replace content with a placeholder and character count
                        original_length = len(content)
                        content = f"(bot_response, {original_length} characters)"
                    elif author_display == SYSTEM_NAME: 
                         if len(content) > 100:
                            content = content[:100] + f"... (system_msg_truncated, {len(content)} chars)"
                    
                    if content:
                        f.write(f"{author_display}: {content}\n")
                        total_messages_written += 1
                f.write("\n")

            f.write("========================================\n")
        
        return messages_txt_path, total_messages_written

    def log_prompt_analysis(self, interaction: discord.Interaction, message_count: int = 0, filter_params: Dict = None, input_tokens: int = 0, output_tokens: int = 0, total_tokens: int = 0, cost: float = 0.0, request_id: str = None):
        """Log the prompt analysis to a JSON file."""
        try:
            # Use central history file
            log_file = direct_path_finder('files', 'gpt', 'gpt_history.json')
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # Load existing logs or create new
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Get current date for daily totals
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # Calculate daily totals
            daily_tokens = 0
            daily_cost = 0.0
            for log in logs:
                if log.get('timestamp', '').startswith(current_date):
                    daily_tokens += log.get('context_info', {}).get('total_tokens', 0)
                    daily_cost += log.get('context_info', {}).get('cost', 0.0)
            
            # Add new totals
            daily_tokens += total_tokens
            daily_cost += cost
            
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
                "request_id": request_id,
                "context_info": {
                    "message_count": message_count,
                    "model_used": "gpt-4",
                    "has_messages": True,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost,
                    "daily_tokens": daily_tokens,
                    "daily_cost": daily_cost
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
    
    async def get_gpt_response(self, prompt: str, filter_params: Dict = None, interaction = None) -> Tuple[str, int, int, int, str]:
        """Get a response from OpenAI's GPT model.
        Returns (response, input_tokens, output_tokens, message_count, request_id)"""
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
            
            # Preprocess the prompt to replace channel IDs with names
            import re
            channel_id_to_name = {str(ch['id']): ch['name'] for ch in guild_config.get('channels', []) if 'id' in ch and 'name' in ch}
            def replace_channel_id(match):
                channel_id = match.group(1)
                return f"#{channel_id_to_name.get(channel_id, channel_id)}"
            prompt = re.sub(r'<#(\d+)>', replace_channel_id, prompt)

            # Process messages using the centralized filtering method
            conversation_text_file_path, message_count = await self._prepare_gpt_messages_from_file(guild_name)
            if DEBUG_MODE:
                print(f"[DEBUG] Prepared messages.txt: {conversation_text_file_path} with {message_count} messages.")

            # Use the loaded system prompt template
            guild_info = f"Guild: {guild_name}"
            current_channel = filter_params.get('current_channel', 'unknown')
            
            system_prompt = self.system_prompt_template.format(
                guild_info=guild_info,
                current_channel=current_channel
            )

            # Prepare messages for the API call
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add the user's query
            user_display_name = interaction.user.display_name
            formatted_user_prompt = f"{user_display_name} in {guild_name}'s channel \"{current_channel}\" asks this question:\n{prompt}"
            messages.append({"role": "user", "content": formatted_user_prompt})
            
            # Add conversation history if available
            if conversation_text_file_path and os.path.exists(conversation_text_file_path) and message_count > 0:
                if DEBUG_MODE:
                    print(f"[DEBUG] Adding conversation history from {conversation_text_file_path}...")
                with open(conversation_text_file_path, 'r', encoding='utf-8') as f:
                    history_content = f.read()
                conversation_text_with_label = f"[context]:\n{history_content}"
                messages.append({"role": "user", "content": conversation_text_with_label}) 
                if DEBUG_MODE:
                    print(f"[DEBUG] Added {message_count} messages from {conversation_text_file_path} with [context] label")
            else:
                if DEBUG_MODE:
                    print(f"[DEBUG] No conversation history to add from file or message_count is 0.")
            
            if DEBUG_MODE:
                print(f"[DEBUG] Final API messages structure:")
                for i, msg in enumerate(messages):
                    print(f"[DEBUG] Message {i} ({msg['role']}): {len(msg['content'])} characters")

            # Create a unique identifier for this request
            if interaction and hasattr(interaction, 'message') and interaction.message:
                request_id = str(interaction.message.id)
            elif interaction:
                request_id = str(interaction.id)
            else:
                request_id = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Save the full prompt to a file for debugging
            prompt_dir = direct_path_finder('files', 'gpt', 'prompts')
            os.makedirs(prompt_dir, exist_ok=True)
            prompt_path = os.path.join(prompt_dir, f"prompt_{request_id}.txt")
            with open(prompt_path, 'w', encoding='utf-8') as f:
                for i, m in enumerate(messages):
                    if m['role'] == 'user' and m['content'].startswith('[context]:'):
                        f.write(f"{m['content']}\n") 
                    else:
                        f.write(f"[{m['role']}]:\n{m['content']}\n")
                    
                    if i < len(messages) - 1: 
                        f.write("\n")

            # Count input tokens
            input_tokens = sum(self._count_tokens(msg["content"]) for msg in messages)

            # If we're still over the limit, use the trim function as a fallback
            if input_tokens > 7000:
                messages = self._trim_messages_to_token_limit(messages)
                input_tokens = sum(self._count_tokens(msg["content"]) for msg in messages)

            # Load daily totals from history file
            history_file = direct_path_finder('files', 'gpt', 'gpt_history.json')
            daily_tokens = 0
            daily_cost = 0.0
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    for log in logs:
                        if log.get('timestamp', '').startswith(current_date):
                            daily_tokens += log.get('context_info', {}).get('total_tokens', 0)
                            daily_cost += log.get('context_info', {}).get('cost', 0.0)
            daily_cost = round(daily_cost + 0.005, 2)

            response = await client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )

            # Get output tokens and response text
            output_tokens = self._count_tokens(response.choices[0].message.content)
            response_text = response.choices[0].message.content
            
            # Add message count info if messages were referenced
            if message_count > 0:
                response_text += f"\n\nReferenced {message_count} messages"

            # Save the response to a file for analysis
            response_dir = direct_path_finder('files', 'gpt', 'responses')
            os.makedirs(response_dir, exist_ok=True)
            response_path = os.path.join(response_dir, f"response_{request_id}.txt")
            with open(response_path, 'w', encoding='utf-8') as f:
                f.write(f"Request ID: {request_id}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if interaction:
                    f.write(f"User: {interaction.user.name} ({interaction.user.display_name})\n")
                    f.write(f"User ID: {interaction.user.id}\n")
                f.write(f"Guild: {guild_name}\n")
                f.write(f"Channel: {current_channel}\n")
                f.write(f"Model: gpt-4-1106-preview\n")
                f.write(f"Input Tokens: {input_tokens}\n")
                f.write(f"Output Tokens: {output_tokens}\n")
                f.write(f"Total Tokens: {input_tokens + output_tokens}\n")
                f.write(f"Messages Referenced: {message_count}\n\n")
                f.write("="*60 + "\n\n")
                f.write("RESPONSE:\n")
                f.write(response_text)

            return response_text, input_tokens, output_tokens, message_count, request_id

        except Exception as e:
            print(f"[ERROR] Failed to get response from GPT: {str(e)}")
            print(f"[ERROR] Full error details: {str(e.__class__.__name__)}: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            raise Exception(f"Failed to get response from GPT: {str(e)}")

async def setup(client, tree):
    gpt = GPT(client, tree)