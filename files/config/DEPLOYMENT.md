# Matt Bot Deployment Guide

This guide explains how to deploy the Matt Bot to the production server using systemd services.

## Server Information

- **Production Server**: 199.19.75.180
- **Username**: root
- **Project Path**: `/root/projects/matt_bot`
- **Database Server**: 52.144.45.121

## Prerequisites

1. Linux server with systemd (Ubuntu/Debian/CentOS)
2. Python 3.8+ installed
3. Git installed
4. Access to the production server via SSH

## Deployment Steps

### 1. Connect to Server
```bash
ssh root@199.19.75.180
```

### 2. Clone Repository
```bash
cd /root/projects
git clone https://github.com/your-username/matt_bot.git
cd matt_bot
```

### 3. Set Up Python Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Your `.env` file should already contain:
```bash
# Discord Bot Tokens
MATT_BOT=your_production_discord_bot_token_here
TEST_BOT=your_test_discord_bot_token_here

# Database Configuration
DB_HOST=52.144.45.121
DB_USER=your_database_username
DB_PASS=your_database_password
DB_NAME=your_database_name

# OpenAI API (for GPT commands)
OPENAI_API_KEY=your_openai_api_key_here

# Debug Mode (optional)
DEBUG_MODE=false
```

### 5. Install Systemd Services
```bash
cd services
sudo ./install.sh
```

This will:
- Install `matt_bot.service` (main Discord bot)
- Enable and start the service
- Set up automatic restart on failure

### 6. Verify Installation
```bash
# Check service status
sudo systemctl status matt_bot.service

# View real-time logs
sudo journalctl -f -u matt_bot.service

# Check if bot is responding in Discord
# Try a command like /leaderboard mini
```

## Service Management

### Common Commands
```bash
# Start the bot
sudo systemctl start matt_bot.service

# Stop the bot
sudo systemctl stop matt_bot.service

# Restart the bot
sudo systemctl restart matt_bot.service

# View logs
sudo journalctl -u matt_bot.service --since "1 hour ago"

# Follow logs in real-time
sudo journalctl -f -u matt_bot.service
```

### Updating the Bot
```bash
cd /root/projects/matt_bot
git pull origin main
pip install -r requirements.txt
sudo systemctl restart matt_bot.service
```

## Monitoring

### Health Checks
The bot includes several monitoring features:
- **Discord connection status**: Automatically reconnects on failure
- **Database connectivity**: Handles connection errors gracefully
- **Task execution**: Scheduled tasks run independently

### Log Files
- **systemd journal**: `journalctl -u matt_bot.service`
- **Service logs**: Logged to systemd journal with timestamps

### Performance Limits
- **Memory**: 512MB maximum
- **CPU**: 25% maximum
- **Restart policy**: Always restart on failure
- **Rate limiting**: 10 second delay between restarts

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs for errors
   sudo journalctl -u matt_bot.service --since "10 minutes ago"
   
   # Verify file permissions
   ls -la /root/projects/matt_bot/
   
   # Test bot manually
   cd /root/projects/matt_bot
   source .venv/bin/activate
   python bot.py
   ```

2. **Bot disconnects frequently**
   ```bash
   # Check network connectivity
   ping discord.com
   
   # Verify Discord token
   grep MATT_BOT .env
   
   # Check for rate limiting in logs
   sudo journalctl -u matt_bot.service | grep -i "rate"
   ```

3. **Database connection errors**
   ```bash
   # Test database connectivity
   mysql -h 52.144.45.121 -u username -p
   
   # Check database credentials in .env
   grep DB_ .env
   ```

### Debug Mode
Enable debug mode for verbose logging:
```bash
echo "DEBUG_MODE=true" >> .env
sudo systemctl restart matt_bot.service
```

## Security

### Service Isolation
- **PrivateTmp**: Isolated temporary directory
- **NoNewPrivileges**: Prevents privilege escalation
- **Resource limits**: Memory and CPU constraints
- **User isolation**: Runs as root (can be changed for better security)

### File Permissions
- Service files: 644 (readable by all, writable by owner)
- Scripts: 755 (executable)
- Config files: 600 (readable by owner only)

## Backup and Recovery

### Important Files to Backup
- `.env` (environment variables)
- `files/` directory (bot data and configurations)

### Recovery Process
1. Restore files from backup
2. Reinstall services: `sudo ./services/install.sh`
3. Restart services: `sudo systemctl restart matt_bot.service`

## Support

For issues or questions:
1. Check the logs first: `sudo journalctl -u matt_bot.service`
2. Review this deployment guide
3. Test components individually
4. Check Discord and database connectivity 