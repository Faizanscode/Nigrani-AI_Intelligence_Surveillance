import { API_BASE_URL } from './api';

class WebSocketService {
    constructor() {
        this.ws = null;
        this.listeners = new Map(); // topic -> array of callbacks
        this.reconnectTimer = null;
        this.isConnected = false;
        
        // Derive WS URL from API_BASE_URL
        this.url = API_BASE_URL.replace(/^http/, 'ws') + '/ws/events';
    }

    connect() {
        if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
            return;
        }

        console.log(`Connecting to WebSocket: ${this.url}`);
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
            this.emit('connection', true);
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.emit(data.type, data.payload);
            } catch (err) {
                console.error("Error parsing WS message", err);
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected. Reconnecting in 3s...');
            this.isConnected = false;
            this.emit('connection', false);
            this.ws = null;
            this.scheduleReconnect();
        };

        this.ws.onerror = (err) => {
            console.error('WebSocket error:', err);
            if (this.ws) {
                this.ws.close();
            }
        };
    }

    scheduleReconnect() {
        if (!this.reconnectTimer) {
            this.reconnectTimer = setTimeout(() => {
                this.connect();
            }, 3000);
        }
    }

    disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        if (this.ws) {
            this.ws.close();
        }
    }

    subscribe(topic, callback) {
        if (!this.listeners.has(topic)) {
            this.listeners.set(topic, []);
        }
        this.listeners.get(topic).push(callback);

        // Return an unsubscribe function
        return () => {
            const topicListeners = this.listeners.get(topic);
            if (topicListeners) {
                this.listeners.set(topic, topicListeners.filter(cb => cb !== callback));
            }
        };
    }

    emit(topic, data) {
        const topicListeners = this.listeners.get(topic);
        if (topicListeners) {
            topicListeners.forEach(callback => callback(data));
        }
    }
}

export const wsService = new WebSocketService();
