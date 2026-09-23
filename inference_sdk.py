"""
inference_sdk module providing InferenceHTTPClient and InferenceConfiguration
Compatible with Roboflow Serverless Inference API.
"""

import os
import io
import base64
from typing import Union, Dict, Any, Optional
import httpx
from PIL import Image

class InferenceConfiguration:
    def __init__(self, api_key_transport: str = "header"):
        self.api_key_transport = api_key_transport

class InferenceHTTPClient:
    def __init__(self, api_url: str = "https://serverless.roboflow.com", api_key: Optional[str] = None):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key or os.getenv("ROBOFLOW_API_KEY", "")
        self.config = InferenceConfiguration()

    def configure(self, config: InferenceConfiguration) -> "InferenceHTTPClient":
        self.config = config
        return self

    def _prepare_image_b64(self, image: Union[str, bytes, Image.Image]) -> str:
        if isinstance(image, str):
            if os.path.exists(image):
                with open(image, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            # If it's a data url or raw base64 string
            if "," in image:
                return image.split(",")[-1]
            return image
        elif isinstance(image, bytes):
            return base64.b64encode(image).decode("utf-8")
        elif isinstance(image, Image.Image):
            buf = io.BytesIO()
            image.convert("RGB").save(buf, format="JPEG", quality=90)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        else:
            raise ValueError(f"Unsupported image input type: {type(image)}")

    def infer(self, image: Union[str, bytes, Image.Image], model_id: str = "skin-problem-detection-multiple-clean/2") -> Dict[str, Any]:
        clean_b64 = self._prepare_image_b64(image)
        url = f"{self.api_url}/{model_id}?api_key={self.api_key}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "api-key": self.api_key,
            "x-api-key": self.api_key
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, content=clean_b64)
            if resp.status_code == 200:
                return resp.json()
            else:
                # Fallback to detect.roboflow.com if serverless returns error
                alt_url = f"https://detect.roboflow.com/{model_id}?api_key={self.api_key}"
                resp_alt = client.post(alt_url, headers=headers, content=clean_b64)
                if resp_alt.status_code == 200:
                    return resp_alt.json()
                resp.raise_for_status()
                return {}

    async def infer_async(self, image: Union[str, bytes, Image.Image], model_id: str = "skin-problem-detection-multiple-clean/2") -> Dict[str, Any]:
        clean_b64 = self._prepare_image_b64(image)
        url = f"{self.api_url}/{model_id}?api_key={self.api_key}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "api-key": self.api_key,
            "x-api-key": self.api_key
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, content=clean_b64)
            if resp.status_code == 200:
                return resp.json()
            else:
                alt_url = f"https://detect.roboflow.com/{model_id}?api_key={self.api_key}"
                resp_alt = await client.post(alt_url, headers=headers, content=clean_b64)
                if resp_alt.status_code == 200:
                    return resp_alt.json()
                resp.raise_for_status()
                return {}
