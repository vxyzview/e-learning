import logging
from telegram import Bot
from bot.models.download import DownloadTask, DownloadStatus
from bot.utils.helpers import format_bytes, format_speed, format_time, format_progress_bar

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Track and report download/upload progress to Telegram"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_progress_message(self, task: DownloadTask, chat_id: int) -> int:
        """Send initial progress message"""
        message_text = self._format_progress_message(task)
        
        try:
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode='Markdown'
            )
            return message.message_id
        except Exception as e:
            logger.error(f"Error sending progress message: {e}")
            return None
    
    async def update_progress_message(self, task: DownloadTask, chat_id: int):
        """Update existing progress message"""
        if not task.progress_message_id:
            return
        
        message_text = self._format_progress_message(task)
        
        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=task.progress_message_id,
                text=message_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            # Ignore errors when message content hasn't changed
            if "message is not modified" not in str(e).lower():
                logger.error(f"Error updating progress message: {e}")
    
    async def send_completion_message(self, task: DownloadTask, chat_id: int, 
                                     gdrive_links: list = None):
        """Send completion message with Google Drive links"""
        if task.status == DownloadStatus.COMPLETED:
            message = f"✅ *Download Complete*\n\n"
            message += f"📁 *File:* {task.name}\n"
            message += f"📊 *Size:* {format_bytes(task.total_size)}\n\n"
            
            if gdrive_links:
                message += "🔗 *Google Drive Links:*\n"
                for i, link in enumerate(gdrive_links, 1):
                    if len(gdrive_links) > 1:
                        message += f"{i}. {link}\n"
                    else:
                        message += f"{link}\n"
            else:
                message += "✅ Files uploaded to Telegram and Google Drive"
        
        elif task.status == DownloadStatus.FAILED:
            message = f"❌ *Download Failed*\n\n"
            message += f"📁 *File:* {task.name}\n"
            if task.error_message:
                message += f"⚠️ *Error:* {task.error_message}\n"
        
        elif task.status == DownloadStatus.CANCELLED:
            message = f"🚫 *Download Cancelled*\n\n"
            message += f"📁 *File:* {task.name}\n"
        
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Error sending completion message: {e}")
    
    def _format_progress_message(self, task: DownloadTask) -> str:
        """Format progress message based on task status"""
        message = f"*Download Progress*\n\n"
        message += f"📁 *Name:* {task.name or 'Loading...'}\n"
        message += f"📊 *Size:* {format_bytes(task.total_size)}\n"
        message += f"📌 *Status:* {self._get_status_emoji(task.status)} {task.status.value.replace('_', ' ').title()}\n\n"
        
        if task.status == DownloadStatus.DOWNLOADING:
            progress_bar = format_progress_bar(task.progress)
            message += f"{progress_bar}\n\n"
            message += f"⬇️ *Downloaded:* {format_bytes(task.downloaded_bytes)} / {format_bytes(task.total_size)}\n"
            message += f"🚀 *Speed:* {format_speed(task.download_speed)}\n"
            if task.eta > 0:
                message += f"⏱️ *ETA:* {format_time(task.eta)}\n"
        
        elif task.status == DownloadStatus.UPLOADING_TO_TELEGRAM:
            message += "📤 Uploading to Telegram...\n"
            if task.num_parts > 1:
                message += f"📦 *Part:* {task.current_part}/{task.num_parts}\n"
        
        elif task.status == DownloadStatus.UPLOADING_TO_GDRIVE:
            message += "☁️ Uploading to Google Drive...\n"
            if task.num_parts > 1:
                message += f"📦 *Part:* {task.current_part}/{task.num_parts}\n"
        
        elif task.status == DownloadStatus.PENDING:
            queue_pos = "In queue"
            message += f"⏳ Waiting in queue...\n"
        
        return message
    
    def _get_status_emoji(self, status: DownloadStatus) -> str:
        """Get emoji for status"""
        emoji_map = {
            DownloadStatus.PENDING: "⏳",
            DownloadStatus.DOWNLOADING: "⬇️",
            DownloadStatus.UPLOADING_TO_TELEGRAM: "📤",
            DownloadStatus.UPLOADING_TO_GDRIVE: "☁️",
            DownloadStatus.COMPLETED: "✅",
            DownloadStatus.FAILED: "❌",
            DownloadStatus.CANCELLED: "🚫",
        }
        return emoji_map.get(status, "❓")
