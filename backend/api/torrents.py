import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from backend.models import (
    TorrentRequest,
    TorrentDownloadRequest,
    TorrentInfo,
    TorrentMetadata,
    TorrentProgress,
    TorrentState,
)
from backend.database import get_db
from backend.torrent import get_engine, get_torrent_worker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/torrents", tags=["torrents"])


@router.post("/metadata", response_model=TorrentMetadata)
async def fetch_metadata(request: TorrentRequest):
    """
    Fetch torrent metadata from magnet link without downloading
    """
    try:
        engine = await get_engine()
        metadata = await engine.fetch_metadata(request.magnet_url, timeout=60)
        return metadata

    except TimeoutError:
        raise HTTPException(status_code=408, detail="Metadata fetch timed out")
    except Exception as e:
        logger.error(f"Error fetching metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TorrentInfo)
async def add_torrent(request: TorrentRequest):
    """
    Add torrent to database and fetch metadata
    """
    try:
        db = await get_db()
        engine = await get_engine()

        # Generate torrent ID
        torrent_id = str(uuid.uuid4())

        # Fetch metadata first
        metadata = await engine.fetch_metadata(request.magnet_url, timeout=60)

        # Create torrent info
        torrent = TorrentInfo(
            id=torrent_id,
            magnet_url=request.magnet_url,
            state=TorrentState.METADATA_READY,
            metadata=metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Save to database
        await db.add_torrent(torrent)

        logger.info(f"Torrent {torrent_id} added successfully")
        return torrent

    except Exception as e:
        logger.error(f"Error adding torrent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{torrent_id}/download")
async def start_download(torrent_id: str, request: TorrentDownloadRequest):
    """
    Start downloading selected files from torrent
    """
    try:
        db = await get_db()
        worker = await get_torrent_worker()

        # Get torrent
        torrent = await db.get_torrent(torrent_id)
        if not torrent:
            raise HTTPException(status_code=404, detail="Torrent not found")

        if torrent.state not in [TorrentState.METADATA_READY, TorrentState.PAUSED]:
            raise HTTPException(status_code=400, detail=f"Cannot start download in state: {torrent.state}")

        # Add to download queue
        await worker.add_download(
            torrent_id,
            torrent.magnet_url,
            request.file_indices,
        )

        return {"status": "queued", "torrent_id": torrent_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting download: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[TorrentInfo])
async def list_torrents(state: Optional[TorrentState] = None):
    """
    List all torrents, optionally filtered by state
    """
    try:
        db = await get_db()

        if state:
            torrents = await db.get_torrents_by_state(state)
        else:
            torrents = await db.get_all_torrents()

        return torrents

    except Exception as e:
        logger.error(f"Error listing torrents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{torrent_id}", response_model=TorrentInfo)
async def get_torrent(torrent_id: str):
    """
    Get torrent details by ID
    """
    try:
        db = await get_db()
        torrent = await db.get_torrent(torrent_id)

        if not torrent:
            raise HTTPException(status_code=404, detail="Torrent not found")

        return torrent

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting torrent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{torrent_id}/progress", response_model=TorrentProgress)
async def get_progress(torrent_id: str):
    """
    Get real-time progress for a downloading torrent
    """
    try:
        db = await get_db()
        engine = await get_engine()

        # Get from database first
        torrent = await db.get_torrent(torrent_id)
        if not torrent:
            raise HTTPException(status_code=404, detail="Torrent not found")

        # If downloading, get live progress
        if torrent.state == TorrentState.DOWNLOADING:
            progress = await engine.get_progress(torrent_id)
            if progress:
                # Update database
                await db.update_torrent(torrent_id, progress=progress)
                return progress

        # Return stored progress
        if torrent.progress:
            return torrent.progress

        # Return default progress
        return TorrentProgress(
            torrent_id=torrent_id,
            state=torrent.state,
            progress=0.0,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{torrent_id}/pause")
async def pause_torrent(torrent_id: str):
    """
    Pause a downloading torrent
    """
    try:
        db = await get_db()
        engine = await get_engine()

        torrent = await db.get_torrent(torrent_id)
        if not torrent:
            raise HTTPException(status_code=404, detail="Torrent not found")

        success = await engine.pause_torrent(torrent_id)
        if success:
            await db.update_torrent(torrent_id, state=TorrentState.PAUSED)
            return {"status": "paused"}

        raise HTTPException(status_code=400, detail="Failed to pause torrent")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing torrent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{torrent_id}/resume")
async def resume_torrent(torrent_id: str):
    """
    Resume a paused torrent
    """
    try:
        db = await get_db()
        engine = await get_engine()

        torrent = await db.get_torrent(torrent_id)
        if not torrent:
            raise HTTPException(status_code=404, detail="Torrent not found")

        success = await engine.resume_torrent(torrent_id)
        if success:
            await db.update_torrent(torrent_id, state=TorrentState.DOWNLOADING)
            return {"status": "resumed"}

        raise HTTPException(status_code=400, detail="Failed to resume torrent")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming torrent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{torrent_id}")
async def delete_torrent(torrent_id: str, delete_files: bool = False):
    """
    Delete torrent from database and optionally remove files
    """
    try:
        db = await get_db()
        engine = await get_engine()

        torrent = await db.get_torrent(torrent_id)
        if not torrent:
            raise HTTPException(status_code=404, detail="Torrent not found")

        # Remove from engine if active
        await engine.remove_torrent(torrent_id, delete_files=delete_files)

        # Remove from database
        await db.delete_torrent(torrent_id)

        return {"status": "deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting torrent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
