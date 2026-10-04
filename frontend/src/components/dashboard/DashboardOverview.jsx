import React, { useState, useEffect } from 'react';
import { fetchCameras, fetchSystemHealth, fetchAlerts, fetchEvents } from '../../services/api';
import { Camera, AlertTriangle, Activity, Server, Radio } from 'lucide-react';
import ActiveAlertsPanel from '../alerts/ActiveAlertsPanel';
import EventHistoryTable from '../events/EventHistoryTable';
import ANPRList from '../anpr/ANPRList';
import { wsService } from '../../services/websocket';
import NightModeControl from './NightModeControl';

const StatCard = ({ title, value, subtitle, status, statusColor }) => (
    <div className="bg-panel border border-default rounded p-4 flex flex-col justify-between transition-colors shadow-panel">
        <div className="text-[10px] font-semibold uppercase tracking-widest text-secondary mb-2 transition-colors">{title}</div>
        <div className="text-2xl font-bold text-primary leading-tight transition-colors">{value}</div>
        {subtitle && <p className="text-[11px] text-muted mt-1.5 transition-colors">{subtitle}</p>}
        {status && (
            <div className="flex items-center gap-1.5 mt-2">
                <span className={`w-1.5 h-1.5 rounded-full ${statusColor || 'bg-border-highlight'} transition-colors`}></span>
                <span className={`text-[10px] font-bold uppercase tracking-wider transition-colors ${
                    statusColor === 'bg-status-green' ? 'text-status-green' :
                    statusColor === 'bg-status-red' ? 'text-status-red' :
                    statusColor === 'bg-status-amber' ? 'text-status-amber' : 'text-muted'
                }`}>
                    {status}
                </span>
            </div>
        )}
    </div>
);

const DashboardOverview = () => {
    const [cameras, setCameras] = useState([]);
    const [health, setHealth] = useState(null);
    const [alertsCount, setAlertsCount] = useState(0);
    const [eventsCount, setEventsCount] = useState(0);
    
    const loadData = async () => {
        try {
            const [camsRes, healthRes] = await Promise.all([
                fetchCameras(),
                fetchSystemHealth()
            ]);
            setCameras(camsRes);
            setHealth(healthRes);
            
            // For prototypes, we might just fetch the full list if we don't have count endpoints
            const fullAlerts = await fetchAlerts(0, 100, 'NEW');
            setAlertsCount(fullAlerts.length);
            
            // If the backend has a /statistics/count endpoint we can use it
            try {
                const countRes = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}/events/statistics/count`);
                if(countRes.ok) {
                    const data = await countRes.json();
                    setEventsCount(data.total);
                }
            } catch(e) { console.error(e); }
            
        } catch (err) {
            console.error(err);
        }
    };

    useEffect(() => {
        loadData();
        
        // Listen for live updates to refresh counts
        const unsubAlerts = wsService.subscribe('NEW_ALERT', () => setAlertsCount(c => c + 1));
        const unsubEvents = wsService.subscribe('NEW_EVENT', () => setEventsCount(c => c + 1));
        const unsubAlertUpdate = wsService.subscribe('ALERT_UPDATED', async () => {
            try {
                const fullAlerts = await fetchAlerts(0, 100, 'NEW');
                setAlertsCount(fullAlerts.length);
            } catch (e) {}
        });
        
        return () => {
            unsubAlerts();
            unsubEvents();
            unsubAlertUpdate();
        };
    }, []);

    const onlineCams = cameras.filter(c => c.status === 'active').length;

    return (
        <div className="space-y-5">
            {/* Section Header */}
            <div>
                <h2 className="text-sm font-bold uppercase tracking-widest text-secondary transition-colors">Command Center</h2>
                <p className="text-[11px] text-muted mt-0.5 transition-colors">System Status Overview</p>
            </div>

            {/* Status Cards Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
                <StatCard 
                    title="Cameras" 
                    value={health === null ? 'LOADING' : `${onlineCams} / ${cameras.length}`} 
                    subtitle={health === null ? 'Fetching cameras' : 'Online / Total'}
                    status={health === null ? 'LOADING' : onlineCams > 0 ? 'ONLINE' : 'OFFLINE'}
                    statusColor={health === null ? 'bg-status-amber' : onlineCams > 0 ? 'bg-status-green' : 'bg-border-highlight'}
                />
                <StatCard 
                    title="Active Alerts" 
                    value={alertsCount} 
                    subtitle="Requires attention"
                    status={alertsCount > 0 ? 'ATTENTION' : 'CLEAR'}
                    statusColor={alertsCount > 0 ? 'bg-status-red' : 'bg-status-green'}
                />
                <StatCard 
                    title="Intrusions Today" 
                    value={eventsCount} 
                    subtitle="Recorded events"
                    status={eventsCount > 0 ? 'MONITORING' : 'CLEAR'}
                    statusColor={eventsCount > 0 ? 'bg-status-amber' : 'bg-status-green'}
                />
                <StatCard 
                    title="System" 
                    value={health === null ? 'CHECKING...' : health.status === 'healthy' ? 'HEALTHY' : 'DOWN'} 
                    subtitle={health ? `Uptime: ${health.uptime ? Math.round(health.uptime/60) + ' min' : 'N/A'}` : 'Connecting to services'}
                    status={health === null ? 'CONNECTING' : health.status === 'healthy' ? 'OPERATIONAL' : 'UNAVAILABLE'}
                    statusColor={health === null ? 'bg-status-amber' : health.status === 'healthy' ? 'bg-status-green' : 'bg-status-red'}
                />
                <NightModeControl />
            </div>

            {/* Lower panels: Alerts | Events | ANPR */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 h-[480px]">
                {/* Active Alerts */}
                <div className="lg:col-span-1 bg-panel border border-default rounded flex flex-col h-full transition-colors shadow-panel">
                    <div className="px-3 py-2.5 border-b border-default flex items-center gap-2 transition-colors">
                        <Radio size={13} className="text-status-red" />
                        <h3 className="text-xs font-semibold text-status-red uppercase tracking-wider transition-colors">Active Alerts</h3>
                    </div>
                    <div className="flex-1 overflow-auto min-h-0 p-3">
                        <ActiveAlertsPanel onUpdate={loadData} />
                    </div>
                </div>
                
                {/* Recent Events */}
                <div className="lg:col-span-2 bg-panel border border-default rounded flex flex-col h-full transition-colors shadow-panel">
                    <div className="px-3 py-2.5 border-b border-default transition-colors">
                        <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider transition-colors">Recent Events</h3>
                    </div>
                    <div className="flex-1 overflow-auto min-h-0">
                        <EventHistoryTable minimal={true} />
                    </div>
                </div>

                {/* ANPR */}
                <div className="lg:col-span-1 bg-panel border border-default rounded flex flex-col h-full transition-colors shadow-panel">
                    <div className="px-3 py-2.5 border-b border-default transition-colors">
                        <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider transition-colors">ANPR / Plates</h3>
                    </div>
                    <div className="flex-1 overflow-auto min-h-0 p-3">
                        <ANPRList />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DashboardOverview;
