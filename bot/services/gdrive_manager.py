import os
import io
import logging
from typing import List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from bot.utils.config import Config

logger = logging.getLogger(__name__)

# Scopes required for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveManager:
    """Manage uploads to Google Drive"""
    
    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        token_path = Config.GOOGLE_TOKEN_PATH
        creds_path = Config.GOOGLE_CREDENTIALS_PATH
        
        # Check if token.json exists
        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        # If no valid credentials, authenticate
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    logger.info("Refreshed Google Drive credentials")
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    self.creds = None
            
            if not self.creds:
                if not os.path.exists(creds_path):
                    logger.error(f"Credentials file not found: {creds_path}")
                    logger.info("Please follow the setup instructions to create credentials.json")
                    return
                
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
                logger.info("Obtained new Google Drive credentials")
            
            # Save credentials for future use
            with open(token_path, 'w') as token:
                token.write(self.creds.to_json())
        
        # Build the service
        if self.creds:
            self.service = build('drive', 'v3', credentials=self.creds)
            logger.info("Google Drive service initialized")
        else:
            logger.warning("Google Drive service not initialized - credentials missing")
    
    def upload_file(self, file_path: str, folder_id: str = None, 
                   file_name: str = None) -> Optional[str]:
        """
        Upload a file to Google Drive
        
        Returns:
            File ID of uploaded file, or None on error
        """
        if not self.service:
            logger.error("Google Drive service not initialized")
            return None
        
        try:
            name = file_name or os.path.basename(file_path)
            
            file_metadata = {'name': name}
            
            # Set parent folder if specified
            if folder_id or Config.GOOGLE_DRIVE_FOLDER_ID:
                parent_id = folder_id or Config.GOOGLE_DRIVE_FOLDER_ID
                file_metadata['parents'] = [parent_id]
            
            # Determine MIME type
            mime_type = self._get_mime_type(file_path)
            
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            web_link = file.get('webViewLink')
            
            logger.info(f"Uploaded {name} to Google Drive (ID: {file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"Error uploading file to Google Drive: {e}")
            return None
    
    def upload_from_telegram(self, file_id: str, bot, folder_id: str = None, 
                           file_name: str = None) -> Optional[str]:
        """
        Download file from Telegram and upload to Google Drive
        
        Returns:
            Google Drive file ID, or None on error
        """
        if not self.service:
            logger.error("Google Drive service not initialized")
            return None
        
        try:
            # Download file from Telegram
            file = bot.get_file(file_id)
            file_bytes = file.download_as_bytearray()
            
            name = file_name or f"telegram_file_{file_id[:8]}"
            
            file_metadata = {'name': name}
            
            # Set parent folder if specified
            if folder_id or Config.GOOGLE_DRIVE_FOLDER_ID:
                parent_id = folder_id or Config.GOOGLE_DRIVE_FOLDER_ID
                file_metadata['parents'] = [parent_id]
            
            # Upload from memory
            fh = io.BytesIO(file_bytes)
            media = MediaIoBaseUpload(fh, mimetype='application/octet-stream', resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Uploaded {name} to Google Drive from Telegram (ID: {file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"Error uploading from Telegram to Google Drive: {e}")
            return None
    
    def upload_multiple_files(self, file_paths: List[str], folder_id: str = None) -> dict:
        """
        Upload multiple files to Google Drive
        
        Returns:
            Dict mapping file paths to Google Drive file IDs
        """
        results = {}
        
        for file_path in file_paths:
            file_id = self.upload_file(file_path, folder_id)
            results[file_path] = file_id
        
        return results
    
    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> Optional[str]:
        """
        Create a folder in Google Drive
        
        Returns:
            Folder ID, or None on error
        """
        if not self.service:
            logger.error("Google Drive service not initialized")
            return None
        
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id or Config.GOOGLE_DRIVE_FOLDER_ID:
                parent_id = parent_folder_id or Config.GOOGLE_DRIVE_FOLDER_ID
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created folder '{folder_name}' (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return None
    
    def get_file_link(self, file_id: str) -> Optional[str]:
        """Get shareable link for a file"""
        if not self.service:
            return None
        
        try:
            # Make file accessible to anyone with the link
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            # Get the web view link
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            return file.get('webViewLink')
            
        except Exception as e:
            logger.error(f"Error getting file link: {e}")
            return None
    
    def _get_mime_type(self, file_path: str) -> str:
        """Determine MIME type from file extension"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'
    
    def is_authenticated(self) -> bool:
        """Check if Google Drive is authenticated"""
        return self.service is not None
