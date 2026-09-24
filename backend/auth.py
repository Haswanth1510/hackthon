import hashlib
import hmac
import os
import json
import base64
import time
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.database import get_db

SECRET_KEY = os.getenv("JWT_SECRET", "skincare_fashion_ai_super_secret_key_2026_xai")
ALGORITHM = "HS256"
TOKEN_EXPIRY_SECONDS = 86400 * 7  # 7 days

security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hashes password with PBKDF2-HMAC-SHA256 and unique salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}:{key.hex()}"

def verify_password(stored_password: str, provided_password: str) -> bool:
    """
    Verifies provided password against stored hash.
    Supports:
    1. PBKDF2-HMAC-SHA256 (salt_hex:key_hex)
    2. bcrypt ($2b$, $2a$, $2y$)
    3. Plain SHA-256 fallback for legacy migrations
    """
    if not stored_password or not provided_password:
        return False

    stored_password = stored_password.strip()

    # 1. Bcrypt hash check
    if stored_password.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            import bcrypt
            return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))
        except Exception as e:
            print(f"[Auth Error] Bcrypt verification exception: {e}")
            return False

    # 2. PBKDF2-HMAC-SHA256 (salt:key)
    if ":" in stored_password:
        try:
            salt_hex, key_hex = stored_password.split(":", 1)
            salt = bytes.fromhex(salt_hex)
            expected_key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
            return hmac.compare_digest(expected_key.hex(), key_hex)
        except Exception as e:
            print(f"[Auth Error] PBKDF2 verification exception: {e}")

    # 3. Plain SHA-256 fallback
    try:
        sha256_hash = hashlib.sha256(provided_password.encode('utf-8')).hexdigest()
        if hmac.compare_digest(sha256_hash, stored_password):
            return True
    except Exception:
        pass

    return False

def create_access_token(user_id: int, email: str) -> str:
    """Generates signed payload token containing user_id and expiration."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS
    }
    header_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(SECRET_KEY.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_token(token: str) -> Dict[str, Any]:
    """Decodes and validates HMAC signature and expiration."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Malformed token")
        header_b64, payload_b64, sig_b64 = parts
        
        # Verify signature
        expected_sig = hmac.new(SECRET_KEY.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
        # Add padding back if necessary
        sig_b64_padded = sig_b64 + "=" * (-len(sig_b64) % 4)
        if not hmac.compare_digest(base64.urlsafe_b64decode(sig_b64_padded), expected_sig):
            raise ValueError("Signature mismatch")
        
        payload_b64_padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64_padded).decode())
        
        if payload.get("exp", 0) < time.time():
            raise ValueError("Token expired")
            
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """Dependency to extract authenticated user from Bearer token."""
    if not credentials:
        return None
    token = credentials.credentials
    payload = decode_token(token)
    user_id = int(payload["sub"])
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        return dict(row)

def require_current_user(user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency that requires user authentication."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user
