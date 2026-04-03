import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv(dotenv_path='config/.env')

class Config:
    """Configuration loader for the bot"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    AUTHORIZED_USER_IDS = [
        int(uid.strip()) for uid in os.getenv('AUTHORIZED_USER_IDS', '').split(',') if uid.strip()
    ]
    
    # Google Drive
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'config/credentials.json')
    GOOGLE_TOKEN_PATH = os.getenv('GOOGLE_TOKEN_PATH', 'config/token.json')
    
    # Download Settings
    MAX_CONCURRENT_DOWNLOADS = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', '2'))
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '2048'))
    DOWNLOAD_PATH = Path(os.getenv('DOWNLOAD_PATH', './downloads'))
    
    # Telegram File Upload Settings
    TELEGRAM_FILE_CHUNK_SIZE_MB = int(os.getenv('TELEGRAM_FILE_CHUNK_SIZE_MB', '2000'))
    TELEGRAM_FILE_CHUNK_SIZE_BYTES = TELEGRAM_FILE_CHUNK_SIZE_MB * 1024 * 1024
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', './bot_queue.db')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        if not cls.AUTHORIZED_USER_IDS:
            errors.append("AUTHORIZED_USER_IDS is required")
        
        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"- {e}" for e in errors))
        
        # Create download directory if it doesn't exist
        cls.DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
        
        return True

# Validate configuration on import
Config.validate()
