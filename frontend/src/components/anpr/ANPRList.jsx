import React, { useState, useEffect, useCallback } from 'react';
import { fetchANPR } from '../../services/api';
import { getCameraNameMap } from '../../utils/cameraMap';
import { wsService } from '../../services/websocket';
import { Car, RefreshCw, ShieldAlert, CheckCircle } from 'lucide-react';

const POLL_INTERVAL_MS = 15000;

const ANPRList = ({ minimal = false }) => {
    const [plates, setPlates]     = useState([]);
    const [cameraMap, setCameraMap] = useState({});
    const [loading, setLoading]   = useState(false);
    const [lastUpdated, setLastUpdated] = useState(null);

    const loadPlates = useCallback(async () => {
        try {
            setLoading(true);
            const [data, map] = await Promise.all([
                fetchANPR(50),
                getCameraNameMap()
            ]);
            setPlates(data);
            setCameraMap(map);
            setLastUpdated(new Date());
        } catch (err) {
            console.error('[ANPRList] fetch error:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // Initial load
        loadPlates();

        // WebSocket live updates — pushed by backend on every new plate
        const unsub = wsService.subscribe('NEW_ANPR', (data) => {
            setPlates(prev => {
                // Deduplicate by id on the frontend side
                const exists = prev.some(p => p.id === data.id);
                if (exists) return prev;
                return [data, ...prev].slice(0, 50);
            });
            setLastUpdated(new Date());
        });

        // Polling fallback every 5 s (in case WS message is missed)
        const poll = setInterval(loadPlates, POLL_INTERVAL_MS);

        return () => {
            unsub();
            clearInterval(poll);
        };
    }, [loadPlates]);

    const formatTime = (ts) => {
        if (!ts) return '—';
        try {
            const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
        } catch { return '—'; }
    };

    const shortCamId = (id) => {
        if (!id) return '—';
        return id.includes('-') ? id.slice(-8).toUpperCase() : id.toUpperCase();
    };

    return (
        <div className="space-y-2 pr-1">
            {/* Header row */}
            {!minimal && (
                <div className="flex items-center justify-between mb-2 transition-colors">
                    <span className="text-[10px] text-secondary flex items-center gap-1 font-bold uppercase tracking-widest transition-colors">
                        <ShieldAlert size={12} className="text-status-blue" />
                        Fence Intruder Plates
                    </span>
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] text-muted font-mono tracking-wide transition-colors">
                            {lastUpdated ? `UPDATED: ${lastUpdated.toLocaleTimeString('en-US', {hour12: false})}` : 'LOADING...'}
                        </span>
                        <button
                            onClick={loadPlates}
                            className="text-[10px] font-bold text-secondary hover:text-primary flex items-center gap-1 transition-colors uppercase tracking-wider"
                        >
                            <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
                            Refresh
                        </button>
                    </div>
                </div>
            )}

            {plates.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-muted space-y-3 opacity-80 min-h-[120px] bg-panel border border-default rounded transition-colors shadow-panel">
                    {loading ? (
                        <>
                            <RefreshCw size={24} className="animate-spin opacity-50" />
                            <p className="text-[11px] uppercase tracking-wider font-semibold">Scanning for plates...</p>
                        </>
                    ) : (
                        <>
                            <CheckCircle size={28} className="text-status-green/50" />
                            <p className="text-[11px] uppercase tracking-wider font-semibold">No Plates Detected</p>
                        </>
                    )}
                </div>
            ) : (
                plates.map((plate) => (
                    <div
                        key={plate.id}
                        className="bg-base border border-default hover:border-status-blue/50 p-2.5 rounded flex items-center justify-between transition-colors group"
                    >
                        <div className="flex items-center gap-3">
                            <div className="bg-border-default p-2 rounded text-status-blue shrink-0 transition-colors">
                                <Car size={16} />
                            </div>
                            <div>
                                {/* Plate number — highlighted */}
                                <div className="flex items-center gap-2">
                                    <div className="font-mono text-sm font-bold text-status-amber tracking-widest bg-status-amber/10 border border-status-amber/20 px-2 py-0.5 rounded transition-colors">
                                        {plate.plate_text || plate.raw_text || 'UNKNOWN'}
                                    </div>
                                    <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-status-blue/15 text-status-blue border border-status-blue/25 flex items-center gap-0.5 transition-colors">
                                        <ShieldAlert size={10} />
                                        INTRUDER
                                    </span>
                                </div>
                                {!minimal && (
                                    <div className="text-[10px] text-secondary mt-1.5 flex items-center gap-2 font-mono uppercase tracking-wider transition-colors">
                                        <span>{plate.vehicle_class || 'VEHICLE'}</span>
                                        <span className="text-border-highlight transition-colors">•</span>
                                        <span>CAM: {cameraMap[plate.camera_id] || shortCamId(plate.camera_id)}</span>
                                        <span className="text-border-highlight transition-colors">•</span>
                                        <span>TRK: {plate.vehicle_track_id}</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="text-right flex flex-col items-end gap-1.5 shrink-0">
                            <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider border transition-colors ${
                                plate.validation_status === 'VALID'   ? 'bg-status-green/10 text-status-green border-status-green/30' :
                                plate.validation_status === 'INVALID' ? 'bg-status-red/10 text-status-red border-status-red/30'       :
                                'bg-status-amber/10 text-status-amber border-status-amber/30'
                            }`}>
                                {plate.validation_status}
                            </span>
                            {!minimal && (
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] text-muted font-mono tracking-wide transition-colors">
                                        {formatTime(plate.timestamp)}
                                    </span>
                                    <span className="text-[10px] bg-border-default text-status-blue px-1 rounded font-mono border border-default transition-colors">
                                        {Math.round((plate.ocr_confidence || 0) * 100)}%
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                ))
            )}
        </div>
    );
};

export default ANPRList;
