#!/bin/bash
# SOC Platform Terminal Interface Launch Script

echo "🛡️ Starting SOC Platform Terminal Interface..."
echo "Configuration: soc_terminal_config.json"
echo "API Endpoint: http://localhost:8000"
echo ""

# Check if OpenTUI is installed
if ! command -v opentui &> /dev/null; then
    echo "❌ OpenTUI not found. Installing..."
    # Try different package managers
    if command -v npm &> /dev/null; then
        npm install -g @sst/opentui
    elif command -v bun &> /dev/null; then
        bun install -g @sst/opentui
    elif command -v pnpm &> /dev/null; then
        pnpm install -g @sst/opentui
    else
        echo "❌ No supported package manager found (npm, bun, pnpm)"
        echo "Please install Node.js and npm first:"
        echo "  curl -fsSL https://nodejs.org/install.sh | bash"
        exit 1
    fi
fi

# Launch OpenTUI with our config
echo "🚀 Launching terminal interface..."
opentui --config soc_terminal_config.json --port 3001 --host 0.0.0.0

# Alternative launch methods if direct config doesn't work
if [ $? -ne 0 ]; then
    echo "⚡ Trying alternative launch method..."
    
    # Create a simple HTML page that loads our config
    cat > soc_terminal.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>SOC Platform Terminal</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://unpkg.com/@sst/opentui@latest/dist/index.js"></script>
    <style>
        body { margin: 0; padding: 0; font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace; }
        .terminal { height: 100vh; background: #1a1a1a; color: #00ff00; }
    </style>
</head>
<body>
    <div id="terminal" class="terminal"></div>
    <script>
        // Load configuration and initialize OpenTUI
        fetch('./soc_terminal_config.json')
            .then(response => response.json())
            .then(config => {
                const terminal = new OpenTUI(config);
                terminal.mount('#terminal');
            })
            .catch(error => {
                console.error('Failed to load terminal config:', error);
                document.getElementById('terminal').innerHTML = 
                    '<div style="padding: 20px;">❌ Failed to load terminal interface</div>';
            });
    </script>
</body>
</html>
EOF
    
    echo "📄 Created HTML interface: soc_terminal.html"
    echo "🌐 Open http://localhost:8080/soc_terminal.html in your browser"
    
    # Start a simple HTTP server
    if command -v python3 &> /dev/null; then
        echo "Starting Python HTTP server..."
        python3 -m http.server 8080
    elif command -v python &> /dev/null; then
        echo "Starting Python HTTP server..."
        python -m http.server 8080
    elif command -v node &> /dev/null; then
        echo "Starting Node.js HTTP server..."
        npx http-server -p 8080
    else
        echo "⚠️  No HTTP server available. Please open soc_terminal.html manually."
    fi
fi
