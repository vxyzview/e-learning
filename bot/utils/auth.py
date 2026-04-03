from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.config import Config
import logging

logger = logging.getLogger(__name__)

def authorized_only(func):
    """Decorator to restrict command access to authorized users only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if user_id not in Config.AUTHORIZED_USER_IDS:
            logger.warning(f"Unauthorized access attempt by user {user_id}")
            await update.message.reply_text(
                "⛔ You are not authorized to use this bot.\n\n"
                f"Your user ID: `{user_id}`\n"
                "Contact the bot administrator to get access.",
                parse_mode='Markdown'
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def is_authorized(user_id: int) -> bool:
    """Check if a user ID is authorized"""
    return user_id in Config.AUTHORIZED_USER_IDS
