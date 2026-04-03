import logging
import asyncio
import os
import time
from telegram import Bot
from bot.models.download import DownloadTask, DownloadStatus
from bot.services.queue_manager import QueueManager
from bot.services.torrent_manager import TorrentManager
from bot.services.telegram_uploader import TelegramUploader
from bot.services.gdrive_manager import GoogleDriveManager
from bot.services.progress_tracker import ProgressTracker
from bot.utils.config import Config
from bot.utils.helpers import format_bytes

logger = logging.getLogger(__name__)

class DownloadProcessor:
    """Process download queue and manage downloads"""
    
    def __init__(self, bot: Bot, queue_manager: QueueManager, 
                 torrent_manager: TorrentManager,
                 telegram_uploader: TelegramUploader,
                 gdrive_manager: GoogleDriveManager,
                 progress_tracker: ProgressTracker):
        self.bot = bot
        self.queue_manager = queue_manager
        self.torrent_manager = torrent_manager
        self.telegram_uploader = telegram_uploader
        self.gdrive_manager = gdrive_manager
        self.progress_tracker = progress_tracker
        self.running = False
        self.active_downloads = {}
    
    async def start(self):
        """Start the download processor"""
        self.running = True
        logger.info("Download processor started")
        
        while self.running:
            await self.process_queue()
            await asyncio.sleep(5)  # Check queue every 5 seconds
    
    def stop(self):
        """Stop the download processor"""
        self.running = False
        logger.info("Download processor stopped")
    
    async def process_queue(self):
        """Process pending downloads from queue"""
        try:
            # Check how many active downloads we have
            active_count = len(self.active_downloads)
            
            if active_count >= Config.MAX_CONCURRENT_DOWNLOADS:
                return  # Max concurrent downloads reached
            
            # Get pending tasks
            slots_available = Config.MAX_CONCURRENT_DOWNLOADS - active_count
            pending_tasks = self.queue_manager.get_pending_tasks(limit=slots_available)
            
            # Start downloads for pending tasks
            for task in pending_tasks:
                if task.task_id not in self.active_downloads:
                    asyncio.create_task(self.process_download(task))
                    self.active_downloads[task.task_id] = task
        
        except Exception as e:
            logger.error(f"Error processing queue: {e}")
    
    async def process_download(self, task: DownloadTask):
        """Process a single download task"""
        try:
            logger.info(f"Starting download for task {task.task_id}")
            
            # Send initial progress message
            task.progress_message_id = await self.progress_tracker.send_progress_message(
                task, task.user_id
            )
            
            # Step 1: Download torrent
            await self.download_torrent(task)
            
            if task.status == DownloadStatus.FAILED or task.status == DownloadStatus.CANCELLED:
                await self.cleanup_task(task)
                return
            
            # Step 2: Upload to Telegram
            await self.upload_to_telegram(task)
            
            if task.status == DownloadStatus.FAILED or task.status == DownloadStatus.CANCELLED:
                await self.cleanup_task(task)
                return
            
            # Step 3: Upload to Google Drive
            await self.upload_to_gdrive(task)
            
            # Complete
            task.status = DownloadStatus.COMPLETED
            self.queue_manager.update_task(task)
            
            # Send completion message
            gdrive_links = []
            for file_id in task.gdrive_file_ids:
                link = self.gdrive_manager.get_file_link(file_id)
                if link:
                    gdrive_links.append(link)
            
            await self.progress_tracker.send_completion_message(
                task, task.user_id, gdrive_links
            )
            
        except Exception as e:
            logger.error(f"Error processing download {task.task_id}: {e}")
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
            self.queue_manager.update_task(task)
            await self.progress_tracker.send_completion_message(task, task.user_id)
        
        finally:
            await self.cleanup_task(task)
    
    async def download_torrent(self, task: DownloadTask):
        """Download files using torrent"""
        try:
            task.status = DownloadStatus.DOWNLOADING
            self.queue_manager.update_task(task)
            
            # Add torrent to manager
            self.torrent_manager.add_torrent(task)
            
            # Set file priorities if selective download
            selected_indices = [f.index for f in task.files if f.selected]
            if selected_indices:
                self.torrent_manager.set_file_priorities(task.task_id, selected_indices)
            
            # Start download
            self.torrent_manager.start_download(task.task_id)
            
            # Monitor progress
            while not self.torrent_manager.is_download_complete(task.task_id):
                # Check if cancelled
                updated_task = self.queue_manager.get_task(task.task_id)
                if updated_task.status == DownloadStatus.CANCELLED:
                    task.status = DownloadStatus.CANCELLED
                    return
                
                # Update progress
                progress_info = self.torrent_manager.get_progress(task.task_id)
                if progress_info:
                    task.progress = progress_info['progress']
                    task.download_speed = progress_info['download_rate']
                    task.eta = progress_info.get('eta', 0)
                    task.downloaded_bytes = progress_info['total_download']
                    
                    self.queue_manager.update_task(task)
                    await self.progress_tracker.update_progress_message(task, task.user_id)
                
                await asyncio.sleep(2)  # Update every 2 seconds
            
            logger.info(f"Download complete for task {task.task_id}")
            
        except Exception as e:
            logger.error(f"Error downloading torrent: {e}")
            task.status = DownloadStatus.FAILED
            task.error_message = f"Download failed: {str(e)}"
            raise
    
    async def upload_to_telegram(self, task: DownloadTask):
        """Upload downloaded files to Telegram"""
        try:
            task.status = DownloadStatus.UPLOADING_TO_TELEGRAM
            self.queue_manager.update_task(task)
            await self.progress_tracker.update_progress_message(task, task.user_id)
            
            # Get downloaded file paths
            file_paths = self.torrent_manager.get_downloaded_files(task)
            
            if not file_paths:
                raise Exception("No files found to upload")
            
            # Upload each file
            for i, file_path in enumerate(file_paths, 1):
                task.current_part = i
                task.num_parts = len(file_paths)
                self.queue_manager.update_task(task)
                await self.progress_tracker.update_progress_message(task, task.user_id)
                
                file_name = os.path.basename(file_path)
                caption = f"{task.name}\n{file_name}" if len(file_paths) > 1 else task.name
                
                file_ids = await self.telegram_uploader.upload_file(
                    file_path, task.user_id, caption
                )
                task.telegram_file_ids.extend(file_ids)
            
            self.queue_manager.update_task(task)
            logger.info(f"Telegram upload complete for task {task.task_id}")
            
        except Exception as e:
            logger.error(f"Error uploading to Telegram: {e}")
            task.status = DownloadStatus.FAILED
            task.error_message = f"Telegram upload failed: {str(e)}"
            raise
    
    async def upload_to_gdrive(self, task: DownloadTask):
        """Upload files to Google Drive"""
        try:
            task.status = DownloadStatus.UPLOADING_TO_GDRIVE
            self.queue_manager.update_task(task)
            await self.progress_tracker.update_progress_message(task, task.user_id)
            
            # Get downloaded file paths
            file_paths = self.torrent_manager.get_downloaded_files(task)
            
            # Create folder for this download if multiple files
            folder_id = None
            if len(file_paths) > 1:
                folder_id = self.gdrive_manager.create_folder(task.name)
                task.gdrive_folder_id = folder_id
            
            # Upload each file
            for i, file_path in enumerate(file_paths, 1):
                task.current_part = i
                task.num_parts = len(file_paths)
                self.queue_manager.update_task(task)
                await self.progress_tracker.update_progress_message(task, task.user_id)
                
                file_id = self.gdrive_manager.upload_file(file_path, folder_id)
                if file_id:
                    task.gdrive_file_ids.append(file_id)
            
            self.queue_manager.update_task(task)
            logger.info(f"Google Drive upload complete for task {task.task_id}")
            
        except Exception as e:
            logger.error(f"Error uploading to Google Drive: {e}")
            task.status = DownloadStatus.FAILED
            task.error_message = f"Google Drive upload failed: {str(e)}"
            raise
    
    async def cleanup_task(self, task: DownloadTask):
        """Cleanup after download completion/failure"""
        try:
            # Remove from active downloads
            if task.task_id in self.active_downloads:
                del self.active_downloads[task.task_id]
            
            # Cancel torrent
            self.torrent_manager.cancel_download(task.task_id)
            
            # Delete downloaded files
            file_paths = self.torrent_manager.get_downloaded_files(task)
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")
            
            # Delete torrent file if it was uploaded
            if task.source and os.path.exists(task.source) and task.source.endswith('.torrent'):
                try:
                    os.remove(task.source)
                except:
                    pass
            
            logger.info(f"Cleanup complete for task {task.task_id}")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
