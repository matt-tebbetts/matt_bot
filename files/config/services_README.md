# Matt Bot Systemd Services

This directory contains systemd service files for automating Matt Bot operations on a Linux server.

## Services Overview

### `matt_bot.service`
- **Purpose**: Main Discord bot service that runs continuously
- **Type**: Simple service (keeps running)
- **Features**: Handles Discord events, commands, and scheduled tasks
- **Auto-restart**: Yes, on failure

## Installation

### Prerequisites
1. Linux server with systemd
2. Matt Bot project cloned to server
3. Python virtual environment set up
4. Environment variables configured in `.env`

### Quick Install
```bash
# Run as root for system-wide installation
sudo ./install.sh

# Or run as user for user-specific installation
./install.sh
```

### Manual Installation
1. Copy service files to systemd directory
2. Update `%PROJECT_DIR%` placeholders with actual path
3. Reload systemd daemon
4. Enable and start services

## Configuration

### Environment Variables
Your `.env` file should contain:
- `MATT_BOT`: Discord bot token for production
- `TEST_BOT`: Discord bot token for testing
- Database connection variables
- OpenAI API key

### Server Configuration
The server details are configured in `files/config/remote_server_config.json`:
- Server IP address: 199.19.75.180
- SSH connection info
- Project paths

## Service Management

### Status Checks
```bash
# Check service status
sudo systemctl status matt_bot.service

# View real-time logs
sudo journalctl -f -u matt_bot.service
```

### Start/Stop/Restart
```bash
# Start the bot
sudo systemctl start matt_bot.service

# Stop the bot
sudo systemctl stop matt_bot.service

# Restart the bot
sudo systemctl restart matt_bot.service

# Enable auto-start on boot
sudo systemctl enable matt_bot.service
```

### Manual Testing
```bash
# Test the bot manually
sudo systemctl start matt_bot.service
```

## Monitoring

### Log Files
- **systemd journal**: `journalctl -u matt_bot.service`
- **Application logs**: Logged to systemd journal with timestamps

### Health Checks
The bot includes internal health monitoring:
- Discord connection status
- Database connectivity
- Task execution status
- Memory and performance metrics

## Troubleshooting

### Common Issues
1. **Service won't start**: Check file permissions and project path
2. **Bot disconnects**: Check Discord token and network connectivity
3. **Database errors**: Verify database server connectivity

### Debug Mode
Set `DEBUG_MODE=true` in `.env` for verbose logging.

### Service Logs
```bash
# View recent logs
sudo journalctl -u matt_bot.service --since "1 hour ago"

# Follow logs in real-time
sudo journalctl -f -u matt_bot.service

# View all logs for today
sudo journalctl -u matt_bot.service --since today
```

## Security

### Service Isolation
- **PrivateTmp**: Yes (isolated temp directory)
- **NoNewPrivileges**: Yes (prevents privilege escalation)
- **Memory limits**: 512M max
- **CPU limits**: 25% max

### File Permissions
Service files should be:
- Owner: root:root
- Permissions: 644
- Location: `/etc/systemd/system/` (system-wide)

## Updates

### Updating the Bot
1. Pull latest code changes
2. Install any new dependencies
3. Restart the service:
   ```bash
   sudo systemctl restart matt_bot.service
   ```

### Updating Service Files
1. Edit service files in this directory
2. Run install script again
3. Reload and restart:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart matt_bot.service
   ``` 