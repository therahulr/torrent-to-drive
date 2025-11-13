import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import TorrentPage from './components/TorrentPage';
import StoragePage from './components/StoragePage';

function Navigation() {
  const location = useLocation();

  const navStyle = {
    display: 'flex',
    gap: '0',
    backgroundColor: '#2c3e50',
    padding: '0',
    margin: 0,
    listStyle: 'none',
  };

  const linkStyle = (isActive) => ({
    padding: '15px 30px',
    color: 'white',
    textDecoration: 'none',
    backgroundColor: isActive ? '#34495e' : 'transparent',
    borderBottom: isActive ? '3px solid #3498db' : '3px solid transparent',
    transition: 'all 0.3s',
  });

  return (
    <nav>
      <ul style={navStyle}>
        <li>
          <Link to="/" style={linkStyle(location.pathname === '/')}>
            Torrents
          </Link>
        </li>
        <li>
          <Link to="/storage" style={linkStyle(location.pathname === '/storage')}>
            Storage
          </Link>
        </li>
      </ul>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
        <Navigation />
        <Routes>
          <Route path="/" element={<TorrentPage />} />
          <Route path="/storage" element={<StoragePage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
