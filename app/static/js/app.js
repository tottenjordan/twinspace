import { VideoHandler } from './video-handler.js';
import { AudioPlayer } from './audio-player.js';
import { AudioRecorder } from './audio-recorder.js';

class ApplianceInventoryApp {
    constructor() {
        this.ws = null;
        this.connected = false;
        this.userId = `user_${Date.now()}`;
        this.sessionId = `session_${Date.now()}`;

        this.videoHandler = new VideoHandler();
        this.audioPlayer = new AudioPlayer();
        this.audioRecorder = new AudioRecorder();

        this.setupEventListeners();
    }

    setupEventListeners() {
        document.getElementById('startBtn').addEventListener('click', () => this.startCamera());
        document.getElementById('connectBtn').addEventListener('click', () => this.connect());
        document.getElementById('disconnectBtn').addEventListener('click', () => this.disconnect());
        document.getElementById('sendBtn').addEventListener('click', () => this.sendText());
        document.getElementById('clearEventsBtn').addEventListener('click', () => this.clearEvents());

        document.getElementById('textInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendText();
        });

        // Video frame callback
        this.videoHandler.onFrame = (imageData) => {
            if (this.connected) {
                this.sendImage(imageData);
            }
        };

        // Audio chunk callback
        this.audioRecorder.onAudioChunk = (chunk) => {
            if (this.connected && this.ws) {
                this.ws.send(chunk);
            }
        };
    }

    async startCamera() {
        const success = await this.videoHandler.start();
        if (success) {
            document.getElementById('startBtn').disabled = true;
            document.getElementById('connectBtn').disabled = false;
            this.updateStatus('Camera started - Ready to connect');
        } else {
            this.updateStatus('Failed to start camera', 'error');
        }
    }

    async connect() {
        const wsUrl = `ws://${window.location.host}/ws/${this.userId}/${this.sessionId}`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.connected = true;
                document.getElementById('connectBtn').disabled = true;
                document.getElementById('disconnectBtn').disabled = false;
                document.getElementById('textInput').disabled = false;
                document.getElementById('sendBtn').disabled = false;

                this.updateStatus('Connected to AI assistant');
                this.addMessage('agent', 'Hello! I\'m ready to help you catalog your appliances. Just walk around and show me your appliances.');

                // Start audio recording
                this.audioRecorder.start();

                // Start sending video frames
                this.videoHandler.startCapture();
            };

            this.ws.onmessage = (event) => {
                this.handleServerMessage(event.data);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateStatus('Connection error', 'error');
            };

            this.ws.onclose = () => {
                this.connected = false;
                document.getElementById('connectBtn').disabled = false;
                document.getElementById('disconnectBtn').disabled = true;
                document.getElementById('textInput').disabled = true;
                document.getElementById('sendBtn').disabled = true;

                this.updateStatus('Disconnected');
                this.audioRecorder.stop();
                this.videoHandler.stopCapture();
            };

        } catch (error) {
            console.error('Connection error:', error);
            this.updateStatus('Failed to connect', 'error');
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    handleServerMessage(data) {
        const event = JSON.parse(data);
        this.logEvent(event);

        // Handle different event types
        if (event.server_content?.model_turn?.parts) {
            const parts = event.server_content.model_turn.parts;
            for (const part of parts) {
                if (part.text) {
                    this.addMessage('agent', part.text);
                }
                if (part.inline_data?.data) {
                    // Audio response
                    this.audioPlayer.play(part.inline_data.data);
                }
            }
        }

        // Handle tool calls
        if (event.tool_call) {
            this.handleToolCall(event.tool_call);
        }

        // Handle tool responses
        if (event.tool_response) {
            this.handleToolResponse(event.tool_response);
        }
    }

    handleToolCall(toolCall) {
        const toolName = toolCall.function_calls?.[0]?.name;
        this.logEvent({ type: 'tool_call', name: toolName });
    }

    handleToolResponse(toolResponse) {
        const responses = toolResponse.function_responses || [];
        for (const response of responses) {
            if (response.response) {
                const data = JSON.parse(response.response);
                if (data.status === 'completed' && data.total_appliances) {
                    this.updateInventory();
                }
            }
        }
    }

    sendText() {
        const input = document.getElementById('textInput');
        const text = input.value.trim();

        if (text && this.connected && this.ws) {
            this.ws.send(JSON.stringify({
                type: 'text',
                text: text
            }));

            this.addMessage('user', text);
            input.value = '';
        }
    }

    sendImage(imageData) {
        if (this.connected && this.ws) {
            // Send base64 encoded image
            const base64Data = imageData.split(',')[1];
            this.ws.send(JSON.stringify({
                type: 'image',
                data: base64Data,
                mimeType: 'image/jpeg'
            }));
        }
    }

    addMessage(role, text) {
        const log = document.getElementById('conversationLog');
        const message = document.createElement('div');
        message.className = `message ${role}`;
        message.textContent = text;
        log.appendChild(message);
        log.scrollTop = log.scrollHeight;
    }

    updateStatus(message, type = 'info') {
        const status = document.getElementById('status');
        status.textContent = message;
        status.style.background = type === 'error' ? '#fed7d7' : '#edf2f7';
    }

    logEvent(event) {
        const console = document.getElementById('eventsConsole');
        const entry = document.createElement('div');
        entry.className = 'event-entry';

        const timestamp = new Date().toLocaleTimeString();
        const eventType = event.type || event.server_content?.model_turn ? 'model_turn' : 'unknown';

        entry.innerHTML = `
            <div class="event-timestamp">${timestamp}</div>
            <div>${eventType}: ${JSON.stringify(event, null, 2)}</div>
        `;

        console.appendChild(entry);
        console.scrollTop = console.scrollHeight;
    }

    clearEvents() {
        document.getElementById('eventsConsole').innerHTML = '';
    }

    async updateInventory() {
        // Fetch current inventory from backend
        try {
            const response = await fetch('/api/inventory');
            const data = await response.json();

            const list = document.getElementById('inventoryList');
            list.innerHTML = '';

            if (data.appliances && data.appliances.length > 0) {
                data.appliances.forEach(appliance => {
                    const card = document.createElement('div');
                    card.className = 'appliance-card';
                    card.innerHTML = `
                        <h3>${appliance.type}</h3>
                        <p><strong>Make:</strong> ${appliance.make}</p>
                        <p><strong>Model:</strong> ${appliance.model}</p>
                        <p class="event-timestamp">Added: ${new Date(appliance.completed_at).toLocaleString()}</p>
                    `;
                    list.appendChild(card);
                });
            } else {
                list.innerHTML = '<p class="empty-state">No appliances added yet</p>';
            }
        } catch (error) {
            console.error('Failed to update inventory:', error);
        }
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ApplianceInventoryApp();
});
