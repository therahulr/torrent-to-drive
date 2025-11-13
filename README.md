# Torrent-to-Drive

High-performance torrent downloader with automatic Google Drive upload. Built for Google Cloud VMs.

## Architecture

### Technology Stack
- **Backend**: FastAPI (async, WebSocket support)
- **Torrent Engine**: libtorrent (production-grade, used by qBittorrent/Deluge)
- **Storage**: Google Drive API v3 with resumable uploads
- **Frontend**: React + Vite
- **Database**: SQLite (async)
- **Concurrency**: asyncio with worker queues

### System Flow
1. User pastes magnet URL → Backend fetches metadata via libtorrent
2. User selects files → Download worker starts (async queue)
3. On completion → Upload worker pushes to Google Drive (chunked, resumable)
4. WebSocket broadcasts real-time progress updates
5. Storage UI queries Drive API for file listing

## Features

- **Torrent Management**
  - Fetch full metadata from magnet links (files, size, seeders, trackers)
  - Selective file downloading
  - Concurrent downloads with configurable limits
  - Resume support
  - Real-time progress tracking (speed, ETA, peers)

- **Google Drive Integration**
  - Automatic upload to shared folder
  - Chunked resumable uploads
  - Retry logic with exponential backoff
  - Directory structure preservation

- **Web Interface**
  - Clean, minimal UI
  - Real-time WebSocket updates
  - Torrent page: Add, monitor, control downloads
  - Storage page: Browse and download uploaded files

## Installation

### Prerequisites
- Debian/Ubuntu-based system (Google Cloud VM)
- Python 3.9+
- Node.js 16+
- Internet connection

### Quick Setup

```bash
# Clone repository
git clone <repository-url>
cd torrent-to-drive

# Make scripts executable
chmod +x setup.sh start.sh

# Run setup
./setup.sh
```

The setup script will:
1. Install system dependencies (Python, libtorrent, Node.js)
2. Create Python virtual environment
3. Install Python packages
4. Build frontend
5. Create necessary directories

## Google Drive API Setup

### 1. Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Create new project or select existing
3. Enable **Google Drive API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

### 2. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure consent screen if prompted:
   - User Type: External
   - Add your email as test user
4. Application type: **Desktop app**
5. Name: "Torrent-to-Drive"
6. Click "Create"
7. Download JSON file

### 3. Configure Credentials

```bash
# Place downloaded file
mv ~/Downloads/client_secret_*.json ./config/credentials.json
```

### 4. Get Shared Folder ID

1. Create or open folder in Google Drive
2. Right-click folder > "Share"
3. Set appropriate permissions
4. Copy folder ID from URL:
   - URL: `https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9`
   - Folder ID: `1a2b3c4d5e6f7g8h9`

### 5. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env
nano .env
```

Set your folder ID:
```
DRIVE_FOLDER_ID=your_folder_id_here
```

## Configuration

Edit `config/settings.yaml` to customize:

```yaml
server:
  host: "0.0.0.0"
  port: 8000

torrent:
  download_path: "./data/torrents"
  max_concurrent_downloads: 5  # Adjust based on bandwidth
  max_connections: 200
  upload_rate_limit: 0  # 0 = unlimited (bytes/sec)
  download_rate_limit: 0

google_drive:
  chunk_size: 10485760  # 10MB chunks
  max_retries: 5
```

## Running the Application

### Start Server

```bash
./start.sh
```

On first run:
1. Browser opens for Google OAuth authentication
2. Sign in with your Google account
3. Grant permissions
4. Token saved to `config/token.json`

### Access Web Interface

Open browser: http://localhost:8000

Or from remote machine: http://YOUR_VM_IP:8000

### Running as Service (Production)

Create systemd service:

```bash
sudo nano /etc/systemd/system/torrent-to-drive.service
```

```ini
[Unit]
Description=Torrent-to-Drive Service
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/torrent-to-drive
Environment="PATH=/home/YOUR_USER/torrent-to-drive/venv/bin"
ExecStart=/home/YOUR_USER/torrent-to-drive/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable torrent-to-drive
sudo systemctl start torrent-to-drive
sudo systemctl status torrent-to-drive
```

## Usage

### Adding a Torrent

1. Navigate to "Torrents" page
2. Paste magnet URL in input box
3. Click "Fetch Metadata"
4. Review torrent info (name, size, files)
5. Select files to download (or "Select All")
6. Click "Start Download"

### Monitoring Progress

- Real-time progress bars
- Download/upload speeds
- Peer/seed count
- ETA calculation
- State transitions: downloading → completed → uploading → uploaded

### Accessing Files

1. Navigate to "Storage" page
2. Browse uploaded files/folders
3. Click "Download" to get file from Drive
4. Files open in Google Drive web interface

## API Endpoints

### Torrents

- `POST /api/torrents/metadata` - Fetch metadata from magnet
- `POST /api/torrents/` - Add torrent
- `POST /api/torrents/{id}/download` - Start download
- `GET /api/torrents/` - List all torrents
- `GET /api/torrents/{id}` - Get torrent details
- `GET /api/torrents/{id}/progress` - Get live progress
- `POST /api/torrents/{id}/pause` - Pause download
- `POST /api/torrents/{id}/resume` - Resume download
- `DELETE /api/torrents/{id}` - Delete torrent

### Storage

- `GET /api/storage/files` - List Drive files
- `GET /api/storage/files/{id}` - Get file metadata
- `GET /api/storage/health` - Check Drive connection

### WebSocket

- `WS /ws` - Real-time progress updates

## Troubleshooting

### libtorrent not found

```bash
sudo apt-get install python3-libtorrent libtorrent-rasterbar-dev
```

### Google Drive authentication fails

1. Check credentials.json is valid
2. Delete config/token.json and re-authenticate
3. Ensure OAuth consent screen configured
4. Add your email as test user

### Slow downloads

1. Increase `max_connections` in settings.yaml
2. Check VM network bandwidth limits
3. Verify seeders available for torrent

### Port already in use

Change port in config/settings.yaml or use:
```bash
cd backend
python -m uvicorn main:app --port 8080
```

## Performance Tuning

### For High Bandwidth VMs

```yaml
torrent:
  max_concurrent_downloads: 10
  max_connections: 500

google_drive:
  chunk_size: 52428800  # 50MB chunks
```

### For Limited Resources

```yaml
torrent:
  max_concurrent_downloads: 2
  max_connections: 100

google_drive:
  chunk_size: 5242880  # 5MB chunks
```

## Security Considerations

1. **Firewall**: Restrict port 8000 to trusted IPs
2. **OAuth**: Keep credentials.json and token.json secure
3. **HTTPS**: Use nginx reverse proxy with SSL for production
4. **Authentication**: Add auth middleware for multi-user setup

## Project Structure

```
torrent-to-drive/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── models.py            # Data models
│   ├── api/
│   │   ├── torrents.py      # Torrent endpoints
│   │   └── storage.py       # Storage endpoints
│   ├── torrent/
│   │   ├── engine.py        # libtorrent wrapper
│   │   └── worker.py        # Download worker
│   ├── drive/
│   │   ├── client.py        # Google Drive client
│   │   └── uploader.py      # Upload worker
│   └── database/
│       └── db.py            # SQLite database
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TorrentPage.jsx
│   │   │   └── StoragePage.jsx
│   │   ├── services/
│   │   │   └── api.js       # API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
├── config/
│   ├── settings.yaml        # Application config
│   └── credentials.json     # Google OAuth (not in git)
├── data/                    # Downloads and database (not in git)
├── requirements.txt
├── setup.sh
├── start.sh
└── README.md
```

## License

MIT
