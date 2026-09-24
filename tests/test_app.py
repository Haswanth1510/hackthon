import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db, init_db
from backend.services.grok_service import GrokSkinService

class TestSkincareFashionAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ALLOW_MOCK_FALLBACK"] = "true"
        init_db()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM face_embeddings WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%')")
            cursor.execute("DELETE FROM users WHERE email LIKE 'test_%'")
        cls.client = TestClient(app)
        cls.test_email = f"test_{os.getpid()}@example.com"
        cls.test_password = "SecurePassword123!"

    def test_01_health(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("database", data)

    def test_02_register_and_login(self):
        # Register with credentials only (no age/gender requested during registration)
        reg_payload = {
            "email": self.test_email,
            "password": self.test_password,
            "full_name": "Aria Sharma"
        }
        resp = self.client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["email"], self.test_email)
        self.token = data["access_token"]

        # Post-authentication: User provides age, gender, and budget preferences
        prof_resp = self.client.put(
            "/api/auth/profile",
            json={"gender": "female", "age": 24, "budget_skincare": 2500.0, "budget_fashion": 4000.0},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(prof_resp.status_code, 200)
        prof_data = prof_resp.json()
        self.assertEqual(prof_data["gender"], "female")
        self.assertEqual(prof_data["age"], 24)

        # Duplicate register should fail
        resp_dup = self.client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(resp_dup.status_code, 400)

        # Login
        login_payload = {
            "email": self.test_email,
            "password": self.test_password
        }
        login_resp = self.client.post("/api/auth/login", json=login_payload)
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("access_token", login_resp.json())

    def test_03_auth_credential_validation(self):
        # Invalid password returns 401
        bad_pass_resp = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "wrongpassword123"
        })
        self.assertEqual(bad_pass_resp.status_code, 401)

        # Invalid email returns 401
        bad_email_resp = self.client.post("/api/auth/login", json={
            "email": "nonexistent_user_999@example.com",
            "password": "anyPassword123"
        })
        self.assertEqual(bad_email_resp.status_code, 401)

    def test_04_skin_analysis_and_budget_matching(self):
        login_resp = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Send skin analysis
        scan_payload = {
            "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP...",
            "landmarks": [{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(50)],
            "budget_skincare": 2000.0,
            "budget_fashion": 3500.0
        }
        scan_resp = self.client.post("/api/skin/analyze", json=scan_payload, headers=headers)
        self.assertEqual(scan_resp.status_code, 200)
        data = scan_resp.json()
        self.assertIn("scan_id", data)
        self.assertIn("issues", data)
        self.assertGreater(len(data["issues"]), 0)
        self.assertIn("recommendations", data)
        self.assertIn("am_routine", data)
        self.assertIn("pm_routine", data)
        self.assertIn("outfit", data)
        self.assertIn("image_data", data)
        self.assertTrue(any(item["item_type"] == "Headwear" for item in data["outfit"]["items"]))

        # Check all recommendations are within individual budget
        for rec in data["recommendations"]:
            self.assertLessEqual(rec["price_inr"], 2000.0)
            self.assertIn(rec["platform"], ["Amazon", "Flipkart"])

    def test_05_fashion_outfit_generator(self):
        login_resp = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        outfit_payload = {
            "occasion": "Casual",
            "style_preference": "Minimalist Streetwear",
            "budget_inr": 3000.0
        }
        outfit_resp = self.client.post("/api/fashion/outfit", json=outfit_payload, headers=headers)
        self.assertEqual(outfit_resp.status_code, 200)
        data = outfit_resp.json()
        self.assertLessEqual(data["total_cost_inr"], 3000.0)
        self.assertGreater(len(data["items"]), 0)
        self.assertIn("palette", data)
        self.assertIn("styling_tips", data)

    def test_06_progress_tracker_and_purchases(self):
        login_resp = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Track a product click
        click_payload = {
            "product_name": "Minimalist 2% Salicylic Acid Cleanser",
            "platform": "Amazon",
            "price_inr": 299.0,
            "product_url": "https://www.amazon.in/s?k=Minimalist+Cleanser",
            "category": "Cleanser"
        }
        click_resp = self.client.post("/api/purchases/click", json=click_payload, headers=headers)
        self.assertEqual(click_resp.status_code, 200)

        # Get purchases
        purchases_resp = self.client.get("/api/purchases", headers=headers)
        self.assertEqual(purchases_resp.status_code, 200)
        self.assertGreater(len(purchases_resp.json()), 0)

        # Get progress trends
        progress_resp = self.client.get("/api/scans/progress", headers=headers)
        self.assertEqual(progress_resp.status_code, 200)
        self.assertGreater(progress_resp.json()["scans_count"], 0)

    def test_07_change_password_and_security(self):
        login_resp = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt change password with wrong old password -> 400
        fail_resp = self.client.post("/api/auth/change-password", json={
            "old_password": "WrongPassword999!",
            "new_password": "NewSecurePassword456!"
        }, headers=headers)
        self.assertEqual(fail_resp.status_code, 400)

        # Successfully change password
        succ_resp = self.client.post("/api/auth/change-password", json={
            "old_password": self.test_password,
            "new_password": "NewSecurePassword456!"
        }, headers=headers)
        self.assertEqual(succ_resp.status_code, 200)
        self.assertEqual(succ_resp.json()["status"], "success")

        # Verify old password no longer works
        old_login = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(old_login.status_code, 401)

        # Verify new password works
        new_login = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "NewSecurePassword456!"
        })
        self.assertEqual(new_login.status_code, 200)

        # Restore original password so subsequent tests can authenticate cleanly
        restore_resp = self.client.post("/api/auth/change-password", json={
            "old_password": "NewSecurePassword456!",
            "new_password": self.test_password
        }, headers={"Authorization": f"Bearer {new_login.json()['access_token']}"})
        self.assertEqual(restore_resp.status_code, 200)

    def test_08_get_current_user_profile(self):
        login_resp = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Verify profile endpoint
        me_resp = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["email"], self.test_email)
        self.assertEqual(me_resp.json()["full_name"], "Aria Sharma")

    def test_09_skin_analysis_dynamic_scoring_and_telemetry(self):
        login_resp = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        import io
        import base64
        from PIL import Image

        # Image A: Normal balanced tones (normal ambient lighting, luminance > 35)
        img_a = Image.new("RGB", (120, 120), (190, 160, 140))
        buf_a = io.BytesIO()
        img_a.save(buf_a, format="JPEG")
        b64_a = f"data:image/jpeg;base64,{base64.b64encode(buf_a.getvalue()).decode()}"

        # Image B: High erythema (excessive redness: 230, 70, 70)
        img_b = Image.new("RGB", (120, 120), (230, 70, 70))
        buf_b = io.BytesIO()
        img_b.save(buf_b, format="JPEG")
        b64_b = f"data:image/jpeg;base64,{base64.b64encode(buf_b.getvalue()).decode()}"

        with patch.object(GrokSkinService, "_call_gemini_vision", return_value=None), \
             patch.object(GrokSkinService, "_call_grok_vision", return_value=None):
            resp_a = self.client.post("/api/skin/analyze", json={
                "image_base64": b64_a,
                "landmarks": [{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(50)]
            }, headers=headers)
            self.assertEqual(resp_a.status_code, 200)
            data_a = resp_a.json()

            resp_b = self.client.post("/api/skin/analyze", json={
                "image_base64": b64_b,
                "landmarks": [{"x": 0.5, "y": 0.5, "z": 0.0} for _ in range(50)]
            }, headers=headers)
            self.assertEqual(resp_b.status_code, 200)
            data_b = resp_b.json()

        score_a = data_a["overall_score"]
        score_b = data_b["overall_score"]

        # Scores should be in valid clinical range 40-95
        self.assertTrue(40 <= score_a <= 95, f"Score A {score_a} out of range")
        self.assertTrue(40 <= score_b <= 95, f"Score B {score_b} out of range")

        # Image with high erythema should receive a significantly lower health score than balanced image
        self.assertGreater(score_a, score_b, f"Score A ({score_a}) should be higher than erythematous Score B ({score_b})")

        # Normal lighting image must NOT be labeled dark or underexposed in summary
        self.assertNotIn("dark environment", data_a["summary"].lower())
        self.assertNotIn("underexposed", data_a["summary"].lower())

if __name__ == "__main__":
    unittest.main()
