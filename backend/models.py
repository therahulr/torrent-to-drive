from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List


class TorrentState(str, Enum):
    FETCHING_METADATA = "fetching_metadata"
    METADATA_READY = "metadata_ready"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    ERROR = "error"
    PAUSED = "paused"


class FileInfo(BaseModel):
    index: int
    path: str
    size: int
    selected: bool = False


class TorrentMetadata(BaseModel):
    name: str
    total_size: int
    num_files: int
    files: List[FileInfo]
    info_hash: str
    trackers: List[str] = []
    comment: Optional[str] = None
    creation_date: Optional[int] = None


class TorrentProgress(BaseModel):
    torrent_id: str
    state: TorrentState
    progress: float = 0.0  # 0-100
    download_rate: int = 0  # bytes/sec
    upload_rate: int = 0  # bytes/sec
    num_peers: int = 0
    num_seeds: int = 0
    downloaded: int = 0
    total_size: int = 0
    eta: Optional[int] = None  # seconds
    error: Optional[str] = None


class TorrentRequest(BaseModel):
    magnet_url: str


class TorrentDownloadRequest(BaseModel):
    torrent_id: str
    file_indices: Optional[List[int]] = None  # None = all files


class DriveFile(BaseModel):
    id: str
    name: str
    size: int
    mime_type: str
    created_time: datetime
    web_view_link: Optional[str] = None
    web_content_link: Optional[str] = None
    is_folder: bool = False


class TorrentInfo(BaseModel):
    id: str
    magnet_url: str
    state: TorrentState
    metadata: Optional[TorrentMetadata] = None
    progress: Optional[TorrentProgress] = None
    created_at: datetime
    updated_at: datetime
    drive_file_id: Optional[str] = None
