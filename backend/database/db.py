import json
import aiosqlite
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path
from backend.models import TorrentInfo, TorrentState, TorrentMetadata, TorrentProgress


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS torrents (
                    id TEXT PRIMARY KEY,
                    magnet_url TEXT NOT NULL,
                    state TEXT NOT NULL,
                    metadata TEXT,
                    progress TEXT,
                    drive_file_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.commit()

    async def add_torrent(self, torrent: TorrentInfo) -> None:
        """Add a new torrent"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO torrents (id, magnet_url, state, metadata, progress, drive_file_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    torrent.id,
                    torrent.magnet_url,
                    torrent.state.value,
                    json.dumps(torrent.metadata.dict()) if torrent.metadata else None,
                    json.dumps(torrent.progress.dict()) if torrent.progress else None,
                    torrent.drive_file_id,
                    torrent.created_at.isoformat(),
                    torrent.updated_at.isoformat(),
                ),
            )
            await db.commit()

    async def update_torrent(self, torrent_id: str, **updates) -> None:
        """Update torrent fields"""
        fields = []
        values = []

        for key, value in updates.items():
            fields.append(f"{key} = ?")
            if key in ("metadata", "progress") and value:
                values.append(json.dumps(value.dict() if hasattr(value, "dict") else value))
            elif isinstance(value, Enum):
                values.append(value.value)
            else:
                values.append(value)

        if not fields:
            return

        fields.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(torrent_id)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE torrents SET {', '.join(fields)} WHERE id = ?",
                values,
            )
            await db.commit()

    async def get_torrent(self, torrent_id: str) -> Optional[TorrentInfo]:
        """Get torrent by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM torrents WHERE id = ?", (torrent_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_torrent(row)
        return None

    async def get_all_torrents(self) -> List[TorrentInfo]:
        """Get all torrents"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM torrents ORDER BY created_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_torrent(row) for row in rows]

    async def get_torrents_by_state(self, state: TorrentState) -> List[TorrentInfo]:
        """Get torrents by state"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM torrents WHERE state = ?", (state.value,)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_torrent(row) for row in rows]

    async def delete_torrent(self, torrent_id: str) -> None:
        """Delete torrent"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM torrents WHERE id = ?", (torrent_id,))
            await db.commit()

    def _row_to_torrent(self, row: aiosqlite.Row) -> TorrentInfo:
        """Convert database row to TorrentInfo"""
        return TorrentInfo(
            id=row["id"],
            magnet_url=row["magnet_url"],
            state=TorrentState(row["state"]),
            metadata=TorrentMetadata(**json.loads(row["metadata"])) if row["metadata"] else None,
            progress=TorrentProgress(**json.loads(row["progress"])) if row["progress"] else None,
            drive_file_id=row["drive_file_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


# Global database instance
db: Optional[Database] = None


async def get_db() -> Database:
    """Get database instance"""
    global db
    if db is None:
        from backend.config import settings
        db = Database(settings.database.path)
        await db.init()
    return db
