import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.auth import authorized_only
from bot.utils.helpers import format_bytes
from bot.services.queue_manager import QueueManager
from bot.models.download import DownloadStatus

logger = logging.getLogger(__name__)

@authorized_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = (
        "🤖 *Welcome to Torrent to Google Drive Bot!*\n\n"
        "This bot can download torrents/magnets and upload them to Google Drive.\n\n"
        "*Available Commands:*\n"
        "/start - Show this welcome message\n"
        "/help - Show detailed help\n"
        "/status - Check download queue status\n"
        "/cancel - Cancel a download\n"
        "/list - List recent downloads\n\n"
        "*How to use:*\n"
        "1️⃣ Send a .torrent file or magnet link\n"
        "2️⃣ Bot will download the torrent\n"
        "3️⃣ Files are uploaded to Telegram (split if > 2GB)\n"
        "4️⃣ Finally uploaded to Google Drive\n\n"
        "Send a torrent file or magnet link to get started!"
    )
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_message = (
        "📚 *Detailed Help*\n\n"
        "*Sending Torrents:*\n"
        "• Upload a .torrent file directly\n"
        "• Send a magnet link as text\n"
        "• For multi-file torrents, you can select specific files\n\n"
        "*File Size Limits:*\n"
        "• Telegram free accounts: ~2GB per file\n"
        "• Large files are automatically split into parts\n"
        "• All parts are uploaded to both Telegram and Google Drive\n\n"
        "*Queue System:*\n"
        "• Downloads are processed in order\n"
        "• Multiple downloads can run concurrently\n"
        "• Use /status to check queue position\n\n"
        "*Commands:*\n"
        "/status - Show active and queued downloads\n"
        "/list - Show your recent downloads\n"
        "/cancel <task_id> - Cancel a specific download\n\n"
        "*Tips:*\n"
        "• Progress is updated in real-time\n"
        "• Google Drive links are sent upon completion\n"
        "• Failed downloads can be retried\n\n"
        "Need more help? Contact the bot administrator."
    )
    
    await update.message.reply_text(help_message, parse_mode='Markdown')

@authorized_only
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    queue_manager = context.bot_data.get('queue_manager')
    
    if not queue_manager:
        await update.message.reply_text("❌ Queue manager not initialized")
        return
    
    # Get active tasks
    active_tasks = queue_manager.get_active_tasks()
    pending_tasks = queue_manager.get_pending_tasks(limit=5)
    
    message = "*📊 Download Queue Status*\n\n"
    
    if active_tasks:
        message += f"*🔄 Active Downloads ({len(active_tasks)}):*\n"
        for task in active_tasks:
            status_emoji = {
                DownloadStatus.DOWNLOADING: "⬇️",
                DownloadStatus.UPLOADING_TO_TELEGRAM: "📤",
                DownloadStatus.UPLOADING_TO_GDRIVE: "☁️",
            }.get(task.status, "❓")
            
            progress_pct = int(task.progress * 100)
            message += f"{status_emoji} {task.name[:30]}... - {progress_pct}%\n"
        message += "\n"
    
    if pending_tasks:
        message += f"*⏳ Queued Downloads ({len(pending_tasks)}):*\n"
        for i, task in enumerate(pending_tasks, 1):
            message += f"{i}. {task.name or 'Loading metadata'}...\n"
        message += "\n"
    
    if not active_tasks and not pending_tasks:
        message += "✨ No active or queued downloads\n\n"
    
    queue_size = queue_manager.get_queue_size()
    message += f"Total in queue: {queue_size}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

@authorized_only
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command - show user's recent downloads"""
    queue_manager = context.bot_data.get('queue_manager')
    
    if not queue_manager:
        await update.message.reply_text("❌ Queue manager not initialized")
        return
    
    user_id = update.effective_user.id
    tasks = queue_manager.get_user_tasks(user_id, limit=10)
    
    if not tasks:
        await update.message.reply_text("📝 No downloads found")
        return
    
    message = "*📋 Your Recent Downloads*\n\n"
    
    for i, task in enumerate(tasks, 1):
        status_emoji = {
            DownloadStatus.COMPLETED: "✅",
            DownloadStatus.FAILED: "❌",
            DownloadStatus.CANCELLED: "🚫",
            DownloadStatus.DOWNLOADING: "⬇️",
            DownloadStatus.PENDING: "⏳",
        }.get(task.status, "❓")
        
        message += f"{i}. {status_emoji} {task.name or 'Unknown'}\n"
        message += f"   Size: {format_bytes(task.total_size)}\n"
        message += f"   Status: {task.status.value.replace('_', ' ').title()}\n"
        if task.status == DownloadStatus.FAILED and task.error_message:
            message += f"   Error: {task.error_message[:50]}...\n"
        message += "\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

@authorized_only
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a task ID\n"
            "Usage: /cancel <task_id>"
        )
        return
    
    task_id = context.args[0]
    queue_manager = context.bot_data.get('queue_manager')
    
    if not queue_manager:
        await update.message.reply_text("❌ Queue manager not initialized")
        return
    
    task = queue_manager.get_task(task_id)
    
    if not task:
        await update.message.reply_text("❌ Task not found")
        return
    
    if task.user_id != update.effective_user.id:
        await update.message.reply_text("❌ You can only cancel your own downloads")
        return
    
    # Update task status to cancelled
    task.status = DownloadStatus.CANCELLED
    queue_manager.update_task(task)
    
    # Cancel the download in torrent manager if active
    torrent_manager = context.bot_data.get('torrent_manager')
    if torrent_manager:
        torrent_manager.cancel_download(task_id)
    
    await update.message.reply_text(f"🚫 Download cancelled: {task.name}")
