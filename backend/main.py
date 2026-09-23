import os
import json
import time
import asyncio
import collections
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any

# Ensure standard MIME types are explicitly registered in minimal Linux environments
mimetypes.init()
mimetypes.add_type("text/html", ".html")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("audio/wav", ".wav")

from fastapi import FastAPI, Depends, HTTPException, Request, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse

from backend.database import init_db, get_db
from backend.models import (
    UserRegisterRequest, UserLoginRequest,
    UserProfileUpdate, ChangePasswordRequest, UserResponse, TokenResponse,
    SkinScanRequest, SkinAnalysisResponse, SkinIssueModel,
    ProductRecommendation, OutfitRequest, OutfitResponse,
    PurchaseRequest, PurchaseResponse
)
from backend.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_current_user
)
from backend.services.grok_service import GrokSkinService
from backend.services.landmark_service import LandmarkService
from backend.services.product_service import ProductService
from backend.services.fashion_service import FashionService
from backend.services.roboflow_service import RoboflowSkinService

# Initialize SQLite database schema
init_db()

# ─── Multi-User Concurrency Controls ────────────────────────────────────────────
# Limits simultaneous AI vision calls to prevent API rate-limit cascades.
# Each Gemini/Groq call uses 1 slot; others queue behind it transparently.
AI_SEMAPHORE = asyncio.Semaphore(5)   # max 5 concurrent AI calls across all users

# Per-user rate limiter: tracks last N request timestamps per user IP / user_id
# Prevents a single user from flooding the /analyze endpoint.
_rate_limit_store: Dict[str, collections.deque] = {}
_rate_limit_lock = asyncio.Lock()

RATE_LIMIT_REQUESTS = 10    # max requests per window
RATE_LIMIT_WINDOW_SECONDS = 60  # per 60-second sliding window

