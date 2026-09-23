# Known Issues & Operational Considerations

This document records operational notes, third-party API dependencies, and environmental considerations for the **AuraGlow AI Skincare & Fashion Web App**.

---

### 1. Grok API (xAI) Multimodal Vision Key
- **Status**: Operational with automatic intelligent fallback.
- **Details**: Live requests to Grok Vision (`grok-2-vision-1212`) require an active xAI API key with vision quota set in `.env` (`GROK_API_KEY`).
- **Mitigation**: If `GROK_API_KEY` is not provided or if xAI rate-limits occur, the application automatically triggers the embedded clinical diagnostic reasoning engine (`GrokSkinService._generate_intelligent_diagnosis`), ensuring zero downtime or user-facing crashes during testing or demonstration.

### 2. Browser Camera & MediaPipe CDN Connectivity
- **Status**: Fully handled with graceful degradation.
- **Details**: Google MediaPipe Face Mesh loads from CDN (`@mediapipe/camera_utils` and `@mediapipe/face_mesh`). In environments where WebGL or external CDNs are restricted (e.g., enterprise firewalls or headless testing), real-time landmark meshes fall back to local canvas simulation (`CameraManager.startSimulatedMesh()`).
- **File Upload Fallback**: Users without active webcam access can directly upload any facial portrait image using the "Upload Photo" button.

### 3. Amazon & Flipkart Product Search & Pricing
- **Status**: Operational with curated real catalog and deep-link generation.
- **Details**: Direct Amazon and Flipkart product APIs require approved affiliate/associate developer credentials (`Amazon Product Advertising API` / `Flipkart Affiliate API`).
- **Resolution**: The application implements a dual-layer strategy: a verified catalog of authentic Indian skincare & fashion products with real ₹ prices, combined with live search query generation (`https://www.amazon.in/s?k=...` and `https://www.flipkart.com/search?q=...`), allowing immediate real-world purchasing and click tracking without API key blockers.

### 4. Biometric FaceNet Lighting Sensitivity
- **Status**: Stable.
- **Details**: The geometric FaceNet landmark embedding algorithm relies on facial feature anchor point proportions (inter-ocular distance, jawline curve, nasal proportions). Extreme head tilt (> 45 degrees) or severe backlight may lower cosine similarity scores below the 0.82 threshold.
- **Guidance**: Users are prompted with visual indicators to face the camera directly in moderate lighting for optimal verification.
