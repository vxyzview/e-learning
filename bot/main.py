#!/usr/bin/env python3
"""
Telegram Torrent to Google Drive Bot
Downloads torrents/magnets and uploads to Google Drive via Telegram
"""

import logging
import sys
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Import configurations
from bot.utils.config import Config

# Import handlers
from bot.handlers.commands import (
    start_command, help_command, status_command, 
    list_command, cancel_command
)
from bot.handlers.download import (
    handle_torrent_file, handle_magnet_link, download_all_files
)

# Import services
from bot.services.queue_manager import QueueManager
from bot.services.torrent_manager import TorrentManager
from bot.services.telegram_uploader import TelegramUploader
from bot.services.gdrive_manager import GoogleDriveManager
from bot.services.progress_tracker import ProgressTracker
from bot.services.download_processor import DownloadProcessor

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)

async def post_init(application: Application):
    """Initialize services after bot starts"""
    logger.info("Initializing bot services...")
    
    # Initialize managers
    queue_manager = QueueManager()
    torrent_manager = TorrentManager()
    telegram_uploader = TelegramUploader(application.bot)
    gdrive_manager = GoogleDriveManager()
    progress_tracker = ProgressTracker(application.bot)
    
    # Store in bot_data for access in handlers
    application.bot_data['queue_manager'] = queue_manager
    application.bot_data['torrent_manager'] = torrent_manager
    application.bot_data['telegram_uploader'] = telegram_uploader
    application.bot_data['gdrive_manager'] = gdrive_manager
    application.bot_data['progress_tracker'] = progress_tracker
    
    # Initialize download processor
    download_processor = DownloadProcessor(
        application.bot,
        queue_manager,
        torrent_manager,
        telegram_uploader,
        gdrive_manager,
        progress_tracker
    )
    application.bot_data['download_processor'] = download_processor
    
    # Start download processor in background
    asyncio.create_task(download_processor.start())
    
    # Check Google Drive authentication
    if gdrive_manager.is_authenticated():
        logger.info("✅ Google Drive authenticated successfully")
    else:
        logger.warning("⚠️ Google Drive not authenticated - uploads will fail!")
        logger.info("Please run the bot locally once to authenticate with Google Drive")
    
    logger.info("✅ Bot services initialized successfully")

async def post_shutdown(application: Application):
    """Cleanup on bot shutdown"""
    logger.info("Shutting down bot services...")
    
    # Stop download processor
    if 'download_processor' in application.bot_data:
        application.bot_data['download_processor'].stop()
    
    # Cleanup torrent manager
    if 'torrent_manager' in application.bot_data:
        application.bot_data['torrent_manager'].cleanup()
    
    logger.info("✅ Bot shutdown complete")

def main():
    """Main function to start the bot"""
    try:
        # Validate configuration
        Config.validate()
        
        logger.info("🤖 Starting Torrent to Google Drive Bot...")
        logger.info(f"📝 Authorized users: {Config.AUTHORIZED_USER_IDS}")
        logger.info(f"⚙️ Max concurrent downloads: {Config.MAX_CONCURRENT_DOWNLOADS}")
        logger.info(f"📦 Telegram chunk size: {Config.TELEGRAM_FILE_CHUNK_SIZE_MB}MB")
        
        # Create application
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Register post-init and post-shutdown hooks
        application.post_init = post_init
        application.post_shutdown = post_shutdown
        
        # Register command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(CommandHandler("downloadall", download_all_files))
        
        # Register message handlers
        application.add_handler(
            MessageHandler(filters.Document.MimeType("application/x-bittorrent"), handle_torrent_file)
        )
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_magnet_link)
        )
        
        # Start bot
        logger.info("✅ Bot started successfully!")
        logger.info("Press Ctrl+C to stop")
        
        # Run bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