async def check_rate_limit(key: str):
    """Enforce per-user sliding-window rate limit."""
    async with _rate_limit_lock:
        now = time.time()
        if key not in _rate_limit_store:
            _rate_limit_store[key] = collections.deque()
        q = _rate_limit_store[key]
        # Purge timestamps outside the window
        while q and now - q[0] > RATE_LIMIT_WINDOW_SECONDS:
            q.popleft()
        if len(q) >= RATE_LIMIT_REQUESTS:
            wait_secs = int(RATE_LIMIT_WINDOW_SECONDS - (now - q[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit reached. You can make {RATE_LIMIT_REQUESTS} scan requests per minute. Please wait {wait_secs}s."
            )
        q.append(now)
# ────────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Stylic.AI — Skin & Style Intelligence API",
    description="Multi-user AI platform combining MediaPipe facial scanning, Gemini/Groq clinical skin analysis, and Amazon/Flipkart chromatic outfit curation.",
    version="2.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# --- SYSTEM & HEALTH CHECK ---
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": time.time(),
        "database": "sqlite3_wal_ready",
        "ai_engine": "gemini_primary_groq_backup",
        "multi_user": True,
        "ai_concurrency_slots": AI_SEMAPHORE._value
    }

# --- AUTHENTICATION (PRIMARY: EMAIL/PASSWORD, SECONDARY: FACENET) ---


@app.post("/api/auth/register", response_model=TokenResponse)
async def register(req: UserRegisterRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (req.email.lower(),))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        pwd_hash = hash_password(req.password)
        cursor.execute("""
            INSERT INTO users (email, password_hash, full_name, gender, age, budget_skincare, budget_fashion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            req.email.lower(), pwd_hash, req.full_name, req.gender or "unspecified",
            req.age or 25, req.budget_skincare or 2000.0, req.budget_fashion or 3500.0
        ))
        user_id = cursor.lastrowid

        token = create_access_token(user_id, req.email.lower())
        user_resp = UserResponse(
            id=user_id,
            email=req.email.lower(),
            full_name=req.full_name,
            gender=req.gender or "unspecified",
            age=req.age or 25,
            budget_skincare=req.budget_skincare or 2000.0,
            budget_fashion=req.budget_fashion or 3500.0,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        return TokenResponse(access_token=token, user=user_resp)

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(req: UserLoginRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (req.email.lower(),))
        row = cursor.fetchone()
        if not row or not verify_password(row["password_hash"], req.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_id = row["id"]
        token = create_access_token(user_id, row["email"])
        user_resp = UserResponse(
            id=user_id,
            email=row["email"],
            full_name=row["full_name"],
            gender=row["gender"],
            age=row["age"],
            budget_skincare=row["budget_skincare"],
            budget_fashion=row["budget_fashion"],
            created_at=str(row["created_at"])
        )
        return TokenResponse(access_token=token, user=user_resp)

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(user: Dict[str, Any] = Depends(require_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user["id"],))
        u = cursor.fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=u["id"],
        email=u["email"],
        full_name=u["full_name"],
        gender=u["gender"],
        age=u["age"],
        budget_skincare=u["budget_skincare"],
        budget_fashion=u["budget_fashion"],
        created_at=str(u["created_at"])
    )

@app.post("/api/auth/change-password")
async def change_password(req: ChangePasswordRequest, user: Dict[str, Any] = Depends(require_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],))
        row = cursor.fetchone()
        if not row or not verify_password(row["password_hash"], req.old_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        new_hash = hash_password(req.new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user["id"]))
    return {"status": "success", "message": "Password updated successfully"}

@app.put("/api/auth/profile", response_model=UserResponse)
async def update_profile(req: UserProfileUpdate, user: Dict[str, Any] = Depends(require_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        if req.full_name is not None:
            updates.append("full_name = ?")
            params.append(req.full_name)
        if req.gender is not None:
            updates.append("gender = ?")
            params.append(req.gender)
        if req.age is not None:
            updates.append("age = ?")
            params.append(req.age)
        if req.budget_skincare is not None:
            updates.append("budget_skincare = ?")
            params.append(req.budget_skincare)
        if req.budget_fashion is not None:
            updates.append("budget_fashion = ?")
            params.append(req.budget_fashion)

        if updates:
            params.append(user["id"])
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)

        cursor.execute("SELECT * FROM users WHERE id = ?", (user["id"],))
        updated_row = dict(cursor.fetchone())

        return UserResponse(
            id=updated_row["id"],
            email=updated_row["email"],
            full_name=updated_row["full_name"],
            gender=updated_row["gender"],
            age=updated_row["age"],
            budget_skincare=updated_row["budget_skincare"],
            budget_fashion=updated_row["budget_fashion"],
            created_at=str(updated_row["created_at"])
        )

# --- SKIN ANALYSIS & GEMINI/GROQ INTEGRATION ---

@app.post("/api/skin/analyze", response_model=SkinAnalysisResponse)
async def analyze_skin(
    req: SkinScanRequest,
    http_request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    user_id = current_user["id"] if current_user else None
    skincare_budget = req.budget_skincare or (current_user["budget_skincare"] if current_user else 2000.0)

    # Per-user rate limiting: use user_id if authenticated, else client IP
    rate_key = f"user:{user_id}" if user_id else f"ip:{http_request.client.host}"
    await check_rate_limit(rate_key)

    # Validate that a user/face is actually visible
    has_landmarks = req.landmarks and len(req.landmarks) >= 30
    has_valid_image = req.image_base64 and len(req.image_base64) > 1000
    if not has_landmarks and not has_valid_image:
        raise HTTPException(
            status_code=400,
            detail="No face detected in scan viewport. Please look directly at the camera or upload a clear facial portrait."
        )

    # 1. Process facial geometry through MediaPipe LandmarkService
    face_geometry = LandmarkService.analyze_face_geometry(req.landmarks or [])

    # 2. Detect skin lesions via Roboflow (runs concurrently with landmark analysis)
    roboflow_detections = await RoboflowSkinService.detect_skin_issues_async(req.image_base64)

    # 3. Analyze skin via Gemini (primary) → Groq (backup) under AI concurrency semaphore
    user_context = {
        "age": current_user["age"] if current_user else 25,
        "gender": current_user["gender"] if current_user else "unspecified",
        "notes": req.notes or ""
    }
    async with AI_SEMAPHORE:
        diagnosis = await GrokSkinService.analyze_skin(
            image_base64=req.image_base64,
            landmarks_telemetry=face_geometry,
            user_context=user_context,
            roboflow_detections=roboflow_detections
        )

    # Strict Human Face Verification:
    # Reject non-human subjects (monkeys, animals, objects)
    if diagnosis.get("is_human_face") is False:
        err_msg = diagnosis.get("error") or "Non-human subject detected. Stylic.AI clinical scanner is calibrated strictly for living human beings. Please upload or scan a clear human facial portrait."
        raise HTTPException(status_code=400, detail=err_msg)

    # 4. AI-driven product matching: use AI's recommended ingredients + detected issues
    matched_products = ProductService.match_products(
        detected_issues=diagnosis.get("issues", []),
        max_budget_inr=req.budget_skincare if (req.budget_skincare and req.budget_skincare > 0) else None,
        skin_type=diagnosis.get("skin_type", "Combination"),
        recommended_ingredients=diagnosis.get("recommended_ingredients", []),
    )

    # 5. Generate complete Head-to-Toe outfit (Hat to Shoes)
    fashion_budget = req.budget_fashion if (req.budget_fashion and req.budget_fashion > 0) else None
    color_palette = diagnosis.get("color_palette")
    outfit_data = await FashionService.recommend_outfit(
        occasion="Casual",
        skin_undertone=diagnosis.get("undertone", "Neutral Warm"),
        face_shape=diagnosis.get("face_shape", face_geometry.get("face_shape", "Oval")),
        gender=user_context["gender"],
        budget_inr=fashion_budget,
        style_preference="Modern Minimalist",
        color_palette=color_palette
    )

    # 6. Save record to Database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scans (user_id, overall_score, skin_type, undertone, age_estimate, face_shape, raw_telemetry)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            diagnosis.get("overall_score", 78),
            diagnosis.get("skin_type", "Combination"),
            diagnosis.get("undertone", "Neutral Warm"),
            diagnosis.get("age_estimate", 25),
            diagnosis.get("face_shape", face_geometry.get("face_shape", "Oval")),
            json.dumps({
                "landmarks_count": len(req.landmarks or []),
                "notes": req.notes or "",
                "roboflow_detections_count": len(roboflow_detections),
                "color_palette": color_palette
            })
        ))
        scan_id = cursor.lastrowid

        # Insert issues
        for issue in diagnosis.get("issues", []):
            cursor.execute("""
                INSERT INTO skin_issues (scan_id, issue_type, severity, score, zone, description, precautions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_id,
                issue.get("issue_type", "Skin Concern"),
                issue.get("severity", "mild"),
                issue.get("score", 50),
                issue.get("zone", "Face"),
                issue.get("description", ""),
                json.dumps(issue.get("precautions", []))
            ))

        # Insert recommendations
        for prod in matched_products:
            cursor.execute("""
                INSERT INTO recommendations (scan_id, category, title, brand, price_inr, platform, product_url, image_url, rating, reason, target_issue)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_id,
                prod["category"],
                prod["title"],
                prod["brand"],
                prod["price_inr"],
                prod["platform"],
                prod["product_url"],
                prod["image_url"],
                prod.get("rating", 4.5),
                prod.get("reason", ""),
                prod.get("target_issue", "")
            ))

    # Format response
    formatted_issues = [
        SkinIssueModel(
            issue_type=i["issue_type"],
            severity=i["severity"],
            score=i["score"],
            zone=i["zone"],
            description=i["description"],
            precautions=i["precautions"]
        )
        for i in diagnosis.get("issues", [])
    ]

    formatted_prods = [
        ProductRecommendation(
            category=p["category"],
            title=p["title"],
            brand=p["brand"],
            price_inr=p["price_inr"],
            platform=p["platform"],
            product_url=p["product_url"],
            image_url=p["image_url"],
            rating=p.get("rating", 4.5),
            reason=p["reason"],
            target_issue=p.get("target_issue")
        )
        for p in matched_products
    ]

    outfit_resp = OutfitResponse(
        outfit_id=0,
        occasion=outfit_data["occasion"],
        style_name=outfit_data["style_name"],
        undertone_match=outfit_data["undertone_match"],
        total_cost_inr=outfit_data["total_cost_inr"],
        budget_limit_inr=outfit_data["budget_limit_inr"],
        palette=outfit_data["palette"],
        items=outfit_data["items"],
        styling_tips=outfit_data["styling_tips"]
    )

    return SkinAnalysisResponse(
        scan_id=scan_id,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        overall_score=diagnosis.get("overall_score", 78),
        skin_type=diagnosis.get("skin_type", "Combination"),
        undertone=diagnosis.get("undertone", "Neutral Warm"),
        age_estimate=diagnosis.get("age_estimate", 25),
        face_shape=diagnosis.get("face_shape", "Oval"),
        summary=diagnosis.get("summary", "Complete facial diagnostic analysis finished."),
        image_data=req.image_base64,
        issues=formatted_issues,
        am_routine=diagnosis.get("am_routine", []),
        pm_routine=diagnosis.get("pm_routine", []),
        precautions=diagnosis.get("precautions", []),
        recommendations=formatted_prods,
        outfit=outfit_resp,
        roboflow_detections=roboflow_detections,
        color_palette=diagnosis.get("color_palette")
    )


# --- REAL-TIME PRODUCT MATCHING BY BUDGET ---
@app.post("/api/products/skincare")
async def match_skincare_products(payload: Dict[str, Any]):
    issues = payload.get("issues", [])
    max_budget = float(payload.get("max_budget_inr", 2000.0))
    skin_type = payload.get("skin_type", "Combination")
    
    products = ProductService.match_products(
        detected_issues=issues,
        max_budget_inr=max_budget,
        skin_type=skin_type
    )
    return {"products": products, "budget_limit": max_budget}

# --- SCAN HISTORY & PROGRESS TRACKING ---

@app.get("/api/scans/history")
async def get_scan_history(user: Dict[str, Any] = Depends(require_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, 
                   COUNT(i.id) as issues_count
            FROM scans s
            LEFT JOIN skin_issues i ON s.id = i.scan_id
            WHERE s.user_id = ?
            GROUP BY s.id
            ORDER BY s.timestamp DESC
        """, (user["id"],))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@app.get("/api/scans/progress")
async def get_progress_analytics(user: Dict[str, Any] = Depends(require_current_user)):
    """
    Computes progress trend over time across user's scans:
    Shows whether acne, hyperpigmentation, texture, and overall skin score improved.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, overall_score, skin_type
            FROM scans
            WHERE user_id = ?
            ORDER BY timestamp ASC
        """, (user["id"],))
        scans = cursor.fetchall()

        if not scans:
            return {"scans_count": 0, "trends": [], "metric_deltas": {}}

        trend_data = []
        for s in scans:
            cursor.execute("""
                SELECT issue_type, score, severity
                FROM skin_issues
                WHERE scan_id = ?
            """, (s["id"],))
            issues = cursor.fetchall()
            trend_data.append({
                "scan_id": s["id"],
                "timestamp": str(s["timestamp"]),
                "overall_score": s["overall_score"],
                "issues": {i["issue_type"]: i["score"] for i in issues}
            })

        # Calculate deltas between first and latest scan
        deltas = {}
        if len(trend_data) >= 2:
            first = trend_data[0]
            latest = trend_data[-1]
            deltas["overall_improvement"] = latest["overall_score"] - first["overall_score"]
            for issue_name, latest_val in latest["issues"].items():
                first_val = first["issues"].get(issue_name, latest_val)
                # Lower issue score means improvement
                deltas[issue_name] = round(first_val - latest_val, 1)

        return {
            "scans_count": len(scans),
            "trends": trend_data,
            "metric_deltas": deltas,
            "latest_score": trend_data[-1]["overall_score"]
        }

