export class AudioPlayer {
    constructor() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.queue = [];
        this.playing = false;
    }

    async play(base64Data) {
        try {
            console.log(`Attempting to play audio (${base64Data.length} chars of base64)`);

            // Resume AudioContext if suspended (browser autoplay policy)
            if (this.audioContext.state === 'suspended') {
                console.log('Resuming suspended AudioContext...');
                await this.audioContext.resume();
            }

            // Convert URL-safe base64 to standard base64
            // Live API uses URL-safe base64 (- and _ instead of + and /)
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

            // Live API sends raw PCM 16-bit mono at 24kHz
            // Convert Int16 PCM to Float32 for Web Audio API
            const pcmData = new Int16Array(bytes.buffer);
            const sampleRate = 24000; // Live API native audio sample rate
            const numSamples = pcmData.length;

            console.log(`PCM data: ${numSamples} samples at ${sampleRate}Hz = ${numSamples/sampleRate}s duration`);

            // Create AudioBuffer
            const audioBuffer = this.audioContext.createBuffer(
                1,              // mono
                numSamples,
                sampleRate
            );

            // Convert Int16 to Float32 (-1.0 to 1.0)
            const channelData = audioBuffer.getChannelData(0);
            for (let i = 0; i < numSamples; i++) {
                channelData[i] = pcmData[i] / 32768.0; // Convert to -1.0 to 1.0 range
            }

            // Create source and play
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);

            source.onended = () => {
                console.log('Audio playback finished');
            };

            source.start(0);
            console.log(`✅ Audio playback started (${(numSamples/sampleRate).toFixed(1)}s)`);
        } catch (error) {
            console.error('❌ Audio playback error:', error);
            alert(`Audio error: ${error.message}. Check console for details.`);
        }
    }
}
