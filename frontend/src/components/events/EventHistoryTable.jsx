import React, { useState, useEffect, useMemo, useRef } from 'react';
import { fetchEvents } from '../../services/api';
import { getCameraNameMap } from '../../utils/cameraMap';
import { wsService } from '../../services/websocket';
import { useSearchParams, Link, useLocation } from 'react-router-dom';
import { Target, Activity, ShieldAlert, X, Eye } from 'lucide-react';
import EventDetailsModal from './EventDetailsModal';
import { acknowledgeAlert, resolveAlert } from '../../services/api';

const EventHistoryTable = ({ minimal = false }) => {
    const [events, setEvents] = useState([]);
    const [cameraMap, setCameraMap] = useState({});
    const cameraMapRef = useRef({});
    const [loading, setLoading] = useState(true);
    const [selectedEvent, setSelectedEvent] = useState(null);

    // Camera filter from URL param (?camera=CAM-ID)
    const [searchParams] = useSearchParams();
    const cameraIdFilter = searchParams.get('camera') || null;
    const location = useLocation();
    const fromMap = location.state?.fromMap;

    const loadEvents = async () => {
        try {
            const [data, map] = await Promise.all([
                fetchEvents(0, minimal ? 10 : 50),
                getCameraNameMap()
            ]);
            cameraMapRef.current = map;
            setCameraMap(map);
            setEvents(data.sort((a,b) => new Date(b.timestamp * 1000) - new Date(a.timestamp * 1000)));
        } catch(e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadEvents();
        
        let timer = null;
        const unsub = wsService.subscribe('NEW_EVENT', async (newEventData) => {
            if (newEventData && (newEventData.event_id || newEventData.timestamp)) {
                // If this is a new camera we don't have in our map, fetch the map again
                if (newEventData.camera_id && !cameraMapRef.current[newEventData.camera_id]) {
                    const newMap = await getCameraNameMap(true); // force refresh
                    cameraMapRef.current = newMap;
                    setCameraMap(newMap);
                }
                
                setEvents(prev => {
                    const id = newEventData.event_id || `${newEventData.timestamp}-${newEventData.camera_id}`;
                    const exists = prev.some(e => (e.event_id || `${e.timestamp}-${e.camera_id}`) === id);
                    if (exists) return prev;
                    return [newEventData, ...prev].slice(0, minimal ? 10 : 50);
                });
            }
        });
        return () => {
            if (timer) clearTimeout(timer);
            unsub();
        };
    }, [minimal]);

    // Client-side camera filter
    const displayedEvents = useMemo(() => {
        if (!cameraIdFilter) return events;
        return events.filter(e => e.camera_id === cameraIdFilter);
    }, [events, cameraIdFilter]);

    const handleAcknowledge = async (eventToUpdate) => {
        try {
            await acknowledgeAlert(eventToUpdate.alert_id || eventToUpdate.event_id);
            // Optmistic update
            setEvents(prev => prev.map(e => e.event_id === eventToUpdate.event_id ? { ...e, status: 'ACKNOWLEDGED' } : e));
            if (selectedEvent && selectedEvent.event_id === eventToUpdate.event_id) {
                setSelectedEvent({ ...selectedEvent, status: 'ACKNOWLEDGED' });
            }
        } catch (err) {
            console.error('Failed to acknowledge:', err);
        }
    };

    const handleResolve = async (eventToUpdate) => {
        try {
            await resolveAlert(eventToUpdate.alert_id || eventToUpdate.event_id);
            setEvents(prev => prev.map(e => e.event_id === eventToUpdate.event_id ? { ...e, status: 'RESOLVED' } : e));
            if (selectedEvent && selectedEvent.event_id === eventToUpdate.event_id) {
                setSelectedEvent({ ...selectedEvent, status: 'RESOLVED' });
            }
        } catch (err) {
            console.error('Failed to resolve:', err);
        }
    };

    if (loading) return <div className="text-secondary text-xs animate-pulse p-4 transition-colors">Loading events...</div>;
    
    if (events.length === 0 && !cameraIdFilter) return (
        <div className="flex flex-col items-center justify-center h-full text-muted space-y-3 opacity-80 min-h-[150px] transition-colors">
            <Activity size={28} className="opacity-50" />
            <p className="text-[11px] uppercase tracking-wider font-semibold">No Recent Events</p>
        </div>
    );

    return (
        <div>
            {/* Camera filter banner */}
            {cameraIdFilter && (
                <div className="flex items-center justify-between px-4 py-2 mb-2 bg-status-blue/10 border border-status-blue/20 rounded text-xs transition-colors">
                    <span className="text-secondary">
                        Filtered by camera: <span className="text-primary font-semibold font-mono">{cameraMap[cameraIdFilter] || cameraIdFilter}</span>
                        {' — '}<span className="text-muted">{displayedEvents.length} event{displayedEvents.length !== 1 ? 's' : ''}</span>
                    </span>
                    <div className="flex items-center gap-4">
                        {fromMap && (
                            <Link to="/camera-map" className="flex items-center gap-1 text-status-blue hover:text-status-blue/80 transition-colors font-semibold">
                                &larr; Back to Map
                            </Link>
                        )}
                        <Link
                            to="/events"
                            className="flex items-center gap-1 text-muted hover:text-primary transition-colors"
                            title="Clear camera filter"
                        >
                            <X size={12} /> Clear
                        </Link>
                    </div>
                </div>
            )}
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="border-b border-default text-[10px] uppercase tracking-widest text-secondary bg-base sticky top-0 z-10 transition-colors">
                        <th className="px-4 py-2.5 font-semibold">Time</th>
                        <th className="px-4 py-2.5 font-semibold">Camera</th>
                        <th className="px-4 py-2.5 font-semibold">Type</th>
                        <th className="px-4 py-2.5 font-semibold">Object</th>
                        {!minimal && <th className="px-4 py-2.5 font-semibold">Severity</th>}
                        <th className="px-4 py-2.5 font-semibold text-right">Action</th>
                    </tr>
                </thead>
                <tbody className="text-xs">
                    {displayedEvents.length === 0 ? (
                        <tr>
                            <td colSpan={minimal ? 4 : 5} className="px-4 py-8 text-center text-muted border-b border-default">
                                {cameraIdFilter ? "No events found for this camera." : "No recent events."}
                            </td>
                        </tr>
                    ) : (
                        displayedEvents.map(evt => {
                            const date = new Date(evt.timestamp * 1000);
                            const camName = cameraMap[evt.camera_id] || evt.camera_id;
                            return (
                                <tr key={evt.event_id} className="border-b border-default hover:bg-border-default/50 transition-colors">
                                    <td className="px-4 py-2.5 text-secondary font-mono text-[11px] whitespace-nowrap transition-colors">
                                        {minimal ? date.toLocaleTimeString('en-US', { hour12: false }) : date.toLocaleString('en-US', { hour12: false })}
                                    </td>
                                    <td className="px-4 py-2.5 text-primary font-semibold text-[11px] tracking-wide transition-colors">
                                        {camName}
                                    </td>
                                    <td className="px-4 py-2.5">
                                        <div className="flex items-center gap-2 text-primary font-medium transition-colors">
                                            {evt.severity === 'CRITICAL' || evt.severity === 'HIGH' ? (
                                                <ShieldAlert size={12} className="text-status-red" />
                                            ) : (
                                                <Target size={12} className="text-status-blue" />
                                            )}
                                            {evt.event_type.replace(/_/g, ' ')}
                                        </div>
                                    </td>
                                    <td className="px-4 py-2.5 text-primary capitalize text-[11px] transition-colors">
                                        <span className="font-semibold">{evt.name ? `${evt.name} (${evt.status || 'Face'})` : (evt.object_class || evt.object_type || 'Unknown')}</span> 
                                        {evt.track_id ? <span className="text-secondary ml-1 font-mono text-[10px] transition-colors">#{evt.track_id}</span> : ''}
                                    </td>
                                    {!minimal && (
                                        <td className="px-4 py-2.5">
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider transition-colors ${
                                                evt.severity === 'CRITICAL' ? 'bg-status-red/20 text-status-red' :
                                                evt.severity === 'HIGH' ? 'bg-status-amber/20 text-status-amber' :
                                                'bg-status-blue/20 text-status-blue'
                                            }`}>
                                                {evt.severity || 'HIGH'}
                                            </span>
                                        </td>
                                    )}
                                    <td className="px-4 py-2.5 text-right">
                                        <button 
                                            onClick={() => setSelectedEvent(evt)}
                                            className="inline-flex items-center gap-1.5 px-2 py-1 text-[10px] uppercase font-bold text-muted hover:text-primary bg-panel-alt hover:bg-border-default rounded transition-colors"
                                        >
                                            <Eye size={12} /> View
                                        </button>
                                    </td>
                                </tr>
                            );
                        })
                    )}
                </tbody>
            </table>
        </div>
        
        {selectedEvent && (
            <EventDetailsModal 
                event={selectedEvent} 
                onClose={() => setSelectedEvent(null)} 
                cameraMap={cameraMap}
                onAcknowledge={handleAcknowledge}
                onResolve={handleResolve}
            />
        )}
        </div>
    );
};

export default EventHistoryTable;
