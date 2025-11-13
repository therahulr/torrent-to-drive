import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from backend.models import DriveFile
from backend.drive import get_drive_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/files", response_model=List[DriveFile])
async def list_files(folder_id: Optional[str] = None):
    """
    List all files in the configured Google Drive folder
    """
    try:
        drive = await get_drive_client()
        files = await drive.list_files(folder_id=folder_id)
        return files

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}", response_model=DriveFile)
async def get_file(file_id: str):
    """
    Get metadata for a specific file
    """
    try:
        drive = await get_drive_client()
        file = await drive.get_file_metadata(file_id)
        return file

    except Exception as e:
        logger.error(f"Error getting file metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Check if Google Drive connection is working
    """
    try:
        drive = await get_drive_client()
        # Test connection by listing files
        await drive.list_files(page_size=1)
        return {"status": "healthy", "service": "google_drive"}

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {"status": "unhealthy", "service": "google_drive", "error": str(e)}
