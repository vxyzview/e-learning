import sqlite3
import logging
from typing import Optional, List
from datetime import datetime
from bot.models.download import DownloadTask, DownloadStatus
from bot.utils.config import Config
import uuid

logger = logging.getLogger(__name__)

class QueueManager:
    """Manage download queue using SQLite database"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_queue (
                task_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                download_type TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                name TEXT,
                total_size INTEGER DEFAULT 0,
                files TEXT DEFAULT '[]',
                downloaded_bytes INTEGER DEFAULT 0,
                uploaded_bytes INTEGER DEFAULT 0,
                download_speed REAL DEFAULT 0.0,
                upload_speed REAL DEFAULT 0.0,
                progress REAL DEFAULT 0.0,
                eta INTEGER DEFAULT 0,
                num_parts INTEGER DEFAULT 1,
                current_part INTEGER DEFAULT 0,
                progress_message_id INTEGER,
                telegram_file_ids TEXT DEFAULT '[]',
                gdrive_file_ids TEXT DEFAULT '[]',
                gdrive_folder_id TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                started_at TEXT,
                completed_at TEXT
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_status 
            ON download_queue(user_id, status)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def add_task(self, task: DownloadTask) -> bool:
        """Add a new task to the queue"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            task_dict = task.to_dict()
            columns = ', '.join(task_dict.keys())
            placeholders = ', '.join(['?' for _ in task_dict])
            
            cursor.execute(
                f'INSERT INTO download_queue ({columns}) VALUES ({placeholders})',
                tuple(task_dict.values())
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Task {task.task_id} added to queue")
            return True
        except Exception as e:
            logger.error(f"Error adding task to queue: {e}")
            return False
    
    def update_task(self, task: DownloadTask) -> bool:
        """Update an existing task"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            task_dict = task.to_dict()
            set_clause = ', '.join([f'{k} = ?' for k in task_dict.keys() if k != 'task_id'])
            values = [v for k, v in task_dict.items() if k != 'task_id']
            values.append(task.task_id)
            
            cursor.execute(
                f'UPDATE download_queue SET {set_clause} WHERE task_id = ?',
                values
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """Get a task by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM download_queue WHERE task_id = ?', (task_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return DownloadTask.from_dict(dict(row))
            return None
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None
    
    def get_pending_tasks(self, limit: int = None) -> List[DownloadTask]:
        """Get pending tasks"""
        return self._get_tasks_by_status(DownloadStatus.PENDING, limit)
    
    def get_active_tasks(self) -> List[DownloadTask]:
        """Get all active (downloading/uploading) tasks"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM download_queue 
                WHERE status IN (?, ?, ?)
                ORDER BY started_at ASC
            ''', (
                DownloadStatus.DOWNLOADING.value,
                DownloadStatus.UPLOADING_TO_TELEGRAM.value,
                DownloadStatus.UPLOADING_TO_GDRIVE.value
            ))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [DownloadTask.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting active tasks: {e}")
            return []
    
    def get_user_tasks(self, user_id: int, limit: int = 10) -> List[DownloadTask]:
        """Get all tasks for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM download_queue 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [DownloadTask.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting user tasks: {e}")
            return []
    
    def _get_tasks_by_status(self, status: DownloadStatus, limit: int = None) -> List[DownloadTask]:
        """Get tasks by status"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM download_queue WHERE status = ? ORDER BY created_at ASC'
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query, (status.value,))
            rows = cursor.fetchall()
            conn.close()
            
            return [DownloadTask.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting tasks by status: {e}")
            return []
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task from the queue"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM download_queue WHERE task_id = ?', (task_id,))
            conn.commit()
            conn.close()
            logger.info(f"Task {task_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False
    
    def get_queue_size(self) -> int:
        """Get total number of tasks in queue"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM download_queue WHERE status = ?', 
                          (DownloadStatus.PENDING.value,))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return 0
    
    @staticmethod
    def generate_task_id() -> str:
        """Generate a unique task ID"""
        return str(uuid.uuid4())
