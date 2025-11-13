import os
import yaml
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


class TorrentConfig(BaseModel):
    download_path: str = "./data/torrents"
    listen_ports: list[int] = [6881, 6891]
    max_connections: int = 200
    max_uploads: int = 50
    upload_rate_limit: int = 0
    download_rate_limit: int = 0
    max_concurrent_downloads: int = 5


class GoogleDriveConfig(BaseModel):
    credentials_file: str = "./config/credentials.json"
    token_file: str = "./config/token.json"
    shared_folder_id: str = ""
    chunk_size: int = 10485760
    max_retries: int = 5


class DatabaseConfig(BaseModel):
    path: str = "./data/torrents.db"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class Settings(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    torrent: TorrentConfig = Field(default_factory=TorrentConfig)
    google_drive: GoogleDriveConfig = Field(default_factory=GoogleDriveConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, config_path: str = "./config/settings.yaml") -> "Settings":
        """Load settings from YAML file with environment variable overrides"""
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        # Environment variable overrides
        if folder_id := os.getenv("DRIVE_FOLDER_ID"):
            data.setdefault("google_drive", {})["shared_folder_id"] = folder_id

        return cls(**data)


# Global settings instance
settings = Settings.load()
