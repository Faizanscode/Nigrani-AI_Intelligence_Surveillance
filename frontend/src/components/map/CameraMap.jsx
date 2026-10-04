import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, useMap, useMapEvents, Marker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './map.css';
import { fetchCameraMap, addCamera } from '../../services/api';
import { wsService } from '../../services/websocket';
import { invalidateCameraCache } from '../../utils/cameraMap';
import {
    Search, RefreshCw, Camera, AlertTriangle, WifiOff, Wifi,
    X, ExternalLink, List, ChevronDown, Activity, Plus
} from 'lucide-react';

// ── Tile layer URLs ──────────────────────────────────────────────────────────
const TILE_DARK  = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_LIGHT = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_ATTR  = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

// India national center + zoom
const INDIA_CENTER = [22.5, 80.0];
const INDIA_ZOOM   = 5;

// ── Status config ────────────────────────────────────────────────────────────
const STATUS_CONFIG = {
    'ONLINE':       { color: 'var(--status-green)', cls: 'online',  label: 'Online',       dot: '#22c55e' },
    'ACTIVE ALERT': { color: 'var(--status-red)',   cls: 'alert',   label: 'Active Alert', dot: '#ef4444' },
    'OFFLINE':      { color: '#475569',             cls: 'offline', label: 'Offline',      dot: '#475569' },
};

function statusCls(status) {
    return STATUS_CONFIG[status]?.cls ?? 'offline';
}

// ── Validate lat/lon ─────────────────────────────────────────────────────────
function isValidCoord(lat, lng) {
    return (
        lat != null && lng != null &&
        isFinite(lat) && isFinite(lng) &&
        lat >= -90 && lat <= 90 &&
        lng >= -180 && lng <= 180
    );
}

// ── Build Leaflet DivIcon for a camera marker ────────────────────────────────
function buildIcon(status, isSearched) {
    const cls = statusCls(status);
    const searchCls = isSearched ? 'searched' : '';
    return L.divIcon({
        className: 'cam-marker',
        html: `<div class="cam-marker-dot ${cls} ${searchCls}"></div>`,
        iconSize:   [12, 12],
        iconAnchor: [6, 6],
        popupAnchor:[0, -8],
    });
}

// ── Removed ThemeAwareTile in favor of standard TileLayer ────────────────────

// ── Camera markers rendered directly on map ──────────────────────────────────
function CameraMarkers({ cameras, onSelect, searchActive }) {
    const map = useMap();
    const markersMapRef = useRef(new Map()); // camera.id -> L.marker

    // Zoom and pan if exactly one camera is searched
    useEffect(() => {
        if (searchActive && cameras.length === 1) {
            const cam = cameras[0];
            if (isValidCoord(cam.latitude, cam.longitude)) {
                map.flyTo([cam.latitude, cam.longitude], 12, { animate: true, duration: 1.5 });
            }
        }
    }, [cameras, map, searchActive]);

    useEffect(() => {
        const currentIds = new Set();
        const isSingleSearchMatch = searchActive && cameras.length === 1;

        cameras.forEach(cam => {
            if (!isValidCoord(cam.latitude, cam.longitude)) return;
            
            currentIds.add(cam.id);
            const icon = buildIcon(cam.status, isSingleSearchMatch);
            const latlng = [cam.latitude, cam.longitude];

            let marker = markersMapRef.current.get(cam.id);
            if (marker) {
                // Update existing marker
                marker.setIcon(icon);
                marker.setLatLng(latlng);
                // We update the click handler to use the latest cam object
                marker.off('click');
                marker.on('click', () => onSelect(cam));
            } else {
                // Create new marker
                marker = L.marker(latlng, { icon });
                marker.on('click', () => onSelect(cam));
                marker.addTo(map);
                markersMapRef.current.set(cam.id, marker);
            }
        });

        // Remove markers that are no longer in the cameras list
        for (const [id, marker] of markersMapRef.current.entries()) {
            if (!currentIds.has(id)) {
                marker.remove();
                markersMapRef.current.delete(id);
            }
        }
        
        // We do NOT return a cleanup function that clears all markers here,
        // otherwise they would be destroyed on every re-render (since this effect runs on every update).
    }, [cameras, map, onSelect, searchActive]);

    // Cleanup on unmount only
    useEffect(() => {
        return () => {
            for (const marker of markersMapRef.current.values()) {
                marker.remove();
            }
            markersMapRef.current.clear();
        };
    }, []);

    return null;
}