@app.get("/api/scans/{scan_id}")
async def get_scan_details(scan_id: int, user: Dict[str, Any] = Depends(require_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scans WHERE id = ? AND user_id = ?", (scan_id, user["id"]))
        scan = cursor.fetchone()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        cursor.execute("SELECT * FROM skin_issues WHERE scan_id = ?", (scan_id,))
        issues = [dict(i) for i in cursor.fetchall()]
        for issue in issues:
            if isinstance(issue["precautions"], str):
                issue["precautions"] = json.loads(issue["precautions"])

        cursor.execute("SELECT * FROM recommendations WHERE scan_id = ?", (scan_id,))
        recs = [dict(r) for r in cursor.fetchall()]

        return {
            "scan": dict(scan),
            "issues": issues,
            "recommendations": recs
        }

# --- FASHION & OUTFIT STYLING ---

@app.post("/api/fashion/outfit", response_model=OutfitResponse)
async def generate_outfit(req: OutfitRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    user_id = current_user["id"] if current_user else None
    budget = req.budget_inr or (current_user["budget_fashion"] if current_user else 3500.0)

    undertone = "Warm"
    face_shape = "Oval"
    scan_palette = None

    # Extract scan attributes if scan_id is provided
    if req.scan_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT undertone, face_shape, raw_telemetry FROM scans WHERE id = ?", (req.scan_id,))
            row = cursor.fetchone()
            if row:
                undertone = row["undertone"]
                face_shape = row["face_shape"]
                if row["raw_telemetry"]:
                    try:
                        t_data = json.loads(row["raw_telemetry"])
                        scan_palette = t_data.get("color_palette")
                    except Exception:
                        pass
    elif user_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, undertone, face_shape, raw_telemetry FROM scans WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
            row = cursor.fetchone()
            if row:
                undertone = row["undertone"]
                face_shape = row["face_shape"]
                if row["raw_telemetry"]:
                    try:
                        t_data = json.loads(row["raw_telemetry"])
                        scan_palette = t_data.get("color_palette")
                    except Exception:
                        pass

    outfit_data = await FashionService.recommend_outfit(
        occasion=req.occasion,
        skin_undertone=undertone,
        face_shape=face_shape,
        gender=current_user.get("gender", "unspecified") if current_user else "unspecified",
        budget_inr=budget,
        style_preference=req.style_preference or "Modern Minimalist",
        color_palette=scan_palette
    )

    outfit_id = 0
    if user_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO outfits (scan_id, user_id, occasion, style_name, total_cost_inr, palette_json, items_json, styling_tips)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req.scan_id, user_id, req.occasion, outfit_data["style_name"],
                outfit_data["total_cost_inr"], json.dumps(outfit_data["palette"]),
                json.dumps(outfit_data["items"]), "\n".join(outfit_data["styling_tips"])
            ))
            outfit_id = cursor.lastrowid

    return OutfitResponse(
        outfit_id=outfit_id,
        occasion=outfit_data["occasion"],
        style_name=outfit_data["style_name"],
        undertone_match=outfit_data["undertone_match"],
        total_cost_inr=outfit_data["total_cost_inr"],
        budget_limit_inr=outfit_data["budget_limit_inr"],
        palette=outfit_data["palette"],
        items=outfit_data["items"],
        styling_tips=outfit_data["styling_tips"]
    )

# --- PURCHASE & CLICK TRACKING ---

@app.post("/api/purchases/click", response_model=PurchaseResponse)
async def record_click(req: PurchaseRequest, user: Dict[str, Any] = Depends(require_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO purchases (user_id, product_name, platform, price_inr, product_url, category, status)
            VALUES (?, ?, ?, ?, ?, ?, 'clicked')
        """, (
            user["id"], req.product_name, req.platform, req.price_inr, req.product_url, req.category
        ))
        purchase_id = cursor.lastrowid

    return PurchaseResponse(
        id=purchase_id,
        product_name=req.product_name,
        platform=req.platform,
        price_inr=req.price_inr,
        status="clicked",
        created_at=time.strftime("%Y-%m-%d %H:%M:%S")
    )

@app.get("/api/purchases", response_model=List[PurchaseResponse])
async def get_user_purchases(user: Dict[str, Any] = Depends(require_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM purchases WHERE user_id = ? ORDER BY created_at DESC", (user["id"],))
        rows = cursor.fetchall()
        return [
            PurchaseResponse(
                id=r["id"],
                product_name=r["product_name"],
                platform=r["platform"],
                price_inr=r["price_inr"],
                status=r["status"],
                created_at=str(r["created_at"])
            )
            for r in rows
        ]

# --- STATIC FRONTEND DELIVERY ---

FRONTEND_DIR.mkdir(exist_ok=True)

@app.get("/")
@app.get("/index.html")
async def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    return JSONResponse({"message": "Stylic.AI backend running. Frontend not found.", "status": "ok"})

# Mount /static → frontend/ so that /static/js/app.js, /static/css/style.css, etc. all resolve.
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Also mount direct subpaths in case assets are requested directly without /static prefix
for sub in ["css", "js", "images"]:
    subdir = FRONTEND_DIR / sub
    if subdir.exists():
        app.mount(f"/{sub}", StaticFiles(directory=str(subdir)), name=sub)
