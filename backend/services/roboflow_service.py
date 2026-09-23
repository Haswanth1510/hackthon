import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import io
import base64
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# Ensure root directory is importable for inference_sdk
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from inference_sdk import InferenceHTTPClient, InferenceConfiguration
except ImportError:
    InferenceHTTPClient = None
    InferenceConfiguration = None

logger = logging.getLogger("roboflow_service")

ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "ZY76QlWEaZ2kntzMzf37")
ROBOFLOW_MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID", "skin-problem-detection-multiple-clean/2")
ROBOFLOW_API_URL = os.getenv("ROBOFLOW_API_URL", "https://serverless.roboflow.com")


class RoboflowSkinService:
    """
    Integrates with Roboflow Serverless Inference API using model:
    'skin-problem-detection-multiple-clean/2' to detect granular facial lesions,
    including acne, pustules, blackheads, dark spots, and redness.
    """

    @classmethod
    def get_client(cls) -> Optional[Any]:
        if InferenceHTTPClient is None:
            logger.warning("InferenceHTTPClient could not be imported.")
            return None

        api_key = os.getenv("ROBOFLOW_API_KEY", ROBOFLOW_API_KEY)
        api_url = os.getenv("ROBOFLOW_API_URL", ROBOFLOW_API_URL)

        client = InferenceHTTPClient(api_url=api_url, api_key=api_key)
        if InferenceConfiguration is not None:
            client.configure(InferenceConfiguration(api_key_transport="header"))
        return client

    @classmethod
    def _map_coordinates_to_zone(cls, norm_x: float, norm_y: float) -> str:
        """
        Maps normalized center coordinates (0.0 to 1.0) of a detected lesion to an anatomical facial zone.
        """
        if norm_y < 0.33:
            return "Forehead"
        elif norm_y < 0.48:
            if 0.20 <= norm_x <= 0.45:
                return "Left Periorbital / Under-Eye"
            elif 0.55 <= norm_x <= 0.80:
                return "Right Periorbital / Under-Eye"
            else:
                return "Glabella & Upper Bridge"
        elif norm_y < 0.72:
            if 0.38 <= norm_x <= 0.62:
                return "Nose & T-Zone"
            elif norm_x < 0.38:
                return "Left Cheek"
            else:
                return "Right Cheek"
        else:
            if 0.35 <= norm_x <= 0.65:
                return "Chin"
            elif norm_x < 0.35:
                return "Left Jawline"
            else:
                return "Right Jawline"

    @classmethod
    def _format_predictions(cls, predictions: List[Dict[str, Any]], img_w: int, img_h: int) -> List[Dict[str, Any]]:
        formatted = []
        for pred in predictions:
            cx = float(pred.get("x", 0))
            cy = float(pred.get("y", 0))
            w = float(pred.get("width", 0))
            h = float(pred.get("height", 0))
            conf = float(pred.get("confidence", 0.0))
            cls_name = pred.get("class", "Skin Lesion")

            norm_x = max(0.0, min(1.0, cx / img_w)) if img_w > 0 else 0.5
            norm_y = max(0.0, min(1.0, cy / img_h)) if img_h > 0 else 0.5
            norm_w = max(0.0, min(1.0, w / img_w)) if img_w > 0 else 0.1
            norm_h = max(0.0, min(1.0, h / img_h)) if img_h > 0 else 0.1

            x_min = max(0.0, cx - (w / 2.0))
            y_min = max(0.0, cy - (h / 2.0))

            zone = cls._map_coordinates_to_zone(norm_x, norm_y)

            if conf >= 0.75:
                severity = "moderate" if norm_w < 0.08 else "severe"
            elif conf >= 0.50:
                severity = "moderate"
            else:
                severity = "mild"

            formatted.append({
                "class": cls_name,
                "confidence": round(conf, 3),
                "x": round(cx, 1),
                "y": round(cy, 1),
                "width": round(w, 1),
                "height": round(h, 1),
                "x_min": round(x_min, 1),
                "y_min": round(y_min, 1),
                "norm_x": round(norm_x, 4),
                "norm_y": round(norm_y, 4),
                "norm_width": round(norm_w, 4),
                "norm_height": round(norm_h, 4),
                "zone": zone,
                "severity": severity,
                "detection_id": pred.get("detection_id", "")
            })

        return formatted

    @classmethod
    def _get_image_dimensions(cls, image_data: Union[str, bytes, Image.Image]) -> tuple[int, int]:
        try:
            if isinstance(image_data, Image.Image):
                return image_data.size
            elif isinstance(image_data, str):
                clean_b64 = image_data.split(",")[-1] if "," in image_data else image_data
                raw = base64.b64decode(clean_b64)
                with Image.open(io.BytesIO(raw)) as img:
                    return img.size
            elif isinstance(image_data, bytes):
                with Image.open(io.BytesIO(image_data)) as img:
                    return img.size
        except Exception:
            pass
        return 640, 640

    @classmethod
    async def detect_skin_issues_async(
        cls,
        image: Union[str, bytes, Image.Image],
        model_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Asynchronously sends image to Roboflow Inference API and returns parsed bounding box detections.
        """
        model = model_id or os.getenv("ROBOFLOW_MODEL_ID", ROBOFLOW_MODEL_ID)
        client = cls.get_client()
        if not client:
            return []

        try:
            img_w, img_h = cls._get_image_dimensions(image)
            resp = await client.infer_async(image, model_id=model)

            predictions = resp.get("predictions", [])
            # In case image dimensions were returned by Roboflow response
            if "image" in resp and isinstance(resp["image"], dict):
                img_w = resp["image"].get("width", img_w)
                img_h = resp["image"].get("height", img_h)

            return cls._format_predictions(predictions, img_w, img_h)
        except Exception as e:
            logger.warning(f"[RoboflowSkinService] Async inference error: {e}. Gracefully returning empty detections.")
            return []

    @classmethod
    def detect_skin_issues(
        cls,
        image: Union[str, bytes, Image.Image],
        model_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Synchronous inference call to Roboflow Inference API.
        """
        model = model_id or os.getenv("ROBOFLOW_MODEL_ID", ROBOFLOW_MODEL_ID)
        client = cls.get_client()
        if not client:
            return []

        try:
            img_w, img_h = cls._get_image_dimensions(image)
            resp = client.infer(image, model_id=model)

            predictions = resp.get("predictions", [])
            if "image" in resp and isinstance(resp["image"], dict):
                img_w = resp["image"].get("width", img_w)
                img_h = resp["image"].get("height", img_h)

            return cls._format_predictions(predictions, img_w, img_h)
        except Exception as e:
            logger.warning(f"[RoboflowSkinService] Sync inference error: {e}. Gracefully returning empty detections.")
            return []

    @classmethod
    def summarize_detections(cls, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarizes detection counts, classes, and affected anatomical zones.
        """
        class_counts: Dict[str, int] = {}
        zones: set[str] = set()

        for d in detections:
            c = d.get("class", "Skin Issue")
            class_counts[c] = class_counts.get(c, 0) + 1
            zones.add(d.get("zone", "Face"))

        return {
            "total_detections": len(detections),
            "class_counts": class_counts,
            "affected_zones": sorted(list(zones)),
            "has_lesions": len(detections) > 0
        }