// ── Location Picker (Add Camera) ─────────────────────────────────────────────
function LocationPicker({ onLocationSelected, isSelecting }) {
    useMapEvents({
        click(e) {
            if (isSelecting) {
                onLocationSelected(e.latlng);
            }
        }
    });
    return null;
}

// ── Camera Registration Form ──────────────────────────────────────────────────
function AddCameraForm({ location, onCancel, onSave }) {
    const [formData, setFormData] = useState({
        name: '', type: 'rtsp', source: '', 
        border_region: 'NORTH', border_state: '', border_sector: '', bop_name: ''
    });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    const handleChange = (e) => setFormData(p => ({ ...p, [e.target.name]: e.target.value }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        setError(null);
        try {
            const payload = {
                ...formData,
                latitude: location.lat,
                longitude: location.lng,
            };
            await onSave(payload);
        } catch (err) {
            setError(err.message);
            setSaving(false);
        }
    };

    return (
        <div style={{
            position: 'absolute', top: '12px', right: '12px', zIndex: 900,
            width: '320px', background: 'var(--bg-panel)',
            border: '1px solid var(--border-default)', borderRadius: '6px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.35)', overflow: 'hidden'
        }}>
            <div style={{
                background: 'var(--bg-panel-alt)', borderBottom: '1px solid var(--border-default)',
                padding: '10px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
            }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>Register New Camera</div>
                <button onClick={onCancel} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}><X size={14} /></button>
            </div>
            
            <form onSubmit={handleSubmit} style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {error && <div style={{ fontSize: '11px', color: 'var(--status-red)', background: 'var(--status-red)15', padding: '6px', borderRadius: '4px' }}>{error}</div>}
                
                <div style={{ display: 'flex', gap: '8px' }}>
                    <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '2px' }}>LATITUDE</label>
                        <input type="text" readOnly value={location.lat.toFixed(6)} style={{ width: '100%', padding: '6px', fontSize: '12px', background: 'var(--bg-base)', border: '1px solid var(--border-default)', color: 'var(--text-secondary)', boxSizing: 'border-box' }} />
                    </div>
                    <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '2px' }}>LONGITUDE</label>
                        <input type="text" readOnly value={location.lng.toFixed(6)} style={{ width: '100%', padding: '6px', fontSize: '12px', background: 'var(--bg-base)', border: '1px solid var(--border-default)', color: 'var(--text-secondary)', boxSizing: 'border-box' }} />
                    </div>
                </div>

                <div>
                    <label style={{ display: 'block', fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '2px' }}>CAMERA NAME *</label>
                    <input name="name" required value={formData.name} onChange={handleChange} placeholder="e.g. Border Camera 05" style={{ width: '100%', padding: '6px', fontSize: '12px', background: 'var(--bg-base)', border: '1px solid var(--border-default)', color: 'var(--text-primary)', boxSizing: 'border-box' }} />
                </div>
                
                <div style={{ display: 'flex', gap: '8px' }}>
                    <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '2px' }}>VIDEO TYPE *</label>
                        <select name="type" value={formData.type} onChange={handleChange} style={{ width: '100%', padding: '6px', fontSize: '12px', background: 'var(--bg-base)', border: '1px solid var(--border-default)', color: 'var(--text-primary)', boxSizing: 'border-box' }}>
                            <option value="rtsp">RTSP Stream</option>
                            <option value="webcam">Webcam</option>
                            <option value="file">Video File</option>
                        </select>
                    </div>
                    <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '2px' }}>REGION</label>
                        <select name="border_region" value={formData.border_region} onChange={handleChange} style={{ width: '100%', padding: '6px', fontSize: '12px', background: 'var(--bg-base)', border: '1px solid var(--border-default)', color: 'var(--text-primary)', boxSizing: 'border-box' }}>
                            <option value="NORTH">North</option>
                            <option value="WEST">West</option>
                            <option value="EAST">East</option>
                            <option value="SOUTH">South</option>
                            <option value="NORTHEAST">Northeast</option>
                        </select>
                    </div>
                </div>
                
                <div>
                    <label style={{ display: 'block', fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '2px' }}>SOURCE URL *</label>
                    <input name="source" required value={formData.source} onChange={handleChange} placeholder="rtsp://... or 0" style={{ width: '100%', padding: '6px', fontSize: '12px', background: 'var(--bg-base)', border: '1px solid var(--border-default)', color: 'var(--text-primary)', boxSizing: 'border-box' }} />
                </div>
                
                <div>
                    <label style={{ display: 'block', fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '2px' }}>STATE / SECTOR / BOP</label>
                    <div style={{ display: 'flex', gap: '4px', boxSizing: 'border-box' }}>
                        <input name="border_state" value={formData.border_state} onChange={handleChange} placeholder="State" style={{ flex: 1, minWidth: 0, padding: '6px', fontSize: '12px', background: 'var(--bg-base)', border: '1px solid var(--border-default)', color: 'var(--text-primary)', boxSizing: 'border-box' }} />
                        <input name="border_sector" value={formData.border_sector} onChange={handleChange} placeholder="Sector" style={{ flex: 1, minWidth: 0, padding: '6px', fontSize: '12px', background: 'var(--bg-base)', border: '1px solid var(--border-default)', color: 'var(--text-primary)', boxSizing: 'border-box' }} />
                        <input name="bop_name" value={formData.bop_name} onChange={handleChange} placeholder="BOP" style={{ flex: 1, minWidth: 0, padding: '6px', fontSize: '12px', background: 'var(--bg-base)', border: '1px solid var(--border-default)', color: 'var(--text-primary)', boxSizing: 'border-box' }} />
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                    <button type="button" onClick={onCancel} style={{ flex: 1, padding: '8px', background: 'transparent', border: '1px solid var(--border-default)', color: 'var(--text-secondary)', cursor: 'pointer', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>CANCEL</button>
                    <button type="submit" disabled={saving} style={{ flex: 1, padding: '8px', background: 'var(--status-blue)', border: 'none', color: '#fff', cursor: 'pointer', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>{saving ? 'SAVING...' : 'SAVE CAMERA'}</button>
                </div>
            </form>
        </div>
    );
}

// ── Camera info popup panel (sidebar-style, not Leaflet popup) ───────────────
function CameraInfoPanel({ camera, onClose }) {
    const navigate = useNavigate();
    if (!camera) return null;

    const cfg = STATUS_CONFIG[camera.status] ?? STATUS_CONFIG['OFFLINE'];

    const handleViewLive = () => {
        navigate(`/cameras/${camera.id}`, { state: { fromMap: true } });
    };

    const handleViewEvents = () => {
        navigate(`/events?camera=${camera.id}`, { state: { fromMap: true } });
    };

    return (
        <div
            style={{
                position: 'absolute', top: '12px', right: '12px', zIndex: 900,
                width: '248px',
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-default)',
                borderRadius: '6px',
                boxShadow: '0 4px 24px rgba(0,0,0,0.35)',
                overflow: 'hidden',
            }}
        >
            {/* Header */}
            <div style={{
                background: 'var(--bg-panel-alt)',
                borderBottom: '1px solid var(--border-default)',
                padding: '10px 12px',
                display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px'
            }}>
                <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '2px' }}>
                        {camera.id}
                    </div>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.3, wordBreak: 'break-word' }}>
                        {camera.name}
                    </div>
                </div>
                <button
                    onClick={onClose}
                    style={{
                        flexShrink: 0, background: 'transparent', border: 'none', cursor: 'pointer',
                        color: 'var(--text-muted)', padding: '2px', borderRadius: '3px',
                        display: 'flex', alignItems: 'center', lineHeight: 1
                    }}
                    aria-label="Close camera info"
                >
                    <X size={14} />
                </button>
            </div>

            {/* Status badge */}
            <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-default)' }}>
                <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: '5px',
                    fontSize: '11px', fontWeight: 700, padding: '3px 8px',
                    borderRadius: '3px', textTransform: 'uppercase', letterSpacing: '0.05em',
                    color: cfg.color,
                    background: `${cfg.color}15`,
                    border: `1px solid ${cfg.color}30`,
                }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: cfg.color, flexShrink: 0 }} />
                    {cfg.label}
                </span>
            </div>

            {/* Metadata */}
            <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {[
                    ['Sector',  camera.border_sector],
                    ['State',   camera.border_state],
                    ['Region',  camera.border_region],
                    ['BOP',     camera.bop_name],
                ].map(([label, value]) => value ? (
                    <div key={label} style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', minWidth: '46px', flexShrink: 0 }}>
                            {label}
                        </span>
                        <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 500, lineHeight: 1.3 }}>
                            {value}
                        </span>
                    </div>
                ) : null)}
                {camera.latitude != null && (
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', minWidth: '46px', flexShrink: 0 }}>
                            Coords
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
                            {camera.latitude.toFixed(4)}°N, {camera.longitude.toFixed(4)}°E
                        </span>
                    </div>
                )}
            </div>

            {/* Actions */}
            <div style={{ padding: '10px 12px', borderTop: '1px solid var(--border-default)', display: 'flex', gap: '6px' }}>
                <button
                    onClick={handleViewLive}
                    style={{
                        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px',
                        fontSize: '11px', fontWeight: 600, padding: '6px 8px', borderRadius: '4px',
                        cursor: 'pointer', border: '1px solid var(--status-blue)',
                        background: 'var(--status-blue)15', color: 'var(--status-blue)',
                        textTransform: 'uppercase', letterSpacing: '0.05em', transition: 'background 0.15s',
                    }}
                >
                    <ExternalLink size={11} />
                    View Live
                </button>
                <button
                    onClick={handleViewEvents}
                    style={{
                        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px',
                        fontSize: '11px', fontWeight: 600, padding: '6px 8px', borderRadius: '4px',
                        cursor: 'pointer', border: '1px solid var(--border-hover)',
                        background: 'transparent', color: 'var(--text-secondary)',
                        textTransform: 'uppercase', letterSpacing: '0.05em', transition: 'background 0.15s',
                    }}
                >
                    <List size={11} />
                    Events
                </button>
            </div>
        </div>
    );
}

