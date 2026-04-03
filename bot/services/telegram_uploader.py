import os
import logging
from typing import List, Optional
from telegram import Bot, InputFile
from bot.utils.config import Config
from bot.utils.helpers import split_file_into_parts, format_bytes

logger = logging.getLogger(__name__)

class TelegramUploader:
    """Upload files to Telegram with automatic chunking for large files"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.chunk_size = Config.TELEGRAM_FILE_CHUNK_SIZE_BYTES
    
    async def upload_file(self, file_path: str, chat_id: int, caption: str = None, 
                         progress_callback: callable = None) -> List[str]:
        """
        Upload a file to Telegram, splitting into parts if necessary
        
        Returns:
            List of file_id strings for uploaded files
        """
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        
        # If file is small enough, upload directly
        if file_size <= self.chunk_size:
            return await self._upload_single_file(file_path, chat_id, caption)
        
        # Large file - split into parts
        logger.info(f"File {file_name} ({format_bytes(file_size)}) will be split into parts")
        return await self._upload_file_in_parts(file_path, chat_id, caption, progress_callback)
    
    async def _upload_single_file(self, file_path: str, chat_id: int, 
                                  caption: str = None) -> List[str]:
        """Upload a single file to Telegram"""
        try:
            file_name = os.path.basename(file_path)
            
            with open(file_path, 'rb') as f:
                message = await self.bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(f, filename=file_name),
                    caption=caption or f"📁 {file_name}",
                    read_timeout=300,
                    write_timeout=300,
                )
            
            file_id = message.document.file_id
            logger.info(f"Uploaded {file_name} to Telegram")
            return [file_id]
            
        except Exception as e:
            logger.error(f"Error uploading file to Telegram: {e}")
            raise
    
    async def _upload_file_in_parts(self, file_path: str, chat_id: int, 
                                   caption: str = None, 
                                   progress_callback: callable = None) -> List[str]:
        """Upload a large file split into parts"""
        try:
            file_name = os.path.basename(file_path)
            parts = split_file_into_parts(file_path, self.chunk_size)
            file_ids = []
            
            logger.info(f"Splitting {file_name} into {len(parts)} parts")
            
            for part in parts:
                part_num = part['part_num']
                total_parts = part['total_parts']
                start = part['start']
                end = part['end']
                
                # Create part filename
                base_name, ext = os.path.splitext(file_name)
                part_filename = f"{base_name}.part{part_num:03d}{ext}"
                part_path = os.path.join(os.path.dirname(file_path), part_filename)
                
                # Extract part from original file
                logger.info(f"Creating part {part_num}/{total_parts}: {part_filename}")
                with open(file_path, 'rb') as src:
                    src.seek(start)
                    data = src.read(end - start)
                    
                    with open(part_path, 'wb') as dst:
                        dst.write(data)
                
                # Upload part
                part_caption = f"📦 Part {part_num}/{total_parts}\n{caption or file_name}"
                
                with open(part_path, 'rb') as f:
                    message = await self.bot.send_document(
                        chat_id=chat_id,
                        document=InputFile(f, filename=part_filename),
                        caption=part_caption,
                        read_timeout=300,
                        write_timeout=300,
                    )
                
                file_ids.append(message.document.file_id)
                logger.info(f"Uploaded part {part_num}/{total_parts}")
                
                # Clean up part file
                try:
                    os.remove(part_path)
                except:
                    pass
                
                # Progress callback
                if progress_callback:
                    await progress_callback(part_num, total_parts)
            
            logger.info(f"Successfully uploaded {file_name} in {len(parts)} parts")
            return file_ids
            
        except Exception as e:
            logger.error(f"Error uploading file in parts: {e}")
            raise
    
    async def upload_multiple_files(self, file_paths: List[str], chat_id: int, 
                                   caption_prefix: str = None) -> dict:
        """
        Upload multiple files to Telegram
        
        Returns:
            Dict mapping file paths to list of file_ids
        """
        results = {}
        
        for file_path in file_paths:
            file_name = os.path.basename(file_path)
            caption = f"{caption_prefix}\n📁 {file_name}" if caption_prefix else file_name
            
            try:
                file_ids = await self.upload_file(file_path, chat_id, caption)
                results[file_path] = file_ids
                logger.info(f"Successfully uploaded {file_name}")
            except Exception as e:
                logger.error(f"Failed to upload {file_name}: {e}")
                results[file_path] = []
        
        return results
    
    async def download_file(self, file_id: str, destination_path: str) -> bool:
        """Download a file from Telegram by file_id"""
        try:
            file = await self.bot.get_file(file_id)
            await file.download_to_drive(destination_path)
            logger.info(f"Downloaded file from Telegram to {destination_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading file from Telegram: {e}")
            return False
