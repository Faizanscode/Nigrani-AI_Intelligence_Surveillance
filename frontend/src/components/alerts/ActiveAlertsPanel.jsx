import React, { useState, useEffect } from 'react';
import { fetchAlerts, acknowledgeAlert, resolveAlert, dismissAlert } from '../../services/api';
import { getCameraNameMap } from '../../utils/cameraMap';
import { wsService } from '../../services/websocket';
import { ShieldAlert, CheckCircle, XCircle, Info, Clock, Check } from 'lucide-react';
import EventDetailsModal from '../events/EventDetailsModal';

const AlertCard = ({ alert, cameraMap, onUpdate, onClick }) => {
    
    const handleAction = async (actionFn) => {
        try {
            await actionFn(alert.alert_id);
            onUpdate();
        } catch(err) {
            console.error(err);
        }
    };

    let severityColors = {
        CRITICAL: "border-status-red/40 bg-status-red/10 text-status-red border-l-status-red",
        HIGH:     "border-status-amber/40 bg-status-amber/10 text-status-amber border-l-status-amber",
        MEDIUM:   "border-status-amber/40 bg-status-amber/10 text-status-amber border-l-status-amber",
        LOW:      "border-status-blue/40 bg-status-blue/10 text-status-blue border-l-status-blue",
    };

    let sColor = severityColors[alert.severity] || severityColors.LOW;
    const camName = cameraMap[alert.camera_id] || alert.camera_id;
    const displayMessage = alert.message && alert.camera_id 
        ? alert.message.replace(alert.camera_id, camName) 
        : alert.message;

    return (
        <div 
            onClick={() => onClick(alert)}
            className={`p-3 rounded border border-l-4 mb-2.5 transition-colors cursor-pointer hover:shadow-lg ${sColor}`}
        >
            <div className="flex justify-between items-start mb-1.5">
                <div className="flex items-center gap-1.5">
                    <ShieldAlert size={12} className="opacity-80" />
                    <span className="text-[10px] font-bold uppercase tracking-widest opacity-90 transition-colors">
                        {alert.severity}
                    </span>
                    <span className="text-secondary text-[10px] mx-1 transition-colors">•</span>
                    <span className="text-[10px] font-semibold tracking-wide text-secondary transition-colors truncate max-w-[140px]">
                        {camName}
                    </span>
                </div>
                <div className="flex items-center gap-1 text-[10px] opacity-70 font-mono transition-colors">
                    <Clock size={10} />
                    {new Date(alert.created_at).toLocaleTimeString('en-US', { hour12: false })}
                </div>
            </div>
            
            <div className="text-xs font-medium text-primary mb-3 leading-snug transition-colors">
                {displayMessage}
            </div>
            
            <div className="flex gap-2">
                {alert.status === 'NEW' && (
                    <button 
                        onClick={(e) => { e.stopPropagation(); handleAction(acknowledgeAlert); }}
                        className="flex-1 flex justify-center items-center gap-1 text-[10px] bg-base hover:bg-status-blue/20 px-2 py-1.5 rounded transition-colors text-primary hover:text-status-blue border border-default hover:border-status-blue/30 uppercase tracking-wider font-semibold"
                    >
                        <Info size={12}/> Ack
                    </button>
                )}
                {alert.status === 'ACKNOWLEDGED' && (
                    <button 
                        onClick={(e) => { e.stopPropagation(); handleAction(resolveAlert); }}
                        className="flex-1 flex justify-center items-center gap-1 text-[10px] bg-status-green/10 hover:bg-status-green/20 px-2 py-1.5 rounded transition-colors text-status-green border border-status-green/40 hover:border-status-green uppercase tracking-wider font-semibold"
                    >
                        <Check size={12}/> Resolve
                    </button>
                )}
                {(alert.status === 'NEW' || alert.status === 'ACKNOWLEDGED') && (
                    <button 
                        onClick={(e) => { e.stopPropagation(); handleAction(dismissAlert); }}
                        className="flex-1 flex justify-center items-center gap-1 text-[10px] bg-base hover:bg-border-highlight px-2 py-1.5 rounded transition-colors text-secondary hover:text-primary border border-default uppercase tracking-wider font-semibold"
                    >
                        <XCircle size={12}/> Dismiss
                    </button>
                )}
            </div>
        </div>
    );
};

