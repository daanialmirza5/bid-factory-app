import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, Upload, BookOpen, CheckSquare, LogOut, Activity } from 'lucide-react';
import { useEffect, useState } from 'react';
import { auth } from './firebase';
import { onAuthStateChanged, signOut } from 'firebase/auth';

// Pages
import Dashboard from './pages/Dashboard';
import Bids from './pages/Bids';
import NewRfp from './pages/NewRfp';
import KnowledgeBase from './pages/KnowledgeBase';
import Reviews from './pages/Reviews';
import BidDetail from './pages/BidDetail';
import { Chatbot } from './components/Chatbot';
import Login from './pages/Login';
import LandingPage from './pages/LandingPage';
import { apiUrl } from './config';

const Sidebar = () => {
  const location = useLocation();
  const [apiConnected, setApiConnected] = useState(false);

  useEffect(() => {
    // Check backend connection
    fetch(apiUrl('/api/knowledge-base/search?query=test'))
      .then(res => setApiConnected(res.ok))
      .catch(() => setApiConnected(false));
  }, []);

  const navs = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Bids', path: '/bids', icon: FileText },
    { name: 'New RFP', path: '/new-rfp', icon: Upload },
    { name: 'Knowledge Base', path: '/kb', icon: BookOpen },
    { name: 'Reviews', path: '/reviews', icon: CheckSquare },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header" style={{ flexDirection: 'column', alignItems: 'flex-start', padding: '1.5rem', height: 'auto', gap: '0.25rem' }}>
        <div className="flex items-center gap-2">
          <Activity size={24} className="text-primary" />
          <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>BidFactory</span>
        </div>
        <div className="text-muted" style={{ fontSize: '0.7rem', fontWeight: 500, lineHeight: 1.2, marginTop: '0.5rem' }}>
          AI-Powered RFP Response & <br /> Compliance Platform
        </div>
      </div>

      <nav className="sidebar-nav">
        {navs.map(n => (
          <Link key={n.name} to={n.path} className={`nav-item ${location.pathname === n.path ? 'active' : ''}`}>
            <n.icon size={20} />
            {n.name}
          </Link>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="flex items-center gap-2 mb-4 cursor-pointer hover:text-primary transition-colors" onClick={() => signOut(auth).then(() => window.location.href = '/')}>
          <LogOut size={18} />
          Logout
        </div>
        <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)', fontSize: '0.75rem' }}>System Status</div>
        <div className="system-status">
          <div className={`status-indicator ${!apiConnected ? 'offline' : ''}`} />
          <span className="text-muted" style={{ fontSize: '0.75rem' }}>
            {apiConnected ? 'RocketRide & Backend Connected' : 'Backend Unavailable'}
          </span>
        </div>
      </div>
    </aside>
  );
};

const TopBar = () => {
  const location = useLocation();

  const getTitle = () => {
    if (location.pathname === '/') return 'Command Center';
    if (location.pathname === '/bids') return 'Active Pipelines';
    if (location.pathname.startsWith('/bids/')) return 'Workspace';
    if (location.pathname === '/new-rfp') return 'New RFP Analysis';
    if (location.pathname === '/kb') return 'Knowledge Base';
    if (location.pathname === '/reviews') return 'Human Reviews';
    return '';
  };

  return (
    <header className="top-bar">
      <div className="page-title">{getTitle()}</div>
      <div className="flex items-center gap-4">
        {/* Placeholder for user/notifications */}
        <div className="badge badge-neutral">{auth.currentUser?.email || 'Logged In'}</div>
        <button
          onClick={() => signOut(auth).then(() => window.location.href = '/')}
          className="btn btn-outline"
          style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
        >
          Sign Out
        </button>
      </div>
    </header>
  );
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
      }
    });
    return () => unsubscribe();
  }, []);

  // Show loading spinner or blank while Firebase checks session
  if (isAuthenticated === null) {
    return <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center' }}>Loading Enterprise Auth...</div>;
  }

  return (
    <BrowserRouter>
      {!isAuthenticated ? (
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<LandingPage />} />
        </Routes>
      ) : (
        <div className="app-container">
          <Sidebar />
          <div className="main-content">
            <TopBar />
            <main className="content-area">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/bids" element={<Bids />} />
                <Route path="/bids/:bidId" element={<BidDetail />} />
                <Route path="/new-rfp" element={<NewRfp />} />
                <Route path="/kb" element={<KnowledgeBase />} />
                <Route path="/reviews" element={<Reviews />} />
                <Route path="*" element={<Dashboard />} />
              </Routes>
            </main>
          </div>
          <Chatbot />
        </div>
      )}
    </BrowserRouter>
  );
}

export default App;
