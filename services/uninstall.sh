#!/bin/bash

# Matt Bot Systemd Uninstallation Script
# This script removes the systemd service files for the Matt Bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SYSTEMD_SYSTEM_DIR="/etc/systemd/system"

echo -e "${GREEN}Matt Bot Systemd Uninstallation${NC}"
echo "====================================="

# Check if running as root for system-wide uninstallation
if [[ $EUID -eq 0 ]]; then
    echo -e "${YELLOW}Uninstalling system-wide services...${NC}"
    INSTALL_DIR="$SYSTEMD_SYSTEM_DIR"
    SYSTEMCTL_CMD="systemctl"
else
    echo -e "${YELLOW}Uninstalling user services...${NC}"
    INSTALL_DIR="$SYSTEMD_USER_DIR"
    SYSTEMCTL_CMD="systemctl --user"
fi

# Stop and disable services
echo -e "${BLUE}Stopping and disabling services...${NC}"

if $SYSTEMCTL_CMD is-active --quiet matt_bot.service; then
    echo "  ✓ Stopping matt_bot.service"
    $SYSTEMCTL_CMD stop matt_bot.service
fi

if $SYSTEMCTL_CMD is-enabled --quiet matt_bot.service; then
    echo "  ✓ Disabling matt_bot.service"
    $SYSTEMCTL_CMD disable matt_bot.service
fi

# Remove service files
echo -e "${BLUE}Removing service files...${NC}"

if [[ -f "$INSTALL_DIR/matt_bot.service" ]]; then
    rm "$INSTALL_DIR/matt_bot.service"
    echo "  ✓ Removed matt_bot.service"
fi

# Reload systemd daemon
echo "Reloading systemd daemon..."
$SYSTEMCTL_CMD daemon-reload

echo -e "${GREEN}Uninstallation complete!${NC}"
echo ""
echo "All Matt Bot services have been removed and disabled." 