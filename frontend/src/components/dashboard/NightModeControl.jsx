import React, { useState, useEffect } from 'react';
import { fetchNightMovementMode, updateNightMovementMode } from '../../services/api';
import { Moon, Loader2, AlertCircle } from 'lucide-react';

const NightModeControl = () => {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadStatus = async () => {
        try {
            const data = await fetchNightMovementMode();
            setStatus(data);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadStatus();
        const interval = setInterval(loadStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleModeChange = async (newMode) => {
        if (status?.mode === newMode) return;
        setLoading(true);
        try {
            const data = await updateNightMovementMode(newMode);
            setStatus(data);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading && !status) {
        return (
            <div className="bg-panel border border-default rounded p-4 flex items-center justify-center min-h-[120px] transition-colors shadow-panel">
                <Loader2 className="animate-spin text-muted" size={20} />
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-panel border border-default rounded p-4 flex items-center gap-2 min-h-[120px] transition-colors shadow-panel">
                <AlertCircle className="text-status-red shrink-0" size={16} />
                <div className="text-status-red text-xs">{error}</div>
            </div>
        );
    }

    const { mode, active } = status;

    let reasonText = "";
    if (mode === "AUTO") {
        reasonText = active ? "Automatic Night Mode" : "Daytime";
    } else if (mode === "ON") {
        reasonText = "Manual Override";
    } else if (mode === "OFF") {
        reasonText = "Manually Disabled";
    }

    return (
        <div className="bg-panel border border-default rounded p-4 flex flex-col justify-between h-full transition-colors shadow-panel">
            {/* Header with mode toggle */}
            <div>
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-1.5">
                        <Moon size={14} className="text-status-blue" />
                        <span className="text-[10px] font-semibold uppercase tracking-widest text-secondary transition-colors">Night Movement</span>
                    </div>
                </div>

                {/* Mode buttons */}
                <div className="flex items-center gap-1 bg-base p-0.5 rounded transition-colors border border-default">
                    {['AUTO', 'ON', 'OFF'].map(m => (
                        <button
                            key={m}
                            onClick={() => handleModeChange(m)}
                            disabled={loading}
                            className={`flex-1 px-2 py-1.5 text-[11px] font-bold rounded transition-colors tracking-wide ${
                                mode === m
                                    ? m === 'ON'
                                        ? 'bg-status-amber text-white'
                                        : m === 'OFF'
                                            ? 'bg-border-highlight text-white'
                                            : 'bg-status-blue text-white'
                                    : 'text-secondary hover:text-primary hover:bg-border-default'
                            }`}
                        >
                            {m}
                        </button>
                    ))}
                </div>
            </div>

            {/* Status */}
            <div className="mt-3 pt-3 border-t border-default flex items-center justify-between transition-colors">
                <div className="flex items-center gap-1.5">
                    <span className={`h-2 w-2 rounded-full transition-colors ${active ? 'bg-status-green' : 'bg-border-highlight'}`}></span>
                    <span className={`text-[11px] font-bold tracking-wide transition-colors ${active ? 'text-status-green' : 'text-muted'}`}>
                        {active ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                </div>
                <span className={`text-[11px] font-medium transition-colors ${mode === 'ON' ? 'text-status-amber' : 'text-muted'}`}>
                    {reasonText}
                </span>
            </div>
        </div>
    );
};

export default NightModeControl;
