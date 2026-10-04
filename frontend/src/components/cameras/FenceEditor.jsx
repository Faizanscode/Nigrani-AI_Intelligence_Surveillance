/**
 * FenceEditor – per-camera virtual fence drawing tool.
 *
 * Modes:
 *  'view'  – shows saved fence overlay on top of the live stream
 *  'draw'  – live stream as background + interactive canvas for polygon drawing
 *
 * Coordinates are normalized [0-1] so the fence is resolution-independent.
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getFence, saveFence, deleteFence } from '../../services/api';
import { Shield, Edit, Trash2, Undo2, X, Save, RotateCcw, MapPin, VideoOff } from 'lucide-react';
import { displayToNormalized, normalizedToDisplay } from '../../utils/videoCoordinateUtils';

const API_BASE = 'http://localhost:8000/api/v1';

const FENCE_COLOR   = 'rgba(0, 230, 118, 0.90)';
const FILL_COLOR    = 'rgba(0, 230, 118, 0.15)';
const POINT_COLOR   = '#00ff88';
const PREVIEW_COLOR = 'rgba(0, 230, 118, 0.55)';

export default function FenceEditor({ cameraId, isOnline }) {
    const [mode, setMode]           = useState('view');
    const [fenceData, setFenceData] = useState(null);
    const [isDefault, setIsDefault] = useState(true);
    const [points, setPoints]       = useState([]);
    const [mousePos, setMousePos]   = useState(null);
    const [saving, setSaving]       = useState(false);
    const [error, setError]         = useState('');
    const [success, setSuccess]     = useState('');
    const [streamKey, setStreamKey] = useState(Date.now());
    const [videoDims, setVideoDims] = useState({ w: 0, h: 0 });

    const canvasRef    = useRef(null);
    const containerRef = useRef(null);
    const imgRef       = useRef(null);

    // Stream URL – same endpoint used by the Live Camera viewer
    const streamUrl = isOnline && cameraId
        ? `${API_BASE}/cameras/${cameraId}/stream?editor=1&t=${streamKey}`
        : null;

    // ── Load saved fence ────────────────────────────────────────────────────
    useEffect(() => {
        if (!cameraId) return;
        getFence(cameraId)
            .then(res => { setFenceData(res.fence || null); setIsDefault(res.is_default); })
            .catch(() => setFenceData(null));
    }, [cameraId]);

    // ── Canvas drawing ───────────────────────────────────────────────────────
    const drawCanvas = useCallback(() => {
        const canvas = canvasRef.current;
        const container = containerRef.current;
        if (!canvas || !container) return;

        const W = container.clientWidth;
        const H = container.clientHeight;
        canvas.width  = W;
        canvas.height = H;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, W, H);

        const px = ([nx, ny]) => {
            if (videoDims.w && videoDims.h) {
                return normalizedToDisplay(nx, ny, W, H, videoDims.w, videoDims.h);
            }
            return [nx * W, ny * H];
        };

        const drawShape = (pts, closed, fillColor, strokeColor, lineWidth = 2.5) => {
            if (pts.length < 1) return;
            ctx.beginPath();
            const [x0, y0] = px(pts[0]);
            ctx.moveTo(x0, y0);
            for (let i = 1; i < pts.length; i++) {
                const [xi, yi] = px(pts[i]);
                ctx.lineTo(xi, yi);
            }
            if (closed) ctx.closePath();
            if (fillColor && pts.length >= 3) { ctx.fillStyle = fillColor; ctx.fill(); }
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = lineWidth;
            ctx.setLineDash(closed ? [] : [6, 3]);
            ctx.stroke();
            ctx.setLineDash([]);
        };

        // ── VIEW mode: show saved fence ────────────────────────────────
        if (mode === 'view' && fenceData?.points) {
            const pts = fenceData.points;
            drawShape(pts, true, FILL_COLOR, FENCE_COLOR);
            pts.forEach(pt => {
                const [x, y] = px(pt);
                ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2);
                ctx.fillStyle = POINT_COLOR; ctx.fill();
            });
            if (pts.length > 0) {
                const [lx, ly] = px(pts[0]);
                ctx.font = 'bold 13px sans-serif';
                ctx.fillStyle = FENCE_COLOR;
                ctx.fillText('▸ ' + (fenceData.name || 'Custom Fence'), lx + 8, ly - 8);
            }
        }

        // ── DRAW mode: interactive polygon ─────────────────────────────
        if (mode === 'draw') {
            // Draw completed segments
            drawShape(points, false, null, FENCE_COLOR);

            // Preview line to cursor
            if (points.length > 0 && mousePos) {
                const [lastX, lastY] = px(points[points.length - 1]);
                ctx.beginPath(); ctx.moveTo(lastX, lastY); ctx.lineTo(mousePos[0], mousePos[1]);
                ctx.strokeStyle = PREVIEW_COLOR; ctx.lineWidth = 1.5;
                ctx.setLineDash([4, 4]); ctx.stroke(); ctx.setLineDash([]);

                if (points.length >= 3) {
                    const [fx, fy] = px(points[0]);
                    ctx.beginPath(); ctx.moveTo(mousePos[0], mousePos[1]); ctx.lineTo(fx, fy);
                    ctx.strokeStyle = PREVIEW_COLOR; ctx.lineWidth = 1;
                    ctx.setLineDash([2, 4]); ctx.stroke(); ctx.setLineDash([]);
                }
            }

            // Fill polygon if closed-enough
            if (points.length >= 3) {
                drawShape(points, true, FILL_COLOR, FENCE_COLOR);
            }

            // Draw point dots + numbers
            points.forEach(([nx, ny], idx) => {
                const [x, y] = px([nx, ny]);
                ctx.beginPath(); ctx.arc(x, y, idx === 0 ? 7 : 5, 0, Math.PI * 2);
                ctx.fillStyle = idx === 0 ? '#ffcc00' : POINT_COLOR; ctx.fill();
                ctx.strokeStyle = '#111'; ctx.lineWidth = 1; ctx.stroke();
                ctx.font = 'bold 10px sans-serif'; ctx.fillStyle = '#111';
                ctx.fillText(idx + 1, x - 3, y + 4);
            });

            // First-click prompt
            if (points.length === 0) {
                ctx.font = 'bold 14px sans-serif';
                ctx.fillStyle = 'rgba(255,255,255,0.85)';
                ctx.textAlign = 'center';
                ctx.shadowColor = 'rgba(0,0,0,0.7)';
                ctx.shadowBlur = 8;
                ctx.fillText('Click on the video to place fence points', W / 2, H / 2);
                ctx.shadowBlur = 0;
                ctx.textAlign = 'left';
            }
        }
    }, [mode, fenceData, points, mousePos, videoDims]);

    useEffect(() => { drawCanvas(); }, [drawCanvas]);

    useEffect(() => {
        const h = () => drawCanvas();
        window.addEventListener('resize', h);
        return () => window.removeEventListener('resize', h);
    }, [drawCanvas]);

    // ── Pointer handlers ─────────────────────────────────────────────────────
    const handleCanvasClick = (e) => {
        if (mode !== 'draw') return;
        const rect = canvasRef.current.getBoundingClientRect();
        
        let nx, ny;
        if (videoDims.w && videoDims.h) {
            const [newNx, newNy] = displayToNormalized(
                e.clientX - rect.left, e.clientY - rect.top, rect, videoDims.w, videoDims.h
            );
            nx = newNx;
            ny = newNy;
        } else {
            nx = parseFloat(((e.clientX - rect.left) / rect.width).toFixed(4));
            ny = parseFloat(((e.clientY - rect.top)  / rect.height).toFixed(4));
        }
        
        setPoints(prev => [...prev, [nx, ny]]);
        setError('');
    };

    const handleMouseMove = (e) => {
        if (mode !== 'draw') return;
        const rect = canvasRef.current.getBoundingClientRect();
        setMousePos([e.clientX - rect.left, e.clientY - rect.top]);
    };

    const handleMouseLeave = () => setMousePos(null);

    // ── Actions ──────────────────────────────────────────────────────────────
    const startDraw = () => {
        setStreamKey(Date.now()); // force stream reload
        setPoints(fenceData?.points ? [...fenceData.points] : []);
        setMode('draw');
        setError(''); setSuccess('');
    };

    const cancelDraw = () => {
        setPoints([]); setMousePos(null); setMode('view'); setError('');
    };

    const undoLast = () => setPoints(prev => prev.slice(0, -1));
    const clearAll = () => setPoints([]);

    const handleSave = async () => {
        if (points.length < 3) { setError('Need at least 3 points. Keep clicking!'); return; }
        setSaving(true); setError('');
        try {
            const res = await saveFence(cameraId, points);
            setFenceData(res.fence); setIsDefault(false);
            setMode('view'); setPoints([]);
            setSuccess('Fence saved! Detection zone updated instantly.');
            setTimeout(() => setSuccess(''), 4000);
        } catch (err) {
            setError(`Save failed: ${err.message}`);
        } finally { setSaving(false); }
    };

    const handleReset = async () => {
        if (!window.confirm('Reset to default fence? Your custom fence will be deleted.')) return;
        try {
            await deleteFence(cameraId);
            setFenceData(null); setIsDefault(true);
            setSuccess('Reset to default detection zone.');
            setTimeout(() => setSuccess(''), 3000);
        } catch (err) { setError(`Reset failed: ${err.message}`); }
    };

    // ── Derived state ────────────────────────────────────────────────────────
    const fenceStatus = isDefault
        ? { label: 'Default', cls: 'bg-base text-secondary' }
        : { label: 'Custom',  cls: 'bg-status-green/15 text-status-green border border-status-green/30' };

    const showStream = isOnline && streamUrl;
    const editorHeight = mode === 'draw' ? '360px' : '260px';   // taller in draw mode

    return (
        <div className="bg-panel border border-default rounded overflow-hidden transition-colors shadow-panel">

            {/* ── Header ── */}
            <div className="flex items-center justify-between px-3 py-2.5 border-b border-default transition-colors">
                <div className="flex items-center gap-2">
                    <Shield size={13} className="text-status-green" />
                    <span className="text-xs font-semibold text-primary uppercase tracking-wider transition-colors">Virtual Fence</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors ${fenceStatus.cls}`}>
                        {fenceStatus.label}
                    </span>
                </div>

                {mode === 'view' && (
                    <div className="flex gap-1.5">
                        <button onClick={startDraw}
                            className="flex items-center gap-1 text-[11px] bg-status-green hover:opacity-90 text-white px-2.5 py-1 rounded transition-colors font-medium">
                            <Edit size={10} /> {fenceData ? 'Edit' : 'Configure'}
                        </button>
                        {!isDefault && (
                            <button onClick={handleReset}
                                className="flex items-center gap-1 text-[11px] bg-base hover:bg-border-highlight text-secondary px-2.5 py-1 rounded transition-colors font-medium">
                                <RotateCcw size={10} /> Reset
                            </button>
                        )}
                    </div>
                )}

                {mode === 'draw' && (
                    <div className="flex gap-1.5">
                        <button onClick={undoLast} disabled={points.length === 0}
                            className="flex items-center gap-1 text-[11px] bg-base hover:bg-border-highlight disabled:opacity-30 text-secondary px-2 py-1 rounded font-medium transition-colors">
                            <Undo2 size={10} /> Undo
                        </button>
                        <button onClick={clearAll} disabled={points.length === 0}
                            className="flex items-center gap-1 text-[11px] bg-base hover:bg-border-highlight disabled:opacity-30 text-secondary px-2 py-1 rounded font-medium transition-colors">
                            <Trash2 size={10} /> Clear
                        </button>
                        <button onClick={cancelDraw}
                            className="flex items-center gap-1 text-[11px] bg-base hover:bg-border-highlight text-secondary px-2 py-1 rounded font-medium transition-colors">
                            <X size={10} /> Cancel
                        </button>
                        <button onClick={handleSave} disabled={saving || points.length < 3}
                            className="flex items-center gap-1 text-[11px] bg-status-green hover:opacity-90 disabled:opacity-40 text-white px-2.5 py-1 rounded font-semibold transition-colors">
                            <Save size={10} /> {saving ? 'Saving…' : `Save (${points.length} pts)`}
                        </button>
                    </div>
                )}
            </div>

            {/* ── Video + Canvas area ── */}
            <div ref={containerRef} className="relative overflow-hidden bg-black"
                style={{ height: editorHeight }}>

                {/* ── Live stream background (always shown when online) ── */}
                {showStream ? (
                    <img
                        ref={imgRef}
                        src={streamUrl}
                        alt="Camera stream"
                        className="absolute inset-0 w-full h-full object-contain"
                        style={{ zIndex: 1 }}
                        onLoad={(e) => setVideoDims({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
                        onError={(e) => {
                            setTimeout(() => { e.target.src = streamUrl + '&r=' + Date.now(); }, 2000);
                        }}
                    />
                ) : (
                    /* ── Offline placeholder ── */
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-base transition-colors"
                        style={{ zIndex: 1 }}>
                        <VideoOff size={30} className="text-muted mb-2 opacity-40 transition-colors" />
                        <p className="text-secondary text-xs transition-colors">
                            {isOnline ? 'Stream connecting…' : 'Start the stream to see the fence overlay'}
                        </p>
                        {mode === 'draw' && !isOnline && (
                            <p className="text-muted text-[10px] mt-1 transition-colors">
                                You can still draw the fence without a live stream
                            </p>
                        )}
                    </div>
                )}

                {/* ── Canvas overlay for drawing / view ── */}
                <canvas
                    ref={canvasRef}
                    onClick={handleCanvasClick}
                    onMouseMove={handleMouseMove}
                    onMouseLeave={handleMouseLeave}
                    className="absolute inset-0 w-full h-full"
                    style={{
                        zIndex: 10,
                        cursor: mode === 'draw' ? 'crosshair' : 'default',
                    }}
                />

                {/* ── No fence message (view mode, no fence, online) ── */}
                {mode === 'view' && !fenceData && isOnline && (
                    <div className="absolute bottom-3 left-0 right-0 flex justify-center"
                        style={{ zIndex: 20 }}>
                        <div className="bg-black/60 backdrop-blur-sm text-secondary text-[10px] px-3 py-1.5 rounded-full flex items-center gap-1.5">
                            <MapPin size={10} /> Default detection zone — click Edit to customize
                        </div>
                    </div>
                )}

                {/* ── Draw mode instruction bar ── */}
                {mode === 'draw' && (
                    <div className="absolute bottom-0 left-0 right-0 bg-black/75 text-center py-2"
                        style={{ zIndex: 20 }}>
                        <p className="text-[10px] text-green-300">
                            <span className="font-bold text-yellow-400">●</span> = first point &nbsp;|&nbsp;
                            {points.length < 3
                                ? `Click to add points (${points.length} / 3 min)`
                                : `${points.length} pts placed — click "Save" when done`}
                        </p>
                    </div>
                )}
            </div>

            {/* ── Status messages ── */}
            {(error || success) && (
                <div className={`px-3 py-2 text-xs transition-colors ${error ? 'bg-status-red/10 text-status-red' : 'bg-status-green/10 text-status-green'}`}>
                    {error || success}
                </div>
            )}
        </div>
    );
}
