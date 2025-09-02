# Matt Bot

A Discord bot that tracks game scores, provides leaderboards, and integrates with GPT for intelligent chat analysis.

## 🎮 Supported Games

The bot automatically detects and tracks scores for games defined in `files/config/games.json`:
- **Word Games**: Wordle, Worldle, Connections
- **Crosswords**: Crosswordle, Mini Crossword, Octordle variants  
- **Puzzles**: Pips (Easy/Medium/Hard), Actorle
- **And many more...**

## 🔧 Key Features

### Game Score Tracking
- **Automatic Detection**: Recognizes game posts and saves scores
- **Dynamic Leaderboards**: Generates `/command` for each game  
- **Smart Ranking**: Handles different scoring types (time, guesses, points)
- **Emoji Reactions**: Reacts to scores with appropriate game emojis
- **Daily Winners**: Posts daily winners summary at 11 PM
- **Mini Crossword**: Posts final leaderboard when mini expires (6pm weekends, 10pm weekdays)

### GPT Integration (`/gpt` command)
- **Smart Context Detection**: Determines if questions need Discord message history
- **Message Analysis**: Analyzes real Discord conversations to answer questions
- **User Personality Analysis**: Describes user personalities based on messages
- **Token Management**: Tracks usage and costs with daily totals

### Universal Server Support
- **Server-Agnostic**: Works on any Discord server without manual setup
- **No Hardcoded Values**: Uses Discord usernames dynamically
- **Auto-Configuration**: Creates guild configs automatically

## 🚀 Quick Start

### Local Development
```bash
python3 bot.py  # Uses TEST_BOT token
```

### Production Deployment
```bash
# On Linux server (uses MATT_BOT token)
cd /root/projects/matt_bot
git pull
sudo systemctl restart bot.service
```

## 📁 File Structure

```
matt_bot/
├── bot/
│   ├── commands/
│   │   ├── gpt.py              # GPT integration
│   │   └── leaderboards.py     # Game leaderboards
│   ├── functions/
│   │   ├── save_scores.py      # Game score processing
│   │   ├── save_messages.py    # Score detection
│   │   └── admin.py            # Utility functions
│   └── connections/
│       ├── tasks.py            # Background tasks
│       └── config.py           # Configuration
├── files/
│   ├── config/
│   │   ├── games.json          # Game configuration
│   │   └── gpt_models.json     # GPT model costs
│   ├── gpt/
│   │   ├── system_prompt.txt   # GPT system prompt
│   │   └── gpt_history.json    # Usage logs
│   ├── queries/
│   │   ├── active/             # SQL queries
│   │   └── views/              # Database view definitions
│   └── guilds/
│       └── [guild_name]/
│           ├── messages.json   # Message history
│           └── config.json     # Guild settings
└── services/
    ├── install.sh              # Service installer
    └── matt_bot.service        # Systemd service
```

## ⚙️ Configuration

### Environment Variables (`.env`)
```bash
# Discord Bot Tokens
MATT_BOT=production_discord_bot_token
TEST_BOT=test_discord_bot_token

# Database
DB_HOST=52.144.45.121
DB_USER=username
DB_PASS=password
DB_NAME=database_name

# OpenAI API
OPENAI_API_KEY=your_openai_key

# Debug Mode
DEBUG_MODE=false
```

### Game Configuration (`files/config/games.json`)
Each game entry includes:
- `game_name`: Display name for commands
- `prefix`: Text pattern to detect
- `scoring_type`: "time", "guesses", or "points"
- `emoji`: Reaction emoji
- `difficulty`: For games with variants

## 🖥️ Deployment

### Production Server: 199.19.75.180

#### Initial Setup
```bash
# Connect to server
ssh root@199.19.75.180

# Clone repository
cd /root/projects
git clone https://github.com/your-repo/matt_bot.git
cd matt_bot

# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install systemd service
cd services
sudo ./install.sh
```

