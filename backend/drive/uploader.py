import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict
from backend.models import TorrentState
from backend.database import get_db
from backend.torrent import get_engine
from backend.drive.client import get_drive_client
from backend.config import settings

logger = logging.getLogger(__name__)


class UploadWorker:
    """Manages concurrent uploads to Google Drive with retry logic"""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active_uploads: Dict[str, asyncio.Task] = {}
        self.running = False
        self._worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the upload worker"""
        if self.running:
            return

        self.running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("Upload worker started")

    async def stop(self):
        """Stop the upload worker"""
        if not self.running:
            return

        self.running = False

        # Cancel all active uploads
        for task in self.active_uploads.values():
            task.cancel()

        if self._worker_task:
            self._worker_task.cancel()

        logger.info("Upload worker stopped")

    async def add_upload(self, torrent_id: str):
        """Add torrent to upload queue"""
        await self.queue.put(torrent_id)
        logger.info(f"Torrent {torrent_id} added to upload queue")

    async def _process_queue(self):
        """Process upload queue with concurrency limit"""
        while self.running:
            try:
                # Wait for slot or queue item
                if len(self.active_uploads) >= self.max_concurrent:
                    await asyncio.sleep(1)
                    continue

                # Get next item from queue (non-blocking)
                try:
                    torrent_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Start upload task
                task = asyncio.create_task(self._upload_torrent(torrent_id))
                self.active_uploads[torrent_id] = task

                # Cleanup completed tasks
                completed = [tid for tid, t in self.active_uploads.items() if t.done()]
                for tid in completed:
                    del self.active_uploads[tid]

            except Exception as e:
                logger.error(f"Error in upload queue processing: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _upload_torrent(self, torrent_id: str):
        """Upload a completed torrent to Google Drive with retry logic"""
        db = await get_db()
        drive = await get_drive_client()
        engine = await get_engine()

        try:
            logger.info(f"Starting upload for torrent {torrent_id}")

            # Update state
            await db.update_torrent(torrent_id, state=TorrentState.UPLOADING)

            # Get torrent info
            torrent = await db.get_torrent(torrent_id)
            if not torrent or not torrent.metadata:
                raise ValueError(f"Torrent {torrent_id} not found or missing metadata")

            # Get download path
            download_path = engine.get_download_path(torrent_id)
            if not download_path or not download_path.exists():
                raise ValueError(f"Download path not found for torrent {torrent_id}")

            # Create folder in Drive for this torrent
            folder_id = await self._upload_with_retry(
                drive.create_folder,
                torrent.metadata.name,
            )

            # Upload files/folders
            if torrent.metadata.num_files == 1:
                # Single file torrent
                file_path = download_path / torrent.metadata.files[0].path
                await self._upload_with_retry(
                    drive.upload_file,
                    file_path,
                    parent_id=folder_id,
                )
            else:
                # Multi-file torrent - upload directory structure
                await self._upload_directory(drive, download_path, folder_id)

            # Update state and store Drive folder ID
            await db.update_torrent(
                torrent_id,
                state=TorrentState.UPLOADED,
                drive_file_id=folder_id,
            )

            logger.info(f"Torrent {torrent_id} uploaded successfully to Drive folder {folder_id}")

            # Optional: cleanup local files after successful upload
            # await self._cleanup_local_files(download_path)

        except asyncio.CancelledError:
            logger.info(f"Upload cancelled for torrent {torrent_id}")
            await db.update_torrent(torrent_id, state=TorrentState.COMPLETED)
            raise

        except Exception as e:
            logger.error(f"Error uploading torrent {torrent_id}: {e}", exc_info=True)
            await db.update_torrent(torrent_id, state=TorrentState.ERROR)

        finally:
            # Cleanup
            if torrent_id in self.active_uploads:
                del self.active_uploads[torrent_id]

    async def _upload_directory(self, drive, local_path: Path, parent_id: str):
        """Recursively upload directory structure to Drive"""
        for item in local_path.iterdir():
            if item.is_file():
                await self._upload_with_retry(
                    drive.upload_file,
                    item,
                    parent_id=parent_id,
                )
            elif item.is_dir():
                # Create subfolder
                subfolder_id = await self._upload_with_retry(
                    drive.create_folder,
                    item.name,
                    parent_id=parent_id,
                )
                # Recursively upload contents
                await self._upload_directory(drive, item, subfolder_id)

    async def _upload_with_retry(self, upload_func, *args, **kwargs):
        """Execute upload with exponential backoff retry"""
        max_retries = settings.google_drive.max_retries
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                return await upload_func(*args, **kwargs)

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Upload attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Upload failed after {max_retries} attempts")
                    raise

    async def _cleanup_local_files(self, path: Path):
        """Remove local files after successful upload"""
        try:
            if path.exists():
                shutil.rmtree(path)
                logger.info(f"Cleaned up local files: {path}")
        except Exception as e:
            logger.error(f"Error cleaning up local files: {e}", exc_info=True)


# Global worker instance
_upload_worker: Optional[UploadWorker] = None


async def get_upload_worker() -> UploadWorker:
    """Get global upload worker instance"""
    global _upload_worker
    if _upload_worker is None:
        _upload_worker = UploadWorker(max_concurrent=3)
        await _upload_worker.start()
    return _upload_worker
