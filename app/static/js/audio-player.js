export class AudioPlayer {
    constructor() {
        // Create AudioContext with 24kHz sample rate to match Live API output
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 24000
        });
        this.queue = [];
        this.playing = false;
    }

    async play(base64Data) {
        // Add to queue
        this.queue.push(base64Data);

        // Start playing if not already
        if (!this.playing) {
            this.playing = true;
            await this.playNext();
        }
    }

    async playNext() {
        if (this.queue.length === 0) {
            this.playing = false;
            return;
        }

        const base64Data = this.queue.shift();

        try {
            // Resume AudioContext if suspended (browser autoplay policy)
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            // Convert URL-safe base64 to standard base64
            let standardBase64 = base64Data.replace(/-/g, '+').replace(/_/g, '/');

            // Add padding if needed
            while (standardBase64.length % 4 !== 0) {
                standardBase64 += '=';
            }

            // Decode base64 to array buffer
            const binaryString = atob(standardBase64);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            // Verify we have valid data
            if (bytes.length === 0 || bytes.length % 2 !== 0) {
                console.error('Invalid audio data length:', bytes.length);
                this.playNext();
                return;
            }

            // Live API sends raw PCM 16-bit little-endian mono at 24kHz
            const pcmData = new Int16Array(bytes.buffer);
            const sampleRate = 24000;
            const numSamples = pcmData.length;

            if (numSamples === 0) {
                console.error('No audio samples decoded');
                this.playNext();
                return;
            }

            // Create AudioBuffer
            const audioBuffer = this.audioContext.createBuffer(1, numSamples, sampleRate);

            // Convert Int16 to Float32 (-1.0 to 1.0)
            const channelData = audioBuffer.getChannelData(0);
            for (let i = 0; i < numSamples; i++) {
                channelData[i] = pcmData[i] / 32768.0;
            }

            // Create source and play immediately
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);

            // Play next chunk when this one ends
            source.onended = () => {
                this.playNext();
            };

            source.start(0);

        } catch (error) {
            console.error('Audio playback error:', error);
            // Continue with next chunk even if this one failed
            this.playNext();
        }
    }
}
