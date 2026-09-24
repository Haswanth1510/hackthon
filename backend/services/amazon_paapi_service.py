import os
import json
import time
import hmac
import hashlib
import urllib.parse
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("amazon_paapi")

class AmazonPAAPIService:
    """
    Amazon Product Advertising API (PA-API 5.0) Client.
    Performs SearchItems operations with AWS Signature Version 4 (SigV4) signing.
    Extracts real product title, image, price, and affiliate detail page URL.
    Handles and logs Amazon API errors distinctly from Gemini API errors.
    """

    @classmethod
    def get_credentials(cls) -> Dict[str, str]:
        access_key = os.getenv("AMAZON_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID") or ""
        secret_key = os.getenv("AMAZON_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY") or ""
        tag = os.getenv("AMAZON_AFFILIATE_TAG") or os.getenv("AMAZON_ASSOCIATE_TAG") or "stylicai21-21"
        host = os.getenv("AMAZON_HOST", "webservices.amazon.in").strip()
        region = os.getenv("AMAZON_REGION", "eu-west-1").strip()
        marketplace = "www.amazon.in" if "amazon.in" in host else "www.amazon.com"

        return {
            "access_key": access_key.strip(),
            "secret_key": secret_key.strip(),
            "tag": tag.strip(),
            "host": host,
            "region": region,
            "marketplace": marketplace
        }

    @classmethod
    def _sign(cls, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    @classmethod
    def _get_signature_key(cls, key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
        k_date = cls._sign(("AWS4" + key).encode("utf-8"), date_stamp)
        k_region = cls._sign(k_date, region_name)
        k_service = cls._sign(k_region, service_name)
        k_signing = cls._sign(k_service, "aws4_request")
        return k_signing

    @classmethod
    def build_sigv4_headers(
        cls,
        payload_bytes: bytes,
        host: str,
        region: str,
        access_key: str,
        secret_key: str,
        target: str = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"
    ) -> Dict[str, str]:
        """Constructs AWS SigV4 signed headers for PA-API 5.0."""
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        method = "POST"
        canonical_uri = "/paapi5/searchitems"
        canonical_querystring = ""

        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        # Canonical headers must be sorted in lowercase
        canonical_headers = (
            f"content-encoding:amz-1.0\n"
            f"content-type:application/json; charset=utf-8\n"
            f"host:{host}\n"
            f"x-amz-date:{amz_date}\n"
            f"x-amz-target:{target}\n"
        )
        signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"

        canonical_request = (
            f"{method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/ProductAdvertisingAPI/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = cls._get_signature_key(secret_key, date_stamp, region, "ProductAdvertisingAPI")
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization_header = (
            f"{algorithm} Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        return {
            "content-type": "application/json; charset=utf-8",
            "content-encoding": "amz-1.0",
            "x-amz-date": amz_date,
            "x-amz-target": target,
            "host": host,
            "Authorization": authorization_header
        }

    @classmethod
    async def search_item(
        cls,
        keywords: str,
        search_index: str = "Apparel",
        fallback_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a real Amazon PA-API SearchItems call with the given keywords.
        Requests: Images.Primary.Medium, Offers.Listings.Price, ItemInfo.Title, DetailPageURL.
        Parses real product details, images, price, and affiliate URL.
        Logs Amazon errors distinctly.
        Falls back gracefully if keys are absent or API fails.
        """
        creds = cls.get_credentials()
        partner_tag = creds["tag"]

        # Default fallback structure
        fallback_link = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(keywords)}&tag={partner_tag}"
        default_item = {
            "title": (fallback_data.get("name") if fallback_data else keywords),
            "brand": (fallback_data.get("brand") if fallback_data else "Amazon Fashion"),
            "price_inr": float(fallback_data.get("price") if (fallback_data and fallback_data.get("price")) else 999.0),
            "platform": "Amazon",
            "product_url": (fallback_data.get("direct_url") or fallback_link if fallback_data else fallback_link),
            "image_url": (fallback_data.get("img") if (fallback_data and fallback_data.get("img")) else "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=500&auto=format&fit=crop&q=60"),
            "asin": (fallback_data.get("asin") if fallback_data else None),
            "source": "curated_fallback"
        }

        # If credentials are not configured, log clearly and return fallback
        if not creds["access_key"] or not creds["secret_key"]:
            print(f"[AmazonPAAPI Notice] Live Amazon API keys (AMAZON_ACCESS_KEY/AMAZON_SECRET_KEY) not configured. Using verified affiliate deep-link for '{keywords}' with tag '{partner_tag}'.")
            return default_item

        payload_obj = {
            "Keywords": keywords,
            "Resources": [
                "Images.Primary.Medium",
                "Offers.Listings.Price",
                "ItemInfo.Title",
                "DetailPageURL"
            ],
            "SearchIndex": search_index,
            "ItemCount": 1,
            "PartnerTag": partner_tag,
            "PartnerType": "Associates",
            "Marketplace": creds["marketplace"]
        }

        payload_json = json.dumps(payload_obj)
        payload_bytes = payload_json.encode("utf-8")

        try:
            headers = cls.build_sigv4_headers(
                payload_bytes=payload_bytes,
                host=creds["host"],
                region=creds["region"],
                access_key=creds["access_key"],
                secret_key=creds["secret_key"]
            )

            url = f"https://{creds['host']}/paapi5/searchitems"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, content=payload_bytes)

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("SearchResult", {}).get("Items", [])
                if items:
                    raw_item = items[0]
                    # Parse nested fields: Title
                    title = raw_item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue") or default_item["title"]
                    # Parse nested fields: Primary Image Medium
                    img_url = raw_item.get("Images", {}).get("Primary", {}).get("Medium", {}).get("URL") or default_item["image_url"]
                    # Parse nested fields: DetailPageURL (contains affiliate tag)
                    detail_url = raw_item.get("DetailPageURL") or default_item["product_url"]
                    # Parse nested fields: Price
                    price_inr = default_item["price_inr"]
                    listings = raw_item.get("Offers", {}).get("Listings", [])
                    if listings:
                        price_obj = listings[0].get("Price", {})
                        if "Amount" in price_obj:
                            try:
                                price_inr = float(price_obj["Amount"])
                            except Exception:
                                pass

                    asin = raw_item.get("ASIN")

                    print(f"[AmazonPAAPI Success] Real product matched for '{keywords}': '{title[:50]}...' | ₹{price_inr} | ASIN: {asin}")
                    return {
                        "title": title,
                        "brand": default_item["brand"],
                        "price_inr": price_inr,
                        "platform": "Amazon",
                        "product_url": detail_url,
                        "image_url": img_url,
                        "asin": asin,
                        "source": "live_paapi"
                    }
                else:
                    print(f"[AmazonPAAPI Warning] SearchItems returned 0 items for keywords: '{keywords}'. Using fallback catalog entry.")
                    return default_item
            else:
                # Distinct logging of Amazon API error (separate from Gemini errors)
                print(f"[AmazonPAAPI Error] HTTP {resp.status_code} for keywords '{keywords}': {resp.text[:250]}. Gracefully utilizing verified fallback.")
                return default_item

        except Exception as e:
            # Distinct logging of Amazon API network / signing exception
            print(f"[AmazonPAAPI Exception] Search failed for '{keywords}': {type(e).__name__}: {str(e)}. Seamlessly engaging fallback.")
            return default_item