// ── Simple select dropdown ───────────────────────────────────────────────────
function FilterSelect({ label, value, onChange, options }) {
    return (
        <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
            <select
                value={value}
                onChange={e => onChange(e.target.value)}
                aria-label={label}
                style={{
                    appearance: 'none',
                    background: 'var(--bg-panel)',
                    border: '1px solid var(--border-default)',
                    borderRadius: '4px',
                    color: value ? 'var(--text-primary)' : 'var(--text-muted)',
                    fontSize: '12px',
                    fontWeight: 500,
                    padding: '5px 26px 5px 10px',
                    cursor: 'pointer',
                    outline: 'none',
                    fontFamily: 'inherit',
                }}
            >
                <option value="">{label}</option>
                {options.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                ))}
            </select>
            <ChevronDown size={12} style={{ position: 'absolute', right: '8px', pointerEvents: 'none', color: 'var(--text-muted)' }} />
        </div>
    );
}

// ── Stat pill ────────────────────────────────────────────────────────────────
function StatPill({ icon: Icon, count, label, color }) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 10px', background: 'var(--bg-panel-alt)', border: '1px solid var(--border-default)', borderRadius: '4px' }}>
            <Icon size={12} style={{ color, flexShrink: 0 }} />
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>{count}</span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
        </div>
    );
}

