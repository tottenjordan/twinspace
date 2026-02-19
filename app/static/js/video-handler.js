export class VideoHandler {
    constructor() {
        this.video = document.getElementById('videoElement');
        this.canvas = document.getElementById('videoCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.stream = null;
        this.captureInterval = null;
        this.onFrame = null;
    }

    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'environment'
                },
                audio: false
            });

            this.video.srcObject = this.stream;
            return true;
        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Could not access camera. Please grant permission.');
            return false;
        }
    }

    startCapture() {
        // Capture at 1 FPS (Gemini Live API processes video at 1 FPS)
        this.captureInterval = setInterval(() => {
            this.captureFrame();
        }, 1000);
    }

    stopCapture() {
        if (this.captureInterval) {
            clearInterval(this.captureInterval);
            this.captureInterval = null;
        }
    }

    captureFrame() {
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            // Set canvas size to video size
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;

            // Draw current frame
            this.ctx.drawImage(this.video, 0, 0);

            // Get image data as base64
            const imageData = this.canvas.toDataURL('image/jpeg', 0.8);

            // Call callback if set
            if (this.onFrame) {
                this.onFrame(imageData);
            }
        }
    }

    stop() {
        this.stopCapture();
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }
}
