#!/bin/bash

# Telegram Torrent Bot Setup Script

echo "🤖 Telegram Torrent to Google Drive Bot - Setup Script"
echo "======================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Setup config
echo ""
echo "Setting up configuration..."
if [ ! -f "config/.env" ]; then
    cp config/.env.example config/.env
    echo "✅ Created config/.env - Please edit this file with your settings"
else
    echo "⚠️  config/.env already exists, skipping"
fi

if [ ! -f "config/credentials.json" ]; then
    cp config/credentials.json.example config/credentials.json
    echo "✅ Created config/credentials.json - Please replace with your actual Google OAuth credentials"
else
    echo "⚠️  config/credentials.json already exists, skipping"
fi

# Create downloads directory
echo ""
echo "Creating downloads directory..."
mkdir -p downloads

echo ""
echo "======================================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config/.env with your bot token and user ID"
echo "2. Replace config/credentials.json with your Google OAuth credentials"
echo "3. Run 'source venv/bin/activate' to activate the virtual environment"
echo "4. Run 'python bot/main.py' to start the bot (first run will authenticate with Google)"
echo ""
echo "For detailed instructions, see README.md"
echo "======================================================"
