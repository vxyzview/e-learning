# Telegram Torrent to Google Drive Bot

A powerful Telegram bot that downloads torrents/magnets and automatically uploads them to Google Drive, using Telegram as intermediate storage.

## Features

- **Download from Multiple Sources**
  - Upload `.torrent` files
  - Send magnet links
  - Automatic metadata fetching for magnets

- **Smart File Handling**
  - Automatic file splitting for files > 2GB
  - Multi-file torrent support with selective downloads
  - Progress tracking with real-time updates

- **Dual Upload Strategy**
  - Files uploaded to Telegram first (with auto-splitting)
  - Then uploaded to Google Drive
  - Supports both free and premium Telegram accounts

- **Queue Management**
  - SQLite-based persistent queue
  - Concurrent download support
  - User-specific download history

- **Security**
  - User ID-based authentication
  - Authorized users only
  - Private downloads

## Architecture Flow

```
Torrent/Magnet Link
        ↓
Download via libtorrent
        ↓
Upload to Telegram (split if > 2GB)
        ↓
Upload to Google Drive
        ↓
Share Google Drive link
```

## Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Google Cloud Project with Drive API enabled
- For VPS: 500MB+ disk space
- For cloud platforms: Check storage limits

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd e-learning
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Save the bot token

### 4. Get Your Telegram User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy your user ID

### 5. Setup Google Drive API

#### Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

#### Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - User Type: External
   - App name: Your bot name
   - Add your email
   - Add scope: `../auth/drive.file`
4. Create OAuth client ID:
   - Application type: Desktop app
   - Name: Telegram Bot
5. Download the JSON file
6. Rename it to `credentials.json`
7. Move it to `config/credentials.json`

#### First-Time Authentication

```bash
# Run the bot locally first to authenticate
python bot/main.py

# A browser will open for Google authentication
# Grant permissions
# token.json will be created automatically
```

### 6. Configure Environment Variables

Copy the example configuration:

```bash
cp config/.env.example config/.env
```

Edit `config/.env`:

```bash
# Telegram Bot Token from BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Your Telegram User ID (comma-separated for multiple users)
AUTHORIZED_USER_IDS=123456789,987654321

# Google Drive Folder ID (optional - leave empty for root)
# To get folder ID: Open folder in Drive, copy ID from URL
GOOGLE_DRIVE_FOLDER_ID=

# Download Settings
MAX_CONCURRENT_DOWNLOADS=2
MAX_FILE_SIZE_MB=2048
DOWNLOAD_PATH=./downloads

# Telegram Settings (adjust based on account type)
# Free: 2000MB, Premium: 4000MB
TELEGRAM_FILE_CHUNK_SIZE_MB=2000

# Database
DATABASE_PATH=./bot_queue.db

# Logging
LOG_LEVEL=INFO
```

## Running the Bot

### Local / VPS Deployment

```bash
# Run directly
python bot/main.py

# Or use with nohup for background running
nohup python bot/main.py > bot.log 2>&1 &

# With systemd (recommended for VPS)
# Create /etc/systemd/system/torrent-bot.service
```

### Heroku Deployment

```bash
# Login to Heroku
heroku login

# Create app
heroku create your-bot-name

# Set environment variables
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set AUTHORIZED_USER_IDS=your_user_id
# ... set other variables

# Note: Google Drive auth won't work on Heroku
# You must authenticate locally first, then upload token.json

# Deploy
git push heroku main

# Scale worker
heroku ps:scale worker=1

# View logs
heroku logs --tail
```

### Railway Deployment

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Set environment variables in Railway dashboard
# Upload credentials.json and token.json as files

# Deploy
railway up
```

### Docker Deployment

```bash
# Build image
docker build -t torrent-bot .

# Run container
docker run -d \
  --name torrent-bot \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/downloads:/app/downloads \
  -e TELEGRAM_BOT_TOKEN=your_token \
  torrent-bot
