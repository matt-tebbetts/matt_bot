# Matt Bot

A Discord bot that tracks game scores and provides leaderboards for word games, puzzles, and more.

## 📚 Documentation

All documentation has been moved to `files/config/` for better organization:

- **[Main README](files/config/README.md)** - Bot overview, features, and how it works
- **[Deployment Guide](files/config/DEPLOYMENT.md)** - Production deployment instructions
- **[Universal Server Support](files/config/UNIVERSAL_SERVER_SUPPORT.md)** - Multi-server compatibility guide
- **[Services Documentation](files/config/services_README.md)** - Systemd service management

## 🚀 Quick Start

1. **Local Development**: `python3 bot.py` (uses TEST_BOT token)
2. **Production**: Deploy to Linux server (uses MATT_BOT token)
3. **Configuration**: See `files/config/` for all settings

## 🎮 Supported Games

The bot automatically detects and tracks scores for games defined in `files/config/games.json`, including:
- Wordle, Worldle, Connections
- Crosswordle, Actorle, Octordle variants
- Pips (Easy/Medium/Hard), Mini Crossword
- And many more...

## 🔧 Key Features

- **Automatic Score Detection**: Recognizes game posts and saves scores
- **Dynamic Leaderboards**: Generates `/command` for each game  
- **Universal Server Support**: Works on any Discord server without manual setup
- **Smart Ranking**: Handles different scoring types (time, guesses, points)
- **Emoji Reactions**: Reacts to scores with appropriate game emojis
