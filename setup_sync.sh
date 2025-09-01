#!/bin/bash
# Setup Redis Sync Service

PROJECT_DIR="/Users/cbernal/AIProjects/Claude/soc_agent_project"
SERVICE_FILE="$PROJECT_DIR/sync_redis.service"
SCRIPT_FILE="$PROJECT_DIR/sync_redis.py"

echo "Setting up Redis sync service..."

# Check if files exist
if [[ ! -f "$SCRIPT_FILE" ]]; then
    echo "❌ Sync script not found: $SCRIPT_FILE"
    exit 1
fi

if [[ ! -f "$SERVICE_FILE" ]]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

# Install pip dependencies if needed
echo "Installing Python dependencies..."
pip3 install redis

# Test the sync script
echo "Testing sync script..."
python3 "$SCRIPT_FILE" --test

if [[ $? -ne 0 ]]; then
    echo "❌ Sync script test failed"
    exit 1
fi

echo "✅ Sync script test passed"

# Option 1: systemd service (Linux)
if command -v systemctl &> /dev/null; then
    echo "Setting up systemd service..."
    sudo cp "$SERVICE_FILE" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable redis-sync.service
    sudo systemctl start redis-sync.service
    sudo systemctl status redis-sync.service
    echo "✅ systemd service installed and started"

# Option 2: launchd (macOS)
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Setting up launchd service for macOS..."
    
    # Create launchd plist
    cat > "$HOME/Library/LaunchAgents/com.soc.redis-sync.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.soc.redis-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$SCRIPT_FILE</string>
        <string>--continuous</string>
        <string>--interval</string>
        <string>300</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/redis-sync.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/redis-sync-error.log</string>
</dict>
</plist>
EOF
    
    # Create logs directory
    mkdir -p "$PROJECT_DIR/logs"
    
    # Load the service
    launchctl load "$HOME/Library/LaunchAgents/com.soc.redis-sync.plist"
    launchctl start com.soc.redis-sync
    
    echo "✅ launchd service installed and started"
    echo "Logs: $PROJECT_DIR/logs/redis-sync.log"
    
# Option 3: Manual cron job
else
    echo "Setting up cron job..."
    
    # Add cron job to run every 5 minutes
    (crontab -l 2>/dev/null; echo "*/5 * * * * cd $PROJECT_DIR && python3 sync_redis.py >> logs/redis-sync.log 2>&1") | crontab -
    
    # Create logs directory
    mkdir -p "$PROJECT_DIR/logs"
    
    echo "✅ Cron job installed (runs every 5 minutes)"
    echo "Logs: $PROJECT_DIR/logs/redis-sync.log"
fi

echo ""
echo "🎉 Redis sync setup complete!"
echo ""
echo "Available commands:"
echo "  # Run one-time sync:"
echo "  python3 $SCRIPT_FILE"
echo ""
echo "  # Run continuous sync (every 5 minutes):"
echo "  python3 $SCRIPT_FILE --continuous --interval 300"
echo ""
echo "  # Test connection:"
echo "  python3 $SCRIPT_FILE --test"