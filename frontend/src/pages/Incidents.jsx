import React, { useState, useEffect } from 'react';
import { fetchIncidents, updateIncidentStatus } from '../services/api';
import IncidentDetailsModal from '../components/incidents/IncidentDetailsModal';
import { ShieldAlert, ChevronRight, Activity } from 'lucide-react';

const Incidents = ({ socket, cameraMap }) => {
    const [incidents, setIncidents] = useState([]);
    const [selectedIncident, setSelectedIncident] = useState(null);

    useEffect(() => {
        fetchIncidentsData();
        
        if (socket) {
            const handleIncidentNew = (data) => {
                setIncidents(prev => [data, ...prev]);
            };
            const handleIncidentUpdate = (data) => {
                setIncidents(prev => prev.map(inc => inc.id === data.id ? data : inc));
                if (selectedIncident && selectedIncident.id === data.id) {
                    setSelectedIncident(data);
                }
            };

            socket.on('alerts.incident_new', handleIncidentNew);
            socket.on('alerts.incident_update', handleIncidentUpdate);

            return () => {
                socket.off('alerts.incident_new', handleIncidentNew);
                socket.off('alerts.incident_update', handleIncidentUpdate);
            };
        }
    }, [socket, selectedIncident]);

    const fetchIncidentsData = async () => {
        try {
            const res = await fetchIncidents();
            setIncidents(res);
        } catch (error) {
            console.error('Failed to fetch incidents', error);
        }
    };

    const handleAcknowledge = async (incident) => {
        try {
            await updateIncidentStatus(incident.id, 'ACKNOWLEDGED');
            fetchIncidentsData();
            if (selectedIncident && selectedIncident.id === incident.id) {
                setSelectedIncident({ ...selectedIncident, status: 'ACKNOWLEDGED' });
            }
        } catch (error) {
            console.error('Failed to acknowledge incident', error);
        }
    };

    const handleResolve = async (incident) => {
        try {
            await updateIncidentStatus(incident.id, 'RESOLVED');
            fetchIncidentsData();
            if (selectedIncident && selectedIncident.id === incident.id) {
                setSelectedIncident({ ...selectedIncident, status: 'RESOLVED' });
            }
        } catch (error) {
            console.error('Failed to resolve incident', error);
        }
    };

    const activeCount = incidents.filter(i => i.status === 'ACTIVE').length;

    return (
        <div className="flex-1 overflow-auto bg-background p-6">
            <div className="mb-6 flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-primary flex items-center gap-2">
                        <ShieldAlert size={28} className="text-status-red" /> Multi-Camera Incidents
                    </h1>
                    <p className="text-secondary mt-1">Cross-camera threat correlation and incident timelines</p>
                </div>
                
                <div className="flex gap-4">
                    <div className="bg-panel px-4 py-2 rounded-lg border border-default flex flex-col items-center min-w-[100px]">
                        <span className="text-3xl font-mono text-status-red font-bold">{activeCount}</span>
                        <span className="text-[10px] text-muted font-bold tracking-wider uppercase">Active</span>
                    </div>
                    <div className="bg-panel px-4 py-2 rounded-lg border border-default flex flex-col items-center min-w-[100px]">
                        <span className="text-3xl font-mono text-primary font-bold">{incidents.length}</span>
                        <span className="text-[10px] text-muted font-bold tracking-wider uppercase">Total</span>
                    </div>
                </div>
            </div>

            <div className="bg-panel border border-default rounded-lg overflow-hidden shadow-lg">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-panel-alt text-xs font-bold text-muted uppercase tracking-wider border-b border-default">
                            <th className="p-4 py-3">Incident ID</th>
                            <th className="p-4 py-3">Time Window</th>
                            <th className="p-4 py-3">Cameras</th>
                            <th className="p-4 py-3">Events</th>
                            <th className="p-4 py-3">Score</th>
                            <th className="p-4 py-3">Status</th>
                            <th className="p-4 py-3">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {incidents.length === 0 ? (
                            <tr>
                                <td colSpan="7" className="p-8 text-center text-muted">
                                    <Activity size={24} className="mx-auto mb-2 opacity-50" />
                                    No incidents detected by correlation engine
                                </td>
                            </tr>
                        ) : (
                            incidents.map((incident) => (
                                <tr key={incident.id} className="border-b border-default hover:bg-panel-alt/50 transition-colors">
                                    <td className="p-4 font-mono text-sm text-primary font-bold">
                                        <div className="flex items-center gap-2">
                                            {incident.severity === 'CRITICAL' && <div className="w-2 h-2 rounded-full bg-status-red animate-pulse"></div>}
                                            {incident.id}
                                        </div>
                                    </td>
                                    <td className="p-4 text-xs text-secondary">
                                        <div>{new Date(incident.first_seen_at * 1000).toLocaleTimeString()}</div>
                                        <div className="text-muted">to {new Date(incident.last_seen_at * 1000).toLocaleTimeString()}</div>
                                    </td>
                                    <td className="p-4">
                                        <div className="text-sm font-semibold text-primary">{incident.related_camera_ids.length + 1} Cameras</div>
                                    </td>
                                    <td className="p-4 font-mono text-sm text-secondary">
                                        {incident.event_ids.length}
                                    </td>
                                    <td className="p-4">
                                        <span className="text-status-amber font-mono font-bold">{incident.correlation_score}</span>
                                    </td>
                                    <td className="p-4">
                                        <span className={`px-2 py-1 text-[10px] font-bold rounded ${
                                            incident.status === 'ACTIVE' ? 'bg-status-red/20 text-status-red' : 
                                            incident.status === 'ACKNOWLEDGED' ? 'bg-status-amber/20 text-status-amber' : 
                                            'bg-status-green/20 text-status-green'
                                        }`}>
                                            {incident.status}
                                        </span>
                                    </td>
                                    <td className="p-4">
                                        <button 
                                            onClick={() => setSelectedIncident(incident)}
                                            className="flex items-center gap-1 text-xs font-bold text-accent hover:text-accent/80 transition-colors uppercase tracking-wider"
                                        >
                                            View <ChevronRight size={14} />
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <IncidentDetailsModal 
                incident={selectedIncident} 
                onClose={() => setSelectedIncident(null)}
                onAcknowledge={handleAcknowledge}
                onResolve={handleResolve}
                cameraMap={cameraMap}
            />
        </div>
    );
};

export default Incidents;