#### Updates
```bash
cd /root/projects/matt_bot
git pull origin main
sudo systemctl restart bot.service
```

#### Service Management
```bash
# Check status
sudo systemctl status bot.service

# View logs
sudo journalctl -f -u bot.service

# Restart
sudo systemctl restart bot.service
```

## 🎯 Background Tasks

The bot runs several automated tasks:

### 1. Mini Leader Detection (Every 60 seconds)
- Checks for new mini crossword leaders
- Posts announcements when someone takes the lead

### 2. Mini Reset (Every 10 minutes)  
- Resets mini leaderboard at expiration time
- Backs up final standings

### 3. Daily Mini Summary (Every 10 minutes)
- Posts mini warnings for incomplete players
- Posts final mini leaderboard at expiration time

### 4. Daily Winners Summary (Every 10 minutes)
- Posts daily winners at 11 PM
- Shows all game winners for the day

## 🤖 GPT Features

### How It Works
1. User types `/gpt <question>`
2. Bot analyzes if question needs Discord context
3. Loads relevant messages if needed
4. Sends formatted prompt to GPT-4
5. Returns response with usage stats

### Context Detection Keywords
Questions containing these trigger message context:
- `summarize`, `conversation`, `messages`, `chat`
- `what happened`, `what was said`, `personality`
- `describe`, `about`, `people`, `user`

### Message Format for GPT
```
[channel_name] timestamp username: message content
```

### Usage Examples
```
/gpt summarize what happened in #general today
/gpt describe acowinthecrowd's personality
/gpt what movies are people talking about?
/gpt who's been most active in discussions?
```

## 🛠️ Adding New Games

1. **Add to `games.json`**:
```json
{
  "new_game": {
    "game_name": "new_game",
    "prefix": "Game #",
    "scoring_type": "time",
    "emoji": "🎯"
  }
}
```

2. **Create processor function** in `save_scores.py`:
```python
def process_new_game(message):
    # Parse game score and details
    return {
        'game_score': score,
        'game_detail': detail,
        'game_bonuses': bonus
    }
```

3. **Register processor** in `get_score_info()`:
```python
game_processors = {
    'new_game': process_new_game,
    # ... other processors
}
```

## 📊 Database Views

Key database views in `files/queries/views/`:
- `game_view`: Main game statistics
- `daily_view`: Daily game summaries  
- `user_view`: User information
- `mini_view`: Mini crossword data

## 🔍 Monitoring & Logs

### Service Logs
```bash
# Recent activity
sudo journalctl -u bot.service --since "1 hour ago"

# Real-time monitoring
sudo journalctl -f -u bot.service

# Error filtering
sudo journalctl -u bot.service | grep ERROR
```

### Performance Limits
- **Memory**: 512MB maximum
- **CPU**: 25% maximum  
- **Auto-restart**: On failure with 10s delay

## 🐛 Troubleshooting

### Common Issues

**Bot won't start:**
```bash
# Check logs
sudo journalctl -u bot.service --since "10 minutes ago"

# Test manually
cd /root/projects/matt_bot
source .venv/bin/activate
python bot.py
```

**GPT says "no access to messages":**
- Check `files/gpt/system_prompt.txt` 
- Verify `messages.json` exists and has recent data
- Review debug logs in `files/gpt/prompts/`

**Database connection errors:**
```bash
# Test connection
mysql -h 52.144.45.121 -u username -p

# Check credentials
grep DB_ .env
```

### Debug Mode
```bash
echo "DEBUG_MODE=true" >> .env
sudo systemctl restart bot.service
```

## 🏆 Daily Features

### Mini Crossword (Weekdays 10pm, Weekends 6pm)
- Leader announcements throughout the day
- Warning reminders before expiration  
- Final leaderboard at expiration time

### Daily Winners (Every day 11pm)
- Comprehensive daily winners summary
- Shows winners for all games played that day
- Posted to all connected Discord servers

---

**Production Server**: 199.19.75.180 | **Database**: 52.144.45.121