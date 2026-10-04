export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export const fetchCameras = async () => {
    const res = await fetch(`${API_BASE_URL}/cameras`);
    if (!res.ok) throw new Error('Failed to fetch cameras');
    return res.json();
};

export const addCamera = async (cameraData) => {
    const res = await fetch(`${API_BASE_URL}/cameras`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cameraData)
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to add camera');
    }
    return res.json();
};

export const deleteCamera = async (id) => {
    const res = await fetch(`${API_BASE_URL}/cameras/${id}`, { method: 'DELETE' });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to delete camera');
    }
    return res.json();
};

export const startCamera = async (id) => {
    const res = await fetch(`${API_BASE_URL}/cameras/${id}/start`, { method: 'POST' });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to start camera');
    }
    return res.json();
};

export const stopCamera = async (id) => {
    const res = await fetch(`${API_BASE_URL}/cameras/${id}/stop`, { method: 'POST' });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to stop camera');
    }
    return res.json();
};

export const fetchSystemHealth = async () => {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) throw new Error('Failed to fetch health');
    return res.json();
};

export const fetchEvents = async (skip = 0, limit = 50) => {
    const res = await fetch(`${API_BASE_URL}/events?skip=${skip}&limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch events');
    return res.json();
};

export const fetchAlerts = async (skip = 0, limit = 50, status = '') => {
    let url = `${API_BASE_URL}/alerts?skip=${skip}&limit=${limit}`;
    if (status) url += `&status=${status}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch alerts');
    return res.json();
};

export const acknowledgeAlert = async (id, user_id = 'operator_1') => {
    const res = await fetch(`${API_BASE_URL}/alerts/${id}/acknowledge?user_id=${user_id}`, { method: 'PATCH' });
    if (!res.ok) throw new Error('Failed to acknowledge alert');
    return res.json();
};

export const resolveAlert = async (id) => {
    const res = await fetch(`${API_BASE_URL}/alerts/${id}/resolve`, { method: 'PATCH' });
    if (!res.ok) throw new Error('Failed to resolve alert');
    return res.json();
};

export const dismissAlert = async (id) => {
    const res = await fetch(`${API_BASE_URL}/alerts/${id}/dismiss`, { method: 'PATCH' });
    if (!res.ok) throw new Error('Failed to dismiss alert');
    return res.json();
};

export const getStreamUrl = (cameraId) => {
    return `${API_BASE_URL}/cameras/${cameraId}/stream`;
};

export const fetchANPR = async (limit = 10, cameraId = null) => {
    let url = `${API_BASE_URL}/anpr?limit=${limit}`;
    if (cameraId) url += `&camera_id=${cameraId}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch ANPR');
    return res.json();
};

// ─── Virtual Fence API ────────────────────────────────────────────────────────

export const getFence = async (cameraId) => {
    const res = await fetch(`${API_BASE_URL}/cameras/${cameraId}/fence`);
    if (!res.ok) throw new Error('Failed to fetch fence');
    return res.json(); // { camera_id, fence: NormalizedFence | null, is_default }
};

export const saveFence = async (cameraId, points, name = 'Custom Fence') => {
    const res = await fetch(`${API_BASE_URL}/cameras/${cameraId}/fence`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, points }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Failed to save fence');
    }
    return res.json();
};

export const deleteFence = async (cameraId) => {
    const res = await fetch(`${API_BASE_URL}/cameras/${cameraId}/fence`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete fence');
    return res.json();
};

// ─── Settings API ─────────────────────────────────────────────────────────────

export const fetchNightMovementMode = async () => {
    const res = await fetch(`${API_BASE_URL}/settings/night-movement`);
    if (!res.ok) throw new Error('Failed to fetch night movement mode');
    return res.json();
};

export const updateNightMovementMode = async (mode) => {
    const res = await fetch(`${API_BASE_URL}/settings/night-movement`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
    });
    if (!res.ok) throw new Error('Failed to update night movement mode');
    return res.json();
};

// ─── Camera Map API (MAP-01) ──────────────────────────────────────────────────

export const fetchCameraMap = async ({ status, border_sector, border_state, border_region } = {}) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (border_sector) params.set('border_sector', border_sector);
    if (border_state) params.set('border_state', border_state);
    if (border_region) params.set('border_region', border_region);
    const query = params.toString();
    const url = `${API_BASE_URL}/cameras/map${query ? `?${query}` : ''}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch camera map data');
    return res.json();
};

export const fetchIncidents = async () => {
    const res = await fetch(`${API_BASE_URL}/incidents/`);
    if (!res.ok) throw new Error('Failed to fetch incidents');
    return res.json();
};

export const updateIncidentStatus = async (id, status) => {
    const res = await fetch(`${API_BASE_URL}/incidents/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
    });
    if (!res.ok) throw new Error('Failed to update incident status');
    return res.json();
};
