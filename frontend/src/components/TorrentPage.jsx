import { useState, useEffect } from 'react';
import { torrentAPI, WebSocketClient } from '../services/api';

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

const formatSpeed = (bytesPerSec) => {
  return formatBytes(bytesPerSec) + '/s';
};

const formatTime = (seconds) => {
  if (!seconds || seconds < 0) return 'N/A';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
};

export default function TorrentPage() {
  const [magnetUrl, setMagnetUrl] = useState('');
  const [metadata, setMetadata] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [torrents, setTorrents] = useState([]);
  const [progressMap, setProgressMap] = useState({});

  useEffect(() => {
    loadTorrents();

    // Setup WebSocket for real-time updates
    const ws = new WebSocketClient((message) => {
      if (message.type === 'progress') {
        setProgressMap(prev => ({
          ...prev,
          [message.torrent_id]: message.data,
        }));
      }
    });
    ws.connect();

    return () => ws.disconnect();
  }, []);

  const loadTorrents = async () => {
    try {
      const data = await torrentAPI.listTorrents();
      setTorrents(data);
    } catch (err) {
      console.error('Error loading torrents:', err);
    }
  };

  const handleFetchMetadata = async () => {
    if (!magnetUrl.trim()) {
      setError('Please enter a magnet URL');
      return;
    }

    setLoading(true);
    setError('');
    setMetadata(null);

    try {
      const data = await torrentAPI.fetchMetadata(magnetUrl);
      setMetadata(data);
      // Select all files by default
      setSelectedFiles(new Set(data.files.map(f => f.index)));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartDownload = async () => {
    if (!metadata) return;

    setLoading(true);
    setError('');

    try {
      // Add torrent first
      const torrent = await torrentAPI.addTorrent(magnetUrl);

      // Start download with selected files
      await torrentAPI.startDownload(
        torrent.id,
        selectedFiles.size > 0 ? Array.from(selectedFiles) : null
      );

      setMetadata(null);
      setMagnetUrl('');
      setSelectedFiles(new Set());
      await loadTorrents();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleFileSelection = (index) => {
    const newSelection = new Set(selectedFiles);
    if (newSelection.has(index)) {
      newSelection.delete(index);
    } else {
      newSelection.add(index);
    }
    setSelectedFiles(newSelection);
  };

  const selectAll = () => {
    setSelectedFiles(new Set(metadata.files.map(f => f.index)));
  };

  const deselectAll = () => {
    setSelectedFiles(new Set());
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Torrent Downloader</h1>

      {/* Add Torrent Section */}
      <div style={{ marginBottom: '30px', padding: '20px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h2>Add Torrent</h2>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
          <input
            type="text"
            placeholder="Paste magnet URL here..."
            value={magnetUrl}
            onChange={(e) => setMagnetUrl(e.target.value)}
            style={{ flex: 1, padding: '10px', fontSize: '14px' }}
          />
          <button
            onClick={handleFetchMetadata}
            disabled={loading}
            style={{ padding: '10px 20px', cursor: 'pointer' }}
          >
            {loading ? 'Fetching...' : 'Fetch Metadata'}
          </button>
        </div>

        {error && <div style={{ color: 'red', marginTop: '10px' }}>{error}</div>}

        {/* Metadata Display */}
        {metadata && (
          <div style={{ marginTop: '20px' }}>
            <h3>{metadata.name}</h3>
            <p><strong>Total Size:</strong> {formatBytes(metadata.total_size)}</p>
            <p><strong>Files:</strong> {metadata.num_files}</p>
            <p><strong>Info Hash:</strong> {metadata.info_hash}</p>

            <div style={{ marginTop: '15px' }}>
              <div style={{ marginBottom: '10px' }}>
                <button onClick={selectAll} style={{ marginRight: '10px' }}>Select All</button>
                <button onClick={deselectAll}>Deselect All</button>
              </div>

              <div style={{ maxHeight: '300px', overflow: 'auto', border: '1px solid #eee', padding: '10px' }}>
                {metadata.files.map(file => (
                  <div key={file.index} style={{ marginBottom: '8px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={selectedFiles.has(file.index)}
                        onChange={() => toggleFileSelection(file.index)}
                        style={{ marginRight: '10px' }}
                      />
                      <span style={{ flex: 1 }}>{file.path}</span>
                      <span style={{ color: '#666' }}>{formatBytes(file.size)}</span>
                    </label>
                  </div>
                ))}
              </div>

              <button
                onClick={handleStartDownload}
                disabled={selectedFiles.size === 0 || loading}
                style={{ marginTop: '15px', padding: '10px 20px', cursor: 'pointer' }}
              >
                Start Download ({selectedFiles.size} files selected)
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Active Torrents */}
      <div>
        <h2>Torrents</h2>
        {torrents.length === 0 ? (
          <p>No torrents yet. Add one above to get started.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {torrents.map(torrent => {
              const progress = progressMap[torrent.id] || torrent.progress || { progress: 0 };
              return (
                <div key={torrent.id} style={{ border: '1px solid #ddd', padding: '15px', borderRadius: '8px' }}>
                  <h3 style={{ marginTop: 0 }}>{torrent.metadata?.name || 'Loading...'}</h3>
                  <div style={{ marginBottom: '10px' }}>
                    <strong>State:</strong> {torrent.state}
                  </div>

                  {torrent.state === 'downloading' && (
                    <>
                      <div style={{ marginBottom: '10px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                          <span>Progress: {progress.progress?.toFixed(2)}%</span>
                          <span>
                            {formatBytes(progress.downloaded)} / {formatBytes(progress.total_size)}
                          </span>
                        </div>
                        <div style={{ width: '100%', height: '20px', backgroundColor: '#eee', borderRadius: '10px', overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${progress.progress}%`,
                              height: '100%',
                              backgroundColor: '#4CAF50',
                              transition: 'width 0.3s',
                            }}
                          />
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '14px' }}>
                        <div>⬇ {formatSpeed(progress.download_rate)}</div>
                        <div>⬆ {formatSpeed(progress.upload_rate)}</div>
                        <div>Peers: {progress.num_peers}</div>
                        <div>Seeds: {progress.num_seeds}</div>
                        <div>ETA: {formatTime(progress.eta)}</div>
                      </div>
                    </>
                  )}

                  {torrent.state === 'completed' && (
                    <div style={{ color: 'green' }}>✓ Download completed</div>
                  )}

                  {torrent.state === 'uploading' && (
                    <div style={{ color: 'blue' }}>☁ Uploading to Google Drive...</div>
                  )}

                  {torrent.state === 'uploaded' && (
                    <div style={{ color: 'green' }}>✓ Uploaded to Google Drive</div>
                  )}

                  {torrent.state === 'error' && (
                    <div style={{ color: 'red' }}>✗ Error: {progress.error}</div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
