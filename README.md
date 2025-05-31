# Matt Bot - Discord GPT Integration

A Discord bot that integrates with OpenAI's GPT-4 to analyze Discord conversations and answer questions about server activity, user interactions, and message history.

## Overview

This bot allows Discord users to ask ChatGPT questions about their server's conversations using the `/gpt` command. The bot intelligently determines whether a question needs Discord message context and provides relevant answers based on actual chat history.

## Key Features

- **Smart Context Detection**: Automatically determines if questions need Discord message history
- **Message Analysis**: Analyzes real Discord messages to answer questions about users, conversations, and server activity
- **Token Management**: Tracks usage and costs with daily totals
- **Multi-Channel Support**: Can analyze messages across different channels
- **User Personality Analysis**: Can describe user personalities based on their messages

## How It Works

### The `/gpt` Command Flow

1. **User Input**: User types `/gpt <prompt>` in Discord
2. **Prompt Analysis**: Bot analyzes if the prompt needs Discord message context using GPT-4
3. **Message Loading**: If context needed, loads messages from `messages.json`
4. **Response Generation**: Sends formatted messages + prompt to ChatGPT
5. **Response Display**: Shows ChatGPT's response with token/cost info

### Context Detection

The bot determines if a prompt needs message context by checking for keywords like:
- `summarize`, `conversation`, `messages`, `chat`, `discussion`, `talk`
- `what happened`, `what was said`, `personality`, `user`, `says`
- `describe`, `about`, `people`

## Recent Fixes (Important!)

### Problem Solved: "I don't have access to messages"

**Issue**: ChatGPT was responding with "I don't have access to Discord messages" even though the bot was correctly loading and sending message history.

**Root Cause**: The system prompt was too vague and didn't clearly establish that ChatGPT was looking at real Discord messages.

**Solution Applied**:
1. **Updated System Prompt** (`files/gpt/system_prompt.txt`):
   - Made explicit that ChatGPT is analyzing "real Discord messages"
   - Added instruction to "Never say you don't have access to messages"
   - Clarified that it should answer personality/conversation questions based on actual messages

2. **Enhanced Keyword Detection**: Added personality-related keywords (`personality`, `user`, `describe`, `about`, `people`) to trigger message context

3. **Improved Analysis Prompt** (`files/gpt/analysis_prompt.txt`):
   - Added explicit instruction that user personality questions need context
   - Clarified that questions about Discord users always need message context

## File Structure

```
bot/
├── commands/
│   └── gpt.py                 # Main GPT integration logic
├── functions/
│   ├── df_to_image.py        # DataFrame to image conversion
│   └── admin.py              # Admin utilities (direct_path_finder)
└── connections/
    └── config.py             # Configuration settings

files/
├── config/
│   ├── games.json           # Game configuration and settings
│   ├── gpt_models.json      # Model costs and configuration
│   └── sms_carriers.json    # SMS carrier configurations
├── gpt/
│   ├── system_prompt.txt     # Main system prompt template
│   ├── analysis_prompt.txt   # Prompt analysis template
│   ├── analysis_system_prompt.txt
│   ├── gpt_history.json     # Usage logs and history
│   └── prompts/             # Debug prompt logs
└── guilds/
    └── [guild_name]/
        ├── messages.json    # Discord message history
        └── config.json      # Guild configuration
```

## Key Classes and Methods

### `GPT` Class (`bot/commands/gpt.py`)

- **`analyze_prompt()`**: Determines if prompt needs message context using GPT-4
- **`get_gpt_response()`**: Generates response with or without Discord context
- **`filter_messages()`**: Filters messages by date (24 hours) and token limit (5000 tokens)
- **`log_prompt_analysis()`**: Logs all interactions for tracking and debugging

### Important Configuration

- **Token Limits**: 
  - Message context: 5000 tokens max
  - Total request: 7000 tokens max (with fallback trimming)
- **Date Range**: Only includes last 24 hours of messages
- **Model**: Uses `gpt-4-1106-preview` for responses
- **Response Length**: 500 token limit to encourage concise answers

## Message Format

Discord messages are formatted for ChatGPT as:
```
[channel_name] timestamp username: message content
```

Example:
```
[general] 2024-01-15 10:30:15 acowinthecrowd: This is a great discussion!
[things-we-watch] 2024-01-15 10:35:22 Matt: Just watched Dune, visuals were amazing
```

## Troubleshooting

### If ChatGPT says "I don't have access to messages":

1. **Check the system prompt** in `files/gpt/system_prompt.txt` - should explicitly state it's analyzing real Discord messages
2. **Verify keyword detection** - ensure conversation/personality keywords trigger context
3. **Check message loading** - verify `messages.json` exists and contains recent messages
4. **Review debug logs** - check `files/gpt/prompts/` for actual prompts sent to ChatGPT

### If context isn't being triggered:

1. **Add keywords** to the conversation_keywords lists in `gpt.py` (lines ~278 and ~442)
2. **Check analysis prompt** - ensure it recognizes the question type in `files/gpt/analysis_prompt.txt`
3. **Review analysis logs** in `files/gpt/gpt_history.json` to see needs_context decisions

### Common Issues:

- **Token limit exceeded**: Increase `max_tokens` in `filter_messages()` or improve message filtering
- **No messages found**: Check if `messages.json` is being updated by message collection system
- **Analysis errors**: Check JSON parsing in `analyze_prompt()` method

## Usage Examples

```
/gpt summarize what acowinthecrowd says and describe his personality
/gpt what happened in #general today?
/gpt what movies are people talking about?
/gpt who's been most active in discussions?
```

## Future Improvements

- Add user-specific filtering (currently filters by channel/date only)
- Implement message search by keywords
- Add conversation threading/context tracking
- Optimize token usage with better message summarization

## Development Notes

- The bot loads all prompts from text files for easy editing
- All interactions are logged to `gpt_history.json` with full details
- Debug prompts are saved to `files/gpt/prompts/` for troubleshooting
- The system supports multiple Discord servers (guilds) with separate configs

---

**Last Updated**: After multiple iterations fixing the "no access to messages" issue:
- Updated system prompts to be more forceful and explicit
- Added clear headers to message data to mark it as "REAL MESSAGES"  
- Used directive language like "YOU HAVE BEEN PROVIDED" and "DO NOT say you lack access"