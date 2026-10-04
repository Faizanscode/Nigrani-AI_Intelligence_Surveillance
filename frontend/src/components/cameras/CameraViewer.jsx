import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { fetchCameras, getFence, API_BASE_URL } from '../../services/api';
import { wsService } from '../../services/websocket';
import { ArrowLeft, VideoOff, Target, ShieldAlert, Activity, UserCheck } from 'lucide-react';
import FenceEditor from './FenceEditor';
import { normalizedToDisplay } from '../../utils/videoCoordinateUtils';

// ── Event card ────────────────────────────────────────────────────────────────
const EVENT_COLORS = {
    VIRTUAL_FENCE_INTRUSION: 'text-status-red border-status-red/40 bg-status-red/10',
    LOITERING_DETECTED:      'text-status-amber border-status-amber/40 bg-status-amber/10',
    NIGHT_MOVEMENT_DETECTED: 'text-status-blue border-status-blue/40 bg-status-blue/10',
    FACE_RECOGNITION:        'text-status-green border-status-green/40 bg-status-green/10',
    OBJECT_DETECTED:         'text-primary border-default bg-panel',
    DEFAULT:                 'text-primary border-default bg-panel',
};

const EventCard = ({ evt }) => {
    const colorClass = EVENT_COLORS[evt.event_type] || EVENT_COLORS.DEFAULT;
    const label = (evt.event_type || '').replace(/_/g, ' ');
    const objLabel = evt.object_class || evt.object_type || 'Unknown';
    const trackLabel = evt.track_id != null ? ` #${evt.track_id}` : '';
    const ts = evt.timestamp ? new Date(evt.timestamp * 1000).toLocaleTimeString() : '';

    return (
        <div className={`border rounded p-2.5 text-xs transition-colors ${colorClass}`}>
            <div className="flex justify-between items-start mb-1">
                <div className="flex items-center gap-1 font-bold">
                    {evt.severity === 'HIGH' && <ShieldAlert size={11} className="text-status-red" />}
                    {label}
                </div>
                <div className="text-[10px] opacity-60">{ts}</div>
            </div>
            <div className="opacity-80 capitalize">{objLabel}{trackLabel}</div>
            {evt.description && (
                <div className="text-[10px] mt-1 opacity-50">{evt.description}</div>
            )}
        </div>
    );
};

// ── Fence overlay on top of the MJPEG stream ─────────────────────────────────
const FenceOverlay = ({ cameraId, containerRef, videoDims }) => {
    const canvasRef = useRef(null);
    const [fenceData, setFenceData] = useState(null);

    useEffect(() => {
        if (!cameraId) return;
        const load = () =>
            getFence(cameraId)
                .then(r => setFenceData(r.fence || null))
                .catch(() => {});
        load();
        const t = setInterval(load, 15000);
        return () => clearInterval(t);
    }, [cameraId]);

    const draw = useCallback(() => {
        const canvas = canvasRef.current;
        const container = containerRef?.current;
        if (!canvas || !container) return;
        const W = container.clientWidth;
        const H = container.clientHeight;
        canvas.width  = W;
        canvas.height = H;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, W, H);
        if (!fenceData?.points) return;

        const pts = fenceData.points.map(([nx, ny]) => {
            if (videoDims?.w && videoDims?.h) {
                return normalizedToDisplay(nx, ny, W, H, videoDims.w, videoDims.h);
            }
            return [nx * W, ny * H];
        });

        ctx.beginPath();
        ctx.moveTo(pts[0][0], pts[0][1]);
        pts.slice(1).forEach(([x, y]) => ctx.lineTo(x, y));
        ctx.closePath();
        ctx.fillStyle = 'rgba(0, 200, 100, 0.08)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(0, 200, 100, 0.9)';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Corner dots
        pts.forEach(([x, y]) => {
            ctx.beginPath();
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fillStyle = '#00ff88';
            ctx.fill();
        });

        // Label
        ctx.font = 'bold 12px sans-serif';
        ctx.fillStyle = '#00ff88';
        ctx.fillText('▸ ' + (fenceData.name || 'Fence'), pts[0][0] + 6, pts[0][1] - 6);
    }, [fenceData, containerRef, videoDims]);

    useEffect(() => { draw(); }, [draw]);
    useEffect(() => {
        const h = () => draw();
        window.addEventListener('resize', h);
        return () => window.removeEventListener('resize', h);
    }, [draw]);

    return (
        <canvas
            ref={canvasRef}
            style={{
                position: 'absolute', inset: 0,
                width: '100%', height: '100%',
                pointerEvents: 'none', zIndex: 5,
            }}
        />
    );
};

