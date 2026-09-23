import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

# --- Auth Models ---
class UserRegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    full_name: str
    gender: Optional[str] = "unspecified"
    age: Optional[int] = None
    budget_skincare: Optional[float] = 2000.0
    budget_fashion: Optional[float] = 3500.0

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v

class UserLoginRequest(BaseModel):
    email: str
    password: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    budget_skincare: Optional[float] = None
    budget_fashion: Optional[float] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    gender: Optional[str] = "unspecified"
    age: Optional[int] = 25
    budget_skincare: Optional[float] = 2000.0
    budget_fashion: Optional[float] = 3500.0
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Skin Diagnostic Models ---
class SkinIssueModel(BaseModel):
    issue_type: str
    severity: str  # mild, moderate, severe
    score: int = Field(..., ge=0, le=100)
    zone: str
    description: str
    precautions: List[str]

class ProductRecommendation(BaseModel):
    id: Optional[int] = None
    category: str
    title: str
    brand: str
    price_inr: float
    platform: str  # Amazon or Flipkart
    product_url: str
    image_url: str
    rating: float = 4.5
    reason: str
    target_issue: Optional[str] = None

class SkinScanRequest(BaseModel):
    image_base64: str
    landmarks: Optional[List[Dict[str, float]]] = None
    budget_skincare: Optional[float] = None
    budget_fashion: Optional[float] = None
    notes: Optional[str] = None

# --- Outfit & Styling Models ---
class OutfitItemModel(BaseModel):
    item_type: str  # Headwear, Topwear, Bottomwear, Footwear, Accessory
    name: str
    brand: str
    price_inr: float
    platform: str  # Amazon or Flipkart
    product_url: str
    image_url: str
    color_name: Optional[str] = None
    color_hex: Optional[str] = None

class OutfitRequest(BaseModel):
    scan_id: Optional[int] = None
    occasion: str = "Casual"  # Casual, Formal, Party, College, Date Night, Traditional
    style_preference: Optional[str] = "Modern Minimalist"
    budget_inr: Optional[float] = None

class OutfitResponse(BaseModel):
    outfit_id: int
    occasion: str
    style_name: str
    undertone_match: str
    total_cost_inr: float
    budget_limit_inr: float
    palette: List[str]
    items: List[OutfitItemModel]
    styling_tips: List[str]

class SkinAnalysisResponse(BaseModel):
    scan_id: int
    timestamp: str
    overall_score: int
    skin_type: str
    undertone: str
    age_estimate: int
    face_shape: str
    summary: str
    image_data: Optional[str] = None
    issues: List[SkinIssueModel]
    am_routine: List[str]
    pm_routine: List[str]
    precautions: List[str]
    recommendations: List[ProductRecommendation]
    outfit: Optional[OutfitResponse] = None
    roboflow_detections: Optional[List[Dict[str, Any]]] = None
    color_palette: Optional[Dict[str, Any]] = None

# --- Purchase Tracking ---
class PurchaseRequest(BaseModel):
    product_name: str
    platform: str
    price_inr: float
    product_url: Optional[str] = None
    category: Optional[str] = "Skincare"

class PurchaseResponse(BaseModel):
    id: int
    product_name: str
    platform: str
    price_inr: float
    status: str
    created_at: str
