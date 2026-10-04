import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle, Target, Video, Map, Info, X } from 'lucide-react';
import { API_BASE_URL } from '../../services/api';

const IncidentDetailsModal = ({ incident, onClose, onAcknowledge, onResolve, cameraMap }) => {
    if (!incident) return null;

    const getSeverityColor = (severity) => {
        if (severity === 'CRITICAL') return 'text-status-red bg-status-red/20';
        if (severity === 'HIGH') return 'text-status-amber bg-status-amber/20';
        return 'text-status-blue bg-status-blue/20';
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
            <div className="relative w-full max-w-4xl bg-panel border border-default rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-default bg-panel-alt">
                    <div className="flex items-center gap-3">
                        <ShieldAlert size={20} className={incident.severity === 'CRITICAL' ? 'text-status-red' : 'text-status-amber'} />
                        <h2 className="text-lg font-bold tracking-wider text-primary">
                            {incident.id} - MULTI-CAMERA INCIDENT
                        </h2>
                        <span className={`ml-2 px-2 py-1 text-xs font-bold rounded ${
                            incident.status === 'ACTIVE' ? 'bg-status-red/20 text-status-red' : 
                            incident.status === 'ACKNOWLEDGED' ? 'bg-status-amber/20 text-status-amber' : 
                            'bg-status-green/20 text-status-green'
                        }`}>
                            {incident.status}
                        </span>
                        <span className={`ml-2 px-2 py-1 text-xs font-bold rounded ${getSeverityColor(incident.severity)}`}>
                            {incident.severity}
                        </span>
                    </div>
                    <button onClick={onClose} className="text-muted hover:text-primary transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto flex-1 grid grid-cols-1 md:grid-cols-2 gap-6">
                    
                    {/* Left Column */}
                    <div className="space-y-6">
                        <div>
                            <h3 className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Correlation Score</h3>
                            <div className="flex items-center gap-2">
                                <div className="text-3xl font-mono text-status-amber">{incident.correlation_score}</div>
                                <span className="text-xs text-secondary">/ 100</span>
                            </div>
                        </div>

                        <div>
                            <h3 className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Cameras Involved</h3>
                            <div className="flex flex-wrap gap-2">
                                {[incident.primary_camera_id, ...incident.related_camera_ids].map(camId => (
                                    <span key={camId} className="px-2 py-1 bg-black rounded border border-default text-xs font-mono text-primary flex items-center gap-1">
                                        <Video size={12} className="text-secondary" /> {cameraMap[camId] || camId}
                                    </span>
                                ))}
                            </div>
                        </div>

                        <div>
                            <h3 className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Correlation Reasons</h3>
                            <ul className="space-y-1">
                                {incident.correlation_reasons.map((reason, i) => (
                                    <li key={i} className="text-sm text-secondary flex items-start gap-2">
                                        <Info size={14} className="mt-0.5 text-status-blue flex-shrink-0" />
                                        {reason}
                                    </li>
                                ))}
                            </ul>
                        </div>

                        <div>
                            <h3 className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Event Timeline ({incident.timeline.length})</h3>
                            <div className="space-y-3 relative before:absolute before:inset-0 before:ml-2 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-border-default">
                                {incident.timeline.map((evt, i) => (
                                    <div key={i} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                                        <div className="flex items-center justify-center w-5 h-5 rounded-full border-2 border-panel bg-status-amber text-black shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                                            <div className="w-1.5 h-1.5 bg-black rounded-full"></div>
                                        </div>
                                        <div className="w-[calc(100%-2rem)] md:w-[calc(50%-1.5rem)] bg-panel-alt p-2 rounded border border-default shadow">
                                            <div className="flex justify-between items-start mb-1">
                                                <span className="text-[10px] text-muted">{new Date(evt.timestamp * 1000).toLocaleTimeString()}</span>
                                            </div>
                                            <div className="text-xs font-semibold text-primary">{evt.event_type}</div>
                                            <div className="text-[10px] text-secondary font-mono">{cameraMap[evt.camera_id] || evt.camera_id}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Right Column */}
                    <div className="space-y-6">
                        <div>
                            <h3 className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Object Types</h3>
                            <div className="flex flex-wrap gap-2">
                                {incident.object_types.map(obj => (
                                    <span key={obj} className="px-2 py-1 bg-status-blue/20 rounded border border-status-blue/30 text-xs font-semibold text-status-blue capitalize">
                                        {obj}
                                    </span>
                                ))}
                            </div>
                        </div>

                        <div>
                            <h3 className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Evidence Gallery</h3>
                            <div className="grid grid-cols-2 gap-2">
                                {incident.evidence_urls.map((url, i) => (
                                    <div key={i} className="rounded overflow-hidden border border-default bg-black aspect-video relative">
                                        <img 
                                            src={`${API_BASE_URL}${url.replace('/api/v1', '')}`} 
                                            alt="Evidence" 
                                            className="w-full h-full object-cover"
                                            onError={(e) => { e.target.style.display = 'none'; }}
                                        />
                                    </div>
                                ))}
                                {incident.evidence_urls.length === 0 && (
                                    <div className="col-span-2 p-8 border border-dashed border-default rounded flex flex-col items-center justify-center text-muted">
                                        <Target size={24} className="mb-2 opacity-50" />
                                        <span className="text-xs">No evidence snapshots captured</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                </div>

                {/* Actions */}
                <div className="flex items-center justify-between p-4 border-t border-default bg-panel-alt">
                    <div className="text-xs text-muted flex gap-4">
                        <span>First Seen: {new Date(incident.first_seen_at * 1000).toLocaleString()}</span>
                        <span>Last Updated: {new Date(incident.last_seen_at * 1000).toLocaleString()}</span>
                    </div>
                    
                    {incident.status !== 'RESOLVED' && (
                        <div className="flex gap-2">
                            {incident.status === 'ACTIVE' && (
                                <button 
                                    onClick={() => onAcknowledge && onAcknowledge(incident)}
                                    className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded bg-status-amber/20 text-status-amber border border-status-amber/30 hover:bg-status-amber/30 transition-colors"
                                >
                                    <CheckCircle size={14} /> Acknowledge
                                </button>
                            )}
                            {(incident.status === 'ACTIVE' || incident.status === 'ACKNOWLEDGED') && (
                                <button 
                                    onClick={() => onResolve && onResolve(incident)}
                                    className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded bg-status-green/20 text-status-green border border-status-green/30 hover:bg-status-green/30 transition-colors"
                                >
                                    <CheckCircle size={14} /> Resolve
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default IncidentDetailsModal;
