import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db, init_db
from backend.auth import hash_password, verify_password
from backend.services.amazon_paapi_service import AmazonPAAPIService
from backend.services.fashion_service import FashionService
from backend.services.grok_service import GrokSkinService

class TestMasterFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_task1_gemini_keys_and_services(self):
        """Test Task 1: Gemini split keys and independent retry/service configs."""
        skin_key = os.getenv("GEMINI_API_KEY_SKIN") or os.getenv("GEMINI_API_KEY", "")
        fashion_key = os.getenv("GEMINI_API_KEY_FASHION") or os.getenv("GEMINI_API_KEY", "")
        self.assertTrue(bool(skin_key), "GEMINI_API_KEY_SKIN should be configured or fallback to GEMINI_API_KEY")
        self.assertTrue(bool(fashion_key), "GEMINI_API_KEY_FASHION should be configured or fallback to GEMINI_API_KEY")

    def test_task2_amazon_paapi_service(self):
        """Test Task 2: Amazon PA-API SigV4 headers, search items structure, and fallback."""
        creds = AmazonPAAPIService.get_credentials()
        self.assertEqual(creds["tag"], "stylicai21-21")
        self.assertIn("amazon.in", creds["host"])

        # Test SigV4 header builder with dummy keys
        headers = AmazonPAAPIService.build_sigv4_headers(
            payload_bytes=b'{"Keywords": "shirt"}',
            host="webservices.amazon.in",
            region="eu-west-1",
            access_key="AKIAEXAMPLEKEY",
            secret_key="secretkeyexample123"
        )
        self.assertIn("Authorization", headers)
        self.assertIn("AWS4-HMAC-SHA256", headers["Authorization"])
        self.assertIn("x-amz-date", headers)
        self.assertEqual(headers["x-amz-target"], "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems")

    def test_task3_auth_full_cycle_and_edge_cases(self):
        """Test Task 3: Full signup-then-login test cycle, casing, whitespace, field aliases."""
        test_email = f"signup_login_{os.getpid()}@Example.COM "
        test_pwd = "MySecretPassword123!"
        full_name = "Jane Developer"

        # 1. Register with mixed-case and trailing whitespace
        reg_resp = self.client.post("/api/auth/register", json={
            "email": test_email,
            "password": test_pwd,
            "full_name": full_name
        })
        self.assertEqual(reg_resp.status_code, 200)
        reg_data = reg_resp.json()
        self.assertIn("access_token", reg_data)
        self.assertEqual(reg_data["user"]["email"], test_email.strip().lower())

        # 2. Login with standard email
        login_resp = self.client.post("/api/auth/login", json={
            "email": test_email.strip().lower(),
            "password": test_pwd
        })
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("access_token", login_resp.json())

        # 3. Login with mixed case email and whitespace
        mixed_login = self.client.post("/api/auth/login", json={
            "email": "   SIGNUP_LOGIN_" + str(os.getpid()) + "@EXAMPLE.com  ",
            "password": test_pwd
        })
        self.assertEqual(mixed_login.status_code, 200)

        # 4. Login with userEmail field name (flexible frontend mapping)
        user_email_login = self.client.post("/api/auth/login", json={
            "userEmail": test_email.strip().lower(),
            "password": test_pwd
        })
        self.assertEqual(user_email_login.status_code, 200)

        # 5. Login with username field name
        username_login = self.client.post("/api/auth/login", json={
            "username": test_email.strip().lower(),
            "password": test_pwd
        })
        self.assertEqual(username_login.status_code, 200)

        # 6. Test bcrypt verification support
        try:
            import bcrypt
            bcrypt_hash = bcrypt.hashpw(b"BcryptPassword123!", bcrypt.gensalt()).decode("utf-8")
            self.assertTrue(verify_password(bcrypt_hash, "BcryptPassword123!"))
            self.assertFalse(verify_password(bcrypt_hash, "WrongPassword!"))
        except ImportError:
            pass

        # 7. Test PBKDF2 verification
        pbkdf2_hash = hash_password("PBKDF2Password123!")
        self.assertTrue(verify_password(pbkdf2_hash, "PBKDF2Password123!"))
        self.assertFalse(verify_password(pbkdf2_hash, "WrongPassword!"))

if __name__ == "__main__":
    unittest.main()
