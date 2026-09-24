import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db
from backend.services.roboflow_service import RoboflowSkinService
from backend.services.grok_service import GrokSkinService


class TestRoboflowGrokIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ALLOW_MOCK_FALLBACK"] = "true"
        init_db()
        cls.client = TestClient(app)
        # 1x1 neutral grey dummy jpeg base64
        cls.dummy_b64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="

    def test_01_zone_mapping(self):
        """Verify normalized coordinate mapping to anatomical facial zones."""
        self.assertEqual(RoboflowSkinService._map_coordinates_to_zone(0.5, 0.2), "Forehead")
        self.assertEqual(RoboflowSkinService._map_coordinates_to_zone(0.3, 0.4), "Left Periorbital / Under-Eye")
        self.assertEqual(RoboflowSkinService._map_coordinates_to_zone(0.7, 0.4), "Right Periorbital / Under-Eye")
        self.assertEqual(RoboflowSkinService._map_coordinates_to_zone(0.5, 0.55), "Nose & T-Zone")
        self.assertEqual(RoboflowSkinService._map_coordinates_to_zone(0.2, 0.6), "Left Cheek")
        self.assertEqual(RoboflowSkinService._map_coordinates_to_zone(0.8, 0.6), "Right Cheek")
        self.assertEqual(RoboflowSkinService._map_coordinates_to_zone(0.5, 0.8), "Chin")
        self.assertEqual(RoboflowSkinService._map_coordinates_to_zone(0.2, 0.85), "Left Jawline")

    def test_02_format_predictions_and_summarize(self):
        """Verify parsing raw predictions into normalized detections and summaries."""
        raw_preds = [
            {
                "x": 320.0,
                "y": 120.0,
                "width": 30.0,
                "height": 30.0,
                "confidence": 0.88,
                "class": "acne",
                "detection_id": "det-1"
            },
            {
                "x": 480.0,
                "y": 360.0,
                "width": 25.0,
                "height": 25.0,
                "confidence": 0.65,
                "class": "dark spot",
                "detection_id": "det-2"
            }
        ]

        formatted = RoboflowSkinService._format_predictions(raw_preds, img_w=640, img_h=640)
        self.assertEqual(len(formatted), 2)
        self.assertEqual(formatted[0]["class"], "acne")
        self.assertEqual(formatted[0]["zone"], "Forehead")
        self.assertEqual(formatted[0]["severity"], "moderate")
        self.assertEqual(formatted[1]["class"], "dark spot")
        self.assertEqual(formatted[1]["zone"], "Right Cheek")

        summary = RoboflowSkinService.summarize_detections(formatted)
        self.assertEqual(summary["total_detections"], 2)
        self.assertEqual(summary["class_counts"]["acne"], 1)
        self.assertEqual(summary["class_counts"]["dark spot"], 1)
        self.assertTrue(summary["has_lesions"])

    def test_03_grok_format_roboflow_telemetry(self):
        """Verify Grok clinical prompt telemetry formatter handles Roboflow detections."""
        empty_text = GrokSkinService._format_roboflow_telemetry([])
        self.assertIn("No focal lesions detected", empty_text)

        mock_detections = [
            {"class": "pustule", "confidence": 0.92, "zone": "Left Cheek"},
            {"class": "pustule", "confidence": 0.85, "zone": "Left Cheek"},
            {"class": "blackhead", "confidence": 0.78, "zone": "Nose & T-Zone"}
        ]
        summary_text = GrokSkinService._format_roboflow_telemetry(mock_detections)
        self.assertIn("Total: 3 lesions", summary_text)
        self.assertIn("Pustule: 2 detected", summary_text)
        self.assertIn("Blackhead: 1 detected", summary_text)

    def test_04_grok_intelligent_diagnosis_integration(self):
        """Verify intelligent diagnosis incorporates Roboflow detections when offline or without API key."""
        mock_detections = [
            {"class": "acne", "confidence": 0.89, "zone": "Forehead", "norm_x": 0.5, "norm_y": 0.2, "norm_width": 0.05, "norm_height": 0.05},
            {"class": "dark spot", "confidence": 0.74, "zone": "Right Cheek", "norm_x": 0.75, "norm_y": 0.6, "norm_width": 0.04, "norm_height": 0.04}
        ]
        diag = GrokSkinService._generate_intelligent_diagnosis(
            image_base64=self.dummy_b64,
            landmarks={"face_shape": "Oval"},
            user_context={"age": 22, "gender": "female", "notes": "Focal breakouts"},
            roboflow_detections=mock_detections
        )

        self.assertIn("overall_score", diag)
        self.assertIn("issues", diag)
        self.assertIn("Clinical scan localized 2 focal lesion(s)", diag["summary"])

        # Check that issues mention localized detections
        acne_issue = next((i for i in diag["issues"] if "Acne" in i["issue_type"]), None)
        self.assertIsNotNone(acne_issue)
        self.assertIn("Clinical dermatological scan identified 1 active lesion", acne_issue["description"])

    def test_05_api_skin_analyze_endpoint_returns_roboflow_detections(self):
        """Verify /api/skin/analyze endpoint returns roboflow_detections in response."""
        mock_detections = [
            {
                "class": "acne",
                "confidence": 0.86,
                "x": 320.0,
                "y": 150.0,
                "width": 20.0,
                "height": 20.0,
                "norm_x": 0.5,
                "norm_y": 0.23,
                "norm_width": 0.03,
                "norm_height": 0.03,
                "zone": "Forehead",
                "severity": "moderate"
            }
        ]

        # Generate fake landmarks for validation
        fake_landmarks = [{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(50)]

        with patch.object(RoboflowSkinService, "detect_skin_issues_async", return_value=mock_detections), \
             patch.object(GrokSkinService, "_call_gemini_vision", return_value=None), \
             patch.object(GrokSkinService, "_call_grok_vision", return_value=None):
            resp = self.client.post("/api/skin/analyze", json={
                "image_base64": self.dummy_b64,
                "landmarks": fake_landmarks,
                "budget_skincare": 2000.0,
                "notes": "Testing Roboflow integration"
            })

            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("roboflow_detections", data)
            self.assertIsInstance(data["roboflow_detections"], list)
            self.assertEqual(len(data["roboflow_detections"]), 1)
            self.assertEqual(data["roboflow_detections"][0]["class"], "acne")
            self.assertEqual(data["roboflow_detections"][0]["zone"], "Forehead")


if __name__ == "__main__":
    unittest.main()
