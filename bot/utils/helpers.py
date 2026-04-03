import os
import humanize
from datetime import datetime
from typing import Optional

def format_bytes(bytes_size: int) -> str:
    """Format bytes to human readable format"""
    return humanize.naturalsize(bytes_size, binary=True)

def format_speed(bytes_per_second: float) -> str:
    """Format speed in bytes/second to human readable format"""
    return f"{humanize.naturalsize(bytes_per_second, binary=True)}/s"

def format_time(seconds: int) -> str:
    """Format seconds to human readable time"""
    if seconds < 0:
        return "Unknown"
    return humanize.naturaldelta(seconds)

def format_progress_bar(progress: float, length: int = 20) -> str:
    """Create a progress bar string"""
    filled = int(length * progress)
    bar = '█' * filled + '░' * (length - filled)
    percentage = int(progress * 100)
    return f"{bar} {percentage}%"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system operations"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def split_file_into_parts(file_path: str, chunk_size_bytes: int) -> list:
    """Calculate how to split a file into parts based on chunk size"""
    file_size = os.path.getsize(file_path)
    num_parts = (file_size + chunk_size_bytes - 1) // chunk_size_bytes
    
    parts = []
    for i in range(num_parts):
        start = i * chunk_size_bytes
        end = min((i + 1) * chunk_size_bytes, file_size)
        parts.append({
            'part_num': i + 1,
            'total_parts': num_parts,
            'start': start,
            'end': end,
            'size': end - start
        })
    
    return parts

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return os.path.splitext(filename)[1]

def ensure_directory(path: str) -> None:
    """Ensure directory exists, create if it doesn't"""
    os.makedirs(path, exist_ok=True)
