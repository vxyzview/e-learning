# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites Checklist
- [ ] Python 3.11+ installed
- [ ] Telegram account
- [ ] Google account

### Step 1: Get Telegram Bot Token (2 min)

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Choose a name: `My Torrent Bot`
4. Choose a username: `mytorrent_bot` (must end with 'bot')
5. Copy the token that looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### Step 2: Get Your Telegram User ID (1 min)

1. Search for `@userinfobot` on Telegram
2. Send any message
3. Copy your ID (e.g., `123456789`)

### Step 3: Setup Google Drive API (5 min)

1. Go to https://console.cloud.google.com/
2. Create new project or select existing
3. Enable Google Drive API:
   - Click "Enable APIs and Services"
   - Search "Google Drive API"
   - Click "Enable"
4. Create credentials:
   - Go to "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Configure consent screen if needed (External, add your email)
   - Application type: "Desktop app"
   - Download JSON
   - Save as `config/credentials.json`

### Step 4: Install & Configure (2 min)

```bash
# Run setup script
bash setup.sh

# Edit configuration
nano config/.env
```

Add your settings:
```env
TELEGRAM_BOT_TOKEN=your_token_from_step1
AUTHORIZED_USER_IDS=your_user_id_from_step2
```

### Step 5: Run the Bot

```bash
# Activate virtual environment
source venv/bin/activate

# Start bot (first run will open browser for Google auth)
python bot/main.py
```

### Step 6: Test It!

1. Open Telegram and search for your bot
2. Send `/start`
3. Upload a small .torrent file or send a magnet link
4. Watch the magic happen! ✨

## 🎯 Usage Examples

### Download a torrent file
1. Find a .torrent file
2. Send it to your bot
3. Bot downloads and uploads to Google Drive

### Download from magnet link
1. Copy a magnet link
2. Paste it in chat with your bot
3. Wait for metadata fetch
4. Download starts automatically

### Check download status
- Send `/status` to see active downloads
- Send `/list` to see your download history

## ⚙️ Common Configurations

### For Free Telegram Account
```env
TELEGRAM_FILE_CHUNK_SIZE_MB=2000  # 2GB limit
MAX_FILE_SIZE_MB=2048
```

### For Telegram Premium
```env
TELEGRAM_FILE_CHUNK_SIZE_MB=4000  # 4GB limit
MAX_FILE_SIZE_MB=4096
```

### For Cloud Platforms (Limited Storage)
```env
MAX_CONCURRENT_DOWNLOADS=1
MAX_FILE_SIZE_MB=500  # Download smaller files only
```

### For VPS (More Resources)
```env
MAX_CONCURRENT_DOWNLOADS=5
MAX_FILE_SIZE_MB=10240  # 10GB
```

## 🐛 Troubleshooting Quick Fixes

### "Configuration errors: TELEGRAM_BOT_TOKEN is required"
- Check `config/.env` exists
- Make sure token is set correctly
- No quotes needed around values

### "Google Drive service not initialized"
- Delete `config/token.json`
- Run `python bot/main.py` again
- Browser will open for re-authentication

### "Failed to fetch metadata"
- Magnet link might be dead
- Try a different torrent
- Use .torrent file instead

### Bot not responding
- Check bot is running: `ps aux | grep python`
- Check logs for errors
- Restart: `python bot/main.py`

## 📱 Deployment Options

### Run on VPS (Recommended)
```bash
# Using screen
screen -S torrent-bot
python bot/main.py
# Press Ctrl+A then D to detach

# Reattach later
screen -r torrent-bot
```

### Run on Heroku
```bash
heroku create my-torrent-bot
heroku config:set TELEGRAM_BOT_TOKEN=xxx
heroku config:set AUTHORIZED_USER_IDS=xxx
git push heroku main
```

### Run on Railway
```bash
railway login
railway init
# Set environment variables in dashboard
railway up
```

## 🎓 Next Steps

- Read the full [README.md](README.md) for advanced features
- Set up systemd service for auto-start on VPS
- Configure selective file downloads
- Set up Google Drive folder organization

## 💡 Tips

1. **Start small**: Test with small torrents first
2. **Monitor storage**: Keep an eye on disk space
3. **Use filters**: Only download what you need
4. **Organize**: Create folders in Google Drive
5. **Backup**: Keep your `config/token.json` safe

## 🆘 Need Help?

1. Check the error message
2. Read the full README.md
3. Check bot logs
4. Search for similar issues
5. Create a new issue with details

---

Happy torrenting! 🎉
