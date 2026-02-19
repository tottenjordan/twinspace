export class AudioPlayer {
    constructor() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.queue = [];
        this.playing = false;
    }

    async play(base64Data) {
        try {
            // Decode base64 to array buffer
            const binaryString = atob(base64Data);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            // Decode audio data
            const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);

            // Create source
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);

            // Play
            source.start(0);
        } catch (error) {
            console.error('Audio playback error:', error);
        }
    }
}
