#!/bin/bash

# Matt Bot Systemd Installation Script
# This script installs the systemd service files for the Matt Bot on a Linux server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default project directory - adjust as needed for your server
PROJECT_DIR="${PROJECT_DIR:-/root/projects/matt_bot}"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SYSTEMD_SYSTEM_DIR="/etc/systemd/system"

echo -e "${GREEN}Matt Bot Systemd Installation${NC}"
echo "=================================="
echo "Project directory: $PROJECT_DIR"

# Check if project directory exists
if [[ ! -d "$PROJECT_DIR" ]]; then
    echo -e "${RED}Error: Project directory $PROJECT_DIR not found!${NC}"
    echo "Please ensure the matt_bot project is cloned to the server."
    echo "You can override the path by setting PROJECT_DIR environment variable:"
    echo "  PROJECT_DIR=/path/to/matt_bot ./install.sh"
    exit 1
fi

# Check if running as root for system-wide installation
if [[ $EUID -eq 0 ]]; then
    echo -e "${YELLOW}Installing system-wide services...${NC}"
    INSTALL_DIR="$SYSTEMD_SYSTEM_DIR"
    SYSTEMCTL_CMD="systemctl"
else
    echo -e "${YELLOW}Installing user services...${NC}"
    mkdir -p "$SYSTEMD_USER_DIR"
    INSTALL_DIR="$SYSTEMD_USER_DIR"
    SYSTEMCTL_CMD="systemctl --user"
fi

# Function to install a service
install_service() {
    local service_name="$1"
    local description="$2"
    
    echo -e "${BLUE}Installing $description...${NC}"
    
    # Create temporary file with correct paths
    TEMP_SERVICE=$(mktemp)
    
    # Update service file with correct project path
    sed "s|%PROJECT_DIR%|$PROJECT_DIR|g" "$PROJECT_DIR/services/$service_name" > "$TEMP_SERVICE"
    
    # Copy service file
    cp "$TEMP_SERVICE" "$INSTALL_DIR/$service_name"
    
    # Clean up temp file
    rm "$TEMP_SERVICE"
    
    # Set proper permissions
    chmod 644 "$INSTALL_DIR/$service_name"
    
    echo "  ✓ $service_name installed"
}

# Install main bot service
install_service "matt_bot.service" "Matt Bot Main Service"

echo "Service files copied to $INSTALL_DIR"

# Reload systemd daemon
echo "Reloading systemd daemon..."
$SYSTEMCTL_CMD daemon-reload

# Enable and start the main service
echo "Enabling and starting Matt Bot service..."
echo "  ✓ Enabling matt_bot.service"
$SYSTEMCTL_CMD enable matt_bot.service
$SYSTEMCTL_CMD start matt_bot.service

echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Installed services:"
echo "  • Matt Bot: Discord bot service (matt_bot.service)"
echo ""
echo "Useful commands:"
echo "  Check status: $SYSTEMCTL_CMD status matt_bot.service"
echo "  View logs: journalctl -f -u matt_bot.service"
echo "  Restart bot: $SYSTEMCTL_CMD restart matt_bot.service"
echo "  Stop bot: $SYSTEMCTL_CMD stop matt_bot.service" 