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

// Build tree structure from flat file list
const buildFileTree = (files) => {
  const root = { name: 'root', children: {}, files: [], isFolder: true };

  files.forEach(file => {
    const parts = file.path.split('/');
    let current = root;

    // Navigate through folders
    for (let i = 0; i < parts.length - 1; i++) {
      const folderName = parts[i];
      if (!current.children[folderName]) {
        current.children[folderName] = {
          name: folderName,
          children: {},
          files: [],
          isFolder: true,
        };
      }
      current = current.children[folderName];
    }

    // Add file to current folder
    current.files.push(file);
  });

  return root;
};

// Recursive folder component
function FolderTree({ node, selectedFiles, toggleFileSelection, level = 0 }) {
  const [expanded, setExpanded] = useState(level === 0);

  const hasChildren = Object.keys(node.children).length > 0 || node.files.length > 0;

  return (
    <div style={{ marginLeft: level * 20 + 'px' }}>
      {level > 0 && (
        <div
          onClick={() => setExpanded(!expanded)}
          style={{
            cursor: 'pointer',
            padding: '4px 0',
            fontWeight: 'bold',
            color: '#2196F3',
          }}
        >
          {expanded ? '📂' : '📁'} {node.name}
        </div>
      )}

      {expanded && (
        <>
          {/* Render subfolders */}
          {Object.values(node.children).map((child, idx) => (
            <FolderTree
              key={idx}
              node={child}
              selectedFiles={selectedFiles}
              toggleFileSelection={toggleFileSelection}
              level={level + 1}
            />
          ))}

          {/* Render files */}
          {node.files.map(file => (
            <div key={file.index} style={{ marginBottom: '4px', marginLeft: (level + 1) * 20 + 'px' }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={selectedFiles.has(file.index)}
                  onChange={() => toggleFileSelection(file.index)}
                  style={{ marginRight: '8px' }}
                />
                <span style={{ flex: 1, fontSize: '14px' }}>📄 {file.path.split('/').pop()}</span>
                <span style={{ color: '#666', fontSize: '13px' }}>{formatBytes(file.size)}</span>
              </label>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

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

    // Auto-refresh torrents list
    const interval = setInterval(loadTorrents, 5000);

    return () => {
      ws.disconnect();
      clearInterval(interval);
    };
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

  const fileTree = metadata ? buildFileTree(metadata.files) : null;

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Torrent Downloader</h1>

      {/* Add Torrent Section */}
      <div style={{ marginBottom: '30px', padding: '20px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: 'white' }}>
        <h2>Add Torrent</h2>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
          <input
            type="text"
            placeholder="Paste magnet URL here..."
            value={magnetUrl}
            onChange={(e) => setMagnetUrl(e.target.value)}
            style={{ flex: 1, padding: '10px', fontSize: '14px', border: '1px solid #ddd', borderRadius: '4px' }}
          />
          <button
            onClick={handleFetchMetadata}
            disabled={loading}
            style={{
              padding: '10px 20px',
              cursor: loading ? 'not-allowed' : 'pointer',
              backgroundColor: loading ? '#ccc' : '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontWeight: 'bold',
            }}
          >
            {loading ? 'Fetching...' : 'Fetch Metadata'}
          </button>
        </div>

        {error && (
          <div style={{
            color: 'white',
            backgroundColor: '#f44336',
            padding: '10px',
            borderRadius: '4px',
            marginTop: '10px',
          }}>
            {error}
          </div>
        )}

        {/* Metadata Display */}
        {metadata && (
          <div style={{ marginTop: '20px' }}>
            <h3 style={{ color: '#2196F3' }}>{metadata.name}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '15px' }}>
              <p><strong>Total Size:</strong> {formatBytes(metadata.total_size)}</p>
              <p><strong>Files:</strong> {metadata.num_files}</p>
              <p style={{ gridColumn: '1 / -1', fontSize: '12px', color: '#666' }}>
                <strong>Info Hash:</strong> {metadata.info_hash}
              </p>
            </div>

            <div style={{ marginTop: '15px' }}>
              <div style={{ marginBottom: '10px', display: 'flex', gap: '10px' }}>
                <button
                  onClick={selectAll}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Select All
                </button>
                <button
                  onClick={deselectAll}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#ff9800',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Deselect All
                </button>
                <span style={{ marginLeft: 'auto', alignSelf: 'center', color: '#666' }}>
                  {selectedFiles.size} / {metadata.num_files} files selected
                </span>
              </div>

              <div style={{
                maxHeight: '400px',
                overflow: 'auto',
                border: '1px solid #ddd',
                padding: '10px',
                borderRadius: '4px',
                backgroundColor: '#f9f9f9',
              }}>
                {fileTree && (
                  <FolderTree
                    node={fileTree}
                    selectedFiles={selectedFiles}
                    toggleFileSelection={toggleFileSelection}
                  />
                )}
              </div>

              <button
                onClick={handleStartDownload}
                disabled={selectedFiles.size === 0 || loading}
                style={{
                  marginTop: '15px',
                  padding: '12px 24px',
                  cursor: (selectedFiles.size === 0 || loading) ? 'not-allowed' : 'pointer',
                  backgroundColor: (selectedFiles.size === 0 || loading) ? '#ccc' : '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  fontWeight: 'bold',
                  fontSize: '16px',
                  width: '100%',
                }}
              >
                Start Download ({selectedFiles.size} files selected)
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Active Torrents */}
      <div>
        <h2>Active Torrents</h2>
        {torrents.length === 0 ? (
          <p style={{ color: '#666', textAlign: 'center', padding: '20px' }}>
            No torrents yet. Add one above to get started.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {torrents.map(torrent => {
              const progress = progressMap[torrent.id] || torrent.progress || { progress: 0 };
              const isDownloading = torrent.state === 'downloading';
              const isUploading = torrent.state === 'uploading';
              const isCompleted = torrent.state === 'completed' || torrent.state === 'uploaded';
              const isError = torrent.state === 'error';

              return (
                <div
                  key={torrent.id}
                  style={{
                    border: '1px solid #ddd',
                    padding: '20px',
                    borderRadius: '8px',
                    backgroundColor: 'white',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '10px' }}>
                    <h3 style={{ marginTop: 0, flex: 1 }}>{torrent.metadata?.name || 'Loading...'}</h3>
                    <span
                      style={{
                        padding: '4px 12px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        backgroundColor: isError ? '#f44336' : isCompleted ? '#4CAF50' : isUploading ? '#2196F3' : '#ff9800',
                        color: 'white',
                      }}
                    >
                      {torrent.state.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>

                  {isDownloading && (
                    <>
                      <div style={{ marginBottom: '15px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px' }}>
                          <span style={{ fontWeight: 'bold' }}>
                            Progress: {progress.progress?.toFixed(2)}%
                          </span>
                          <span>
                            {formatBytes(progress.downloaded)} / {formatBytes(progress.total_size)}
                          </span>
                        </div>

                        <div style={{
                          width: '100%',
                          height: '24px',
                          backgroundColor: '#e0e0e0',
                          borderRadius: '12px',
                          overflow: 'hidden',
                          position: 'relative',
                        }}>
                          <div
                            style={{
                              width: `${progress.progress}%`,
                              height: '100%',
                              backgroundColor: '#4CAF50',
                              transition: 'width 0.3s ease',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}
                          />
                          <span style={{
                            position: 'absolute',
                            top: '50%',
                            left: '50%',
                            transform: 'translate(-50%, -50%)',
                            fontSize: '12px',
                            fontWeight: 'bold',
                            color: progress.progress > 50 ? 'white' : '#333',
                          }}>
                            {progress.progress?.toFixed(1)}%
                          </span>
                        </div>
                      </div>

                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                        gap: '12px',
                        fontSize: '14px',
                        padding: '12px',
                        backgroundColor: '#f5f5f5',
                        borderRadius: '6px',
                      }}>
                        <div>
                          <div style={{ color: '#666', fontSize: '12px' }}>Download Speed</div>
                          <div style={{ fontWeight: 'bold', color: '#4CAF50' }}>
                            ⬇ {formatSpeed(progress.download_rate)}
                          </div>
                        </div>
                        <div>
                          <div style={{ color: '#666', fontSize: '12px' }}>Upload Speed</div>
                          <div style={{ fontWeight: 'bold', color: '#2196F3' }}>
                            ⬆ {formatSpeed(progress.upload_rate)}
                          </div>
                        </div>
                        <div>
                          <div style={{ color: '#666', fontSize: '12px' }}>Peers</div>
                          <div style={{ fontWeight: 'bold' }}>👥 {progress.num_peers}</div>
                        </div>
                        <div>
                          <div style={{ color: '#666', fontSize: '12px' }}>Seeds</div>
                          <div style={{ fontWeight: 'bold' }}>🌱 {progress.num_seeds}</div>
                        </div>
                        <div>
                          <div style={{ color: '#666', fontSize: '12px' }}>ETA</div>
                          <div style={{ fontWeight: 'bold' }}>⏱ {formatTime(progress.eta)}</div>
                        </div>
                      </div>
                    </>
                  )}

                  {isUploading && (
                    <div style={{ color: '#2196F3', fontWeight: 'bold', padding: '10px', backgroundColor: '#e3f2fd', borderRadius: '4px' }}>
                      ☁️ Uploading to Google Drive...
                    </div>
                  )}

                  {isCompleted && (
                    <div style={{ color: '#4CAF50', fontWeight: 'bold', padding: '10px', backgroundColor: '#e8f5e9', borderRadius: '4px' }}>
                      ✓ {torrent.state === 'uploaded' ? 'Uploaded to Google Drive' : 'Download completed'}
                    </div>
                  )}

                  {isError && (
                    <div style={{ color: '#f44336', padding: '10px', backgroundColor: '#ffebee', borderRadius: '4px' }}>
                      ✗ Error: {progress.error || 'Unknown error occurred'}
                    </div>
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
