# Stylic.AI — Clinical Skin & Style Intelligence Platform

> **AI-powered, multi-user skin diagnostics + chromatic color palette + head-to-toe outfit curation with live affiliate shopping links.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green)](https://fastapi.tiangolo.com)
[![Multi-User](https://img.shields.io/badge/Users-Multi--User-purple)](https://github.com/Haswanth1510/hackthon)

---

## ✨ What it Does

1. **Live Face Scan** — MediaPipe 468-landmark facial geometry detection directly in browser.
2. **AI Skin Diagnostics** — Gemini Flash (primary) → Groq/Qwen (backup) vision models analyze:
   - Skin type, undertone, age estimate, face shape
   - Active skin concerns: acne, hyperpigmentation, dryness, dark circles, etc.
   - Seasonal chromatic color typology (*Warm Autumn, Deep Winter, Cool Summer*…)
3. **Chromatic Color Palette** — 6 best + 3 worst flattering colors for your exact skin melanin.
4. **Head-to-Toe Outfit Curation** — 5 apparel pieces (Hat → Shoes) in your diagnosed flattering colors, scaled to your **preferred budget price** (₹1,500–₹15,000).
5. **Live Affiliate Shopping** — Every garment links directly to Amazon India + Flipkart search results with affiliate tracking.

---

## 🚀 Multi-User Architecture

- **JWT Authentication** — Each user gets a signed 7-day Bearer token. All data (scans, outfits, progress) is **isolated by user_id**.
- **Per-User Rate Limiting** — Maximum 10 scan requests per 60-second window per user (or IP for unauthenticated). Returns HTTP 429 with retry timing.
- **AI Concurrency Semaphore** — Max 5 simultaneous Gemini/Groq vision calls. Additional requests queue transparently — no dropped requests.
- **SQLite WAL Mode** — Write-Ahead Logging lets unlimited concurrent readers execute alongside any writer. `busy_timeout = 10s` handles lock contention.
- **Stateless API** — All user state lives in the database. The backend can be horizontally scaled behind a load balancer (swap to PostgreSQL for production).

---

## 🛠️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Haswanth1510/hackthon.git
cd hackthon
```

### 2. Create and activate Python virtual environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env and fill in your API keys:
#   GEMINI_API_KEY  — https://aistudio.google.com/app/apikey
#   GROK_API_KEY    — https://console.groq.com/keys
#   ROBOFLOW_API_KEY — https://roboflow.com
```

### 5. Run the server
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8008 --reload
```

### 6. Open in browser
```
http://127.0.0.1:8008
```

---

## 📡 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register` | No | Create new account |
| `POST` | `/api/auth/login` | No | Login, get JWT token |
| `GET` | `/api/auth/me` | JWT | Get current user profile |
| `PUT` | `/api/auth/profile` | JWT | Update profile & budgets |
| `POST` | `/api/skin/analyze` | Optional | Run full skin + outfit scan |
| `GET` | `/api/scans/history` | JWT | Scan history for user |
| `GET` | `/api/scans/progress` | JWT | Trend analysis over time |
| `POST` | `/api/fashion/outfit` | Optional | Generate outfit for occasion |
| `POST` | `/api/purchases/click` | JWT | Track affiliate click |
| `GET` | `/api/health` | No | Health + concurrency status |

---

## 🌐 Multi-User Deployment (Production)

For production deployment with multiple concurrent users:

```bash
# Run with multiple worker processes (uses multiprocessing for true parallelism)
python -m uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 8008 \
  --workers 4 \
  --proxy-headers \
  --forwarded-allow-ips="*"
```

> **Note**: When using multiple `--workers`, switch from SQLite to PostgreSQL (update `backend/database.py`) so all processes share a single connection pool.

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Google Gemini Flash API key (primary AI) |
| `GEMINI_MODEL` | No | Model name (default: `gemini-2.0-flash-lite`) |
| `GROK_API_KEY` | ✅ | Groq Cloud API key (backup AI) |
| `ROBOFLOW_API_KEY` | ✅ | Roboflow skin detection API key |
| `JWT_SECRET` | ✅ | Random secret string for JWT signing |
| `AMAZON_AFFILIATE_TAG` | No | Amazon India affiliate tag |
| `FLIPKART_AFFILIATE_ID` | No | Flipkart affiliate ID |
| `PORT` | No | Server port (default: 8008) |

---

## 🏗️ Project Structure

```
hackthon/
├── backend/
│   ├── main.py              # FastAPI app, multi-user rate limiting, AI semaphore
│   ├── auth.py              # JWT auth, PBKDF2 password hashing
│   ├── database.py          # SQLite WAL mode, multi-user concurrency config
│   ├── models.py            # Pydantic request/response models
│   └── services/
│       ├── grok_service.py  # Gemini (primary) + Groq (backup) AI vision
│       ├── fashion_service.py # Chromatic color-matched outfit curation
│       ├── product_service.py # Skincare affiliate matching
│       ├── landmark_service.py # MediaPipe face geometry
│       └── roboflow_service.py # Skin lesion detection
├── frontend/
│   ├── index.html           # Single-page application
│   ├── css/style.css        # Dark-mode, glassmorphism design
│   └── js/
│       ├── app.js           # Main app controller
│       ├── api.js           # API client with JWT header
│       └── camera.js        # WebRTC camera & MediaPipe
├── .env.example             # Template for environment config
├── requirements.txt         # Python dependencies
└── README.md
```

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.
