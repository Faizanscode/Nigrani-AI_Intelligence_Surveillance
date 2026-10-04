import React, { useState, useEffect } from 'react';
import { fetchCameras, startCamera, stopCamera, deleteCamera } from '../../services/api';
import { Link } from 'react-router-dom';
import { Play, Square, Video, AlertCircle, Trash2, Activity } from 'lucide-react';
import { wsService } from '../../services/websocket';

const CameraCard = ({ camera, onUpdate }) => {
    const isOnline = camera.status === 'active';
    const [loading, setLoading] = useState(false);
    const [deleting, setDeleting] = useState(false);

    const handleToggle = async (e) => {
        e.preventDefault(); // prevent link navigation
        setLoading(true);
        try {
            if (isOnline) {
                await stopCamera(camera.id);
            } else {
                await startCamera(camera.id);
            }
            onUpdate();
        } catch(err) {
            console.error("Failed to toggle camera:", err);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (e) => {
        e.preventDefault();
        if (!window.confirm(`Are you sure you want to delete camera ${camera.name}?`)) return;
        setDeleting(true);
        try {
            await deleteCamera(camera.id);
            onUpdate();
        } catch (err) {
            console.error("Failed to delete camera:", err);
            setDeleting(false); // only reset if error, else it's unmounted
        }
    };

    return (
        <Link to={`/cameras/${camera.id}`} className="block group">
            <div className="bg-panel border border-default rounded overflow-hidden transition-all hover:border-hover shadow-panel">
                {/* Video area */}
                <div className="aspect-video bg-base relative flex items-center justify-center transition-colors">
                    {isOnline ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-muted gap-1.5 transition-colors">
                            <Video size={36} className="opacity-30" />
                            <span className="text-[10px] uppercase tracking-widest font-semibold opacity-60">Live Feed</span>
                        </div>
                    ) : (
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-muted gap-1.5 transition-colors">
                            <Video size={36} className="opacity-20" />
                            <span className="text-[10px] uppercase tracking-widest font-semibold opacity-40">Offline</span>
                        </div>
                    )}

                    {/* Status indicator — top left */}
                    <div className="absolute top-2.5 left-2.5">
                        <span className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider transition-colors ${
                            isOnline
                                ? 'bg-status-green/10 text-status-green border border-status-green/30'
                                : 'bg-base text-secondary border border-default'
                        }`}>
                            <span className={`w-1.5 h-1.5 rounded-full transition-colors ${isOnline ? 'bg-status-green' : 'bg-border-highlight'}`}></span>
                            {isOnline ? 'LIVE' : 'OFFLINE'}
                        </span>
                    </div>

                    {/* Camera Name — top right */}
                    <div className="absolute top-2.5 right-2.5 max-w-[50%]">
                        <span className="text-[9px] text-secondary font-medium tracking-wide transition-colors bg-base/80 backdrop-blur-xs px-1.5 py-0.5 rounded border border-default truncate block">
                            {camera.name}
                        </span>
                    </div>
                </div>

                {/* Info block */}
                <div className="p-3 border-t border-default transition-colors">
                    <h3 className="font-bold text-sm text-primary truncate transition-colors">{camera.name}</h3>
                    <p className="text-[11px] text-muted font-mono truncate mt-0.5 transition-colors">
                        {camera.type.toUpperCase()} • {camera.source}
                    </p>

                    <div className="mt-3 flex justify-between items-center">
                        <span className="text-[10px] text-secondary capitalize bg-base border border-default px-2 py-0.5 rounded font-medium tracking-wide transition-colors">
                            {camera.type}
                        </span>

                        <div className="flex items-center gap-2">
                            <button
                                onClick={handleDelete}
                                disabled={loading || deleting}
                                title="Delete Camera"
                                className={`flex items-center justify-center p-1.5 rounded text-[11px] font-semibold transition-colors bg-base text-muted hover:text-status-red hover:bg-status-red/10 border border-transparent hover:border-status-red/20 ${
                                    (loading || deleting) ? 'opacity-50 cursor-not-allowed' : ''
                                }`}
                            >
                                <Trash2 size={13} />
                            </button>
                            <button
                                onClick={handleToggle}
                                disabled={loading || deleting}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] font-semibold transition-colors ${
                                    (loading || deleting) ? 'opacity-50 cursor-not-allowed' : ''
                                } ${
                                    isOnline
                                    ? 'bg-status-red/10 text-status-red border border-status-red/20 hover:bg-status-red/20'
                                    : 'bg-status-green/10 text-status-green border border-status-green/20 hover:bg-status-green/20'
                                }`}
                            >
                                {isOnline ? <Square size={11} className="fill-current" /> : <Play size={11} className="fill-current" />}
                                {isOnline ? 'Stop' : 'Start'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </Link>
    );
};

const CameraGrid = () => {
    const [cameras, setCameras] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [newCamera, setNewCamera] = useState({ name: '', source: '', type: 'file' });

    const load = async () => {
        try {
            const data = await fetchCameras();
            setCameras(data);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
        const unsub = wsService.subscribe('NEW_CAMERA_STATUS', (data) => {
            setCameras(prev => prev.map(c => 
                c.id === data.camera_id ? { ...c, status: data.status === 'ONLINE' ? 'active' : 'inactive' } : c
            ));
        });
        return () => unsub();
    }, []);

    const handleAddCamera = async (e) => {
        e.preventDefault();
        try {
            await fetch('http://localhost:8000/api/v1/cameras', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newCamera)
            });
            setShowAddModal(false);
            setNewCamera({ name: '', source: '', type: 'file' });
            load();
        } catch (err) {
            console.error("Failed to add camera", err);
            alert("Failed to add camera: " + err.message);
        }
    };

    if (loading && cameras.length === 0) return <div className="text-secondary text-sm animate-pulse transition-colors">Loading cameras...</div>;

    if (error) return (
        <div className="bg-status-red/10 border border-status-red/30 text-status-red p-3 rounded flex items-center gap-2 text-sm transition-colors">
            <AlertCircle size={16} />
            Failed to load cameras: {error}
        </div>
    );

    return (
        <div>
            <div className="flex justify-between items-end mb-5">
                <div>
                    <h2 className="text-sm font-bold uppercase tracking-widest text-secondary transition-colors">Live Cameras</h2>
                    <p className="text-[11px] text-muted mt-0.5 transition-colors">Manage and view connected video sources</p>
                </div>
                <button
                    onClick={() => setShowAddModal(true)}
                    className="bg-status-blue hover:opacity-90 text-white px-3 py-1.5 rounded text-xs font-semibold transition-colors"
                >
                    + Add Camera
                </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {cameras.map(cam => (
                    <CameraCard key={cam.id} camera={cam} onUpdate={load} />
                ))}
            </div>

            {/* Add Camera Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-panel border border-default p-6 rounded-lg max-w-md w-full transition-colors shadow-2xl">
                        <h3 className="text-base font-bold text-primary mb-4 transition-colors">Add New Camera</h3>
                        <form onSubmit={handleAddCamera} className="space-y-4">
                            <div>
                                <label className="block text-[11px] font-semibold text-secondary uppercase tracking-wider mb-1.5 transition-colors">Name</label>
                                <input required type="text" className="w-full bg-base border border-default rounded-md px-3 py-2 text-sm text-primary placeholder:text-muted focus:border-status-blue focus:outline-none transition-colors" value={newCamera.name} onChange={e => setNewCamera({...newCamera, name: e.target.value})} placeholder="e.g. Front Gate" />
                            </div>
                            <div>
                                <label className="block text-[11px] font-semibold text-secondary uppercase tracking-wider mb-1.5 transition-colors">Source / Path / URL</label>
                                <input required type="text" className="w-full bg-base border border-default rounded-md px-3 py-2 text-sm text-primary placeholder:text-muted focus:border-status-blue focus:outline-none transition-colors" value={newCamera.source} onChange={e => setNewCamera({...newCamera, source: e.target.value})} placeholder="C:\path\to\video.mp4 or rtsp://..." />
                            </div>
                            <div>
                                <label className="block text-[11px] font-semibold text-secondary uppercase tracking-wider mb-1.5 transition-colors">Type</label>
                                <select className="w-full bg-base border border-default rounded-md px-3 py-2 text-sm text-primary focus:border-status-blue focus:outline-none transition-colors" value={newCamera.type} onChange={e => setNewCamera({...newCamera, type: e.target.value})}>
                                    <option value="file" className="bg-panel text-primary">File (MP4, AVI)</option>
                                    <option value="webcam" className="bg-panel text-primary">Webcam</option>
                                    <option value="rtsp" className="bg-panel text-primary">RTSP Stream</option>
                                </select>
                            </div>
                            <div className="flex justify-end gap-2.5 pt-2">
                                <button type="button" onClick={() => setShowAddModal(false)} className="px-4 py-2 text-xs font-semibold text-secondary hover:text-primary transition-colors rounded-md border border-default hover:bg-hover">Cancel</button>
                                <button type="submit" className="bg-status-blue hover:opacity-90 text-white px-4 py-2 rounded-md text-xs font-semibold transition-colors shadow-xs">Add Camera</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CameraGrid;
