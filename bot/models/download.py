from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List
import json

class DownloadStatus(Enum):
    """Download status enumeration"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    UPLOADING_TO_TELEGRAM = "uploading_to_telegram"
    UPLOADING_TO_GDRIVE = "uploading_to_gdrive"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DownloadType(Enum):
    """Download type enumeration"""
    TORRENT_FILE = "torrent_file"
    MAGNET_LINK = "magnet_link"

@dataclass
class FileInfo:
    """Information about a file in a torrent"""
    index: int
    name: str
    size: int
    path: str
    selected: bool = True

@dataclass
class DownloadTask:
    """Download task model"""
    task_id: str
    user_id: int
    download_type: DownloadType
    source: str  # File path for torrent file or magnet link
    status: DownloadStatus
    created_at: datetime
    
    # Torrent metadata
    name: Optional[str] = None
    total_size: int = 0
    files: List[FileInfo] = field(default_factory=list)
    
    # Progress tracking
    downloaded_bytes: int = 0
    uploaded_bytes: int = 0
    download_speed: float = 0.0
    upload_speed: float = 0.0
    progress: float = 0.0
    eta: int = 0
    
    # File parts for splitting
    num_parts: int = 1
    current_part: int = 0
    
    # Telegram message IDs for progress updates
    progress_message_id: Optional[int] = None
    telegram_file_ids: List[str] = field(default_factory=list)
    
    # Google Drive
    gdrive_file_ids: List[str] = field(default_factory=list)
    gdrive_folder_id: Optional[str] = None
    
    # Error tracking
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'download_type': self.download_type.value,
            'source': self.source,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'name': self.name,
            'total_size': self.total_size,
            'files': json.dumps([vars(f) for f in self.files]),
            'downloaded_bytes': self.downloaded_bytes,
            'uploaded_bytes': self.uploaded_bytes,
            'download_speed': self.download_speed,
            'upload_speed': self.upload_speed,
            'progress': self.progress,
            'eta': self.eta,
            'num_parts': self.num_parts,
            'current_part': self.current_part,
            'progress_message_id': self.progress_message_id,
            'telegram_file_ids': json.dumps(self.telegram_file_ids),
            'gdrive_file_ids': json.dumps(self.gdrive_file_ids),
            'gdrive_folder_id': self.gdrive_folder_id,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DownloadTask':
        """Create from dictionary"""
        files_data = json.loads(data.get('files', '[]'))
        files = [FileInfo(**f) for f in files_data]
        
        return cls(
            task_id=data['task_id'],
            user_id=data['user_id'],
            download_type=DownloadType(data['download_type']),
            source=data['source'],
            status=DownloadStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            name=data.get('name'),
            total_size=data.get('total_size', 0),
            files=files,
            downloaded_bytes=data.get('downloaded_bytes', 0),
            uploaded_bytes=data.get('uploaded_bytes', 0),
            download_speed=data.get('download_speed', 0.0),
            upload_speed=data.get('upload_speed', 0.0),
            progress=data.get('progress', 0.0),
            eta=data.get('eta', 0),
            num_parts=data.get('num_parts', 1),
            current_part=data.get('current_part', 0),
            progress_message_id=data.get('progress_message_id'),
            telegram_file_ids=json.loads(data.get('telegram_file_ids', '[]')),
            gdrive_file_ids=json.loads(data.get('gdrive_file_ids', '[]')),
            gdrive_folder_id=data.get('gdrive_folder_id'),
            error_message=data.get('error_message'),
            retry_count=data.get('retry_count', 0),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
        )
