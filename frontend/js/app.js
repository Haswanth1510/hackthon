// Main Application Controller & UI Logic
const App = {
  state: {
    currentUser: null,
    currentScan: null,
    currentOutfit: null,
    camera: null,
    hasFashionBudget: false,
    fashionBudget: 3500,
    activeOccasion: "Casual",
    capturedImageBase64: null,
    speechRecognition: null,
    isRecordingVoice: false,
    currentGateView: "password"
  },

  async init() {
    try {
      this.initNavigation();
      this.initVoiceToText();
      this.initFashionBudgetToggle();
      this.initModals();
      this.initAuthGate();
      this.initOccasionChips();
      this.initProfilePage();
      this.initLandingPageInteractions();
      this.checkHealth();
    } catch (e) {
      console.warn("[Init] Base setup warning:", e);
    }

    try {
      await this.initCamera();
    } catch (e) {
      console.warn("[Init] Camera init deferred/offline:", e);
    }

    try {
      await this.initAuth();
    } catch (e) {
      console.warn("[Init] Auth check warning:", e);
    }
  },

  async checkHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      console.log("[System Status]", data);
    } catch (e) {
      console.warn("Backend health check warning:", e);
    }
  },

  async initAuth() {
    const user = API.getUser();
    if (user && API.getToken()) {
      try {
        const freshUser = await API.getMe();
        this.state.currentUser = freshUser;
        this.updateUserUI(freshUser);
        this.unlockApp();
        this.switchView("view-landing");
        return;
      } catch (err) {
        console.warn("[Auth] Session expired or invalid:", err);
        // Token is invalid — clear storage and force login
        API.clearUser();
        this.state.currentUser = null;
        this.updateUserUI(null);
      }
    } else {
      this.state.currentUser = null;
      this.updateUserUI(null);
    }
    // Not authenticated — show the auth gate, lock the app
    this.showAuthGate();
  },

  updateUserUI(user) {
    const navGuest = document.getElementById("navGuestState");
    const navUser = document.getElementById("navLoggedInState");
    const navAvatar = document.getElementById("navAvatarInitial");
    const profAvatar = document.getElementById("profAvatarInitial");
    const authActions = document.getElementById("authActions");
    const userBadge = document.getElementById("userBadge");
    const userNameSpan = document.getElementById("userNameSpan");

    if (user) {
      if (navGuest) navGuest.style.display = "none";
      if (navUser) navUser.style.display = "flex";
      const initial = (user.full_name || user.email || "U")[0].toUpperCase();
      if (navAvatar) navAvatar.textContent = initial;
      if (profAvatar) profAvatar.textContent = initial;
      if (authActions) authActions.style.display = "none";
      if (userBadge) {
        userBadge.style.display = "flex";
        if (userNameSpan) userNameSpan.textContent = user.full_name || user.email.split("@")[0];
      }
    } else {
      if (navGuest) navGuest.style.display = "flex";
      if (navUser) navUser.style.display = "none";
      if (authActions) authActions.style.display = "flex";
      if (userBadge) userBadge.style.display = "none";
    }
  },

  initNavigation() {
    const navButtons = document.querySelectorAll(".nav-btn");
    navButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        const targetView = btn.dataset.view;
        this.switchView(targetView);
      });
    });
  },

  // Routes that require the user to be logged in
  _protectedViews: ["view-scanner", "view-report", "view-progress", "view-tracker", "view-profile"],

  switchView(viewId) {
    // ── Auth Guard ──────────────────────────────────────────
    // If user is not logged in and tries to access a protected view,
    // show the auth gate instead.
    if (this._protectedViews.includes(viewId) && !this.state.currentUser) {
      this.showAuthGate();
      this.showToast("Please sign in to access this feature.", "warning");
      return;
    }
    // ────────────────────────────────────────────────────────

    if (viewId === "view-landing") {
      document.body.classList.add("view-is-landing");
    } else {
      document.body.classList.remove("view-is-landing");
    }

    document.querySelectorAll(".nav-btn").forEach(b => {
      b.classList.toggle("active", b.dataset.view === viewId);
    });

    document.querySelectorAll(".mobile-bottom-btn").forEach(b => {
      b.classList.toggle("active", b.dataset.view === viewId);
    });

    document.querySelectorAll(".view-section").forEach(sec => {
      sec.classList.toggle("active", sec.id === viewId);
    });

    if (viewId === "view-report") {
      const loadingState = document.getElementById("reportLoadingState");
      const contentWrapper = document.getElementById("reportContentWrapper");
      const emptyState = document.getElementById("reportEmptyState");

      if (this.state.isScanning) {
        if (loadingState) loadingState.style.display = "block";
        if (contentWrapper) contentWrapper.style.display = "none";
        if (emptyState) emptyState.style.display = "none";
      } else if (this.state.currentScan) {
        if (loadingState) loadingState.style.display = "none";
        if (contentWrapper) contentWrapper.style.display = "block";
        if (emptyState) emptyState.style.display = "none";
      } else {
        if (loadingState) loadingState.style.display = "none";
        if (contentWrapper) contentWrapper.style.display = "none";
        if (emptyState) emptyState.style.display = "block";
      }
    }

    if (viewId === "view-progress" || viewId === "view-tracker") {
      this.loadProgressData();
    }
    if (viewId === "view-profile") {
      this.renderProfilePage();
    }
  },

  startAnalysis() {
    return this.executeScan();
  },

  triggerUpload() {
    const fileInput = document.getElementById("fileImageUpload") || document.getElementById("photoUploadInput");
    if (fileInput) fileInput.click();
  },

  clearUploadedImage() {
    this.clearUploadedPhoto();
  },

  toggleMesh() {
    const canvas = document.getElementById("meshCanvas");
    if (canvas) {
      canvas.style.display = (canvas.style.display === "none") ? "block" : "none";
      this.showToast(canvas.style.display === "none" ? "Mesh overlay hidden" : "Mesh overlay enabled", "info");
    }
  },

  shareReport() {
    if (navigator.share) {
      navigator.share({
        title: "Suit.AI Skin & Style Report",
        text: "Check out my personalized clinical skin analysis and head-to-toe style report on Suit.AI (https://suit.ai)!",
        url: window.location.href
      }).catch(() => {});
    } else {
      navigator.clipboard.writeText(window.location.href);
      this.showToast("Report link copied to clipboard!", "success");
    }
  },

  downloadReport() {
    window.print();
  },

  initCamera() {
    this.state.camera = new CameraManager();
    this.state.camera.init();

    // Real-time MediaPipe face visibility listener
    this.state.camera.addVisibilityListener((isVisible, landmarks) => {
      // 1. Scanner UI alert banner
      const scannerAlert = document.getElementById("scannerFaceAlert") || document.getElementById("faceAlert");
      if (scannerAlert) {
        if (isVisible) {
          scannerAlert.classList.add("hidden");
        } else {
          // If uploaded image is active, don't show camera face alert
          if (!this.state.capturedImageBase64 || this.state.cameraSnapshotUsed) {
            scannerAlert.classList.remove("hidden");
          }
        }
      }
    });

    // Scan Button
    const btnScan = document.getElementById("btnTriggerScan") || document.getElementById("btnAnalyze");
    if (btnScan) {
      btnScan.addEventListener("click", () => this.executeScan());
    }

    // Image Upload Input & Handlers
    const fileInput = document.getElementById("fileImageUpload") || document.getElementById("photoUploadInput");
    const imgPreview = document.getElementById("uploadedImagePreview") || document.getElementById("uploadedImgPreview");
    const webcamEl = document.getElementById("webcam");
    const uploadBanner = document.getElementById("uploadPhotoBanner") || document.getElementById("uploadedBanner");
    const uploadStatusText = document.getElementById("uploadPhotoStatusText");
    const btnRemoveUpload = document.getElementById("btnRemoveUpload");
    const btnScanLabel = document.getElementById("btnTriggerScanLabel");

    if (fileInput) {
      fileInput.addEventListener("change", async (e) => {
        if (e.target.files && e.target.files[0]) {
          try {
            const file = e.target.files[0];
            const b64 = await this.state.camera.handleFileUpload(file);
            this.state.capturedImageBase64 = b64;
            this.state.cameraSnapshotUsed = false;

            if (imgPreview) {
              imgPreview.src = b64;
              imgPreview.style.display = "block";
            }
            if (webcamEl) webcamEl.style.display = "none";
            if (uploadBanner) uploadBanner.style.display = "flex";
            if (uploadStatusText) uploadStatusText.textContent = `Analyzing "${file.name}" for face...`;
            if (btnScanLabel) btnScanLabel.textContent = "Analyze My Skin (Photo)";

            this.showToast("Uploaded photo loaded. Detecting facial features...", "info");

            const landmarks = await this.state.camera.analyzeImage(b64);
            const scannerAlert = document.getElementById("scannerFaceAlert") || document.getElementById("faceAlert");
            const scannerAlertText = document.getElementById("faceAlertText");
            const btnAnalyze = document.getElementById("btnAnalyze") || document.getElementById("btnTriggerScan");

            if (landmarks && landmarks.length >= 25) {
              this.state.uploadedImageHasHumanFace = true;
              if (uploadStatusText) {
                uploadStatusText.innerHTML = `<span style="color:var(--success, #10b981)">●</span> <strong>Human Face Verified (468 Landmarks)</strong> — "${file.name}"`;
              }
              if (btnScanLabel) btnScanLabel.textContent = "Analyze My Skin (Photo)";
              this.showToast("Human face verified. Ready for clinical skin analysis.", "success");
              if (scannerAlert) scannerAlert.classList.add("hidden");
              if (btnAnalyze) btnAnalyze.disabled = false;
            } else {
              this.state.uploadedImageHasHumanFace = false;
              if (uploadStatusText) {
                uploadStatusText.innerHTML = `<span style="color:var(--error, #ef4444); font-weight: 700;">⚠️ Non-Human Subject Detected</span> — Scanner is calibrated strictly for human beings.`;
              }
              if (btnScanLabel) btnScanLabel.textContent = "Cannot Scan (Non-Human)";
              if (scannerAlertText) {
                scannerAlertText.textContent = "Non-Human Image: Only human faces are supported for clinical scanning.";
              }
              if (scannerAlert) {
                scannerAlert.classList.remove("hidden");
                scannerAlert.classList.add("shake-alert");
                setTimeout(() => scannerAlert.classList.remove("shake-alert"), 800);
              }
              this.showToast("Non-Human Subject Detected: Suit.AI scans only human beings. Please upload a clear human facial portrait.", "danger");
            }
          } catch (err) {
            console.error("File upload error:", err);
            this.showToast("Failed to process uploaded photo: " + err.message, "danger");
          }
        }
      });
    }

    if (btnRemoveUpload) {
      btnRemoveUpload.addEventListener("click", () => {
        this.clearUploadedPhoto();
      });
    }
  },

  clearUploadedPhoto() {
    this.state.capturedImageBase64 = null;
    this.state.cameraSnapshotUsed = false;
    this.state.uploadedImageHasHumanFace = false;
    const imgPreview = document.getElementById("uploadedImagePreview") || document.getElementById("uploadedImgPreview");
    const webcamEl = document.getElementById("webcam");
    const uploadBanner = document.getElementById("uploadPhotoBanner") || document.getElementById("uploadedBanner");
    const btnScanLabel = document.getElementById("btnTriggerScanLabel");
    const fileInput = document.getElementById("fileImageUpload") || document.getElementById("photoUploadInput");
    const scannerAlert = document.getElementById("scannerFaceAlert") || document.getElementById("faceAlert");
    const scannerAlertText = document.getElementById("faceAlertText");

    if (imgPreview) {
      imgPreview.src = "";
      imgPreview.style.display = "none";
    }
    if (webcamEl) webcamEl.style.display = "block";
    if (uploadBanner) uploadBanner.style.display = "none";
    if (btnScanLabel) btnScanLabel.textContent = "Analyze My Skin (Live)";
    if (fileInput) fileInput.value = "";
    if (scannerAlertText) scannerAlertText.textContent = "No human face detected — center your face";
    if (scannerAlert) scannerAlert.classList.add("hidden");

    if (this.state.camera) {
      this.state.camera.clearUploadedImage();
    }
    this.showToast("Returned to live webcam preview.", "info");
  },

  // Voice to Text Module via Web Speech API
  initVoiceToText() {
    const btnVoice = document.getElementById("btnVoiceInput");
    const notesInput = document.getElementById("userNotesInput");
    const feedbackText = document.getElementById("voiceFeedbackText");
    const micIcon = document.getElementById("voiceMicIcon");
    const statusLabel = document.getElementById("voiceStatusLabel");

    if (!btnVoice || !notesInput) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      btnVoice.title = "Voice speech recognition not supported in this browser.";
      btnVoice.addEventListener("click", () => {
        this.showToast("Speech recognition is not supported in this browser. Please type your notes.", "warning");
      });
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      this.state.isRecordingVoice = true;
      btnVoice.classList.add("recording");
      if (micIcon) micIcon.textContent = "REC";
      if (statusLabel) statusLabel.textContent = "Listening...";
      if (feedbackText) feedbackText.style.display = "block";
    };

    recognition.onresult = (event) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        transcript += event.results[i][0].transcript;
      }
      if (transcript.trim()) {
        const existing = notesInput.value.trim();
        notesInput.value = existing ? `${existing} ${transcript}` : transcript;
      }
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      this.showToast(`Voice error: ${event.error}`, "warning");
    };

    recognition.onend = () => {
      this.state.isRecordingVoice = false;
      btnVoice.classList.remove("recording");
      if (micIcon) micIcon.textContent = "Mic";
      if (statusLabel) statusLabel.textContent = "Voice to Text";
      if (feedbackText) feedbackText.style.display = "none";
      this.showToast("Voice transcribed into notes!", "success");
    };

    btnVoice.addEventListener("click", () => {
      if (this.state.isRecordingVoice) {
        recognition.stop();
      } else {
        try {
          recognition.start();
        } catch (err) {
          console.warn("Speech recognition start failed:", err);
        }
      }
    });
  },

  // Fashion Budget Toggle Controller
  initFashionBudgetToggle() {
    const toggle = document.getElementById("toggleFashionBudget");
    const drawer = document.getElementById("fashionBudgetDrawer");
    const slider = document.getElementById("fashionBudgetSlider");
    const display = document.getElementById("fashionBudgetDisplay");

    if (toggle && drawer) {
      toggle.addEventListener("change", (e) => {
        this.state.hasFashionBudget = e.target.checked;
        drawer.style.display = e.target.checked ? "block" : "none";
        if (e.target.checked && slider) {
          this.state.fashionBudget = parseFloat(slider.value);
        }
      });
    }

    if (slider && display) {
      slider.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value);
        this.state.fashionBudget = val;
        display.textContent = `Rs. ${val.toLocaleString("en-IN")}`;
      });
    }
  },

  initOccasionChips() {
    const chips = document.querySelectorAll(".occasion-chip");
    chips.forEach(chip => {
      chip.addEventListener("click", () => {
        chips.forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        this.state.activeOccasion = chip.dataset.occasion;
        if (this.state.currentScan) {
          this.refreshOutfitForOccasion();
        }
      });
    });
  },

  landingAudioPlaying: false,
  landingAudioUtterance: null,

  playClinicalTone() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(587.33, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880.00, ctx.currentTime + 0.12);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.32);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.33);
    } catch (e) {
      // AudioContext optional/muted
    }
  },

  toggleLandingAudioBrief() {
    const now = Date.now();
    if (this._lastAudioToggle && (now - this._lastAudioToggle < 300)) {
      return; // Debounce rapid duplicate clicks
    }
    this._lastAudioToggle = now;

    if (this.landingAudioPlaying) {
      this.stopLandingAudioBrief();
    } else {
      this.startLandingAudioBrief();
    }
  },

  startLandingAudioBrief() {
    const icon = document.getElementById("landingAudioIcon");
    const waveBars = document.querySelectorAll("#landingAudioWaveform div");

    this.landingAudioPlaying = true;
    if (icon) icon.textContent = "pause";
    waveBars.forEach((bar, idx) => {
      bar.style.animation = `landingWavePulse 0.8s ease-in-out infinite alternate ${idx * 0.08}s`;
    });

    // Play subtle clinical medical chime
    this.playClinicalTone();

    // Primary: Play real audio file recorded by clinical voice
    let audio = document.getElementById("landingAudioPlayer");
    if (!audio) {
      audio = new Audio("/static/clinical_brief_084.wav");
      audio.id = "landingAudioPlayer";
    }

    this.landingAudioElement = audio;
    audio.volume = 1.0;
    audio.muted = false;
    audio.currentTime = 0;

    audio.onended = () => {
      this.stopLandingAudioBrief();
    };

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.then(() => {
        console.log("[Audio] Playing clinical_brief_084.wav");
      }).catch(err => {
        console.warn("Direct HTML5 audio play error, falling back to Web Speech:", err);
        this.playSpeechSynthesisFallback();
      });
    }
  },

  playSpeechSynthesisFallback() {
    if (!("speechSynthesis" in window)) return;
    try {
      window.speechSynthesis.cancel();
      window.speechSynthesis.resume();

      const text = "Welcome to Suit.AI. This is your Morning Routine Brief number 84, presented by Doctor Elena Vance. Stratum corneum barrier integrity is measured at 89.4%. Today's recommended active compounding regimen includes liposomal Niacinamide at 4.5% combined with biomimetic ceramides. For your wardrobe, your neutral-cool chromatic profile harmonizes with charcoal horizon and deep aquifer teal.";
      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = 0.98;
      utter.pitch = 1.05;
      utter.volume = 1.0;

      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(v => 
        (v.name.includes("Samantha") || v.name.includes("Google") || v.name.includes("Natural") || v.name.includes("Zira") || v.name.includes("Jenny") || v.name.includes("Victoria") || v.name.includes("Karen")) && v.lang.startsWith("en")
      ) || voices.find(v => v.lang.startsWith("en")) || voices[0];
      if (preferred) utter.voice = preferred;

      utter.onend = () => this.stopLandingAudioBrief();
      utter.onerror = () => this.stopLandingAudioBrief();

      this._activeUtterance = utter; // Prevent garbage collection in Chromium

      setTimeout(() => {
        if (this.landingAudioPlaying) {
          window.speechSynthesis.speak(utter);
        }
      }, 50);
    } catch (e) {
      console.warn("Speech synthesis error:", e);
    }
  },

  stopLandingAudioBrief() {
    this.landingAudioPlaying = false;
    const icon = document.getElementById("landingAudioIcon");
    const waveBars = document.querySelectorAll("#landingAudioWaveform div");

    if (this.landingAudioElement) {
      try {
        this.landingAudioElement.pause();
        this.landingAudioElement.currentTime = 0;
      } catch (e) {}
    }
    const audio = document.getElementById("landingAudioPlayer");
    if (audio) {
      try {
        audio.pause();
        audio.currentTime = 0;
      } catch (e) {}
    }

    if (icon) icon.textContent = "play_arrow";
    waveBars.forEach(bar => {
      bar.style.animation = "none";
    });
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  },

  initLandingPageInteractions() {
    // Note: #landingAudioPlayBtn is handled directly via onclick="App.toggleLandingAudioBrief()"

    const quickScanBtn = document.getElementById("landingQuickScanBtn");
    const quickEmail = document.getElementById("landingQuickEmail");
    if (quickScanBtn) {
      quickScanBtn.addEventListener("click", (e) => {
        e.preventDefault();
        const emailVal = quickEmail ? quickEmail.value.trim() : "";
        if (emailVal) {
          const regEmail = document.getElementById("gateRegEmail");
          const loginEmail = document.getElementById("gateLoginEmail");
          if (regEmail) regEmail.value = emailVal;
          if (loginEmail) loginEmail.value = emailVal;
        }
        this.showToast("Calibrating optical sensors... Opening live camera scanner.", "info");
        this.switchView("view-scanner");
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    // Window resize & outside click listeners for mobile drawer
    window.addEventListener("resize", () => {
      if (window.innerWidth >= 1024) {
        this.closeLandingMobileMenu();
      }
    });

    document.addEventListener("click", (e) => {
      const drawer = document.getElementById("landingMobileNavDrawer");
      const toggleBtn = document.getElementById("btnToggleLandingMobileNav");
      if (drawer && !drawer.classList.contains("hidden")) {
        if (!drawer.contains(e.target) && (!toggleBtn || !toggleBtn.contains(e.target))) {
          this.closeLandingMobileMenu();
        }
      }
    });
  },

  toggleLandingMobileMenu() {
    const drawer = document.getElementById("landingMobileNavDrawer");
    const icon = document.getElementById("landingMobileNavIcon");
    if (drawer) {
      const isClosed = drawer.classList.contains("hidden");
      if (isClosed) {
        drawer.classList.remove("hidden");
        drawer.classList.add("flex");
        if (icon) icon.textContent = "close";
      } else {
        drawer.classList.add("hidden");
        drawer.classList.remove("flex");
        if (icon) icon.textContent = "menu";
      }
    }
  },

  closeLandingMobileMenu() {
    const drawer = document.getElementById("landingMobileNavDrawer");
    const icon = document.getElementById("landingMobileNavIcon");
    if (drawer) {
      drawer.classList.add("hidden");
      drawer.classList.remove("flex");
      if (icon) icon.textContent = "menu";
    }
  },

  async executeScan(options = {}) {
    const isRetry = Boolean(options && options.isRetry);
    const viewport = document.querySelector(".camera-card");
    const scanBtn = document.getElementById("btnTriggerScan") || document.getElementById("btnAnalyze");
    const notesInput = document.getElementById("userNotesInput") || document.getElementById("scanContext");
    const budgetSlider = document.getElementById("budgetRange") || document.getElementById("fashionBudgetSlider");
    if (budgetSlider) {
      this.state.fashionBudget = parseFloat(budgetSlider.value);
      this.state.hasFashionBudget = true;
    }
    
    // 1. Strict human face presence verification: do not generate results if user is not a human being or not visible
    const hasUploadedImage = Boolean(this.state.capturedImageBase64 && !this.state.cameraSnapshotUsed);
    const hasLiveFace = Boolean(this.state.camera && this.state.camera.hasFaceVisible());

    if (!isRetry) {
      if (hasUploadedImage && !this.state.uploadedImageHasHumanFace) {
        this.showToast("Non-Human Subject Detected: The scanner is calibrated strictly for living human beings. Please upload a clear human facial portrait.", "danger");
        
        const banner = document.getElementById("scannerFaceAlert") || document.getElementById("faceAlert");
        const bannerText = document.getElementById("faceAlertText");
        if (bannerText) {
          bannerText.textContent = "Non-Human Image: The scanner is calibrated strictly for living human beings.";
        }
        if (banner) {
          banner.classList.remove("hidden");
          banner.classList.add("shake-alert");
          setTimeout(() => banner.classList.remove("shake-alert"), 800);
        }

        if (viewport) {
          viewport.style.borderColor = "var(--error, #ef4444)";
          viewport.style.boxShadow = "0 0 30px rgba(239, 68, 68, 0.4)";
          setTimeout(() => {
            viewport.style.borderColor = "";
            viewport.style.boxShadow = "";
          }, 3000);
        }
        return; // Stop immediately - do not generate AI results for non-human images
      }

      if (!hasUploadedImage && !hasLiveFace) {
        this.showToast("Face Not Detected: Please look directly at the camera or upload a clear facial portrait.", "danger");
        
        const banner = document.getElementById("scannerFaceAlert") || document.getElementById("faceAlert");
        const bannerText = document.getElementById("faceAlertText");
        if (bannerText) {
          bannerText.textContent = "No human face detected — center your face";
        }
        if (banner) {
          banner.classList.remove("hidden");
          banner.classList.add("shake-alert");
          setTimeout(() => banner.classList.remove("shake-alert"), 800);
        }

        if (viewport) {
          viewport.style.borderColor = "var(--error)";
          viewport.style.boxShadow = "0 0 30px rgba(186, 26, 26, 0.4)";
          setTimeout(() => {
            viewport.style.borderColor = "";
            viewport.style.boxShadow = "";
          }, 3000);
        }
        return; // Stop immediately - do not generate AI results without a visible user
      }
    }

    let imageB64 = this.state.capturedImageBase64;
    if (!isRetry && !hasUploadedImage && this.state.camera) {
      imageB64 = this.state.camera.captureSnapshot();
      this.state.capturedImageBase64 = imageB64;
      this.state.cameraSnapshotUsed = true;
    }

    if (!imageB64 || imageB64.length < 500) {
      this.showToast("Note: Unable to capture camera image. Please check camera access or upload a photo.", "warning");
      return;
    }

    try {
      this.state.isScanning = true;
      if (viewport) viewport.classList.add("scanning");
      if (scanBtn) {
        scanBtn.disabled = true;
        const scanBtnLabel = document.getElementById("btnTriggerScanLabel");
        if (scanBtnLabel) {
          scanBtnLabel.textContent = "Analyzing with AI...";
        } else {
          scanBtn.innerHTML = `<span></span> Analyzing with AI...`;
        }
      }

      // 1. Immediately switch view to AI Report
      this.switchView("view-report");
      window.scrollTo({ top: 0, behavior: "smooth" });

      // 2. Immediately present captured photo in the loading preview
      const loadingPhoto = document.getElementById("loadingCapturedPhoto");
      if (loadingPhoto) loadingPhoto.src = imageB64;
      const photoImg = document.getElementById("capturedPhotoPreview");
      if (photoImg) photoImg.src = imageB64;

      // 3. Clear any previous canvas overlays
      const overlayCanvas = document.getElementById("roboflowOverlayCanvas");
      if (overlayCanvas) {
        const ctx = overlayCanvas.getContext("2d");
        ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
      }

      // 4. Activate ONLY Real-Time Pipeline Loading Animation (Keep report content completely hidden)
      const loadingState = document.getElementById("reportLoadingState");
      const contentWrapper = document.getElementById("reportContentWrapper");
      const emptyState = document.getElementById("reportEmptyState");
      if (loadingState) loadingState.style.display = "block";
      if (contentWrapper) contentWrapper.style.display = "none";
      if (emptyState) emptyState.style.display = "none";

      const title = document.getElementById("pipelineStatusTitle");
      const sub = document.getElementById("pipelineStatusSubtitle");
      if (title) title.textContent = "AI Models Analyzing Facial Portrait...";
      if (sub) sub.textContent = "Synthesizing 3D facial topology, clinical lesion detection, and dermatological analysis...";

      this.showToast("Analyzing portrait with clinical AI models...", "info");

      let landmarks = this.state.camera ? this.state.camera.currentLandmarks : null;
      if (landmarks && landmarks.length > 0) {
        this.state.lastScanLandmarks = landmarks;
      } else if (this.state.lastScanLandmarks) {
        landmarks = this.state.lastScanLandmarks;
      }

      const notes = notesInput ? notesInput.value.trim() : "";
      const fashionBudget = this.state.hasFashionBudget ? this.state.fashionBudget : 3500;

      const res = await API.analyzeSkin(
        imageB64,
        landmarks,
        null, // No budget constraint for skincare
        fashionBudget,
        notes
      );

      this.state.currentScan = res;
      this.state.currentOutfit = res.outfit;

      // Render the report (handles both partial and complete modes)
      this.renderUnifiedReport(res);
      if (res.analysis_status === "partial") {
        this.showToast("Showing detected regions — full clinical scoring available on retry.", "warning");
      } else {
        this.showToast("Clinical analysis & AI report ready!", "success");
      }
    } catch (err) {
      console.error("Scan analysis error:", err);
      const loadingState = document.getElementById("reportLoadingState");
      if (loadingState) {
        loadingState.style.display = "block";
        const title = document.getElementById("pipelineStatusTitle");
        const sub = document.getElementById("pipelineStatusSubtitle");
        if (title) title.textContent = "Analysis Interrupted";
        if (sub) sub.innerHTML = `<span style="color: var(--accent-rose);">${err.message}</span> <button class="btn btn-secondary btn-sm" style="margin-left: 0.75rem; padding: 0.25rem 0.65rem;" onclick="App.switchView('view-scanner')">Return to Scanner</button>`;
      }
      this.showToast(`Scan failed: ${err.message}`, "danger");
    } finally {
      this.state.isScanning = false;
      if (viewport) viewport.classList.remove("scanning");
      if (scanBtn) {
        scanBtn.disabled = false;
        scanBtn.innerHTML = `<span></span> Analyze My Skin (Live)`;
      }
    }
  },

  async retryFullAnalysis() {
    if (!this.state.capturedImageBase64) {
      this.showToast("No active scan capture found. Please return to scanner.", "warning");
      this.switchView("view-scanner");
      return;
    }
    const btn = document.getElementById("btnPartialRetry");
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="material-symbols-outlined spin-icon" style="font-size: 14px; animation: spin 1s linear infinite;">sync</span> Retrying Analysis...`;
    }
    this.showToast("Retrying full clinical AI analysis...", "info");
    try {
      await this.executeScan({ isRetry: true });
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span class="material-symbols-outlined" style="font-size: 15px;">refresh</span> <span>Retry Full Analysis</span>`;
      }
    }
  },

  // Renders the single unified report according to requirements
  renderUnifiedReport(data) {
    const loadingState = document.getElementById("reportLoadingState");
    const contentWrapper = document.getElementById("reportContentWrapper");
    const emptyState = document.getElementById("reportEmptyState");

    if (loadingState) loadingState.style.display = "none";
    if (emptyState) emptyState.style.display = "none";
    if (contentWrapper) contentWrapper.style.display = "block";

    const isPartial = data.analysis_status === "partial";

    // 1. Photo that was captured
    const photoImg = document.getElementById("capturedPhotoPreview");
    if (photoImg) {
      photoImg.src = data.image_data || this.state.capturedImageBase64 || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500";
    }

    this.stopReportSpeech();

    // 2. Inline Notice Banner for Partial Results
    const partialBanner = document.getElementById("partialNoticeBanner");
    const partialNoticeText = document.getElementById("partialNoticeText");
    if (partialBanner) {
      if (isPartial) {
        partialBanner.style.display = "block";
        if (partialNoticeText) {
          partialNoticeText.textContent = data.message || "🤖 AI is too busy — please try later. Showing what we detected so far using computer vision (lesion regions & face geometry). Full clinical scoring, routines, and style curation will be ready once the AI is available again.";
        }
      } else {
        partialBanner.style.display = "none";
      }
    }

    // 3. Short & Clear Analysis: Summary
    const summaryText = document.getElementById("diagSummary");
    if (summaryText) {
      summaryText.textContent = isPartial
        ? "🤖 AI is too busy — please try later."
        : (data.summary || "Comprehensive clinical analysis synthesized from 3D biometric geometry, lesion detection, and dermatological intelligence.");
      // Style it prominently in partial mode
      if (isPartial) {
        summaryText.style.fontWeight = "600";
        summaryText.style.color = "var(--on-surface)";
        summaryText.style.fontSize = "1rem";
      } else {
        summaryText.style.fontWeight = "";
        summaryText.style.color = "";
        summaryText.style.fontSize = "";
      }
    }

    const badgeType = document.getElementById("badgeSkinType");
    const badgeTone = document.getElementById("badgeUndertone");
    const badgeShape = document.getElementById("badgeFaceShape");
    const badgeAge = document.getElementById("badgeAgeEstimate");
    const badgeRoboflow = document.getElementById("badgeRoboflow");

    // Strictly omit AI-derived fields in partial mode - never show fabricated or placeholder values
    if (badgeType) {
      if (isPartial || !data.skin_type) {
        badgeType.style.display = "none";
      } else {
        badgeType.style.display = "inline-block";
        badgeType.innerHTML = `<span class="material-symbols-outlined" style="font-size: 13px; vertical-align: middle; margin-right: 3px;">biotech</span> Skin Type: ${data.skin_type}`;
      }
    }

    if (badgeTone) {
      if (isPartial || !data.undertone) {
        badgeTone.style.display = "none";
      } else {
        badgeTone.style.display = "inline-block";
        badgeTone.innerHTML = `<span class="material-symbols-outlined" style="font-size: 13px; vertical-align: middle; margin-right: 3px;">palette</span> Undertone: ${data.undertone}`;
      }
    }

    if (badgeShape) {
      if (data.face_shape) {
        badgeShape.style.display = "inline-block";
        badgeShape.innerHTML = `<span class="material-symbols-outlined" style="font-size: 13px; vertical-align: middle; margin-right: 3px;">face</span> Face Shape: ${data.face_shape}`;
      } else {
        badgeShape.style.display = "none";
      }
    }

    if (badgeAge) {
      if (isPartial || data.age_estimate == null) {
        badgeAge.style.display = "none";
      } else {
        badgeAge.style.display = "inline-block";
        badgeAge.innerHTML = `<span class="material-symbols-outlined" style="font-size: 13px; vertical-align: middle; margin-right: 3px;">schedule</span> Estimated Age: ~${data.age_estimate}`;
      }
    }

    if (badgeRoboflow) {
      const rfList = data.roboflow_detections || [];
      badgeRoboflow.style.display = "inline-block";
      if (rfList.length > 0) {
        badgeRoboflow.innerHTML = `<span class="material-symbols-outlined" style="font-size: 13px; vertical-align: middle; margin-right: 3px;">view_in_ar</span> ${rfList.length} Lesion(s) Detected`;
      } else {
        badgeRoboflow.innerHTML = `<span class="material-symbols-outlined" style="font-size: 13px; vertical-align: middle; margin-right: 3px;">check_circle</span> Clear Barrier`;
      }
    }

    // Hide clinical narrator audio in partial mode
    const narratorBar = document.querySelector(".narrator-control-bar");
    if (narratorBar) {
      narratorBar.style.display = isPartial ? "none" : "flex";
    }

    // Draw Roboflow bounding box overlays on scanned portrait
    this.drawRoboflowDetections(data.roboflow_detections || []);

    // Detailed issues cards (Roboflow detections or full diagnosis)
    const shortIssuesGrid = document.getElementById("shortIssuesGrid");
    if (shortIssuesGrid) {
      const issues = data.issues || [];
      if (issues.length === 0) {
        shortIssuesGrid.innerHTML = `
          <div style="grid-column: 1 / -1; background: var(--surface-container-lowest); border: 1px dashed var(--surface-container-high); border-radius: var(--radius-md); padding: 1.5rem; text-align: center; color: var(--on-surface-variant); font-size: 0.88rem;">
            <span class="material-symbols-outlined" style="font-size: 28px; color: var(--primary); display: block; margin-bottom: 0.5rem;">verified</span>
            No localized surface lesions detected in scanned facial zones.
          </div>
        `;
      } else {
        shortIssuesGrid.innerHTML = issues.map(issue => {
          const badgeClass = issue.severity === "severe" 
            ? "badge-danger" 
            : (issue.severity === "moderate" ? "badge-warning" : "badge-info");

          const precautionsHtml = (issue.precautions && issue.precautions.length > 0)
            ? `
              <div class="issue-precautions-box">
                <span class="precaution-title">Clinical Precautions & Care:</span>
                <ul class="precaution-bullets">
                  ${issue.precautions.map(p => `<li>${p}</li>`).join("")}
                </ul>
              </div>
            ` : "";

          const confTag = (issue.confidence != null)
            ? `<span style="font-size: 0.72rem; color: var(--on-surface-variant); margin-left: 0.4rem; font-weight: normal;">(${Math.round(issue.confidence * 100)}% conf)</span>`
            : "";

          return `
            <div style="background: var(--surface-container-lowest); border: 1px solid var(--surface-container-high); border-radius: var(--radius-md); padding: 1.1rem; display: flex; flex-direction: column; justify-content: space-between; box-shadow: var(--shadow-sm);">
              <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem;">
                  <strong style="font-size: 0.95rem; color: var(--on-surface); font-family: var(--font-display);">${issue.issue_type}</strong>
                  <span class="badge ${badgeClass}" style="font-size: 0.72rem;">${(issue.severity || 'mild').toUpperCase()} ${confTag}</span>
                </div>
                <span style="font-family: var(--font-label); font-size: 0.75rem; color: var(--primary); display: block; margin-bottom: 0.45rem; font-weight: 600;">Target Zone: ${issue.zone || 'Facial Epidermis'}</span>
                <p style="font-size: 0.82rem; color: var(--on-surface-variant); line-height: 1.5; margin-bottom: 0.5rem;">${issue.description || ''}</p>
              </div>
              ${precautionsHtml}
            </div>
          `;
        }).join("");
      }
    }

    // Barrier Protocol Card - omit in partial mode
    const barrierCard = document.querySelector(".barrier-protocol-card");
    if (barrierCard) {
      barrierCard.style.display = isPartial ? "none" : "block";
    }

    // Comprehensive Global Clinical Precautions List
    const globalPrecautionsList = document.getElementById("globalPrecautionsList");
    if (globalPrecautionsList && !isPartial) {
      const precautions = (data.precautions && data.precautions.length > 0)
        ? data.precautions
        : [
            "Apply broad-spectrum SPF 50+ sunscreen every morning.",
            "Avoid combining strong active acids (AHA/BHA) with retinoids in the same routine.",
            "Patch-test all active skincare products on your jawline 24 hours prior to full use.",
            "Maintain skin barrier hydration using gentle ceramide-rich moisturizers."
          ];
      globalPrecautionsList.innerHTML = precautions.map(p => `<li>${p}</li>`).join("");
    }

    // 4. Targeted Skincare Regimen & Products Card - omit in partial mode
    const skincareCard = document.getElementById("skincareRegimenCard");
    if (skincareCard) {
      skincareCard.style.display = isPartial ? "none" : "block";
    }

    if (!isPartial) {
      const skincareGrid = document.getElementById("reportSkincareGrid");
      const skincareTotalEl = document.getElementById("skincareRegimenCost");
      if (skincareGrid) {
        let skinTotal = 0;
        skincareGrid.innerHTML = (data.recommendations || []).map(p => {
          skinTotal += p.price_inr;
          const isAmazon = p.platform.toLowerCase() === "amazon";
          return `
            <div class="product-card">
              <div class="product-thumb-wrap">
                <img class="product-thumb" src="${p.image_url}" alt="${p.title}" loading="lazy"/>
                <span class="product-badge-platform ${isAmazon ? 'platform-amazon' : 'platform-flipkart'}">
                  ${isAmazon ? 'Amazon.in' : 'Flipkart'}
                </span>
              </div>
              <div class="product-info">
                <span class="product-brand">${p.brand} | ${p.category}</span>
                <h4 class="product-title">${p.title}</h4>
                <p class="product-reason">${p.reason}</p>
                <div class="product-footer">
                  <span class="product-price">Rs. ${p.price_inr.toLocaleString("en-IN")}</span>
                  <a href="${p.product_url}" target="_blank" rel="noopener noreferrer" 
                     class="btn btn-primary btn-sm"
                     onclick="App.trackProductClick('${p.title.replace(/'/g, "\\'")}', '${p.platform}', ${p.price_inr}, '${p.product_url}')">
                    Buy Now &rarr;
                  </a>
                </div>
              </div>
            </div>
          `;
        }).join("");

        if (skincareTotalEl) {
          skincareTotalEl.textContent = `Rs. ${skinTotal.toLocaleString("en-IN")}`;
        }
      }

      // AM / PM Steps
      const amContainer = document.getElementById("amRoutineSteps");
      if (amContainer) {
        amContainer.innerHTML = (data.am_routine || []).map((step, idx) => `
          <div class="routine-step">
            <div class="step-num">${idx + 1}</div>
            <div style="font-size: 0.85rem; color: var(--on-surface); line-height: 1.45;">${step}</div>
          </div>
        `).join("");
      }

      const pmContainer = document.getElementById("pmRoutineSteps");
      if (pmContainer) {
        pmContainer.innerHTML = (data.pm_routine || []).map((step, idx) => `
          <div class="routine-step">
            <div class="step-num" style="background: rgba(75, 65, 225, 0.15); color: var(--secondary);">${idx + 1}</div>
            <div style="font-size: 0.85rem; color: var(--on-surface); line-height: 1.45;">${step}</div>
          </div>
        `).join("");
      }
    }

    // 5. Chromatic Skin Color Palette Card - omit in partial mode
    const chromaticCard = document.getElementById("chromaticPaletteCard");
    if (chromaticCard) {
      chromaticCard.style.display = isPartial ? "none" : "block";
    }
    if (!isPartial) {
      this.renderChromaticColorPalette(data.color_palette, data.undertone);
    }

    // 6. Head-to-Toe Fashion Curation Card - omit in partial mode
    const outfitCard = document.getElementById("outfitCurationCard");
    if (outfitCard) {
      outfitCard.style.display = (isPartial || !data.outfit) ? "none" : "block";
    }
    if (!isPartial && data.outfit) {
      this.renderHeadToToeOutfit(data.outfit);
    }
  },

  renderChromaticColorPalette(palette, fallbackUndertone) {
    const card = document.getElementById("chromaticPaletteCard");
    if (!card) return;

    // Graceful fallback defaults calibrated to skin undertone if palette is empty
    const p = palette || {
      season: "Warm Autumn",
      undertone: fallbackUndertone || "Warm Golden",
      contrast_level: "Medium Contrast",
      best_colors: [
        { name: "Terracotta Rust", hex: "#C85A32", family: "Primary Harmony", advice: "Accentuates skin warmth and illuminates facial features without reddish glare." },
        { name: "Forest Olive", hex: "#3B4E38", family: "Core Earth Tone", advice: "Harmonizes with natural skin undertones and softly neutralizes redness." },
        { name: "Warm Camel Tan", hex: "#C19A6B", family: "Base Neutral", advice: "Foundational wardrobe staple that effortlessly flatters warm melanin tones." },
        { name: "Deep Petrol Teal", hex: "#1B4D5A", family: "Contrasting Jewel", advice: "Striking evening shade that brings healthy, luminous definition." },
        { name: "Warm Ochre", hex: "#D4A017", family: "Sunlit Pop", advice: "Enhances eye depth and creates radiant facial highlights." },
        { name: "Espresso Brown", hex: "#3E2723", family: "Anchor Dark", advice: "Gentle, luxurious alternative to stark black that softens jawline contours." }
      ],
      colors_to_avoid: [
        { name: "Icy Stark White", hex: "#F5FAFA", why: "Creates an unnatural chalky contrast against warm skin pigments." },
        { name: "Neon Acid Lime", hex: "#BFFF00", why: "Reflects a sallow greenish cast across the cheeks and under-eyes." },
        { name: "Cool Icy Lilac", hex: "#DCD0FF", why: "Clashes with golden undertones and exaggerates tired facial shadows." }
      ],
      style_rationale: "Calibrated to your skin undertones and facial contrast. Rich earth pigments and deep jewel tones reflect flattering, warm ambient light onto your skin barrier.",
      wardrobe_guidance: "Wear your primary flattering colors (Terracotta, Forest Olive, Warm Camel) closest to your collarbone and face. Choose warm ivory shirts over stark bleached whites.",
      jewelry_metal_harmony: "Warm Yellow Gold (18k), Antique Brass, and Rose Gold provide superior chromatic resonance over cool chrome."
    };

    // Update badges
    const seasonEl = document.getElementById("colorSeasonBadge");
    const undertoneEl = document.getElementById("colorUndertoneBadge");
    const contrastEl = document.getElementById("colorContrastBadge");

    if (seasonEl) {
      seasonEl.innerHTML = `<span class="material-symbols-outlined" style="font-size: 13px; vertical-align: middle; margin-right: 3px;">auto_awesome</span> ${p.season || 'Warm Autumn'}`;
    }
    if (undertoneEl) {
      undertoneEl.innerHTML = `<span class="material-symbols-outlined" style="font-size: 13px; vertical-align: middle; margin-right: 3px;">palette</span> ${p.undertone || fallbackUndertone || 'Warm Golden'}`;
    }
    if (contrastEl) {
      contrastEl.innerHTML = `<span class="material-symbols-outlined" style="font-size: 13px; vertical-align: middle; margin-right: 3px;">contrast</span> ${p.contrast_level || 'Medium Contrast'}`;
    }

    // Render Best Colors Grid
    const bestGrid = document.getElementById("bestColorsGrid");
    if (bestGrid && Array.isArray(p.best_colors)) {
      bestGrid.innerHTML = p.best_colors.map(c => `
        <div class="chromatic-swatch-card">
          <div class="swatch-color-preview-row">
            <span class="swatch-color-circle" style="background: ${c.hex};"></span>
            <button class="hex-copy-btn" onclick="App.copyHexToClipboard('${c.hex}', '${c.name.replace(/'/g, "\\'")}')" title="Click to copy HEX code">
              ${c.hex}
              <span class="material-symbols-outlined" style="font-size: 12px;">content_copy</span>
            </button>
          </div>
          <div>
            <div class="swatch-name">${c.name}</div>
            <div class="swatch-family-tag">${c.family || 'Harmonizing'}</div>
          </div>
          <p class="swatch-advice">${c.advice || ''}</p>
        </div>
      `).join("");
    }

    // Render Avoid Colors Grid
    const avoidGrid = document.getElementById("avoidColorsGrid");
    if (avoidGrid && Array.isArray(p.colors_to_avoid)) {
      avoidGrid.innerHTML = p.colors_to_avoid.map(c => `
        <div class="avoid-color-chip">
          <span class="avoid-dot" style="background: ${c.hex};"></span>
          <strong>${c.name}</strong>
          <span class="avoid-reason">(${c.why || 'Clashes with undertone'})</span>
        </div>
      `).join("");
    }

    // Rationale & Guidance
    const rationaleEl = document.getElementById("colorStyleRationale");
    if (rationaleEl) rationaleEl.textContent = p.style_rationale || "";

    const wardrobeEl = document.getElementById("colorWardrobeGuidance");
    if (wardrobeEl) wardrobeEl.textContent = p.wardrobe_guidance || "";

    const jewelryEl = document.getElementById("colorJewelryGuidance");
    if (jewelryEl && p.jewelry_metal_harmony) {
      jewelryEl.innerHTML = `<span class="material-symbols-outlined" style="font-size: 14px; vertical-align: middle; margin-right: 3px;">diamond</span> <strong>Metal Harmony:</strong> ${p.jewelry_metal_harmony}`;
    }
  },

  copyHexToClipboard(hex, name) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(hex).then(() => {
        this.showToast(`Copied ${name} (${hex}) to clipboard!`, "success");
      }).catch(() => {
        this.showToast(`Hex: ${hex}`, "info");
      });
    } else {
      this.showToast(`Hex: ${hex}`, "info");
    }
  },

  renderHeadToToeOutfit(outfit) {
    if (!outfit) return;
    this.state.currentOutfit = outfit;

    const outfitGrid = document.getElementById("outfitHeadToToeGrid");
    const totalCostEl = document.getElementById("outfitTotalCost");
    const preferredBudgetEl = document.getElementById("outfitPreferredBudgetDisplay");
    const sliderEl = document.getElementById("outfitBudgetSlider");
    const paletteBox = document.getElementById("paletteBox");
    const adviceEl = document.getElementById("stylingAdviceShort");

    const totalCost = outfit.total_cost_inr || 0;
    const budgetLimit = outfit.budget_limit_inr || totalCost;

    if (totalCostEl) {
      totalCostEl.textContent = `₹${totalCost.toLocaleString("en-IN")}`;
    }

    if (preferredBudgetEl) {
      preferredBudgetEl.textContent = `₹${budgetLimit.toLocaleString("en-IN")}`;
    }

    if (sliderEl && Math.abs(parseFloat(sliderEl.value) - budgetLimit) > 50) {
      sliderEl.value = budgetLimit;
    }

    // Sync active state of preset chips
    const presetChips = document.querySelectorAll(".budget-preset-chip");
    presetChips.forEach(chip => {
      const chipVal = parseFloat(chip.textContent.replace(/[^0-9]/g, ''));
      chip.classList.toggle("active", Math.abs(chipVal - budgetLimit) < 100);
    });

    if (paletteBox) {
      paletteBox.innerHTML = (outfit.palette || []).map(color => {
        const hex = this.getColorHex(color);
        return `
          <div class="palette-swatch" onclick="App.copyHexToClipboard('${hex}', '${color}')" title="Click to copy HEX ${hex}" style="cursor: pointer;">
            <span class="swatch-dot" style="background: ${hex};"></span>
            <span>${color}</span>
          </div>
        `;
      }).join("");
    }

    if (adviceEl && outfit.styling_tips && outfit.styling_tips.length > 0) {
      adviceEl.innerHTML = outfit.styling_tips.map(tip => `<div style="margin-bottom: 0.25rem;">• ${tip}</div>`).join("");
    }

    if (outfitGrid) {
      // Show from Hat to Shoes in sequence
      outfitGrid.innerHTML = (outfit.items || []).map(item => {
        const isAmazon = (item.platform || "").toLowerCase() === "amazon";
        const colorName = item.color_name || "Complementary";
        const colorHex = item.color_hex || this.getColorHex(colorName);

        return `
          <div class="product-card">
            <div class="product-thumb-wrap">
              <img class="product-thumb" src="${item.image_url}" alt="${item.name}" loading="lazy"/>
              <span class="product-badge-platform ${isAmazon ? 'platform-amazon' : 'platform-flipkart'}">
                ${isAmazon ? 'Amazon.in' : 'Flipkart'}
              </span>
              <div class="product-color-badge" title="Diagnosed Skin Harmonious Shade">
                <span class="swatch-dot" style="background: ${colorHex};"></span>
                <span>${colorName}</span>
              </div>
            </div>
            <div class="product-info">
              <div>
                <div class="product-header-line">
                  <span class="product-brand">${item.item_type} · ${item.brand}</span>
                  <span class="item-color-tag">
                    <span class="color-dot" style="background: ${colorHex};"></span>
                    ${colorName}
                  </span>
                </div>
                <h4 class="product-title" title="${item.name}">${item.name}</h4>
              </div>
              <div class="product-footer">
                <div>
                  <span class="product-price">₹${item.price_inr.toLocaleString("en-IN")}</span>
                  <span class="product-affiliate-note">AI Color Match</span>
                </div>
                <a href="${item.product_url}" target="_blank" rel="noopener noreferrer" 
                   class="btn btn-secondary btn-sm"
                   onclick="App.trackProductClick('${item.name.replace(/'/g, "\\'")}', '${item.platform}', ${item.price_inr}, '${item.product_url}')">
                  Shop on ${isAmazon ? 'Amazon' : 'Flipkart'} &rarr;
                </a>
              </div>
            </div>
          </div>
        `;
      }).join("");
    }
  },

  setOutfitBudget(amount) {
    this.state.fashionBudget = amount;
    this.state.hasFashionBudget = true;
    const slider = document.getElementById("outfitBudgetSlider");
    if (slider) slider.value = amount;
    const display = document.getElementById("outfitPreferredBudgetDisplay");
    if (display) display.textContent = `₹${amount.toLocaleString("en-IN")}`;

    const presetChips = document.querySelectorAll(".budget-preset-chip");
    presetChips.forEach(chip => {
      const chipVal = parseFloat(chip.textContent.replace(/[^0-9]/g, ''));
      chip.classList.toggle("active", chipVal === amount);
    });

    const scanSlider = document.getElementById("fashionBudgetSlider");
    if (scanSlider) scanSlider.value = amount;
    const scanDisplay = document.getElementById("fashionBudgetDisplay");
    if (scanDisplay) scanDisplay.textContent = `₹${amount.toLocaleString("en-IN")}`;

    this.refreshOutfitForOccasion();
  },

  onOutfitBudgetSliderChange(val) {
    const num = parseFloat(val);
    this.state.fashionBudget = num;
    this.state.hasFashionBudget = true;
    const display = document.getElementById("outfitPreferredBudgetDisplay");
    if (display) display.textContent = `₹${num.toLocaleString("en-IN")}`;

    const presetChips = document.querySelectorAll(".budget-preset-chip");
    presetChips.forEach(chip => {
      const chipVal = parseFloat(chip.textContent.replace(/[^0-9]/g, ''));
      chip.classList.toggle("active", Math.abs(chipVal - num) < 100);
    });

    clearTimeout(this._budgetDebounceTimer);
    this._budgetDebounceTimer = setTimeout(() => {
      this.refreshOutfitForOccasion();
    }, 300);
  },

  async refreshOutfitForOccasion() {
    try {
      const sid = this.state.currentScan ? this.state.currentScan.scan_id : null;
      const budget = this.state.fashionBudget || 3500;
      const occ = this.state.activeOccasion || "Casual";
      const outfit = await API.generateOutfit(sid, occ, budget, "Modern Minimalist");
      this.renderHeadToToeOutfit(outfit);
    } catch (e) {
      console.warn("Failed to refresh outfit:", e);
    }
  },

  getColorHex(colorName) {
    const map = {
      "Navy Blue": "#1E3A8A",
      "Emerald Green": "#059669",
      "Slate Grey": "#64748B",
      "Crisp White": "#F8FAFC",
      "Lavender": "#C084FC",
      "Earthy Olive": "#556B2F",
      "Terracotta / Rust": "#C2410C",
      "Warm Mustard": "#D97706",
      "Cream / Oatmeal": "#FDE68A",
      "Chocolate Brown": "#78350F",
      "Muted Sage": "#84A98C",
      "Charcoal Heather": "#334155",
      "Sandstone Beige": "#D4A373",
      "Dusty Rose": "#FDA4AF",
      "Classic Monochrome": "#0F172A"
    };
    return map[colorName] || "#8B5CF6";
  },

  async trackProductClick(name, platform, price, url) {
    if (this.state.currentUser) {
      try {
        await API.trackClick(name, platform, price, url, "Skincare & Fashion");
      } catch (e) {}
    }
  },

  showRoboflowOverlays: true,

  toggleRoboflowOverlay() {
    this.showRoboflowOverlays = !this.showRoboflowOverlays;
    const btn = document.getElementById("btnToggleRoboflowOverlay");
    if (btn) {
      btn.textContent = this.showRoboflowOverlays ? " Overlays ON" : " Overlays OFF";
      btn.style.borderColor = this.showRoboflowOverlays ? "var(--accent-cyan)" : "var(--border-subtle)";
    }
    const canvas = document.getElementById("roboflowOverlayCanvas");
    if (canvas) {
      canvas.style.display = this.showRoboflowOverlays ? "block" : "none";
    }
  },

  drawRoboflowDetections(detections) {
    const canvas = document.getElementById("roboflowOverlayCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    canvas.width = 240;
    canvas.height = 240;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!detections || detections.length === 0) return;

    detections.forEach(d => {
      // Norm coordinates (center x, center y, width, height)
      const nx = (d.norm_x !== undefined && d.norm_x !== null) ? d.norm_x : (d.x ? d.x / 640 : 0.5);
      const ny = (d.norm_y !== undefined && d.norm_y !== null) ? d.norm_y : (d.y ? d.y / 640 : 0.5);
      const nw = (d.norm_width !== undefined && d.norm_width !== null) ? d.norm_width : (d.width ? d.width / 640 : 0.1);
      const nh = (d.norm_height !== undefined && d.norm_height !== null) ? d.norm_height : (d.height ? d.height / 640 : 0.1);

      const x = Math.max(0, (nx - nw / 2) * canvas.width);
      const y = Math.max(0, (ny - nh / 2) * canvas.height);
      const w = Math.min(canvas.width - x, nw * canvas.width);
      const h = Math.min(canvas.height - y, nh * canvas.height);

      // Draw box
      ctx.strokeStyle = "#F43F5E";
      ctx.lineWidth = 2;
      ctx.fillStyle = "rgba(244, 63, 94, 0.18)";
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(x, y, w, h, 3);
      } else {
        ctx.rect(x, y, w, h);
      }
      ctx.fill();
      ctx.stroke();

      // Label background & text
      const label = `${d.class} (${Math.round((d.confidence || 0.8) * 100)}%)`;
      ctx.font = "bold 9px sans-serif";
      const txtW = ctx.measureText(label).width;
      const tagY = Math.max(12, y - 3);
      ctx.fillStyle = "rgba(15, 23, 42, 0.88)";
      ctx.fillRect(x, tagY - 10, txtW + 6, 12);
      ctx.fillStyle = "#38BDF8";
      ctx.fillText(label, x + 3, tagY - 1);
    });
  },

  // Clinical Report Text-to-Speech Voice Narrator
  toggleReportSpeech() {
    if (!('speechSynthesis' in window)) {
      this.showToast("Text-to-speech is not supported in this browser.", "warning");
      return;
    }

    const synth = window.speechSynthesis;

    // If currently speaking and not paused, pause
    if (synth.speaking && !synth.paused) {
      synth.pause();
      this.updateVoiceButtonState(false, true);
      return;
    } else if (synth.paused) {
      synth.resume();
      this.updateVoiceButtonState(true);
      return;
    }

    // Cancel previous speech
    synth.cancel();

    const scan = this.state.currentScan;
    if (!scan) {
      this.showToast("No analysis report loaded to narrate.", "warning");
      return;
    }

    // Compose clinical narrative strictly from analysis text and detailed precautions
    let speechText = `Clinical Skin Diagnosis. Skin type is ${scan.skin_type}. `;
    if (scan.summary) {
      speechText += `Analysis summary: ${scan.summary}. `;
    }

    if (scan.issues && scan.issues.length > 0) {
      speechText += `Identified skin conditions and clinical precautions: `;
      scan.issues.forEach((issue, idx) => {
        speechText += `Condition ${idx + 1}: ${issue.issue_type}, localized at ${issue.zone}, with ${issue.severity} severity. ${issue.description}. `;
        if (issue.precautions && issue.precautions.length > 0) {
          speechText += `Clinical precautions: ${issue.precautions.join(". ")}. `;
        }
      });
    }

    if (scan.precautions && scan.precautions.length > 0) {
      speechText += `General skin barrier protocol: ${scan.precautions.join(". ")}.`;
    }

    const utterance = new SpeechSynthesisUtterance(speechText);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;

    const voices = synth.getVoices();
    const naturalVoice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Natural") || v.name.includes("Google") || v.name.includes("Samantha")));
    if (naturalVoice) utterance.voice = naturalVoice;

    utterance.onstart = () => {
      this.updateVoiceButtonState(true);
    };

    utterance.onend = () => {
      this.updateVoiceButtonState(false);
    };

    utterance.onerror = (e) => {
      console.warn("Speech synthesis error:", e);
      this.updateVoiceButtonState(false);
    };

    synth.speak(utterance);
  },

  stopReportSpeech() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.updateVoiceButtonState(false);
  },

  updateVoiceButtonState(isPlaying, isPaused = false) {
    const playIcon = document.getElementById("voicePlayIcon");
    const playText = document.getElementById("voicePlayText");
    const stopBtn = document.getElementById("btnStopReportVoice");
    const equalizer = document.getElementById("voiceEqualizer");

    if (isPlaying) {
      if (playIcon) playIcon.innerHTML = `<span class="material-symbols-outlined" style="font-size: 16px; vertical-align: middle;">pause</span>`;
      if (playText) playText.textContent = "Pause Audio";
      if (stopBtn) stopBtn.style.display = "inline-flex";
      if (equalizer) equalizer.style.display = "flex";
    } else if (isPaused) {
      if (playIcon) playIcon.innerHTML = `<span class="material-symbols-outlined" style="font-size: 16px; vertical-align: middle;">play_arrow</span>`;
      if (playText) playText.textContent = "Resume Audio";
      if (stopBtn) stopBtn.style.display = "inline-flex";
      if (equalizer) equalizer.style.display = "none";
    } else {
      if (playIcon) playIcon.innerHTML = `<span class="material-symbols-outlined" style="font-size: 16px; vertical-align: middle;">volume_up</span>`;
      if (playText) playText.textContent = "Listen to Diagnosis";
      if (stopBtn) stopBtn.style.display = "none";
      if (equalizer) equalizer.style.display = "none";
    }
  },

  // Progress Tracking & Analytics
  async loadProgressData() {
    if (!this.state.currentUser) {
      const container = document.getElementById("progressContent");
      if (container) {
        container.innerHTML = `
          <div style="text-align: center; padding: 3rem; background: var(--bg-card); border-radius: var(--radius-lg); border: 1px solid var(--border-subtle);">
            <h3> Account Required</h3>
            <p style="color: var(--text-muted); margin: 0.75rem 0 1.5rem 0;">Please log in or sign up to track your skin progress over time.</p>
            <button class="btn btn-primary" onclick="App.openModal('loginModal')">Log In to View Progress</button>
          </div>
        `;
      }
      return;
    }

    try {
      const progress = await API.getProgressTrends();
      const purchases = await API.getPurchases();
      this.renderProgressUI(progress, purchases);
    } catch (e) {
      console.warn("Error loading progress:", e);
    }
  },

  renderProgressUI(progress, purchases) {
    const latestSkinType = (progress && progress.trends && progress.trends.length > 0 && progress.trends[0].skin_type)
      ? progress.trends[0].skin_type
      : "Combination";

    // 1. Update Timeline / Tracker elements
    const totalScansEl = document.getElementById("trackerTotalScans");
    const skinTypeEl = document.getElementById("trackerSkinType");
    const barrierStatusEl = document.getElementById("trackerBarrierStatus");
    const logCountEl = document.getElementById("trackerLogCount");
    const timelineListEl = document.getElementById("scanTimelineList");
    const recentScansList = document.getElementById("recentScansList");

    if (totalScansEl) totalScansEl.textContent = (progress && progress.scans_count) ? progress.scans_count : 0;
    if (skinTypeEl) skinTypeEl.textContent = latestSkinType;
    if (barrierStatusEl) barrierStatusEl.textContent = (progress && progress.scans_count > 0) ? "Optimal" : "-";
    if (logCountEl) logCountEl.textContent = `${(progress && progress.scans_count) ? progress.scans_count : 0} scan(s) recorded`;

    if (timelineListEl && progress && progress.trends && progress.trends.length > 0) {
      timelineListEl.innerHTML = progress.trends.map(t => `
        <div class="control-card" style="display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
              <span class="material-symbols-outlined" style="font-size: 18px; color: var(--primary);">dermatology</span>
              <strong style="font-family: var(--font-display); font-size: 1rem; color: var(--on-surface);">Scan #${t.scan_id}</strong>
              <span class="badge badge-primary" style="font-size: 0.7rem;"> ${t.skin_type || 'Completed'}</span>
            </div>
            <div style="font-family: var(--font-label); font-size: 0.72rem; color: var(--on-surface-variant);">${t.timestamp}</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="App.switchView('view-report')">View Diagnostic</button>
        </div>
      `).join("");
    }

    if (recentScansList && progress && progress.trends && progress.trends.length > 0) {
      recentScansList.innerHTML = progress.trends.slice(0, 3).map(t => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0.85rem; background: var(--surface-container-low); border: 1px solid var(--outline-variant); border-radius: var(--radius-sm); cursor: pointer;" onclick="App.switchView('view-report')">
          <div>
            <div style="font-family: var(--font-label); font-size: 0.75rem; font-weight: 700; color: var(--on-surface);">Scan #${t.scan_id} - ${t.skin_type || 'Assessed'}</div>
            <div style="font-size: 0.68rem; color: var(--on-surface-variant);">${t.timestamp}</div>
          </div>
          <span class="material-symbols-outlined" style="font-size: 14px; color: var(--primary);">arrow_forward</span>
        </div>
      `).join("");
    }

    const container = document.getElementById("progressContent");
    if (!container) return;

    if (!progress || progress.scans_count === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: var(--bg-card); border-radius: var(--radius-lg); border: 1px solid var(--border-subtle);">
          <h3> No Previous Scans Found</h3>
          <p style="color: var(--text-muted); margin: 0.75rem 0 1.5rem 0;">Perform your first AI Face Scan to start tracking progress!</p>
          <button class="btn btn-primary" onclick="App.switchView('view-scanner')">Start Face Scan Now</button>
        </div>
      `;
      return;
    }

    const deltas = progress.metric_deltas || {};
    const overallDiff = deltas.overall_improvement || 0;
    const trendsHtml = progress.trends.map((t) => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.9rem; background: rgba(255,255,255,0.02); border-bottom: 1px solid var(--border-subtle);">
        <div>
          <strong>Scan #${t.scan_id}</strong>
          <div style="font-size: 0.8rem; color: var(--text-muted);">${t.timestamp}</div>
        </div>
        <div style="display: flex; align-items: center; gap: 1rem;">
          <span class="badge badge-info"> ${t.skin_type || 'Completed'}</span>
        </div>
      </div>
    `).join("");

    const purchasesHtml = (purchases || []).map(p => `
      <tr>
        <td style="padding: 0.75rem;">${p.product_name}</td>
        <td style="padding: 0.75rem;"><span class="badge ${p.platform.toLowerCase() === 'amazon' ? 'platform-amazon' : 'platform-flipkart'}">${p.platform}</span></td>
        <td style="padding: 0.75rem; font-weight: 700; color: var(--accent-emerald);">Rs. ${p.price_inr}</td>
        <td style="padding: 0.75rem; font-size: 0.8rem; color: var(--text-muted);">${p.created_at}</td>
      </tr>
    `).join("");

    container.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.25rem; margin-bottom: 2rem;">
        <div class="telemetry-item">
          <div class="telemetry-label">Total Scans</div>
          <div class="telemetry-val" style="font-size: 1.8rem;">${progress.scans_count}</div>
        </div>
        <div class="telemetry-item">
          <div class="telemetry-label">Assessed Skin Type</div>
          <div class="telemetry-val" style="font-size: 1.8rem; color: var(--accent-cyan);">${latestSkinType}</div>
        </div>
        <div class="telemetry-item">
          <div class="telemetry-label">Profile Status</div>
          <div class="telemetry-val" style="font-size: 1.8rem; color: var(--accent-emerald);">Active</div>
        </div>
      </div>

      <div class="control-card" style="margin-bottom: 2rem;">
        <h3 style="margin-bottom: 1rem;"> Historical Scan Log</h3>
        <div>${trendsHtml}</div>
      </div>

      <div class="control-card">
        <h3 style="margin-bottom: 1rem;">Product Clicks & History</h3>
        ${purchases.length === 0 ? '<p style="color: var(--text-muted);">No products clicked yet.</p>' : `
          <div style="overflow-x: auto;">
            <table style="width: 100%; text-align: left; border-collapse: collapse;">
              <thead>
                <tr style="border-bottom: 1px solid var(--border-subtle); color: var(--text-muted); font-size: 0.8rem;">
                  <th style="padding: 0.75rem;">Product</th>
                  <th style="padding: 0.75rem;">Platform</th>
                  <th style="padding: 0.75rem;">Price</th>
                  <th style="padding: 0.75rem;">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                ${purchasesHtml}
              </tbody>
            </table>
          </div>
        `}
      </div>
    `;
  },

  // Modals & Biometrics
  initModals() {
    const btnOpenLogin = document.getElementById("btnOpenLogin");
    const btnOpenRegister = document.getElementById("btnOpenRegister");
    if (btnOpenLogin) btnOpenLogin.addEventListener("click", () => this.openModal("loginModal"));
    if (btnOpenRegister) btnOpenRegister.addEventListener("click", () => this.openModal("registerModal"));

    document.querySelectorAll(".modal-close, .modal-overlay").forEach(el => {
      el.addEventListener("click", (e) => {
        if (e.target === el) {
          document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
        }
      });
    });

    const loginForm = document.getElementById("formModalLogin") || document.getElementById("formLogin");
    if (loginForm) {
      loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const emailInput = document.getElementById("modalLoginEmail") || document.getElementById("loginEmail");
        const passwordInput = document.getElementById("modalLoginPassword") || document.getElementById("loginPassword");
        const email = emailInput ? emailInput.value.trim() : "";
        const password = passwordInput ? passwordInput.value : "";
        try {
          const res = await API.login(email, password);
          this.state.currentUser = res.user;
          this.updateUserUI(res.user);
          localStorage.setItem("suit_ai_has_account", "true");
          localStorage.setItem("Stylic.AI_has_account", "true");
          this.unlockApp();
          this.closeModal("loginModal");
          this.showToast(`Welcome back, ${res.user.full_name}!`, "success");
        } catch (err) {
          this.showToast(`Login failed: ${err.message}`, "danger");
        }
      });
    }

    const regForm = document.getElementById("formModalRegister") || document.getElementById("formRegister");
    if (regForm) {
      regForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const nameInput = document.getElementById("modalRegFullName") || document.getElementById("regFullName");
        const emailInput = document.getElementById("modalRegEmail") || document.getElementById("regEmail");
        const passwordInput = document.getElementById("modalRegPassword") || document.getElementById("regPassword");

        const fullName = nameInput ? nameInput.value.trim() : "";
        const email = emailInput ? emailInput.value.trim() : "";
        const password = passwordInput ? passwordInput.value : "";

        try {
          const res = await API.register({
            email,
            password,
            full_name: fullName
          });

          this.state.currentUser = res.user;
          this.updateUserUI(res.user);
          localStorage.setItem("suit_ai_has_account", "true");
          localStorage.setItem("Stylic.AI_has_account", "true");
          this.unlockApp();
          this.closeModal("registerModal");
          this.showToast(`Account created! Welcome, ${fullName}.`, "success");
          
          // Open profile modal after authentication to collect age, gender, and preferences
          setTimeout(() => this.openProfileModal(true), 350);
        } catch (err) {
          this.showToast(`Registration failed: ${err.message}`, "danger");
        }
      });
    }

    // Close modal on click of close button or outside backdrop
    document.querySelectorAll(".modal-close").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const modal = btn.closest(".modal-overlay");
        if (modal) modal.classList.remove("active");
      });
    });

    document.querySelectorAll(".modal-overlay").forEach(overlay => {
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) {
          overlay.classList.remove("active");
        }
      });
    });

    const btnOpenProfile = document.getElementById("btnOpenProfileModal");
    const userBadgeLabel = document.getElementById("userBadgeLabel");
    const navBtnProfile = document.getElementById("navBtnProfile");
    if (btnOpenProfile) {
      btnOpenProfile.addEventListener("click", (e) => {
        e.preventDefault();
        this.switchView("view-profile");
      });
    }
    if (userBadgeLabel) {
      userBadgeLabel.addEventListener("click", (e) => {
        e.preventDefault();
        this.switchView("view-profile");
      });
    }
    if (navBtnProfile) {
      navBtnProfile.addEventListener("click", (e) => {
        e.preventDefault();
        this.switchView("view-profile");
      });
    }

    const btnSkipProfile = document.getElementById("btnSkipProfile");
    if (btnSkipProfile) {
      btnSkipProfile.addEventListener("click", () => {
        this.closeModal("profileModal");
        this.unlockApp();
      });
    }

    const profileForm = document.getElementById("formProfile");
    if (profileForm) {
      profileForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fullName = document.getElementById("profileFullName").value.trim();
        const ageVal = document.getElementById("profileAge").value;
        const gender = document.getElementById("profileGender").value;
        const budgetSkincare = parseFloat(document.getElementById("profileBudgetSkincare").value || "2000");
        const budgetFashion = parseFloat(document.getElementById("profileBudgetFashion").value || "3500");

        try {
          const payload = {};
          if (fullName) payload.full_name = fullName;
          if (ageVal) payload.age = parseInt(ageVal);
          if (gender) payload.gender = gender;
          if (!isNaN(budgetSkincare)) payload.budget_skincare = budgetSkincare;
          if (!isNaN(budgetFashion)) payload.budget_fashion = budgetFashion;

          const updatedUser = await API.updateProfile(payload);
          this.state.currentUser = updatedUser;
          this.updateUserUI(updatedUser);
          this.closeModal("profileModal");
          this.unlockApp();
          this.showToast("Profile customized! Entering Suit.AI...", "success");
        } catch (err) {
          this.showToast(`Failed to update profile: ${err.message}`, "danger");
        }
      });
    }

    const btnLogout = document.getElementById("btnLogout");
    if (btnLogout) {
      btnLogout.addEventListener("click", () => {
        API.setToken(null);
        API.setUser(null);
        this.state.currentUser = null;
        this.updateUserUI(null);
        this.lockApp();
        this.showToast("Logged out successfully. Please authenticate to re-enter.", "info");
      });
    }

  },

  // Auth Gate Controller
  initAuthGate() {
    const btnToSignUpFromPass = document.getElementById("btnSwitchToSignUpFromPassword");
    const btnToLoginFromSign = document.getElementById("btnSwitchToLoginFromSignUp");

    if (btnToSignUpFromPass) btnToSignUpFromPass.addEventListener("click", () => this.switchGateView("signup"));
    if (btnToLoginFromSign) btnToLoginFromSign.addEventListener("click", () => this.switchGateView("password"));

    // Gate Password Login Form
    const formGateLogin = document.getElementById("formGateLogin");
    if (formGateLogin) {
      formGateLogin.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("gateLoginEmail").value.trim();
        const password = document.getElementById("gateLoginPassword").value;
        try {
          const res = await API.login(email, password);
          this.state.currentUser = res.user;
          this.updateUserUI(res.user);
          localStorage.setItem("suit_ai_has_account", "true");
          localStorage.setItem("Stylic.AI_has_account", "true");
          this.unlockApp();
          this.switchView("view-landing");
          this.showToast(`Welcome back, ${res.user.full_name}!`, "success");
        } catch (err) {
          this.showToast(`Login failed: ${err.message}`, "danger");
        }
      });
    }

    // Gate Sign Up Form
    const formGateSignUp = document.getElementById("formGateSignUp");
    if (formGateSignUp) {
      formGateSignUp.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fullName = document.getElementById("gateRegFullName").value.trim();
        const email = document.getElementById("gateRegEmail").value.trim();
        const password = document.getElementById("gateRegPassword").value;

        try {
          const res = await API.register({
            email,
            password,
            full_name: fullName
          });

          this.state.currentUser = res.user;
          this.updateUserUI(res.user);
          localStorage.setItem("suit_ai_has_account", "true");
          localStorage.setItem("Stylic.AI_has_account", "true");
          this.unlockApp();
          this.switchView("view-landing");
          this.showToast(`Account created! Welcome, ${res.user.full_name || 'User'}!`, "success");
        } catch (err) {
          this.showToast(`Registration failed: ${err.message}`, "danger");
        }
      });
    }
  },

  lockApp() {
    document.body.classList.add("app-locked");
    const gate = document.getElementById("authGate");
    if (gate) gate.classList.remove("hidden");

    const hasAccount = localStorage.getItem("suit_ai_has_account") === "true" || localStorage.getItem("Stylic.AI_has_account") === "true";
    if (hasAccount) {
      this.switchGateView("password");
    } else {
      this.switchGateView("signup");
    }
  },

  // Alias used by auth guards throughout the app
  showAuthGate() {
    this.lockApp();
  },

  unlockApp() {
    document.body.classList.remove("app-locked");
    const gate = document.getElementById("authGate");
    if (gate) gate.classList.add("hidden");

    if (this.state.camera) {
      const webcam = document.getElementById("webcam");
      const canvas = document.getElementById("meshCanvas");
      const dot = document.getElementById("statusDot");
      const text = document.getElementById("statusText");
      this.state.camera.attachTo(webcam, canvas, dot, text);
    }
  },

  switchGateView(view) {
    this.state.currentGateView = view;
    const passView = document.getElementById("gatePasswordView");
    const signUpView = document.getElementById("gateSignUpView");

    if (passView) passView.style.display = view === "password" ? "block" : "none";
    if (signUpView) signUpView.style.display = view === "signup" ? "block" : "none";
  },

  async openProfileModal(isInitial = false) {
    let user = this.state.currentUser || API.getUser();

    // If currentUser is not in memory but token exists, fetch fresh from backend
    if (!user && API.getToken()) {
      try {
        user = await API.getMe();
        this.state.currentUser = user;
        this.updateUserUI(user);
      } catch (err) {
        console.warn("[Profile] getMe error:", err);
      }
    }

    if (!user) {
      this.showToast("Please log in or create an account to customize your profile.", "info");
      this.lockApp();
      return;
    }

    this.state.currentUser = user;

    const nameInput = document.getElementById("profileFullName");
    const ageInput = document.getElementById("profileAge");
    const genderSelect = document.getElementById("profileGender");
    const skinBudgetInput = document.getElementById("profileBudgetSkincare");
    const fashionBudgetInput = document.getElementById("profileBudgetFashion");

    if (nameInput) nameInput.value = user.full_name || "";
    if (ageInput) ageInput.value = (user.age && user.age !== 25) || !isInitial ? (user.age || "") : "";
    if (genderSelect) genderSelect.value = user.gender || "unspecified";
    if (skinBudgetInput) skinBudgetInput.value = user.budget_skincare || 2000;
    if (fashionBudgetInput) fashionBudgetInput.value = user.budget_fashion || 3500;

    this.openModal("profileModal");
  },

  openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add("active");
  },

  closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove("active");
  },

  initProfilePage() {
    // 1. Change Password Form
    const formPass = document.getElementById("formChangePassword");
    if (formPass) {
      formPass.addEventListener("submit", async (e) => {
        e.preventDefault();
        const oldPass = document.getElementById("oldPasswordInput").value;
        const newPass = document.getElementById("newPasswordInput").value;
        const confPass = document.getElementById("confirmPasswordInput").value;

        if (newPass !== confPass) {
          this.showToast("New passwords do not match. Please verify.", "warning");
          return;
        }
        if (newPass.length < 6) {
          this.showToast("Password must be at least 6 characters long.", "warning");
          return;
        }

        const submitBtn = document.getElementById("btnSubmitChangePassword");
        if (submitBtn) submitBtn.disabled = true;

        try {
          await API.changePassword(oldPass, newPass);
          this.showToast("Password updated successfully!", "success");
          formPass.reset();
        } catch (err) {
          this.showToast(`Password update failed: ${err.message}`, "danger");
        } finally {
          if (submitBtn) submitBtn.disabled = false;
        }
      });
    }

    // 2. Profile Preferences Form
    const formProf = document.getElementById("formProfileView");
    if (formProf) {
      formProf.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fullName = document.getElementById("profViewName").value.trim();
        const ageVal = parseInt(document.getElementById("profViewAge").value, 10);
        const genderVal = document.getElementById("profViewGender").value;
        const skinBudget = parseFloat(document.getElementById("profViewBudgetSkin").value);
        const fashionBudget = parseFloat(document.getElementById("profViewBudgetFashion").value);

        const saveBtn = document.getElementById("btnSaveProfileView");
        if (saveBtn) saveBtn.disabled = true;

        try {
          const updated = await API.updateProfile({
            full_name: fullName || undefined,
            age: !isNaN(ageVal) ? ageVal : undefined,
            gender: genderVal,
            budget_skincare: !isNaN(skinBudget) ? skinBudget : undefined,
            budget_fashion: !isNaN(fashionBudget) ? fashionBudget : undefined
          });
          this.state.currentUser = updated;
          this.updateUserUI(updated);
          this.renderProfilePage();
          this.showToast("Profile preferences updated successfully!", "success");
        } catch (err) {
          this.showToast(`Failed to update profile: ${err.message}`, "danger");
        } finally {
          if (saveBtn) saveBtn.disabled = false;
        }
      });
    }

  },

  async renderProfilePage() {
    let user = this.state.currentUser || API.getUser();
    if (API.getToken()) {
      try {
        user = await API.getMe();
        this.state.currentUser = user;
        this.updateUserUI(user);
      } catch (e) {
        console.warn("renderProfilePage getMe error:", e);
      }
    }

    const guestState = document.getElementById("profileGuestState");
    const loggedInState = document.getElementById("profileLoggedInState");

    if (!user) {
      if (guestState) guestState.style.display = "block";
      if (loggedInState) loggedInState.style.display = "none";
      return;
    }

    if (guestState) guestState.style.display = "none";
    if (loggedInState) loggedInState.style.display = "grid";

    // User Overview Card
    const nameDisplay = document.getElementById("profFullNameDisplay");
    const emailDisplay = document.getElementById("profEmailDisplay");
    const initialEl = document.getElementById("profAvatarInitial");
    const idBadge = document.getElementById("profUserIdBadge");
    const joinedBadge = document.getElementById("profMemberSinceBadge");

    if (nameDisplay) nameDisplay.textContent = user.full_name || "User";
    if (emailDisplay) emailDisplay.textContent = user.email || "";
    if (initialEl) initialEl.textContent = (user.full_name || user.email || "U")[0].toUpperCase();
    if (idBadge) idBadge.textContent = `ID: #${user.id}`;
    if (joinedBadge) joinedBadge.textContent = `Joined ${user.created_at ? user.created_at.split(" ")[0] : "Recently"}`;



    // Preferences Form fields
    const nameInput = document.getElementById("profViewName");
    const ageInput = document.getElementById("profViewAge");
    const genderSelect = document.getElementById("profViewGender");
    const skinBudgetInput = document.getElementById("profViewBudgetSkin");
    const fashionBudgetInput = document.getElementById("profViewBudgetFashion");

    if (nameInput) nameInput.value = user.full_name || "";
    if (ageInput) ageInput.value = user.age || "";
    if (genderSelect) genderSelect.value = user.gender || "unspecified";
    if (skinBudgetInput) skinBudgetInput.value = user.budget_skincare || 2000;
    if (fashionBudgetInput) fashionBudgetInput.value = user.budget_fashion || 3500;
  },

  logoutFromProfile() {
    API.setToken(null);
    API.setUser(null);
    this.state.currentUser = null;
    this.updateUserUI(null);
    this.lockApp();
    this.showToast("Signed out successfully. Please log in to continue.", "info");
  },

  showToast(message, type = "info") {
    let container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    const icon = type === "success" ? "OK" : (type === "danger" ? "X" : (type === "warning" ? "!" : "i"));
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(50px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
};

window.App = App;
document.addEventListener("DOMContentLoaded", () => App.init());


