const API_BASE = '/api';

class TorrentAPI {
  async fetchMetadata(magnetUrl) {
    const response = await fetch(`${API_BASE}/torrents/metadata`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ magnet_url: magnetUrl }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch metadata');
    }

    return response.json();
  }

  async addTorrent(magnetUrl) {
    const response = await fetch(`${API_BASE}/torrents/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ magnet_url: magnetUrl }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to add torrent');
    }

    return response.json();
  }

  async startDownload(torrentId, fileIndices = null) {
    const response = await fetch(`${API_BASE}/torrents/${torrentId}/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ torrent_id: torrentId, file_indices: fileIndices }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start download');
    }

    return response.json();
  }

  async listTorrents(state = null) {
    const url = state ? `${API_BASE}/torrents/?state=${state}` : `${API_BASE}/torrents/`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error('Failed to fetch torrents');
    }

    return response.json();
  }

  async getTorrent(torrentId) {
    const response = await fetch(`${API_BASE}/torrents/${torrentId}`);

    if (!response.ok) {
      throw new Error('Failed to fetch torrent');
    }

    return response.json();
  }

  async getProgress(torrentId) {
    const response = await fetch(`${API_BASE}/torrents/${torrentId}/progress`);

    if (!response.ok) {
      throw new Error('Failed to fetch progress');
    }

    return response.json();
  }

  async pauseTorrent(torrentId) {
    const response = await fetch(`${API_BASE}/torrents/${torrentId}/pause`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to pause torrent');
    }

    return response.json();
  }

  async resumeTorrent(torrentId) {
    const response = await fetch(`${API_BASE}/torrents/${torrentId}/resume`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to resume torrent');
    }

    return response.json();
  }

  async deleteTorrent(torrentId, deleteFiles = false) {
    const response = await fetch(`${API_BASE}/torrents/${torrentId}?delete_files=${deleteFiles}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('Failed to delete torrent');
    }

    return response.json();
  }
}

class StorageAPI {
  async listFiles(folderId = null) {
    const url = folderId ? `${API_BASE}/storage/files?folder_id=${folderId}` : `${API_BASE}/storage/files`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error('Failed to fetch files');
    }

    return response.json();
  }

  async getFile(fileId) {
    const response = await fetch(`${API_BASE}/storage/files/${fileId}`);

    if (!response.ok) {
      throw new Error('Failed to fetch file');
    }

    return response.json();
  }

  async checkHealth() {
    const response = await fetch(`${API_BASE}/storage/health`);
    return response.json();
  }
}

class WebSocketClient {
  constructor(onMessage) {
    this.ws = null;
    this.onMessage = onMessage;
    this.reconnectDelay = 1000;
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.onMessage(data);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected. Reconnecting...');
      setTimeout(() => this.connect(), this.reconnectDelay);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}

export const torrentAPI = new TorrentAPI();
export const storageAPI = new StorageAPI();
export { WebSocketClient };
