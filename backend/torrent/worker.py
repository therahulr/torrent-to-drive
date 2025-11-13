import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
from ..models import TorrentState, TorrentProgress, TorrentInfo
from ..database import get_db
from .engine import get_engine
from ..config import settings

logger = logging.getLogger(__name__)


class TorrentWorker:
    """Manages concurrent torrent downloads with queue processing"""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active_downloads: Dict[str, asyncio.Task] = {}
        self.running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._progress_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the worker"""
        if self.running:
            return

        self.running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        self._progress_task = asyncio.create_task(self._update_progress())
        logger.info("Torrent worker started")

    async def stop(self):
        """Stop the worker"""
        if not self.running:
            return

        self.running = False

        # Cancel all active downloads
        for task in self.active_downloads.values():
            task.cancel()

        if self._worker_task:
            self._worker_task.cancel()
        if self._progress_task:
            self._progress_task.cancel()

        logger.info("Torrent worker stopped")

    async def add_download(self, torrent_id: str, magnet_url: str, file_indices: Optional[list] = None):
        """Add torrent to download queue"""
        await self.queue.put((torrent_id, magnet_url, file_indices))
        logger.info(f"Torrent {torrent_id} added to queue (queue size: {self.queue.qsize()})")

    async def _process_queue(self):
        """Process download queue with concurrency limit"""
        while self.running:
            try:
                # Wait for slot or queue item
                if len(self.active_downloads) >= self.max_concurrent:
                    await asyncio.sleep(1)
                    continue

                # Get next item from queue (non-blocking)
                try:
                    torrent_id, magnet_url, file_indices = await asyncio.wait_for(
                        self.queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Start download task
                task = asyncio.create_task(
                    self._download_torrent(torrent_id, magnet_url, file_indices)
                )
                self.active_downloads[torrent_id] = task

                # Cleanup completed tasks
                completed = [tid for tid, t in self.active_downloads.items() if t.done()]
                for tid in completed:
                    del self.active_downloads[tid]

            except Exception as e:
                logger.error(f"Error in queue processing: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _download_torrent(self, torrent_id: str, magnet_url: str, file_indices: Optional[list]):
        """Download a single torrent"""
        db = await get_db()
        engine = await get_engine()

        try:
            logger.info(f"Starting download for torrent {torrent_id}")

            # Update state to downloading
            await db.update_torrent(torrent_id, state=TorrentState.DOWNLOADING)

            # Add to engine
            await engine.add_torrent(torrent_id, magnet_url, file_indices)

            # Wait for completion
            while not engine.is_completed(torrent_id):
                await asyncio.sleep(2)

            # Mark as completed
            await db.update_torrent(torrent_id, state=TorrentState.COMPLETED)
            logger.info(f"Torrent {torrent_id} completed successfully")

            # Trigger upload (will be handled by upload worker)
            from ..drive.worker import get_upload_worker
            upload_worker = await get_upload_worker()
            await upload_worker.add_upload(torrent_id)

        except asyncio.CancelledError:
            logger.info(f"Download cancelled for torrent {torrent_id}")
            await db.update_torrent(torrent_id, state=TorrentState.PAUSED)
            raise

        except Exception as e:
            logger.error(f"Error downloading torrent {torrent_id}: {e}", exc_info=True)
            progress = TorrentProgress(
                torrent_id=torrent_id,
                state=TorrentState.ERROR,
                error=str(e),
            )
            await db.update_torrent(
                torrent_id,
                state=TorrentState.ERROR,
                progress=progress,
            )

        finally:
            # Cleanup
            if torrent_id in self.active_downloads:
                del self.active_downloads[torrent_id]

    async def _update_progress(self):
        """Periodically update progress for all active downloads"""
        db = await get_db()
        engine = await get_engine()

        while self.running:
            try:
                for torrent_id in list(self.active_downloads.keys()):
                    progress = await engine.get_progress(torrent_id)
                    if progress:
                        await db.update_torrent(torrent_id, progress=progress)

                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error updating progress: {e}", exc_info=True)
                await asyncio.sleep(5)


# Global worker instance
_worker: Optional[TorrentWorker] = None


async def get_torrent_worker() -> TorrentWorker:
    """Get global torrent worker instance"""
    global _worker
    if _worker is None:
        _worker = TorrentWorker(max_concurrent=settings.torrent.max_concurrent_downloads)
        await _worker.start()
    return _worker
