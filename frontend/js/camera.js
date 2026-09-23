// Camera & MediaPipe Face Mesh Integration Module
class CameraManager {
  constructor() {
    this.videoElement = document.getElementById("webcam");
    this.canvasElement = document.getElementById("meshCanvas");
    this.canvasCtx = this.canvasElement ? this.canvasElement.getContext("2d") : null;
    this.statusDot = document.getElementById("statusDot");
    this.statusText = document.getElementById("statusText");
    
    this.stream = null;
    this.faceMesh = null;
    this.cameraInstance = null;
    this.currentLandmarks = null;
    this.isFaceVisible = false;
    this.visibilityListeners = [];
    this.isScanning = false;
  }

  addVisibilityListener(listener) {
    if (typeof listener === "function") {
      this.visibilityListeners.push(listener);
    }
  }

  notifyVisibility(isVisible, landmarks) {
    for (const fn of this.visibilityListeners) {
      try {
        fn(isVisible, landmarks);
      } catch (err) {
        console.error("Visibility listener error:", err);
      }
    }
  }

  hasFaceVisible() {
    return Boolean(this.isFaceVisible && this.currentLandmarks && this.currentLandmarks.length >= 25);
  }

  async init() {
    try {
      await this.startCamera();
      this.initMediaPipe();
    } catch (err) {
      console.warn("Camera auto-start failed, falling back to upload / manual mode:", err);
      this.updateStatus(false, "Camera offline - Upload supported");
    }
  }

