import math
from typing import List, Dict, Any

class LandmarkService:
    """
    Analyzes MediaPipe facial landmarks to extract geometric metrics,
    facial zones, and estimate face shape.
    """
    @staticmethod
    def analyze_face_geometry(landmarks: List[Dict[str, float]]) -> Dict[str, Any]:
        if not landmarks or len(landmarks) < 30:
            return {
                "face_shape": "Oval",
                "facial_proportions": {"aspect_ratio": 1.35},
                "zones_detected": ["Forehead", "Cheeks", "Nose", "Chin"],
                "has_human_landmarks": False
            }

        def pt(idx: int) -> Dict[str, float]:
            return landmarks[idx] if idx < len(landmarks) else landmarks[0]

        # Standard MediaPipe landmarks:
        # Top forehead: 10
        # Chin tip: 152
        # Left cheek outer: 234
        # Right cheek outer: 454
        # Left jaw angle: 58
        # Right jaw angle: 288
        p_top = pt(10)
        p_chin = pt(152)
        p_lcheek = pt(234)
        p_rcheek = pt(454)
        p_ljaw = pt(58)
        p_rjaw = pt(288)

        face_length = abs(p_chin.get("y", 0) - p_top.get("y", 0)) + 1e-6
        cheek_width = abs(p_rcheek.get("x", 0) - p_lcheek.get("x", 0)) + 1e-6
        jaw_width = abs(p_rjaw.get("x", 0) - p_ljaw.get("x", 0)) + 1e-6

        ratio_length_width = face_length / cheek_width
        ratio_jaw_cheek = jaw_width / cheek_width

        # Face Shape classification
        face_shape = "Oval"
        if ratio_length_width > 1.45:
            face_shape = "Oblong"
        elif ratio_length_width < 1.15:
            if ratio_jaw_cheek > 0.88:
                face_shape = "Square"
            else:
                face_shape = "Round"
        elif ratio_jaw_cheek < 0.75:
            face_shape = "Heart"
        elif ratio_jaw_cheek > 0.88 and ratio_length_width >= 1.2:
            face_shape = "Square"
        else:
            face_shape = "Oval"

        return {
            "face_shape": face_shape,
            "facial_proportions": {
                "length_to_width": round(ratio_length_width, 2),
                "jaw_to_cheek": round(ratio_jaw_cheek, 2)
            },
            "zones_detected": ["Forehead", "Left Cheek", "Right Cheek", "Nasal Bridge", "Chin", "Periorbital"],
            "has_human_landmarks": True
        }
