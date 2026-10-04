import React from 'react';
import { X, ExternalLink, Map, ShieldAlert, Target, CheckCircle, Video } from 'lucide-react';
import { Link } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const EventDetailsModal = ({ event, onClose, onAcknowledge, onResolve, cameraMap }) => {
    if (!event) return null;

    const date = new Date(event.timestamp ? event.timestamp * 1000 : (event.created_at ? new Date(event.created_at).getTime() : Date.now()));
    const camName = cameraMap[event.camera_id] || event.camera_id;
    const isAlert = !!event.alert_id;
    
    // Support either Alert format (snapshot_url, metadata.track_id) or Event format (object_type, track_id)
    const snapshotUrl = event.snapshot_url ? `${API_BASE_URL}${event.snapshot_url}` : null;
    const objectType = event.object_type || event.object_class || (event.metadata && event.metadata.object_class) || 'Object';
    const trackId = event.track_id || (event.metadata && event.metadata.track_id) || 'N/A';
    
    const severityColor = (event.severity === 'CRITICAL' || event.severity === 'HIGH') ? 'text-status-red' : 'text-status-blue';

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
            <div className="relative w-full max-w-2xl bg-panel border border-default rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-default bg-panel-alt">
                    <div className="flex items-center gap-2">
                        {(event.severity === 'CRITICAL' || event.severity === 'HIGH') ? (
                            <ShieldAlert size={18} className="text-status-red" />
                        ) : (
                            <Target size={18} className="text-status-blue" />
                        )}
                        <h2 className="text-sm font-bold tracking-wider uppercase text-primary">
                            {event.event_type.replace(/_/g, ' ')}
                        </h2>
                        {event.status && (
                            <span className={`ml-2 px-2 py-0.5 text-[10px] font-bold rounded ${
                                event.status === 'NEW' ? 'bg-status-red/20 text-status-red' : 
                                event.status === 'ACKNOWLEDGED' ? 'bg-status-amber/20 text-status-amber' : 
                                'bg-status-green/20 text-status-green'
                            }`}>
                                {event.status}
                            </span>
                        )}
                    </div>
                    <button onClick={onClose} className="text-muted hover:text-primary transition-colors">
                        <X size={18} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-4 overflow-y-auto flex-1">
                    
                    {/* Evidence Snapshot */}
                    <div className="mb-6 rounded-md overflow-hidden bg-black border border-default relative min-h-[200px] flex items-center justify-center">
                        {snapshotUrl ? (
                            <img 
                                src={snapshotUrl} 
                                alt="Evidence Snapshot" 
                                className="w-full h-auto object-contain max-h-[400px]"
                                onError={(e) => { e.target.onerror = null; e.target.src = ''; e.target.parentElement.innerHTML = '<div class="text-muted text-xs">Snapshot not available</div>'; }}
                            />
                        ) : (
                            <div className="text-muted text-xs flex flex-col items-center gap-2">
                                <Target size={24} className="opacity-50" />
                                <span>No evidence snapshot captured</span>
                            </div>
                        )}
                        <div className="absolute top-2 left-2 px-2 py-1 bg-black/60 backdrop-blur-md rounded text-[10px] text-primary font-mono border border-white/10 uppercase font-semibold">
                            EVIDENCE CAPTURE
                        </div>
                    </div>

                    {/* Metadata Grid */}
                    <div className="grid grid-cols-2 gap-4 text-sm mb-6">
                        <div className="space-y-3">
                            <div>
                                <label className="block text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Camera</label>
                                <div className="font-semibold text-primary font-mono">{camName}</div>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Time</label>
                                <div className="text-secondary font-mono text-xs">{date.toLocaleString()}</div>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Severity</label>
                                <div className={`font-bold ${severityColor}`}>{event.severity || 'HIGH'}</div>
                            </div>
                        </div>
                        <div className="space-y-3">
                            <div>
                                <label className="block text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Object Type</label>
                                <div className="text-primary capitalize">{objectType}</div>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Track ID</label>
                                <div className="text-secondary font-mono">{trackId}</div>
                            </div>
                            {event.message && (
                                <div>
                                    <label className="block text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Description</label>
                                    <div className="text-primary text-xs">{event.message}</div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-between pt-4 border-t border-default">
                        <div className="flex gap-2">
                            <Link 
                                to={`/cameras/${event.camera_id}`}
                                className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded bg-panel-alt border border-default text-primary hover:bg-border-default transition-colors"
                            >
                                <Video size={14} /> Live Camera
                            </Link>
                            <Link 
                                to={`/camera-map?camera=${event.camera_id}`}
                                className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded bg-panel-alt border border-default text-primary hover:bg-border-default transition-colors"
                            >
                                <Map size={14} /> View on Map
                            </Link>
                        </div>
                        
                        {isAlert && event.status !== 'RESOLVED' && (
                            <div className="flex gap-2">
                                {event.status === 'NEW' && (
                                    <button 
                                        onClick={() => onAcknowledge && onAcknowledge(event)}
                                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded bg-status-amber/20 text-status-amber border border-status-amber/30 hover:bg-status-amber/30 transition-colors"
                                    >
                                        <CheckCircle size={14} /> Acknowledge
                                    </button>
                                )}
                                {(event.status === 'NEW' || event.status === 'ACKNOWLEDGED') && (
                                    <button 
                                        onClick={() => onResolve && onResolve(event)}
                                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded bg-status-green/20 text-status-green border border-status-green/30 hover:bg-status-green/30 transition-colors"
                                    >
                                        <CheckCircle size={14} /> Resolve
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                    
                </div>
            </div>
        </div>
    );
};

export default EventDetailsModal;