// ── Main component ────────────────────────────────────────────────────────────
const CameraViewer = () => {
    const { id } = useParams();
    const location = useLocation();
    const [camera, setCamera] = useState(null);
    const [error, setError]   = useState(null);
    const [events, setEvents] = useState([]);
    const [isStarting, setIsStarting] = useState(false);
    const [streamKey, setStreamKey]   = useState(Date.now());
    const [videoDims, setVideoDims]   = useState({ w: 0, h: 0 });
    const eventsRef    = useRef([]);
    const videoContainerRef = useRef(null);

    const activeTracksRef = useRef(new Set());
    const hadDetectionsRef = useRef(false);

    const addEvent = useCallback((evt) => {
        setEvents(prev => {
            // Deduplicate identical event IDs or same track within 4 seconds
            const isDuplicate = prev.some(e => {
                if (evt.event_id && e.event_id === evt.event_id) return true;
                if (evt.track_id != null && e.track_id === evt.track_id && Math.abs((evt.timestamp || 0) - (e.timestamp || 0)) < 4) return true;
                return false;
            });
            if (isDuplicate) return prev;
            return [evt, ...prev].slice(0, 25);
        });
    }, []);

    const load = useCallback(async () => {
        try {
            const cams = await fetchCameras();
            const cam  = cams.find(c => c.id === id);
            if (!cam) throw new Error('Camera not found.');
            setCamera(cam);
        } catch (e) { setError(e.message); }
    }, [id]);

    // Poll live detections: ONLY log when a new object enters the frame, NO spam while staying in frame
    const pollDetections = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/cameras/${id}/detections`);
            if (!res.ok) return;
            const data = await res.json();

            const tracks = data.tracks || [];
            const detections = data.detections || [];
            const faces = data.face_recognition || [];

            if (tracks.length > 0) {
                const currentTrackIds = new Set(tracks.map(t => t.track_id));

                // Find newly arrived tracks that are not already active in the frame
                tracks.forEach(t => {
                    if (!activeTracksRef.current.has(t.track_id)) {
                        // New arrival!
                        const face = faces.find(f => f.track_id === t.track_id);
                        const faceName = (face && face.status === 'RECOGNIZED' && face.name) ? ` [${face.name}]` : '';
                        const conf = t.confidence ? ` (${(t.confidence * 100).toFixed(0)}%)` : '';

                        addEvent({
                            event_id: `det_${id}_${t.track_id}_${data.timestamp || Date.now()}`,
                            event_type: 'OBJECT_DETECTED',
                            camera_id: id,
                            track_id: t.track_id,
                            timestamp: data.timestamp || Date.now() / 1000,
                            severity: 'INFO',
                            object_class: `${t.class_name}${faceName}${conf}`,
                            description: 'New arrival in frame',
                        });
                    }
                });

                // Update active tracks set (tracks that left the frame are automatically removed)
                activeTracksRef.current = currentTrackIds;
                hadDetectionsRef.current = true;
            } else if (detections.length > 0) {
                // If tracker is warming up, alert once on initial appearance
                if (!hadDetectionsRef.current) {
                    addEvent({
                        event_id: `det_${id}_generic_${Date.now()}`,
                        event_type: 'OBJECT_DETECTED',
                        camera_id: id,
                        timestamp: data.timestamp || Date.now() / 1000,
                        severity: 'INFO',
                        object_class: detections
                            .map(d => `${d.class_name} (${(d.confidence * 100).toFixed(0)}%)`)
                            .join(', '),
                        description: `${detections.length} object(s) entered frame`,
                    });
                    hadDetectionsRef.current = true;
                }
            } else {
                // Frame is empty - clear tracked objects so when an object returns, it triggers a new arrival alert
                activeTracksRef.current.clear();
                hadDetectionsRef.current = false;
            }
        } catch (_) {}
    }, [id, addEvent]);

    useEffect(() => {
        load();
        const detInterval = setInterval(pollDetections, 2000);

        const unsubEvent = wsService.subscribe('NEW_EVENT', (data) => {
            if (!data.camera_id || data.camera_id === id) addEvent(data);
        });
        
        const unsubStatus = wsService.subscribe('NEW_CAMERA_STATUS', (data) => {
             if (data.camera_id === id) setCamera(prev => ({...prev, status: data.status === 'ONLINE' ? 'active' : 'inactive'}));
        });

        return () => {
            clearInterval(detInterval);
            unsubEvent();
            unsubStatus();
        };
    }, [id, load, pollDetections, addEvent]);

    const handleToggleStream = async () => {
        if (!camera) return;
        setIsStarting(true);
        try {
            const action = camera.status === 'active' ? 'stop' : 'start';
            const res = await fetch(`${API_BASE_URL}/cameras/${camera.id}/${action}`, {
                method: 'POST',
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || res.statusText);
            }
            await load();
            if (action === 'start') setStreamKey(Date.now());
        } catch (err) {
            alert(`Failed to toggle stream: ${err.message}`);
        } finally {
            setIsStarting(false);
        }
    };

    const backLink = location.state?.fromMap ? "/camera-map" : "/cameras";
    const backLabel = location.state?.fromMap ? "Back to Camera Map" : "Back to Cameras";

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-full space-y-4">
                <div className="text-status-red p-4 bg-status-red/10 border border-status-red/30 rounded text-sm transition-colors text-center">
                    <p className="font-semibold mb-2">{error}</p>
                    <Link to={backLink} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-panel hover:bg-panel-alt text-primary rounded border border-default transition-colors">
                        <ArrowLeft size={14} /> {backLabel}
                    </Link>
                </div>
            </div>
        );
    }
    if (!camera) return <div className="p-4 text-secondary animate-pulse text-sm transition-colors">Loading camera details…</div>;

    const isOnline   = camera.status === 'active';
    const streamUrl  = `${API_BASE_URL}/cameras/${id}/stream?t=${streamKey}`;

    return (
        <div className="h-full flex flex-col space-y-3">
            {/* ── Header ── */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Link to={backLink}
                        title={backLabel}
                        className="p-1.5 hover:bg-border-default rounded transition-colors text-secondary hover:text-primary">
                        <ArrowLeft size={16} />
                    </Link>
                    <div>
                        <h2 className="text-base font-bold flex items-center gap-2 transition-colors">
                            {camera.name}
                            <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold tracking-wider transition-colors ${
                                isOnline
                                    ? 'bg-status-green/15 text-status-green border border-status-green/25'
                                    : 'bg-base text-secondary border border-default'
                            }`}>
                                {isOnline ? 'LIVE' : 'OFFLINE'}
                            </span>
                        </h2>
                        <p className="text-muted text-[11px] font-mono mt-0.5 transition-colors">
                            {camera.type?.toUpperCase()} • {camera.source}
                        </p>
                    </div>
                </div>
                <button
                    onClick={handleToggleStream}
                    disabled={isStarting}
                    className={`px-4 py-1.5 rounded font-semibold text-xs transition-colors ${
                        isOnline
                            ? 'bg-status-red/10 hover:bg-status-red/20 text-status-red border border-status-red/20'
                            : 'bg-status-green hover:opacity-90 text-white'
                    }`}
                >
                    {isStarting ? 'Please wait…' : isOnline ? '⏹ Stop Stream' : '▶ Start Stream'}
                </button>
            </div>

            {/* ── Main grid ── */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-3 min-h-0">

                {/* ── Left: video + fence editor ── */}
                <div className="lg:col-span-2 flex flex-col gap-3">
                    {/* Video panel */}
                    <div
                        ref={videoContainerRef}
                        className="bg-black rounded overflow-hidden border border-default relative transition-colors shadow-panel"
                        style={{ minHeight: '300px' }}
                    >
                        {isOnline ? (
                            <>
                                <img
                                    key={streamKey}
                                    src={streamUrl}
                                    alt={`Live stream: ${camera.name}`}
                                    className="w-full h-full object-contain"
                                    onLoad={(e) => setVideoDims({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
                                    onError={(e) => {
                                        setTimeout(() => {
                                            e.target.src = streamUrl + '&retry=' + Date.now();
                                        }, 2000);
                                    }}
                                />
                                {/* Fence polygon overlay */}
                                <FenceOverlay
                                    cameraId={id}
                                    containerRef={videoContainerRef}
                                    videoDims={videoDims}
                                />
                            </>
                        ) : (
                            <div className="absolute inset-0 flex flex-col items-center justify-center text-muted bg-base transition-colors">
                                <VideoOff size={40} className="mb-3 opacity-40" />
                                <p className="font-medium uppercase tracking-widest opacity-60 text-xs">Stream Unavailable</p>
                                <p className="text-[11px] mt-1.5 opacity-50">Click "Start Stream" to begin</p>
                            </div>
                        )}
                    </div>

                    {/* Fence Editor (always visible) */}
                    <FenceEditor cameraId={id} isOnline={isOnline} />
                </div>

                {/* ── Right: Live Detection Log ── */}
                <div className="lg:col-span-1 bg-panel rounded border border-default flex flex-col overflow-hidden transition-colors shadow-panel">
                    <div className="px-3 py-2.5 border-b border-default flex items-center justify-between transition-colors">
                        <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider flex items-center gap-1.5 transition-colors">
                            <Target size={12} className="text-status-blue" />
                            Detection Log
                        </h3>
                        {events.length > 0 && (
                            <span className="text-[10px] bg-status-blue/20 text-status-blue border border-status-blue/30 px-1.5 py-0.5 rounded font-medium transition-colors">
                                {events.length}
                            </span>
                        )}
                    </div>
                    <div className="flex-1 overflow-y-auto p-2.5 space-y-1.5">
                        {events.length === 0 ? (
                            <div className="text-center mt-10 space-y-2">
                                <Activity size={22} className="mx-auto text-muted" />
                                <p className="text-secondary text-xs transition-colors">
                                    {isOnline ? 'Waiting for detections…' : 'Start the stream to see live events'}
                                </p>
                            </div>
                        ) : (
                            events.map((evt, idx) => (
                                <EventCard key={`${evt.timestamp}-${idx}`} evt={evt} />
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CameraViewer;