  async startCamera() {
    if (this.stream) {
      this.stopCamera();
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "user"
        },
        audio: false
      });

      this.videoElement.srcObject = this.stream;
      await this.videoElement.play();
      this.updateStatus(false, "Waiting for face...");
    } catch (e) {
      console.warn("User camera access denied or not found:", e);
      this.updateStatus(false, "Webcam unavailable");
      throw e;
    }
  }

  attachTo(videoEl, canvasEl, dotEl = null, textEl = null) {
    this._uploadedImageMode = false;
    this._uploadedImageElement = null;
    if (this.stream && videoEl) {
      videoEl.srcObject = this.stream;
      videoEl.play().catch(() => {});
    }
    this.videoElement = videoEl || this.videoElement;
    this.canvasElement = canvasEl || this.canvasElement;
    this.canvasCtx = this.canvasElement ? this.canvasElement.getContext("2d") : null;
    if (dotEl) this.statusDot = dotEl;
    if (textEl) this.statusText = textEl;

    // Immediately update status on new target element
    if (this.isFaceVisible) {
      this.updateStatus(true, "Face Detected — 468 Landmarks");
    } else {
      this.updateStatus(false, "Position face in frame");
    }
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
  }

  initMediaPipe() {
    if (typeof FaceMesh === "undefined") {
      console.log("MediaPipe FaceMesh CDN not loaded yet, using simulated mesh renderer.");
      this.startSimulatedMesh();
      return;
    }

    try {
      this.faceMesh = new FaceMesh({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
      });

      this.faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });

      this.faceMesh.onResults((results) => this.onFaceMeshResults(results));

      // Use a unified, highly-stable requestAnimationFrame loop that smoothly adapts across viewports
      this.startRequestAnimationFrameLoop();
    } catch (err) {
      console.warn("MediaPipe init error:", err);
      this.startSimulatedMesh();
    }
  }

  startRequestAnimationFrameLoop() {
    this._rafActive = true;
    const loop = async () => {
      if (!this._rafActive) return;
      if (
        !this._uploadedImageMode &&
        !this._isProcessingImage &&
        this.videoElement &&
        this.videoElement.readyState >= 2 &&
        !this.videoElement.paused &&
        this.videoElement.videoWidth > 0 &&
        this.faceMesh
      ) {
        try {
          await this.faceMesh.send({ image: this.videoElement });
        } catch (e) {
          // Suppress transient frame drops
        }
      }
      this._rafId = requestAnimationFrame(loop);
    };
    this._rafId = requestAnimationFrame(loop);
  }

  async analyzeImage(imageSource) {
    if (!this.faceMesh) {
      if (typeof FaceMesh !== "undefined") {
        this.initMediaPipe();
      }
    }
    this._isProcessingImage = true;
    this._uploadedImageMode = true;

    return new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = async () => {
        this._uploadedImageElement = img;
        try {
          if (this.canvasElement && this.canvasCtx) {
            this.canvasElement.width = img.naturalWidth || img.width;
            this.canvasElement.height = img.naturalHeight || img.height;
          }
          this.currentLandmarks = null;
          this.isFaceVisible = false;
          if (this.faceMesh) {
            await this.faceMesh.send({ image: img });
          }
          this._isProcessingImage = false;
          resolve(this.currentLandmarks);
        } catch (err) {
          console.warn("analyzeImage error:", err);
          this._isProcessingImage = false;
          resolve(null);
        }
      };
      img.onerror = () => {
        this._isProcessingImage = false;
        resolve(null);
      };
      if (typeof imageSource === "string") {
        img.src = imageSource;
      } else if (imageSource && imageSource.src) {
        img.src = imageSource.src;
      }
    });
  }

  clearUploadedImage() {
    this._uploadedImageMode = false;
    this._uploadedImageElement = null;
    if (this.canvasElement && this.videoElement) {
      this.canvasElement.width = this.videoElement.videoWidth || 640;
      this.canvasElement.height = this.videoElement.videoHeight || 480;
      if (this.canvasCtx) {
        this.canvasCtx.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height);
      }
    }
  }

  onFaceMeshResults(results) {
    if (!this.canvasCtx || !this.canvasElement) return;

    const activeWidth = this._uploadedImageMode && this._uploadedImageElement
      ? (this._uploadedImageElement.naturalWidth || this._uploadedImageElement.width || 640)
      : (this.videoElement ? (this.videoElement.videoWidth || 640) : 640);
    const activeHeight = this._uploadedImageMode && this._uploadedImageElement
      ? (this._uploadedImageElement.naturalHeight || this._uploadedImageElement.height || 480)
      : (this.videoElement ? (this.videoElement.videoHeight || 480) : 480);

    this.canvasElement.width = activeWidth;
    this.canvasElement.height = activeHeight;

    this.canvasCtx.save();
    this.canvasCtx.clearRect(0, 0, activeWidth, activeHeight);

    if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
      const landmarks = results.multiFaceLandmarks[0];
      this.currentLandmarks = landmarks;
      this.isFaceVisible = true;
      this.updateStatus(true, "Face Detected — 468 Landmarks");

      // Draw custom cyberpunk neon facial mesh overlay
      this.drawFacialMesh(landmarks, this.canvasCtx, activeWidth, activeHeight);

      // Trigger telemetry updates
      if (window.App && typeof window.App.updateLiveTelemetry === "function") {
        window.App.updateLiveTelemetry(landmarks);
      }
      this.notifyVisibility(true, landmarks);
    } else {
      this.currentLandmarks = null;
      this.isFaceVisible = false;
      this.updateStatus(false, "⚠️ No Face Detected");
      this.notifyVisibility(false, null);
    }
    this.canvasCtx.restore();
  }

  drawFacialMesh(landmarks, ctx, width, height) {
    ctx.fillStyle = "rgba(6, 182, 212, 0.7)";
    ctx.strokeStyle = "rgba(139, 92, 246, 0.4)";
    ctx.lineWidth = 0.6;

    // Draw key contour connections
    const keyPoints = [10, 152, 234, 454, 1, 33, 263, 61, 291];
    
    // Draw fine landmark nodes
    for (let i = 0; i < landmarks.length; i += 3) {
      const pt = landmarks[i];
      const x = pt.x * width;
      const y = pt.y * height;
      
      ctx.beginPath();
      ctx.arc(x, y, 1.2, 0, 2 * Math.PI);
      ctx.fill();
    }

    // Connect eyes and jawline with glowing accents
    ctx.beginPath();
    for (let idx of keyPoints) {
      if (landmarks[idx]) {
        const x = landmarks[idx].x * width;
        const y = landmarks[idx].y * height;
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
  }

  startSimulatedMesh() {
    // If MediaPipe CDN or WebGL is blocked, generate dynamic simulated face tracking coordinates
    const loop = () => {
      if (!this.canvasCtx || !this.canvasElement) return;
      this.canvasElement.width = this.videoElement.videoWidth || 640;
      this.canvasElement.height = this.videoElement.videoHeight || 480;

      const w = this.canvasElement.width;
      const h = this.canvasElement.height;
      const time = Date.now() * 0.002;

      this.canvasCtx.clearRect(0, 0, w, h);
      
      // Elliptical facial boundary with gentle breathing animation
      const cx = w * 0.5 + Math.sin(time) * 4;
      const cy = h * 0.48 + Math.cos(time) * 3;
      const rx = w * 0.22;
      const ry = h * 0.32;

      this.canvasCtx.strokeStyle = "rgba(6, 182, 212, 0.5)";
      this.canvasCtx.lineWidth = 1.5;
      this.canvasCtx.beginPath();
      this.canvasCtx.ellipse(cx, cy, rx, ry, 0, 0, 2 * Math.PI);
      this.canvasCtx.stroke();

      // Note: Do not auto-populate fake landmarks so that scanner strictly detects real user visibility

      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  captureSnapshot() {
    const canvas = document.createElement("canvas");
    canvas.width = this.videoElement.videoWidth || 640;
    canvas.height = this.videoElement.videoHeight || 480;
    const ctx = canvas.getContext("2d");

    // Mirror horizontally so it matches webcam preview
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(this.videoElement, 0, 0, canvas.width, canvas.height);

    return canvas.toDataURL("image/jpeg", 0.85);
  }

  handleFileUpload(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          // Render image onto video element or canvas
          resolve(e.target.result);
        };
        img.src = e.target.result;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  updateStatus(active, text) {
    if (this.statusDot) {
      if (active) {
        this.statusDot.classList.remove("offline");
        this.statusDot.classList.add("active");
      } else {
        this.statusDot.classList.remove("active");
        this.statusDot.classList.add("offline");
      }
    }
    if (this.statusText) {
      this.statusText.textContent = text;
    }
  }
}

window.CameraManager = CameraManager;