const ActiveAlertsPanel = ({ onUpdate = () => {} }) => {
    const [alerts, setAlerts] = useState([]);
    const [cameraMap, setCameraMap] = useState({});
    const [loading, setLoading] = useState(true);
    const [selectedAlert, setSelectedAlert] = useState(null);

    const loadAlerts = async () => {
        try {
            // Load NEW, ACKNOWLEDGED alerts and camera map concurrently
            const [newA, ackA, map] = await Promise.all([
                fetchAlerts(0, 50, 'NEW'),
                fetchAlerts(0, 50, 'ACKNOWLEDGED'),
                getCameraNameMap()
            ]);
            setCameraMap(map);
            // Sort by created_at desc
            const all = [...newA, ...ackA].sort((a,b) => new Date(b.created_at) - new Date(a.created_at));
            setAlerts(all);
        } catch(e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadAlerts();
        
        let timer = null;
        const scheduleLoad = () => {
            if (!timer) {
                timer = setTimeout(() => {
                    loadAlerts();
                    timer = null;
                }, 1000);
            }
        };

        const unsubNew = wsService.subscribe('NEW_ALERT', (newAlert) => {
            if (newAlert && newAlert.alert_id) {
                setAlerts(prev => {
                    const exists = prev.some(a => a.alert_id === newAlert.alert_id);
                    if (exists) return prev.map(a => a.alert_id === newAlert.alert_id ? newAlert : a);
                    return [newAlert, ...prev].slice(0, 100);
                });
            } else {
                scheduleLoad();
            }
        });
        const unsubUpd = wsService.subscribe('ALERT_UPDATED', (updatedAlert) => {
            if (updatedAlert && updatedAlert.alert_id) {
                setAlerts(prev => {
                    if (updatedAlert.status !== 'NEW' && updatedAlert.status !== 'ACKNOWLEDGED') {
                        return prev.filter(a => a.alert_id !== updatedAlert.alert_id);
                    }
                    return prev.map(a => a.alert_id === updatedAlert.alert_id ? updatedAlert : a);
                });
            } else {
                scheduleLoad();
            }
        });
        
        return () => {
            if (timer) clearTimeout(timer);
            unsubNew();
            unsubUpd();
        };
    }, []);

    if (loading) return <div className="text-secondary text-xs animate-pulse p-2 transition-colors">Loading alerts...</div>;
    
    if (alerts.length === 0) return (
        <div className="flex flex-col items-center justify-center h-full text-muted space-y-3 opacity-80 min-h-[150px] transition-colors">
            <CheckCircle size={28} className="text-status-green/50" />
            <p className="text-[11px] uppercase tracking-wider font-semibold transition-colors">No Active Alerts</p>
        </div>
    );

    return (
        <div className="h-full overflow-y-auto pr-1 custom-scrollbar">
            {alerts.map(a => (
                <AlertCard key={a.alert_id} alert={a} cameraMap={cameraMap} onUpdate={loadAlerts} onClick={setSelectedAlert} />
            ))}
            
            {selectedAlert && (
                <EventDetailsModal 
                    event={selectedAlert} 
                    onClose={() => setSelectedAlert(null)} 
                    cameraMap={cameraMap}
                    onAcknowledge={async (evt) => {
                        await acknowledgeAlert(evt.alert_id);
                        loadAlerts();
                        setSelectedAlert({ ...selectedAlert, status: 'ACKNOWLEDGED' });
                    }}
                    onResolve={async (evt) => {
                        await resolveAlert(evt.alert_id);
                        loadAlerts();
                        setSelectedAlert({ ...selectedAlert, status: 'RESOLVED' });
                    }}
                />
            )}
        </div>
    );
};

export default ActiveAlertsPanel;
