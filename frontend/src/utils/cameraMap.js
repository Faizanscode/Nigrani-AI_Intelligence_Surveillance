import { fetchCameras } from '../services/api';

let cameraMapCache = {};
let fetchPromise = null;
let lastFetch = 0;
const CACHE_TTL_MS = 30000; // 30 seconds

export async function getCameraNameMap(forceRefresh = false) {
    const now = Date.now();
    if (!forceRefresh && (now - lastFetch < CACHE_TTL_MS) && Object.keys(cameraMapCache).length > 0) {
        return cameraMapCache;
    }

    if (fetchPromise) {
        return fetchPromise;
    }

    fetchPromise = (async () => {
        try {
            const cams = await fetchCameras();
            const map = {};
            if (Array.isArray(cams)) {
                cams.forEach(c => {
                    if (c && c.id) {
                        map[c.id] = c.name || c.id;
                    }
                });
            }
            cameraMapCache = map;
            lastFetch = Date.now();
            return cameraMapCache;
        } catch (e) {
            console.error("Failed to fetch camera map:", e);
            return cameraMapCache;
        } finally {
            fetchPromise = null;
        }
    })();

    return fetchPromise;
}

export function invalidateCameraCache() {
    lastFetch = 0;
    fetchPromise = null;
}
