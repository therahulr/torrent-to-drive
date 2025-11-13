import { useState, useEffect } from 'react';
import { storageAPI } from '../services/api';

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString();
};

export default function StoragePage() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [health, setHealth] = useState(null);

  useEffect(() => {
    loadFiles();
    checkHealth();
  }, []);

  const loadFiles = async () => {
    setLoading(true);
    setError('');

    try {
      const data = await storageAPI.listFiles();
      setFiles(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const checkHealth = async () => {
    try {
      const data = await storageAPI.checkHealth();
      setHealth(data);
    } catch (err) {
      console.error('Health check failed:', err);
    }
  };

  const handleDownload = (file) => {
    if (file.web_content_link) {
      window.open(file.web_content_link, '_blank');
    } else if (file.web_view_link) {
      window.open(file.web_view_link, '_blank');
    } else {
      alert('Download link not available for this file');
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Google Drive Storage</h1>
        <div>
          {health && (
            <span style={{
              padding: '5px 10px',
              borderRadius: '5px',
              backgroundColor: health.status === 'healthy' ? '#4CAF50' : '#f44336',
              color: 'white',
              fontSize: '12px',
            }}>
              {health.status === 'healthy' ? '● Connected' : '● Disconnected'}
            </span>
          )}
          <button
            onClick={loadFiles}
            disabled={loading}
            style={{ marginLeft: '10px', padding: '8px 16px', cursor: 'pointer' }}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '15px',
          backgroundColor: '#ffebee',
          color: '#c62828',
          borderRadius: '8px',
          marginBottom: '20px',
        }}>
          {error}
        </div>
      )}

      {loading && files.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>Loading files...</p>
        </div>
      ) : files.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
          <p>No files uploaded yet.</p>
          <p>Download torrents from the Torrents page to see them here.</p>
        </div>
      ) : (
        <div>
          <div style={{ marginBottom: '15px', color: '#666' }}>
            {files.length} file{files.length !== 1 ? 's' : ''} found
          </div>

          <div style={{ border: '1px solid #ddd', borderRadius: '8px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f5f5f5' }}>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Name</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Type</th>
                  <th style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid #ddd' }}>Size</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Created</th>
                  <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #ddd' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {files.map(file => (
                  <tr key={file.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <span style={{ marginRight: '8px', fontSize: '20px' }}>
                          {file.is_folder ? '📁' : '📄'}
                        </span>
                        {file.name}
                      </div>
                    </td>
                    <td style={{ padding: '12px', fontSize: '14px', color: '#666' }}>
                      {file.is_folder ? 'Folder' : file.mime_type.split('/').pop()}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right', fontSize: '14px' }}>
                      {!file.is_folder && formatBytes(file.size)}
                    </td>
                    <td style={{ padding: '12px', fontSize: '14px', color: '#666' }}>
                      {formatDate(file.created_time)}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <button
                        onClick={() => handleDownload(file)}
                        style={{
                          padding: '6px 12px',
                          cursor: 'pointer',
                          backgroundColor: '#2196F3',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                        }}
                      >
                        {file.is_folder ? 'Open' : 'Download'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
