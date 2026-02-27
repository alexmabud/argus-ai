/**
 * Componente de captura de câmera.
 *
 * Usa getUserMedia para acessar câmera traseira do dispositivo.
 * Captura frame como JPEG (80% qualidade). Fallback para file picker.
 */
class CameraCapture {
  constructor() {
    this.stream = null;
    this.videoEl = null;
  }

  async open(videoElement) {
    this.videoEl = videoElement;

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment",
          width: { ideal: 1280 },
        },
      });
      this.videoEl.srcObject = this.stream;
      await this.videoEl.play();
      return true;
    } catch {
      return false;
    }
  }

  capture() {
    if (!this.videoEl || !this.stream) return null;

    const canvas = document.createElement("canvas");
    canvas.width = this.videoEl.videoWidth;
    canvas.height = this.videoEl.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(this.videoEl, 0, 0);

    return new Promise((resolve) => {
      canvas.toBlob(
        (blob) => resolve(blob),
        "image/jpeg",
        0.8
      );
    });
  }

  close() {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    if (this.videoEl) {
      this.videoEl.srcObject = null;
      this.videoEl = null;
    }
  }
}
