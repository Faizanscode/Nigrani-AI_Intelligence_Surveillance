import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Camera, AlertTriangle, List as ListIcon, Home, Shield, Sun, Moon, Users, Map, ShieldAlert } from 'lucide-react';
import { wsService } from './services/websocket';

// Components
import DashboardOverview from './components/dashboard/DashboardOverview';
import CameraGrid from './components/cameras/CameraGrid';
import CameraViewer from './components/cameras/CameraViewer';
import ActiveAlertsPanel from './components/alerts/ActiveAlertsPanel';
import EventHistoryTable from './components/events/EventHistoryTable';
import FaceRegistryPanel from './components/faces/FaceRegistryPanel';
import CameraMap from './components/map/CameraMap';
import Incidents from './pages/Incidents';

const NAV_ITEMS = [
    { to: '/',            label: 'Dashboard',   icon: Home },
    { to: '/cameras',     label: 'Live Cameras', icon: Camera },
    { to: '/camera-map',  label: 'Camera Map',   icon: Map },
    { to: '/incidents',   label: 'Incidents',    icon: ShieldAlert },
    { to: '/alerts',      label: 'Active Alerts', icon: AlertTriangle },
    { to: '/events',      label: 'Event History', icon: ListIcon },
    { to: '/faces',       label: 'Face Registry', icon: Users },
];

const PAGE_TITLES = {
    '/': 'Dashboard',
    '/cameras': 'Live Cameras',
    '/camera-map': 'Camera Map',
    '/incidents': 'Incidents',
    '/alerts': 'Active Alerts',
    '/events': 'Event History',
    '/faces': 'Face Registry',
};

const Sidebar = () => {
    const location = useLocation();

    return (
        <div className="w-56 bg-panel-alt border-r border-default h-screen flex flex-col shrink-0 transition-colors">
            {/* Brand */}
            <div className="px-4 py-4 border-b border-default transition-colors">
                <div className="flex items-center gap-2">
                    <Shield size={20} className="text-status-blue" />
                    <span className="text-base font-bold text-primary tracking-wide transition-colors">Nigrani AI</span>
                </div>
                <p className="text-[11px] text-muted mt-1 tracking-wide uppercase transition-colors">Intelligent Surveillance</p>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-3 py-3 space-y-0.5">
                {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
                    const isActive = location.pathname === to ||
                        (to === '/cameras' && location.pathname.startsWith('/cameras') && !location.pathname.startsWith('/camera-map'));
                    return (
                        <Link
                            key={to}
                            to={to}
                            className={`flex items-center gap-2.5 px-3 py-2 rounded text-[13px] font-medium transition-colors ${
                                isActive
                                    ? 'bg-status-blue/15 text-status-blue border border-status-blue/20'
                                    : 'text-secondary hover:text-primary hover:bg-border-default border border-transparent'
                            }`}
                        >
                            <Icon size={15} />
                            {label}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="px-4 py-3 border-t border-default text-[10px] text-muted uppercase tracking-wider transition-colors">
                System v1.0
            </div>
        </div>
    );
};

const Header = ({ wsConnected, theme, toggleTheme }) => {
    const location = useLocation();
    const [now, setNow] = useState(new Date());

    useEffect(() => {
        const id = setInterval(() => setNow(new Date()), 1000);
        return () => clearInterval(id);
    }, []);

    // Determine page title from route
    const pageTitle = PAGE_TITLES[location.pathname] ||
        (location.pathname.startsWith('/cameras/') ? 'Camera Viewer' : 'Nigrani AI');

    const formatDate = (d) => {
        const day = d.getDate().toString().padStart(2, '0');
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        const month = months[d.getMonth()];
        const year = d.getFullYear();
        return `${day} ${month} ${year}`;
    };

    const formatTime = (d) => {
        return d.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true,
        });
    };

    return (
        <header className="h-12 bg-panel-alt border-b border-default flex items-center justify-between px-5 shrink-0 transition-colors">
            <h2 className="text-sm font-semibold text-primary tracking-wide transition-colors">{pageTitle}</h2>

            <div className="flex items-center gap-3 text-xs">
                {/* Theme Toggle */}
                <button
                    onClick={toggleTheme}
                    title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                    className="p-1.5 rounded text-secondary hover:text-primary hover:bg-border-default transition-colors focus:outline-none focus:ring-2 focus:ring-status-blue/50"
                    aria-label={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                >
                    {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
                </button>

                <span className="w-px h-4 bg-border-default transition-colors"></span>

                {/* Connection Status */}
                {wsConnected ? (
                    <span className="flex items-center gap-1.5 text-status-green font-semibold">
                        <span className="w-1.5 h-1.5 rounded-full bg-status-green animate-pulse"></span>
                        LIVE
                    </span>
                ) : (
                    <span className="flex items-center gap-1.5 text-status-red font-semibold">
                        <span className="w-1.5 h-1.5 rounded-full bg-status-red"></span>
                        OFFLINE
                    </span>
                )}
                <span className="w-px h-4 bg-border-default transition-colors"></span>
                <span className="text-secondary font-medium tabular-nums transition-colors">
                    {formatDate(now)}
                </span>
                <span className="w-px h-4 bg-border-default transition-colors"></span>
                <span className="text-primary font-semibold tabular-nums tracking-wide transition-colors">
                    {formatTime(now)}
                </span>
            </div>
        </header>
    );
};

function App() {
    const [wsConnected, setWsConnected] = useState(false);
    
    // Theme state
    const [theme, setTheme] = useState(() => {
        return localStorage.getItem('nigrani-theme') || 'dark';
    });

    // Apply theme to HTML tag
    useEffect(() => {
        if (theme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        } else {
            document.documentElement.removeAttribute('data-theme'); // default is dark
        }
        localStorage.setItem('nigrani-theme', theme);
    }, [theme]);

    const toggleTheme = () => {
        setTheme(prev => prev === 'dark' ? 'light' : 'dark');
    };

    useEffect(() => {
        wsService.connect();

        const unsub = wsService.subscribe('connection', (status) => {
            setWsConnected(status);
        });

        return () => {
            unsub();
            wsService.disconnect();
        };
    }, []);

    return (
        <Router>
            <div className="flex h-screen bg-base font-sans text-primary overflow-hidden transition-colors">
                <Sidebar />
                <div className="flex-1 flex flex-col min-w-0">
                    <Header wsConnected={wsConnected} theme={theme} toggleTheme={toggleTheme} />
                    <main className="flex-1 overflow-auto p-5 transition-colors">
                        <Routes>
                            <Route path="/" element={<DashboardOverview />} />
                            <Route path="/cameras" element={<CameraGrid />} />
                            <Route path="/cameras/:id" element={<CameraViewer />} />
                            <Route path="/camera-map" element={<div className="flex flex-col h-full"><CameraMap /></div>} />
                            <Route path="/incidents" element={<div className="flex flex-col h-full overflow-hidden"><Incidents socket={wsService.socket} cameraMap={{}} /></div>} />
                            <Route path="/alerts" element={<div className="h-full"><ActiveAlertsPanel /></div>} />
                            <Route path="/events" element={<div className="h-full"><EventHistoryTable /></div>} />
                            <Route path="/faces" element={<div className="h-full overflow-auto"><FaceRegistryPanel /></div>} />
                        </Routes>
                    </main>
                </div>
            </div>
        </Router>
    );
}

export default App;
