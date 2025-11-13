import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List

from .config import settings
from .database import get_db
from .torrent import get_engine, get_torrent_worker
from .drive import get_upload_worker
from .api import torrents_router, storage_router
from .models import TorrentState

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.logging.level),
    format=settings.logging.format,
)
logger = logging.getLogger(__name__)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


manager = ConnectionManager()


# Progress broadcaster task
async def broadcast_progress():
    """Periodically broadcast torrent progress to all connected clients"""
    db = await get_db()
    engine = await get_engine()

    while True:
        try:
            # Get all active torrents
            active_states = [
                TorrentState.DOWNLOADING,
                TorrentState.UPLOADING,
            ]

            for state in active_states:
                torrents = await db.get_torrents_by_state(state)

                for torrent in torrents:
                    # Get live progress
                    if state == TorrentState.DOWNLOADING:
                        progress = await engine.get_progress(torrent.id)
                        if progress:
                            await manager.broadcast({
                                "type": "progress",
                                "torrent_id": torrent.id,
                                "data": progress.dict(),
                            })

            await asyncio.sleep(2)  # Broadcast every 2 seconds

        except Exception as e:
            logger.error(f"Error in progress broadcaster: {e}", exc_info=True)
            await asyncio.sleep(5)


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    logger.info("Starting Torrent-to-Drive application...")

    # Initialize database
    db = await get_db()
    await db.init()
    logger.info("Database initialized")

    # Start torrent engine
    engine = await get_engine()
    await engine.start()
    logger.info("Torrent engine started")

    # Start workers
    torrent_worker = await get_torrent_worker()
    await torrent_worker.start()
    logger.info("Torrent worker started")

    upload_worker = await get_upload_worker()
    await upload_worker.start()
    logger.info("Upload worker started")

    # Start progress broadcaster
    broadcaster_task = asyncio.create_task(broadcast_progress())
    logger.info("Progress broadcaster started")

    logger.info("Application startup complete")

    yield

    # Cleanup
    logger.info("Shutting down application...")
    broadcaster_task.cancel()
    await torrent_worker.stop()
    await upload_worker.stop()
    await engine.stop()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Torrent-to-Drive",
    description="High-performance torrent downloader with Google Drive integration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(torrents_router)
app.include_router(storage_router)


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Health check
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "torrent-to-drive",
    }


# Serve frontend (if built)
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_path / "index.html"))

    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        file_path = frontend_path / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_path / "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
    )
