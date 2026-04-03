import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.auth import authorized_only
from bot.utils.helpers import sanitize_filename, format_bytes
from bot.models.download import DownloadTask, DownloadType, DownloadStatus
from bot.services.queue_manager import QueueManager
from bot.utils.config import Config

logger = logging.getLogger(__name__)

@authorized_only
async def handle_torrent_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .torrent files"""
    document = update.message.document
    
    # Check if it's a torrent file
    if not document.file_name.endswith('.torrent'):
        await update.message.reply_text("❌ Please send a valid .torrent file")
        return
    
    await update.message.reply_text("📥 Downloading torrent file...")
    
    try:
        # Download the torrent file
        file = await context.bot.get_file(document.file_id)
        torrent_path = os.path.join(
            Config.DOWNLOAD_PATH,
            f"torrent_{update.effective_user.id}_{document.file_id[:8]}.torrent"
        )
        await file.download_to_drive(torrent_path)
        
        # Get queue manager and torrent manager
        queue_manager = context.bot_data.get('queue_manager')
        torrent_manager = context.bot_data.get('torrent_manager')
        
        if not queue_manager or not torrent_manager:
            await update.message.reply_text("❌ Bot services not initialized")
            return
        
        # Create download task
        task_id = QueueManager.generate_task_id()
        task = DownloadTask(
            task_id=task_id,
            user_id=update.effective_user.id,
            download_type=DownloadType.TORRENT_FILE,
            source=torrent_path,
            status=DownloadStatus.PENDING,
            created_at=datetime.now()
        )
        
        # Get torrent info
        await update.message.reply_text("🔍 Reading torrent metadata...")
        torrent_info = torrent_manager.get_torrent_info(task)
        
        if not torrent_info:
            await update.message.reply_text("❌ Failed to read torrent file")
            return
        
        # Update task with torrent info
        task.name = sanitize_filename(torrent_info['name'])
        task.total_size = torrent_info['total_size']
        task.files = torrent_info['files']
        
        # Check if multi-file torrent
        if torrent_info['num_files'] > 1:
            # Store task for file selection
            context.user_data['pending_task'] = task
            
            # Show file selection menu
            message = f"📦 *Multi-file torrent detected*\n\n"
            message += f"*Name:* {task.name}\n"
            message += f"*Total Size:* {format_bytes(task.total_size)}\n"
            message += f"*Files:* {len(task.files)}\n\n"
            message += "Use /selectfiles to choose which files to download\n"
            message += "Or use /downloadall to download everything"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            # Single file torrent - add to queue directly
            queue_manager.add_task(task)
            
            message = f"✅ *Added to queue*\n\n"
            message += f"*Name:* {task.name}\n"
            message += f"*Size:* {format_bytes(task.total_size)}\n"
            message += f"*Task ID:* `{task_id}`\n\n"
            message += "Download will start soon..."
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
            # Trigger download processor
            if 'download_processor' in context.bot_data:
                context.bot_data['download_processor'].process_queue()
    
    except Exception as e:
        logger.error(f"Error handling torrent file: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@authorized_only
async def handle_magnet_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle magnet links sent as text"""
    text = update.message.text.strip()
    
    # Check if it's a magnet link
    if not text.startswith('magnet:?'):
        return  # Not a magnet link, ignore
    
    await update.message.reply_text("🧲 Processing magnet link...")
    
    try:
        # Get managers
        queue_manager = context.bot_data.get('queue_manager')
        torrent_manager = context.bot_data.get('torrent_manager')
        
        if not queue_manager or not torrent_manager:
            await update.message.reply_text("❌ Bot services not initialized")
            return
        
        # Create download task
        task_id = QueueManager.generate_task_id()
        task = DownloadTask(
            task_id=task_id,
            user_id=update.effective_user.id,
            download_type=DownloadType.MAGNET_LINK,
            source=text,
            status=DownloadStatus.PENDING,
            created_at=datetime.now()
        )
        
        # Get torrent metadata (this might take a while)
        await update.message.reply_text("🔍 Fetching metadata from DHT network (may take up to 60 seconds)...")
        torrent_info = torrent_manager.get_torrent_info(task)
        
        if not torrent_info:
            await update.message.reply_text(
                "❌ Failed to fetch metadata from magnet link\n"
                "This can happen if:\n"
                "• The torrent has no seeds\n"
                "• The magnet link is invalid\n"
                "• DHT network is unreachable"
            )
            return
        
        # Update task with torrent info
        task.name = sanitize_filename(torrent_info['name'])
        task.total_size = torrent_info['total_size']
        task.files = torrent_info['files']
        
        # Check if multi-file torrent
        if torrent_info['num_files'] > 1:
            # Store task for file selection
            context.user_data['pending_task'] = task
            
            # Show file selection menu
            message = f"📦 *Multi-file torrent detected*\n\n"
            message += f"*Name:* {task.name}\n"
            message += f"*Total Size:* {format_bytes(task.total_size)}\n"
            message += f"*Files:* {len(task.files)}\n\n"
            message += "Use /selectfiles to choose which files to download\n"
            message += "Or use /downloadall to download everything"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            # Single file - add to queue directly
            queue_manager.add_task(task)
            
            message = f"✅ *Added to queue*\n\n"
            message += f"*Name:* {task.name}\n"
            message += f"*Size:* {format_bytes(task.total_size)}\n"
            message += f"*Task ID:* `{task_id}`\n\n"
            message += "Download will start soon..."
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
            # Trigger download processor
            if 'download_processor' in context.bot_data:
                context.bot_data['download_processor'].process_queue()
    
    except Exception as e:
        logger.error(f"Error handling magnet link: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@authorized_only
async def download_all_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download all files from a multi-file torrent"""
    if 'pending_task' not in context.user_data:
        await update.message.reply_text("❌ No pending torrent found")
        return
    
    task = context.user_data.pop('pending_task')
    queue_manager = context.bot_data.get('queue_manager')
    
    if not queue_manager:
        await update.message.reply_text("❌ Queue manager not initialized")
        return
    
    # All files are already selected by default
    queue_manager.add_task(task)
    
    message = f"✅ *Added to queue*\n\n"
    message += f"*Name:* {task.name}\n"
    message += f"*Size:* {format_bytes(task.total_size)}\n"
    message += f"*Files:* {len(task.files)}\n"
    message += f"*Task ID:* `{task.task_id}`\n\n"
    message += "Download will start soon..."
    
    await update.message.reply_text(message, parse_mode='Markdown')
    
    # Trigger download processor
    if 'download_processor' in context.bot_data:
        context.bot_data['download_processor'].process_queue()