```

## Usage

### Basic Commands

- `/start` - Welcome message and basic info
- `/help` - Detailed help and instructions
- `/status` - Check download queue and active downloads
- `/list` - View your recent downloads
- `/cancel <task_id>` - Cancel a specific download

### Downloading Torrents

**Method 1: Upload .torrent File**
1. Upload a `.torrent` file to the bot
2. Bot will read metadata and add to queue
3. Download starts automatically

**Method 2: Send Magnet Link**
1. Copy magnet link
2. Send it as a text message to the bot
3. Bot fetches metadata (may take 30-60 seconds)
4. Download starts automatically

### Multi-File Torrents

When you send a multi-file torrent:
1. Bot shows file list and total size
2. Use `/downloadall` to download all files
3. Use `/selectfiles` to choose specific files (coming soon)

### File Splitting

Large files (> 2GB for free Telegram) are automatically split:
- Parts are uploaded sequentially to Telegram
- Each part is named `filename.part001.ext`, `part002.ext`, etc.
- All parts are also uploaded to Google Drive
- You can rejoin parts using tools like `cat` or HJSplit

## File Structure

```
e-learning/
├── bot/
│   ├── handlers/
│   │   ├── commands.py          # Command handlers
│   │   └── download.py          # Torrent/magnet handlers
│   ├── services/
│   │   ├── torrent_manager.py   # Torrent download logic
│   │   ├── telegram_uploader.py # Telegram upload with splitting
│   │   ├── gdrive_manager.py    # Google Drive upload
│   │   ├── queue_manager.py     # SQLite queue management
│   │   ├── progress_tracker.py  # Progress updates
│   │   └── download_processor.py# Main download orchestrator
│   ├── models/
│   │   └── download.py          # Data models
│   ├── utils/
│   │   ├── auth.py              # Authentication decorator
│   │   ├── config.py            # Configuration loader
│   │   └── helpers.py           # Utility functions
│   └── main.py                  # Entry point
├── config/
│   ├── .env.example             # Environment variables template
│   ├── credentials.json.example # Google OAuth template
│   └── .env                     # Your configuration (gitignored)
├── downloads/                   # Temporary download storage
├── requirements.txt             # Python dependencies
├── Procfile                     # Heroku/Railway configuration
├── runtime.txt                  # Python version
└── README.md                    # This file
```

## Troubleshooting

### Google Drive Authentication Fails

**Problem**: Browser doesn't open or authentication fails

**Solution**:
```bash
# Ensure credentials.json exists
ls config/credentials.json

# Run locally first to authenticate
python bot/main.py

# If on server, authenticate locally then upload token.json
scp config/token.json user@server:/path/to/bot/config/
```

### Magnet Link Metadata Fetch Timeout

**Problem**: "Failed to fetch metadata" error

**Possible Causes**:
- No seeds available
- DHT network unreachable
- Invalid magnet link

**Solution**:
- Try a different torrent with more seeds
- Wait and retry
- Use .torrent file instead

### Telegram Upload Fails

**Problem**: Files fail to upload to Telegram

**Solutions**:
- Check file size limits (2GB free, 4GB premium)
- Adjust `TELEGRAM_FILE_CHUNK_SIZE_MB` in config
- Check bot token is valid
- Ensure bot hasn't been blocked

### Download Stuck in Queue

**Problem**: Download shows "pending" but never starts

**Solutions**:
```bash
# Check logs
tail -f bot.log

# Restart bot
# Kill and restart the process

# Check queue status
# Use /status command in bot
```

### Storage Issues on Cloud Platforms

**Problem**: "No space left on device"

**Solutions**:
- Reduce `MAX_FILE_SIZE_MB`
- Reduce `MAX_CONCURRENT_DOWNLOADS`
- Use VPS with more storage
- Enable immediate cleanup after upload

## Advanced Configuration

### Systemd Service (VPS)

Create `/etc/systemd/system/torrent-bot.service`:

```ini
[Unit]
Description=Telegram Torrent Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/e-learning
ExecStart=/usr/bin/python3 /path/to/e-learning/bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable torrent-bot
sudo systemctl start torrent-bot
sudo systemctl status torrent-bot
```

### Custom Torrent Settings

Edit `bot/services/torrent_manager.py` to adjust:
- Connection limits
- Upload/download rate limits
- DHT settings
- Tracker settings

## Limitations

### Telegram Limits
- Free accounts: ~2GB per file
- Premium accounts: ~4GB per file
- Rate limits on uploads

### Google Drive Limits
- 750GB/day upload limit per user
- API quota: 1000 requests/100 seconds

### Cloud Platform Limits
- Heroku: 512MB ephemeral storage
- Railway: Variable based on plan
- May timeout on long downloads

## Security Considerations

- Never commit `.env` or `credentials.json` to Git
- Restrict `AUTHORIZED_USER_IDS` to trusted users only
- Use environment variables for sensitive data
- Keep bot token secret
- Regularly rotate Google OAuth tokens

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - feel free to use and modify

## Support

For issues and questions:
1. Check this README first
2. Review error logs
3. Search existing issues
4. Create a new issue with:
   - Error message
   - Steps to reproduce
   - Environment details

## Credits

Built with:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [libtorrent](https://www.libtorrent.org/)
- [Google Drive API](https://developers.google.com/drive)

## Disclaimer

This bot is for educational purposes. Users are responsible for:
- Legal use of torrents
- Compliance with copyright laws
- Proper use of Google Drive storage
- Following Telegram's Terms of Service

Use at your own risk.
