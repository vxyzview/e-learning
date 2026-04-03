import libtorrent as lt
import time
import os
import logging
from pathlib import Path
from typing import Optional, Callable, List
from bot.models.download import DownloadTask, FileInfo, DownloadType
from bot.utils.config import Config
from bot.utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)

class TorrentManager:
    """Manage torrent downloads using libtorrent"""
    
    def __init__(self):
        self.session = lt.session()
        self.session.listen_on(6881, 6891)
        self.handles = {}
        
        # Configure session for better performance
        settings = {
            'user_agent': 'python-libtorrent/' + lt.__version__,
            'listen_interfaces': '0.0.0.0:6881',
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True,
            'announce_to_all_tiers': True,
            'announce_to_all_trackers': True,
            'auto_managed': True,
            'max_connections': 100,
            'max_uploads': 10,
        }
        self.session.apply_settings(settings)
        
        # Add DHT routers
        self.session.add_dht_router('router.bittorrent.com', 6881)
        self.session.add_dht_router('dht.transmissionbt.com', 6881)
        self.session.add_dht_router('router.utorrent.com', 6881)
        
        logger.info("TorrentManager initialized")
    
    def add_torrent(self, task: DownloadTask) -> Optional[str]:
        """Add a torrent to the download queue"""
        try:
            params = {
                'save_path': str(Config.DOWNLOAD_PATH),
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
            }
            
            if task.download_type == DownloadType.MAGNET_LINK:
                params['url'] = task.source
                handle = lt.add_magnet_uri(self.session, task.source, params)
            else:  # TORRENT_FILE
                info = lt.torrent_info(task.source)
                params['ti'] = info
                handle = self.session.add_torrent(params)
            
            self.handles[task.task_id] = handle
            
            logger.info(f"Torrent added for task {task.task_id}")
            return task.task_id
        except Exception as e:
            logger.error(f"Error adding torrent: {e}")
            return None
    
    def get_torrent_info(self, task: DownloadTask) -> Optional[dict]:
        """Get torrent information (name, files, size)"""
        try:
            if task.download_type == DownloadType.MAGNET_LINK:
                # For magnet links, we need to wait for metadata
                params = {
                    'save_path': str(Config.DOWNLOAD_PATH),
                    'url': task.source,
                }
                handle = lt.add_magnet_uri(self.session, task.source, params)
                
                # Wait for metadata (max 60 seconds)
                logger.info(f"Waiting for metadata for task {task.task_id}")
                for _ in range(60):
                    if handle.has_metadata():
                        break
                    time.sleep(1)
                
                if not handle.has_metadata():
                    logger.error("Failed to fetch metadata")
                    self.session.remove_torrent(handle)
                    return None
                
                torrent_info = handle.get_torrent_info()
            else:  # TORRENT_FILE
                torrent_info = lt.torrent_info(task.source)
            
            # Extract file information
            files = []
            for i in range(torrent_info.num_files()):
                file = torrent_info.file_at(i)
                files.append(FileInfo(
                    index=i,
                    name=file.path,
                    size=file.size,
                    path=os.path.join(Config.DOWNLOAD_PATH, file.path),
                    selected=True
                ))
            
            info = {
                'name': torrent_info.name(),
                'total_size': torrent_info.total_size(),
                'num_files': torrent_info.num_files(),
                'files': files,
            }
            
            # Clean up temporary handle for magnet links
            if task.download_type == DownloadType.MAGNET_LINK:
                self.session.remove_torrent(handle)
            
            return info
        except Exception as e:
            logger.error(f"Error getting torrent info: {e}")
            return None
    
    def start_download(self, task_id: str) -> bool:
        """Start downloading a torrent"""
        try:
            if task_id not in self.handles:
                logger.error(f"No handle found for task {task_id}")
                return False
            
            handle = self.handles[task_id]
            handle.resume()
            logger.info(f"Download started for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error starting download: {e}")
            return False
    
    def pause_download(self, task_id: str) -> bool:
        """Pause a download"""
        try:
            if task_id in self.handles:
                self.handles[task_id].pause()
                logger.info(f"Download paused for task {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error pausing download: {e}")
            return False
    
    def cancel_download(self, task_id: str) -> bool:
        """Cancel and remove a download"""
        try:
            if task_id in self.handles:
                handle = self.handles[task_id]
                self.session.remove_torrent(handle)
                del self.handles[task_id]
                logger.info(f"Download cancelled for task {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cancelling download: {e}")
            return False
    
    def get_progress(self, task_id: str) -> Optional[dict]:
        """Get download progress information"""
        try:
            if task_id not in self.handles:
                return None
            
            handle = self.handles[task_id]
            status = handle.status()
            
            progress_info = {
                'progress': status.progress,
                'download_rate': status.download_rate,
                'upload_rate': status.upload_rate,
                'num_peers': status.num_peers,
                'num_seeds': status.num_seeds,
                'total_download': status.total_download,
                'total_upload': status.total_upload,
                'state': str(status.state),
                'paused': status.paused,
            }
            
            # Calculate ETA
            if status.download_rate > 0:
                remaining = status.total_wanted - status.total_wanted_done
                progress_info['eta'] = int(remaining / status.download_rate)
            else:
                progress_info['eta'] = 0
            
            return progress_info
        except Exception as e:
            logger.error(f"Error getting progress: {e}")
            return None
    
    def is_download_complete(self, task_id: str) -> bool:
        """Check if download is complete"""
        try:
            if task_id not in self.handles:
                return False
            
            status = self.handles[task_id].status()
            return status.is_seeding or status.progress >= 1.0
        except Exception as e:
            logger.error(f"Error checking download completion: {e}")
            return False
    
    def get_downloaded_files(self, task: DownloadTask) -> List[str]:
        """Get list of downloaded file paths"""
        try:
            if task.task_id not in self.handles:
                return []
            
            handle = self.handles[task.task_id]
            torrent_info = handle.get_torrent_info()
            
            files = []
            for i, file_info in enumerate(task.files):
                if file_info.selected:
                    file_path = os.path.join(
                        Config.DOWNLOAD_PATH,
                        torrent_info.name(),
                        file_info.name
                    )
                    if os.path.exists(file_path):
                        files.append(file_path)
            
            return files
        except Exception as e:
            logger.error(f"Error getting downloaded files: {e}")
            return []
    
    def set_file_priorities(self, task_id: str, file_indices: List[int]) -> bool:
        """Set which files to download (selective download)"""
        try:
            if task_id not in self.handles:
                return False
            
            handle = self.handles[task_id]
            torrent_info = handle.get_torrent_info()
            
            # Set all files to don't download (priority 0)
            priorities = [0] * torrent_info.num_files()
            
            # Set selected files to normal priority (priority 4)
            for idx in file_indices:
                if idx < len(priorities):
                    priorities[idx] = 4
            
            handle.prioritize_files(priorities)
            logger.info(f"File priorities set for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting file priorities: {e}")
            return False
    
    def cleanup(self):
        """Cleanup and close session"""
        try:
            for task_id in list(self.handles.keys()):
                self.cancel_download(task_id)
            logger.info("TorrentManager cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
