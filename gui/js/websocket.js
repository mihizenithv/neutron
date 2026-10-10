/**
 * NEUTRON WebSocket Client
 * Handles real-time communication with backend
 */

const WebSocketClient = {
    config: {
        url: 'ws://localhost:8000/ws',
        reconnectInterval: 1000,
        maxReconnectAttempts: 30,
    },

    ws: null,
    reconnectAttempts: 0,
    connected: false,
    handlers: {},

    init() {
        this.connect();
    },

    connect() {
        try {
            this.ws = new WebSocket(this.config.url);

            this.ws.onopen = () => this.onOpen();
            this.ws.onclose = () => this.onClose();
            this.ws.onerror = (e) => this.onError(e);
            this.ws.onmessage = (e) => this.onMessage(e);
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.scheduleReconnect();
        }
    },

    onOpen() {
        console.log('WebSocket connected');
        this.connected = true;
        this.reconnectAttempts = 0;

        if (Boot) Boot.onConnectionSuccess();
        this.trigger('connected');
    },

    onClose() {
        console.log('WebSocket disconnected');
        this.connected = false;
        this.trigger('disconnected');
        this.scheduleReconnect();
    },

    onError(error) {
        console.error('WebSocket error:', error);
        if (Boot) Boot.onConnectionFailed();
    },

    onMessage(event) {
        try {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        } catch (error) {
            console.error('Failed to parse message:', error);
        }
    },

    handleMessage(message) {
        const { type, data } = message;

        switch (type) {
            case 'state_update':
                this.trigger('stateUpdate', data);
                break;
            case 'emotion_update':
                this.trigger('emotionUpdate', data);
                break;
            case 'speech_start':
                this.trigger('speechStart', data);
                break;
            case 'speech_end':
                this.trigger('speechEnd', data);
                break;
            case 'text_partial':
                this.trigger('textPartial', data);
                break;
            case 'text_final':
                this.trigger('textFinal', data);
                break;
            case 'audio_level':
                this.trigger('audioLevel', data);
                break;
            case 'gaze_target':
                this.trigger('gazeTarget', data);
                break;
            case 'pong':
                // Heartbeat response
                break;
            default:
                console.log('Unknown message type:', type);
        }
    },

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
            console.log('Max reconnect attempts reached');
            if (Boot) Boot.showErrorScreen();
            return;
        }

        this.reconnectAttempts++;
        console.log(`Reconnecting in ${this.config.reconnectInterval}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => this.connect(), this.config.reconnectInterval);
    },

    send(type, data = {}) {
        if (!this.connected || !this.ws) return;

        this.ws.send(JSON.stringify({ type, data }));
    },

    on(event, handler) {
        if (!this.handlers[event]) {
            this.handlers[event] = [];
        }
        this.handlers[event].push(handler);
    },

    off(event, handler) {
        if (!this.handlers[event]) return;
        this.handlers[event] = this.handlers[event].filter(h => h !== handler);
    },

    trigger(event, data) {
        if (!this.handlers[event]) return;
        this.handlers[event].forEach(handler => handler(data));
    },

    startHeartbeat() {
        setInterval(() => {
            if (this.connected) {
                this.send('ping');
            }
        }, 30000);
    },

    destroy() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.connected = false;
        this.handlers = {};
    },
};

