import os
import logging
from pathlib import Path
from typing import Optional, List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import pickle
from ..models import DriveFile
from ..config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

# Scopes required for Google Drive access
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveClient:
    """Google Drive API client with OAuth2 authentication"""

    def __init__(self):
        self.credentials: Optional[Credentials] = None
        self.service = None

    async def authenticate(self):
        """Authenticate with Google Drive using OAuth2"""
        token_file = settings.google_drive.token_file
        creds_file = settings.google_drive.credentials_file

        # Load existing credentials
        if os.path.exists(token_file):
            with open(token_file, "rb") as token:
                self.credentials = pickle.load(token)

        # Refresh or get new credentials
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                logger.info("Refreshing Google Drive credentials...")
                self.credentials.refresh(Request())
            else:
                if not os.path.exists(creds_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {creds_file}\n"
                        "Please download from Google Cloud Console and place it at this location."
                    )

                logger.info("Starting OAuth2 flow for Google Drive...")
                flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
                self.credentials = flow.run_local_server(port=0)

            # Save credentials
            os.makedirs(os.path.dirname(token_file), exist_ok=True)
            with open(token_file, "wb") as token:
                pickle.dump(self.credentials, token)

        # Build service
        self.service = build("drive", "v3", credentials=self.credentials)
        logger.info("Google Drive client authenticated successfully")

    async def list_files(self, folder_id: Optional[str] = None, page_size: int = 100) -> List[DriveFile]:
        """List files in the specified folder or shared folder"""
        if not self.service:
            await self.authenticate()

        folder_id = folder_id or settings.google_drive.shared_folder_id
        if not folder_id:
            raise ValueError("Google Drive folder ID not configured")

        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    fields="files(id, name, size, mimeType, createdTime, webViewLink, webContentLink)",
                    orderBy="createdTime desc",
                )
                .execute()
            )

            files = []
            for item in results.get("files", []):
                files.append(
                    DriveFile(
                        id=item["id"],
                        name=item["name"],
                        size=int(item.get("size", 0)),
                        mime_type=item["mimeType"],
                        created_time=datetime.fromisoformat(item["createdTime"].replace("Z", "+00:00")),
                        web_view_link=item.get("webViewLink"),
                        web_content_link=item.get("webContentLink"),
                        is_folder=item["mimeType"] == "application/vnd.google-apps.folder",
                    )
                )

            logger.info(f"Listed {len(files)} files from Drive folder {folder_id}")
            return files

        except HttpError as e:
            logger.error(f"Error listing files: {e}", exc_info=True)
            raise

    async def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Create a folder in Google Drive"""
        if not self.service:
            await self.authenticate()

        parent_id = parent_id or settings.google_drive.shared_folder_id

        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }

        try:
            folder = self.service.files().create(body=file_metadata, fields="id").execute()
            folder_id = folder.get("id")
            logger.info(f"Created folder '{name}' with ID: {folder_id}")
            return folder_id

        except HttpError as e:
            logger.error(f"Error creating folder: {e}", exc_info=True)
            raise

    async def upload_file(
        self,
        file_path: Path,
        parent_id: Optional[str] = None,
        resumable: bool = True,
    ) -> str:
        """
        Upload a file to Google Drive with resumable upload support
        Returns: file_id
        """
        if not self.service:
            await self.authenticate()

        parent_id = parent_id or settings.google_drive.shared_folder_id
        if not parent_id:
            raise ValueError("Google Drive folder ID not configured")

        file_metadata = {
            "name": file_path.name,
            "parents": [parent_id],
        }

        try:
            # Use resumable upload for large files
            media = MediaFileUpload(
                str(file_path),
                resumable=resumable,
                chunksize=settings.google_drive.chunk_size,
            )

            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )

            file_id = file.get("id")
            logger.info(f"Uploaded file '{file_path.name}' to Drive with ID: {file_id}")
            return file_id

        except HttpError as e:
            logger.error(f"Error uploading file: {e}", exc_info=True)
            raise

    async def delete_file(self, file_id: str):
        """Delete a file from Google Drive"""
        if not self.service:
            await self.authenticate()

        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file with ID: {file_id}")

        except HttpError as e:
            logger.error(f"Error deleting file: {e}", exc_info=True)
            raise

    async def get_file_metadata(self, file_id: str) -> DriveFile:
        """Get metadata for a specific file"""
        if not self.service:
            await self.authenticate()

        try:
            file = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, size, mimeType, createdTime, webViewLink, webContentLink",
                )
                .execute()
            )

            return DriveFile(
                id=file["id"],
                name=file["name"],
                size=int(file.get("size", 0)),
                mime_type=file["mimeType"],
                created_time=datetime.fromisoformat(file["createdTime"].replace("Z", "+00:00")),
                web_view_link=file.get("webViewLink"),
                web_content_link=file.get("webContentLink"),
                is_folder=file["mimeType"] == "application/vnd.google-apps.folder",
            )

        except HttpError as e:
            logger.error(f"Error getting file metadata: {e}", exc_info=True)
            raise


# Global client instance
_client: Optional[GoogleDriveClient] = None


async def get_drive_client() -> GoogleDriveClient:
    """Get global Google Drive client instance"""
    global _client
    if _client is None:
        _client = GoogleDriveClient()
        await _client.authenticate()
    return _client
