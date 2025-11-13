from .torrents import router as torrents_router
from .storage import router as storage_router

__all__ = ["torrents_router", "storage_router"]