// ── Legend ───────────────────────────────────────────────────────────────────
function MapLegend() {
    return (
        <div style={{
            position: 'absolute', bottom: '28px', left: '12px', zIndex: 900,
            background: 'var(--bg-panel)',
            border: '1px solid var(--border-default)',
            borderRadius: '5px',
            padding: '8px 12px',
            display: 'flex', flexDirection: 'column', gap: '5px',
        }}>
            <div style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '2px' }}>Legend</div>
            {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
                <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: cfg.dot, flexShrink: 0, border: '1px solid rgba(255,255,255,0.15)' }} />
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 500 }}>{cfg.label}</span>
                </div>
            ))}
        </div>
    );
}

// ── Region and state options ─────────────────────────────────────────────────
const REGION_OPTIONS = [
    { value: 'NORTH',     label: 'North' },
    { value: 'WEST',      label: 'West' },
    { value: 'EAST',      label: 'East' },
    { value: 'SOUTH',     label: 'South' },
    { value: 'NORTHEAST', label: 'Northeast' },
];

const STATUS_OPTIONS = [
    { value: 'ONLINE',       label: 'Online' },
    { value: 'ACTIVE ALERT', label: 'Active Alert' },
    { value: 'OFFLINE',      label: 'Offline' },
];

// ── Main CameraMap page ──────────────────────────────────────────────────────
export default function CameraMap() {
    const [cameras,    setCameras]    = useState([]);
    const [loading,    setLoading]    = useState(true);
    const [error,      setError]      = useState(null);
    const [search,     setSearch]     = useState('');
    const [filterStatus,  setFilterStatus]  = useState('');
    const [filterRegion,  setFilterRegion]  = useState('');
    const [selected,   setSelected]   = useState(null);
    const [wsConnected, setWsConnected] = useState(wsService.isConnected);

    // Add camera state
    const [isSelectingLocation, setIsSelectingLocation] = useState(false);
    const [newLocation, setNewLocation] = useState(null);
    const [showRegistrationForm, setShowRegistrationForm] = useState(false);
    const [notification, setNotification] = useState(null);
    const [mapReady, setMapReady] = useState(false);

    const activeAlertsRef = useRef(new Map());

    useEffect(() => {
        const timer = setTimeout(() => setMapReady(true), 200);
        return () => clearTimeout(timer);
    }, []);

    // Detect current theme for tile layer
    const [isDark, setIsDark] = useState(
        () => !document.documentElement.hasAttribute('data-theme')
    );
    useEffect(() => {
        const observer = new MutationObserver(() => {
            setIsDark(!document.documentElement.hasAttribute('data-theme'));
        });
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
        return () => observer.disconnect();
    }, []);

    const loadCameras = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchCameraMap();
            setCameras(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error('[CameraMap] Failed to load cameras:', err);
            setError('Unable to load camera network.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadCameras();
    }, [loadCameras]);

    useEffect(() => {
        const unsubConn = wsService.subscribe('connection', setWsConnected);
        
        const unsubStatus = wsService.subscribe('NEW_CAMERA_STATUS', (data) => {
            setCameras(prev => prev.map(c => 
                c.id === data.camera_id ? { ...c, status: data.status } : c
            ));
        });

        const handleNewAlert = (alert) => {
            const camId = alert.camera_id;
            const alertId = alert.alert_id;
            if (!activeAlertsRef.current.has(camId)) {
                activeAlertsRef.current.set(camId, new Set());
            }
            activeAlertsRef.current.get(camId).add(alertId);
            
            setCameras(prev => prev.map(c => 
                c.id === camId ? { ...c, status: 'ACTIVE ALERT' } : c
            ));
        };

        const handleAlertUpdated = (alert) => {
            const camId = alert.camera_id;
            const alertId = alert.alert_id;
            if (alert.status !== 'NEW') { 
                if (activeAlertsRef.current.has(camId)) {
                    activeAlertsRef.current.get(camId).delete(alertId);
                }
                const count = activeAlertsRef.current.has(camId) ? activeAlertsRef.current.get(camId).size : 0;
                if (count === 0) {
                    setCameras(prev => prev.map(c => {
                        // Keep OFFLINE as OFFLINE, otherwise revert to ONLINE
                        if (c.id === camId && c.status === 'ACTIVE ALERT') {
                            return { ...c, status: 'ONLINE' };
                        }
                        return c;
                    }));
                }
            }
        };

        const unsubNewAlert = wsService.subscribe('NEW_ALERT', handleNewAlert);
        const unsubAlertUpdate = wsService.subscribe('ALERT_UPDATED', handleAlertUpdated);

        return () => {
            unsubConn();
            unsubStatus();
            unsubNewAlert();
            unsubAlertUpdate();
        };
    }, []);

    // Derived stats from raw data (not filtered)
    const stats = useMemo(() => ({
        total:  cameras.length,
        online: cameras.filter(c => c.status === 'ONLINE').length,
        alert:  cameras.filter(c => c.status === 'ACTIVE ALERT').length,
        offline:cameras.filter(c => c.status === 'OFFLINE').length,
    }), [cameras]);

    // Fixed list of Indian border states
    const stateOptions = useMemo(() => [
        { value: 'Arunachal Pradesh', label: 'Arunachal Pradesh' },
        { value: 'Assam', label: 'Assam' },
        { value: 'Bihar', label: 'Bihar' },
        { value: 'Gujarat', label: 'Gujarat' },
        { value: 'Himachal Pradesh', label: 'Himachal Pradesh' },
        { value: 'Jammu and Kashmir', label: 'Jammu and Kashmir' },
        { value: 'Ladakh', label: 'Ladakh' },
        { value: 'Meghalaya', label: 'Meghalaya' },
        { value: 'Mizoram', label: 'Mizoram' },
        { value: 'Nagaland', label: 'Nagaland' },
        { value: 'Punjab', label: 'Punjab' },
        { value: 'Rajasthan', label: 'Rajasthan' },
        { value: 'Sikkim', label: 'Sikkim' },
        { value: 'Tripura', label: 'Tripura' },
        { value: 'Uttar Pradesh', label: 'Uttar Pradesh' },
        { value: 'Uttarakhand', label: 'Uttarakhand' },
        { value: 'West Bengal', label: 'West Bengal' },
    ], []);

    const [filterState, setFilterState] = useState('');

    // Client-side filter + search
    const filtered = useMemo(() => {
        const q = search.trim().toLowerCase();
        return cameras.filter(cam => {
            if (filterStatus && cam.status !== filterStatus) return false;
            if (filterRegion && cam.border_region !== filterRegion) return false;
            if (filterState && cam.border_state !== filterState) return false;
            if (!q) return true;
            return (
                (cam.id          || '').toLowerCase().includes(q) ||
                (cam.name        || '').toLowerCase().includes(q) ||
                (cam.border_sector || '').toLowerCase().includes(q) ||
                (cam.border_state  || '').toLowerCase().includes(q) ||
                (cam.bop_name      || '').toLowerCase().includes(q)
            );
        });
    }, [cameras, search, filterStatus, filterRegion, filterState]);

    // Validate coords for map — skip invalid
    const validCameras = useMemo(() => filtered.filter(c => isValidCoord(c.latitude, c.longitude)), [filtered]);
    const invalidCount  = useMemo(() => filtered.length - validCameras.length, [filtered, validCameras]);

    const handleSelect = useCallback((cam) => {
        if (!isSelectingLocation && !showRegistrationForm) {
            setSelected(cam);
        }
    }, [isSelectingLocation, showRegistrationForm]);

    const clearFilters = () => {
        setSearch('');
        setFilterStatus('');
        setFilterRegion('');
        setFilterState('');
    };

    const handleStartAddCamera = () => {
        setIsSelectingLocation(true);
        setNewLocation(null);
        setShowRegistrationForm(false);
        setSelected(null);
    };

    const handleCancelAdd = () => {
        setIsSelectingLocation(false);
        setNewLocation(null);
        setShowRegistrationForm(false);
    };

    const handleConfirmLocation = () => {
        setIsSelectingLocation(false);
        setShowRegistrationForm(true);
    };

    const handleSaveCamera = async (payload) => {
        try {
            const result = await addCamera(payload);
            invalidateCameraCache(); // ensure recent events fetch the new name
            
            const newCam = {
                id: result.id,
                name: payload.name,
                source: payload.source,
                type: payload.type,
                status: 'ONLINE',
                latitude: payload.latitude,
                longitude: payload.longitude,
                border_sector: payload.border_sector,
                border_state: payload.border_state,
                border_region: payload.border_region,
                bop_name: payload.bop_name
            };
            setCameras(prev => [...prev, newCam]);
            setShowRegistrationForm(false);
            setNewLocation(null);
            setNotification('Camera registered successfully.');
            setTimeout(() => setNotification(null), 3000);
        } catch (err) {
            throw err; // Form will handle it
        }
    };

    const hasFilters = search || filterStatus || filterRegion || filterState;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px' }}>

            {/* ── Page Header ──────────────────────────────────────────────── */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', flexShrink: 0 }}>
                <div>
                    <h1 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', margin: 0, letterSpacing: '0.02em' }}>
                        National Border Surveillance Network
                    </h1>
                    <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: '2px 0 0', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        Camera Network Overview
                        <span style={{ 
                            display: 'inline-flex', alignItems: 'center', gap: '4px',
                            color: wsConnected ? 'var(--status-green)' : 'var(--status-red)',
                            background: wsConnected ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                            padding: '2px 6px', borderRadius: '4px', fontWeight: 600, fontSize: '9px'
                        }}>
                            <Activity size={10} />
                            {wsConnected ? 'LIVE' : 'DISCONNECTED'}
                        </span>
                    </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    <StatPill icon={Camera}        count={stats.total}   label="Cameras"  color="var(--text-muted)"   />
                    <StatPill icon={Wifi}          count={stats.online}  label="Online"   color="var(--status-green)" />
                    <StatPill icon={AlertTriangle} count={stats.alert}   label="Alerts"   color="var(--status-red)"   />
                    <StatPill icon={WifiOff}       count={stats.offline} label="Offline"  color="#475569"             />
                    <button
                        onClick={loadCameras}
                        disabled={loading}
                        title="Refresh camera data"
                        aria-label="Refresh camera data"
                        style={{
                            background: 'var(--bg-panel)',
                            border: '1px solid var(--border-default)',
                            borderRadius: '4px',
                            padding: '5px 8px',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            color: 'var(--text-secondary)',
                            display: 'flex', alignItems: 'center',
                        }}
                    >
                        <RefreshCw size={13} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
                    </button>
                    <button 
                        onClick={handleStartAddCamera} 
                        disabled={isSelectingLocation || showRegistrationForm}
                        style={{ 
                            display: 'flex', alignItems: 'center', gap: '5px', 
                            background: 'var(--status-blue)', border: 'none', borderRadius: '4px', 
                            padding: '5px 12px', color: '#fff', fontSize: '11px', fontWeight: 600, 
                            cursor: (isSelectingLocation || showRegistrationForm) ? 'not-allowed' : 'pointer',
                            opacity: (isSelectingLocation || showRegistrationForm) ? 0.6 : 1
                        }}>
                        <Plus size={12}/> ADD CAMERA
                    </button>
                </div>
            </div>

            {/* ── Controls bar ─────────────────────────────────────────────── */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', flexShrink: 0 }}>
                {/* Search */}
                <div style={{ position: 'relative', flex: '1', minWidth: '180px', maxWidth: '280px' }}>
                    <Search size={12} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
                    <input
                        type="text"
                        placeholder="Search camera, sector, state, BOP..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        aria-label="Search cameras"
                        style={{
                            width: '100%', boxSizing: 'border-box',
                            background: 'var(--bg-panel)',
                            border: '1px solid var(--border-default)',
                            borderRadius: '4px',
                            color: 'var(--text-primary)',
                            fontSize: '12px',
                            padding: '5px 10px 5px 28px',
                            outline: 'none',
                            fontFamily: 'inherit',
                        }}
                    />
                </div>

                <FilterSelect label="Status ▾"  value={filterStatus} onChange={setFilterStatus} options={STATUS_OPTIONS} />
                <FilterSelect label="Region ▾"  value={filterRegion} onChange={setFilterRegion} options={REGION_OPTIONS} />
                <FilterSelect label="State ▾"   value={filterState}  onChange={setFilterState}  options={stateOptions}   />

                {hasFilters && (
                    <button
                        onClick={clearFilters}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '4px',
                            background: 'transparent', border: '1px solid var(--border-default)',
                            borderRadius: '4px', padding: '5px 8px',
                            fontSize: '11px', color: 'var(--text-muted)', cursor: 'pointer',
                            fontFamily: 'inherit',
                        }}
                    >
                        <X size={11} /> Clear
                    </button>
                )}

                <div style={{ marginLeft: 'auto', fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                    {loading ? 'Loading…' : `${validCameras.length} of ${cameras.length} camera${cameras.length !== 1 ? 's' : ''}`}
                    {invalidCount > 0 && <span style={{ color: 'var(--status-amber)' }}> · {invalidCount} no coords</span>}
                </div>
            </div>

            {/* ── Map area ─────────────────────────────────────────────────── */}
            <div style={{
                flex: 1, minHeight: 0, position: 'relative',
                border: '1px solid var(--border-default)', borderRadius: '6px', overflow: 'hidden',
                background: 'var(--bg-base)',
            }}>
                {/* Loading overlay */}
                {loading && (
                    <div style={{
                        position: 'absolute', inset: 0, zIndex: 1000,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: 'var(--bg-base)', flexDirection: 'column', gap: '10px',
                    }}>
                        <RefreshCw size={24} style={{ color: 'var(--text-muted)', animation: 'spin 1s linear infinite' }} />
                        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Loading camera network…</span>
                    </div>
                )}

                {/* Error overlay */}
                {!loading && error && (
                    <div style={{
                        position: 'absolute', inset: 0, zIndex: 1000,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: 'var(--bg-base)', flexDirection: 'column', gap: '10px',
                    }}>
                        <AlertTriangle size={24} style={{ color: 'var(--status-red)' }} />
                        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{error}</span>
                        <button
                            onClick={loadCameras}
                            style={{
                                padding: '6px 16px', fontSize: '12px', fontWeight: 600,
                                background: 'var(--bg-panel)', border: '1px solid var(--border-default)',
                                borderRadius: '4px', cursor: 'pointer', color: 'var(--text-primary)',
                                fontFamily: 'inherit',
                            }}
                        >
                            Retry
                        </button>
                    </div>
                )}

                {/* Empty state (after load, no cameras at all) */}
                {!loading && !error && cameras.length === 0 && (
                    <div style={{
                        position: 'absolute', inset: 0, zIndex: 1000,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: 'var(--bg-base)', flexDirection: 'column', gap: '8px',
                    }}>
                        <Camera size={24} style={{ color: 'var(--text-muted)', opacity: 0.4 }} />
                        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No cameras available.</span>
                    </div>
                )}

                {/* Leaflet Map */}
                {!error && mapReady && (
                    <MapContainer
                        center={INDIA_CENTER}
                        zoom={INDIA_ZOOM}
                        minZoom={5}
                        maxBounds={[
                            [5.0, 65.0],  // Southwest coordinates
                            [38.0, 100.0] // Northeast coordinates
                        ]}
                        maxBoundsViscosity={1.0}
                        style={{ width: '100%', height: '100%', cursor: isSelectingLocation ? 'crosshair' : 'grab' }}
                        zoomControl={true}
                        attributionControl={true}
                    >
                        <TileLayer 
                            className={isDark ? 'dark-tiles' : ''}
                            url={TILE_LIGHT} // Note: url doesn't need to change, filter handles dark mode
                            attribution={TILE_ATTR}
                            maxZoom={18}
                        />
                        <CameraMarkers 
                            cameras={validCameras} 
                            onSelect={handleSelect} 
                            searchActive={search.trim() !== ''} 
                        />
                        
                        <LocationPicker isSelecting={isSelectingLocation} onLocationSelected={setNewLocation} />
                        
                        {newLocation && (
                            <Marker 
                                position={newLocation} 
                                draggable={isSelectingLocation} 
                                eventHandlers={{ dragend: (e) => setNewLocation(e.target.getLatLng()) }}
                                icon={L.divIcon({
                                    className: 'new-cam-marker',
                                    html: `<div class="cam-marker-dot" style="background: var(--status-blue); border-color: rgba(59, 130, 246, 0.4); width: 16px; height: 16px; border-radius: 50%; border: 3px solid rgba(59, 130, 246, 0.4);"></div>`,
                                    iconSize: [16, 16],
                                    iconAnchor: [8, 8]
                                })}
                            />
                        )}
                    </MapContainer>
                )}

                {/* Camera info panel (overlaid on map) */}
                {selected && (
                    <CameraInfoPanel camera={selected} onClose={() => setSelected(null)} />
                )}

                {/* Legend (overlaid on map) */}
                {!loading && !error && <MapLegend />}
                
                {/* Location Selection Overlay */}
                {isSelectingLocation && !newLocation && (
                    <div style={{ position: 'absolute', bottom: '24px', left: '50%', transform: 'translateX(-50%)', zIndex: 900, background: 'var(--bg-panel)', padding: '12px 20px', borderRadius: '6px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)', textAlign: 'center' }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '10px' }}>SELECT CAMERA LOCATION</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>Click anywhere on the map to place the camera.</div>
                        <button onClick={handleCancelAdd} style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--border-default)', borderRadius: '4px', color: 'var(--text-secondary)', fontSize: '11px', fontWeight: 600, cursor: 'pointer' }}>CANCEL</button>
                    </div>
                )}
                
                {isSelectingLocation && newLocation && (
                    <div style={{ position: 'absolute', bottom: '24px', left: '50%', transform: 'translateX(-50%)', zIndex: 900, background: 'var(--bg-panel)', padding: '12px 20px', borderRadius: '6px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)', textAlign: 'center' }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '10px' }}>LOCATION SELECTED</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px', display: 'flex', gap: '12px', justifyContent: 'center' }}>
                            <span style={{ background: 'var(--bg-base)', padding: '4px 8px', borderRadius: '3px', border: '1px solid var(--border-default)' }}>Lat: <strong>{newLocation.lat.toFixed(6)}</strong></span>
                            <span style={{ background: 'var(--bg-base)', padding: '4px 8px', borderRadius: '3px', border: '1px solid var(--border-default)' }}>Lng: <strong>{newLocation.lng.toFixed(6)}</strong></span>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                            <button onClick={handleCancelAdd} style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--border-default)', borderRadius: '4px', color: 'var(--text-secondary)', fontSize: '11px', fontWeight: 600, cursor: 'pointer' }}>CANCEL</button>
                            <button onClick={handleConfirmLocation} style={{ padding: '6px 12px', background: 'var(--status-blue)', border: 'none', borderRadius: '4px', color: '#fff', fontSize: '11px', fontWeight: 600, cursor: 'pointer' }}>CONFIRM LOCATION</button>
                        </div>
                    </div>
                )}
                
                {showRegistrationForm && newLocation && (
                    <AddCameraForm 
                        location={newLocation} 
                        onCancel={handleCancelAdd} 
                        onSave={handleSaveCamera} 
                    />
                )}
                
                {notification && (
                    <div style={{ position: 'absolute', top: '24px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, background: 'var(--status-green)', color: '#fff', padding: '8px 16px', borderRadius: '4px', fontSize: '12px', fontWeight: 600, boxShadow: '0 4px 12px rgba(0,0,0,0.2)' }}>
                        {notification}
                    </div>
                )}

                {/* No results after filtering */}
                {!loading && !error && cameras.length > 0 && validCameras.length === 0 && (
                    <div style={{
                        position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                        zIndex: 800, background: 'var(--bg-panel)', border: '1px solid var(--border-default)',
                        borderRadius: '5px', padding: '12px 18px', textAlign: 'center',
                    }}>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                            No cameras match current filters.
                        </p>
                        {hasFilters && (
                            <button onClick={clearFilters} style={{ marginTop: '8px', fontSize: '11px', color: 'var(--status-blue)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit' }}>
                                Clear filters
                            </button>
                        )}
                    </div>
                )}
            </div>

            {/* Spin keyframes injected inline for RefreshCw animation */}
            <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        </div>
    );
}
