export class AudioRecorder {
    constructor() {
        this.audioContext = null;
        this.mediaStream = null;
        this.processor = null;
        this.onAudioChunk = null;
    }

    async start() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });

            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            const source = this.audioContext.createMediaStreamSource(this.mediaStream);

            // Create processor for PCM data
            await this.audioContext.audioWorklet.addModule('/static/js/pcm-recorder-processor.js');
            this.processor = new AudioWorkletNode(this.audioContext, 'pcm-recorder-processor');

            this.processor.port.onmessage = (event) => {
                if (this.onAudioChunk && event.data.audioData) {
                    // Convert Float32Array to Int16Array PCM
                    const pcmData = this.floatToPCM(event.data.audioData);
                    this.onAudioChunk(pcmData);
                }
            };

            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

        } catch (error) {
            console.error('Audio recording error:', error);
        }
    }

    floatToPCM(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return int16Array.buffer;
    }

    stop() {
        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
    }
}
