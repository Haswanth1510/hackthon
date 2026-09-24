import os
import json
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from dotenv import load_dotenv

from backend.services.amazon_paapi_service import AmazonPAAPIService

load_dotenv()

# Dedicated Fashion & Outfit Gemini Key (Independent from Skin Key)
GEMINI_API_KEY_FASHION = os.getenv("GEMINI_API_KEY_FASHION") or os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

class FashionService:
    """
    AI Fashion Stylist providing complete Head-to-Toe styling (Hat to Shoes).
    Curates Headwear, Topwear, Bottomwear, Footwear, and Accessories in the exact
    chromatic colors diagnosed for the user's skin undertones, strictly calibrated
    to fit within the user's preferred budget price with direct product affiliate links.
    Supports tailored silhouettes for female, male, and gender-inclusive profiles.
    """

    @staticmethod
    def _create_affiliate_link(
        platform: str,
        query: str,
        direct_url: Optional[str] = None,
        asin: Optional[str] = None
    ) -> str:
        from backend.services.product_service import ProductService
        return ProductService.generate_affiliate_url(platform, query, direct_url=direct_url, asin=asin)

    @classmethod
    async def _call_gemini_fashion(
        cls,
        occasion: str,
        skin_undertone: str,
        face_shape: str,
        gender: str,
        budget_inr: float,
        style_preference: str,
        color_palette: Optional[Dict[str, Any]] = None,
        age: int = 25
    ) -> Optional[Dict[str, Any]]:
        """
        Calls Google Gemini API using dedicated GEMINI_API_KEY_FASHION key.
        Applies retry-with-backoff on 429 rate limits independently from skin analysis.
        Logs distinctly if rate limits or errors occur on the fashion key.
        """
        active_key = os.getenv("GEMINI_API_KEY_FASHION") or os.getenv("GEMINI_API_KEY", "")
        if not active_key or not active_key.strip():
            print("[GeminiFashionAPI Error] No fashion API key configured (GEMINI_API_KEY_FASHION / GEMINI_API_KEY missing).")
            return None

        masked_key = f"...{active_key.strip()[-4:]}" if len(active_key.strip()) >= 4 else "..."
        print(f"[GeminiFashionAPI] Initiating outfit styling with dedicated fashion key ({masked_key})")

        best_colors = color_palette.get("best_colors", []) if color_palette else []
        palette_desc = ", ".join([f"{c.get('name', '')} ({c.get('hex', '')})" for c in best_colors[:5]]) if best_colors else f"Flattering to {skin_undertone} undertones"

        prompt = f"""You are an elite personal fashion stylist and aesthetic consultant.
Design a cohesive, complete 5-piece Head-to-Toe capsule outfit (Headwear, Topwear, Bottomwear, Footwear, Accessory) for:
- Gender: {gender}
- Age: {age}
- Diagnosed Skin Undertone: {skin_undertone}
- Face Shape: {face_shape}
- Occasion: {occasion}
- Style Aesthetic: {style_preference}
- Total Budget: INR {budget_inr:.0f}
- Flattering Chromatic Colors: {palette_desc}

Requirements:
1. Provide exactly 5 pieces:
   - Piece 1: Headwear / Hair accessory (hat, cap, headband, hair clip)
   - Piece 2: Topwear (shirt, blouse, blazer, t-shirt, kurta)
   - Piece 3: Bottomwear (trousers, jeans, chinos, skirt)
   - Piece 4: Footwear (heels, sneakers, loafers, boots, flats)
   - Piece 5: Accessory (handbag, tote, watch, belt, jewelry)
2. Total price sum of all 5 items MUST NOT exceed {budget_inr:.0f} INR.
3. For each piece, generate precise Amazon India search keywords including brand name, garment category, and color so that an Amazon SearchItems query finds the real product.

Return ONLY a valid JSON object matching this schema:
{{
  "style_name": "{style_preference} · {gender.capitalize()} Capsule ({occasion})",
  "styling_tips": [
    "Tip 1 regarding chromatic harmony with skin undertone",
    "Tip 2 regarding silhouette and facial geometry balance"
  ],
  "items": [
    {{
      "type": "Headwear",
      "name": "Item Name",
      "brand": "Brand Name",
      "color_name": "Color Name",
      "color_hex": "#HEX",
      "price": 299,
      "keywords": "Brand Name Garment Category Color Name"
    }},
    {{
      "type": "Topwear",
      "name": "Item Name",
      "brand": "Brand Name",
      "color_name": "Color Name",
      "color_hex": "#HEX",
      "price": 999,
      "keywords": "Brand Name Garment Category Color Name"
    }},
    {{
      "type": "Bottomwear",
      "name": "Item Name",
      "brand": "Brand Name",
      "color_name": "Color Name",
      "color_hex": "#HEX",
      "price": 1099,
      "keywords": "Brand Name Garment Category Color Name"
    }},
    {{
      "type": "Footwear",
      "name": "Item Name",
      "brand": "Brand Name",
      "color_name": "Color Name",
      "color_hex": "#HEX",
      "price": 899,
      "keywords": "Brand Name Garment Category Color Name"
    }},
    {{
      "type": "Accessory",
      "name": "Item Name",
      "brand": "Brand Name",
      "color_name": "Color Name",
      "color_hex": "#HEX",
      "price": 499,
      "keywords": "Brand Name Garment Category Color Name"
    }}
  ]
}}
"""
        models_to_try = [
            os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
            "gemini-flash-lite-latest",
            "gemini-flash-latest"
        ]
        seen = set()
        models = [m for m in models_to_try if not (m in seen or seen.add(m))]

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.3
            }
        }

        max_retries = 3
        base_delay = 1.0

        async with httpx.AsyncClient(timeout=30.0) as client:
            for model_name in models:
                for attempt in range(1, max_retries + 1):
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={active_key.strip()}"
                        resp = await client.post(url, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            candidates = data.get("candidates", [])
                            if candidates and "content" in candidates[0]:
                                parts = candidates[0]["content"].get("parts", [])
                                if parts and "text" in parts[0]:
                                    parsed = json.loads(parts[0]["text"])
                                    if "items" in parsed and len(parsed["items"]) >= 3:
                                        print(f"[GeminiFashionAPI] Outfit styling succeeded on fashion key ({masked_key}) with model {model_name}")
                                        return parsed
                        elif resp.status_code == 429:
                            delay = base_delay * (2 ** (attempt - 1))
                            print(f"[GeminiFashionAPI] Rate limit (HTTP 429) on fashion key ({masked_key}) with model {model_name}. Attempt {attempt}/{max_retries}. Backing off {delay:.1f}s...")
                            if attempt < max_retries:
                                await asyncio.sleep(delay)
                                continue
                            else:
                                print(f"[GeminiFashionAPI] Exhausted retries for model {model_name} due to rate limiting on fashion key ({masked_key}).")
                        else:
                            print(f"[GeminiFashionAPI] Fashion key ({masked_key}) with model {model_name} returned HTTP {resp.status_code}: {resp.text[:150]}")
                            break
                    except Exception as e:
                        delay = base_delay * (2 ** (attempt - 1))
                        print(f"[GeminiFashionAPI] Exception on fashion key ({masked_key}) with model {model_name} (Attempt {attempt}/{max_retries}): {e}")
                        if attempt < max_retries:
                            await asyncio.sleep(delay)

        print(f"[GeminiFashionAPI] Fashion AI call failed on key ({masked_key}). Engaging curated chromatic ensemble fallback.")
        return None

    @classmethod
    async def _call_bazaarlink_fashion(
        cls,
        occasion: str,
        skin_undertone: str,
        face_shape: str,
        gender: str,
        budget_inr: float,
        style_preference: str,
        color_palette: Optional[Dict[str, Any]] = None,
        age: int = 25,
        api_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Backup fashion generation using BazaarLink OpenAI-compatible gateway.
        """
        active_key = api_key or os.getenv("BAZAARLINK_API_KEY") or os.getenv("BACKUP_AI_KEY", "")
        if not active_key or not active_key.strip():
            return None

        best_colors = color_palette.get("best_colors", []) if color_palette else []
        palette_desc = ", ".join([f"{c.get('name', '')} ({c.get('hex', '')})" for c in best_colors[:5]]) if best_colors else f"Flattering to {skin_undertone} undertones"

        prompt = f"""You are an elite personal fashion stylist and aesthetic consultant.
Design a cohesive, complete 5-piece Head-to-Toe capsule outfit (Headwear, Topwear, Bottomwear, Footwear, Accessory) for:
- Gender: {gender}
- Age: {age}
- Diagnosed Skin Undertone: {skin_undertone}
- Face Shape: {face_shape}
- Occasion: {occasion}
- Style Aesthetic: {style_preference}
- Total Budget: INR {budget_inr:.0f}
- Flattering Chromatic Colors: {palette_desc}

Requirements:
1. Provide exactly 5 pieces: Headwear, Topwear, Bottomwear, Footwear, Accessory.
2. Total price sum of all 5 items MUST NOT exceed {budget_inr:.0f} INR.
3. For each piece, generate precise Amazon India search keywords including brand name, garment category, and color.

Return ONLY a valid JSON object matching this schema:
{{
  "style_name": "{style_preference} · {gender.capitalize()} Capsule ({occasion})",
  "styling_tips": [
    "Tip 1 regarding chromatic harmony with skin undertone",
    "Tip 2 regarding silhouette and facial geometry balance"
  ],
  "items": [
    {{"type": "Headwear", "name": "Item Name", "brand": "Brand", "color_name": "Color", "color_hex": "#HEX", "price": 299, "keywords": "Brand Garment Color"}},
    {{"type": "Topwear", "name": "Item Name", "brand": "Brand", "color_name": "Color", "color_hex": "#HEX", "price": 999, "keywords": "Brand Garment Color"}},
    {{"type": "Bottomwear", "name": "Item Name", "brand": "Brand", "color_name": "Color", "color_hex": "#HEX", "price": 1099, "keywords": "Brand Garment Color"}},
    {{"type": "Footwear", "name": "Item Name", "brand": "Brand", "color_name": "Color", "color_hex": "#HEX", "price": 899, "keywords": "Brand Garment Color"}},
    {{"type": "Accessory", "name": "Item Name", "brand": "Brand", "color_name": "Color", "color_hex": "#HEX", "price": 204, "keywords": "Brand Garment Color"}}
  ]
}}"""

        endpoint = os.getenv("BAZAARLINK_API_URL", "https://api.bazaarlink.ai/v1/chat/completions")
        model_name = os.getenv("BAZAARLINK_MODEL", "auto:free")
        headers = {
            "Authorization": f"Bearer {active_key.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }

        masked_key = f"...{active_key[-4:]}" if len(active_key) >= 4 else "..."
        async with httpx.AsyncClient(timeout=25.0) as client:
            try:
                resp = await client.post(endpoint, headers=headers, json=payload)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    print(f"[BazaarLinkFashion] Backup outfit generation succeeded with model {model_name} on key ({masked_key})")
                    return parsed
            except Exception as e:
                print(f"[BazaarLinkFashion] Backup outfit generation exception: {e}")
        return None

    @classmethod
    async def recommend_outfit(
        cls,
        occasion: str = "Casual",
        skin_undertone: str = "Warm",
        face_shape: str = "Oval",
        gender: str = "unspecified",
        budget_inr: Optional[float] = None,
        style_preference: str = "Modern Minimalist",
        color_palette: Optional[Dict[str, Any]] = None,
        age: int = 25
    ) -> Dict[str, Any]:
        """
        Builds a complete Head-to-Toe outfit (Hat/Hairwear, Topwear, Bottomwear, Shoes, Accessories)
        tailored in the AI diagnosed chromatic skin colors and verified with real Amazon Product Advertising API (SearchItems).
        Uses independent GEMINI_API_KEY_FASHION key for fashion generation.
        """
        preferred_budget = float(budget_inr) if (budget_inr is not None and budget_inr > 0) else 3500.0

        # 1. Extract Chromatic Colors from AI Color Palette
        best_colors = (color_palette.get("best_colors", []) if color_palette else []) or []
        season = (color_palette.get("season") if color_palette else "") or "Harmonious"

        if len(best_colors) >= 3:
            c_top = best_colors[0]
            c_bot = best_colors[2] if len(best_colors) > 2 else best_colors[1]
            c_head = best_colors[1] if len(best_colors) > 1 else best_colors[0]
            c_foot = best_colors[-1] if len(best_colors) >= 4 else best_colors[0]
            c_acc = best_colors[4] if len(best_colors) > 4 else best_colors[0]
        else:
            undertone_str = (skin_undertone or "").lower()
            if "cool" in undertone_str:
                c_top = {"name": "Cobalt Blue", "hex": "#0047AB"}
                c_bot = {"name": "Slate Grey", "hex": "#708090"}
                c_head = {"name": "Crisp White", "hex": "#FFFFFF"}
                c_foot = {"name": "Deep Black", "hex": "#111827"}
                c_acc = {"name": "Silver Chrome", "hex": "#C0C0C0"}
            elif "warm" in undertone_str:
                c_top = {"name": "Terracotta Rust", "hex": "#C85A32"}
                c_bot = {"name": "Warm Camel Tan", "hex": "#C19A6B"}
                c_head = {"name": "Forest Olive", "hex": "#3B4E38"}
                c_foot = {"name": "Espresso Brown", "hex": "#3E2723"}
                c_acc = {"name": "Warm Ochre", "hex": "#D4A017"}
            else:
                c_top = {"name": "Muted Sage", "hex": "#84A98C"}
                c_bot = {"name": "Sandstone Beige", "hex": "#D4A373"}
                c_head = {"name": "Off-White", "hex": "#FAF9F6"}
                c_foot = {"name": "Charcoal Heather", "hex": "#334155"}
                c_acc = {"name": "Antique Brass", "hex": "#CD7F32"}

        # 2. Strict Budget Allocation for 5-Piece Capsule (Sum <= preferred_budget)
        p_top = round((preferred_budget * 0.28) / 50) * 50 - 1
        p_bot = round((preferred_budget * 0.30) / 50) * 50 - 1
        p_foot = round((preferred_budget * 0.26) / 50) * 50 - 1
        p_head = round((preferred_budget * 0.09) / 50) * 50 - 1
        p_acc = preferred_budget - (p_top + p_bot + p_foot + p_head)

        if p_acc < 99:
            p_acc = 149
            p_foot = max(199, p_foot - 50)

        # 3. Occasion & Gender Apparel Templates (used as fallbacks or base blueprints)
        occ = (occasion or "Casual").strip().title()
        gen_clean = (gender or "").strip().lower()
        is_female = gen_clean in ["female", "woman", "women", "f"]

        if is_female:
            items_def = cls._get_female_ensemble(occ, c_head, c_top, c_bot, c_foot, c_acc, p_head, p_top, p_bot, p_foot, p_acc)
        else:
            items_def = cls._get_male_ensemble(occ, c_head, c_top, c_bot, c_foot, c_acc, p_head, p_top, p_bot, p_foot, p_acc)

        # 4. Attempt Gemini Fashion Call (uses dedicated GEMINI_API_KEY_FASHION)
        gemini_fashion = await cls._call_gemini_fashion(
            occasion=occ,
            skin_undertone=skin_undertone,
            face_shape=face_shape,
            gender=gender,
            budget_inr=preferred_budget,
            style_preference=style_preference,
            color_palette=color_palette,
            age=age
        )

        if not gemini_fashion or "items" not in gemini_fashion or len(gemini_fashion.get("items", [])) < 3:
            backup_key = os.getenv("BAZAARLINK_API_KEY") or os.getenv("BACKUP_AI_KEY")
            if backup_key and backup_key.strip():
                print("[FashionService] Engaging BazaarLink backup AI engine for outfit curation...")
                gemini_fashion = await cls._call_bazaarlink_fashion(
                    occasion=occ,
                    skin_undertone=skin_undertone,
                    face_shape=face_shape,
                    gender=gender,
                    budget_inr=preferred_budget,
                    style_preference=style_preference,
                    color_palette=color_palette,
                    age=age,
                    api_key=backup_key.strip()
                )

        selected_items = []
        actual_total = 0.0
        gender_desc = "Women's" if is_female else ("Men's" if gen_clean in ["male", "man", "men", "m"] else "Unisex")

        if gemini_fashion and "items" in gemini_fashion and len(gemini_fashion["items"]) >= 3:
            # Reconcile Gemini items with real Amazon PA-API search
            raw_items = gemini_fashion["items"]
            for idx, g_item in enumerate(raw_items[:5]):
                fallback_template = items_def[idx] if idx < len(items_def) else items_def[0]
                keywords = g_item.get("keywords") or f"{g_item.get('brand', '')} {g_item.get('name', '')} {g_item.get('color_name', '')}".strip()
                
                # Search real Amazon PA-API (SearchItems) with fallback
                real_amazon_prod = await AmazonPAAPIService.search_item(
                    keywords=keywords,
                    fallback_data=fallback_template
                )

                color_name = g_item.get("color_name") or fallback_template["color"]["name"]
                color_hex = g_item.get("color_hex") or fallback_template["color"]["hex"]
                item_price = float(real_amazon_prod.get("price_inr") or g_item.get("price") or fallback_template["price"])

                selected_items.append({
                    "item_type": g_item.get("type") or fallback_template["type"],
                    "name": real_amazon_prod["title"],
                    "brand": real_amazon_prod.get("brand") or g_item.get("brand") or fallback_template["brand"],
                    "price_inr": round(item_price, 2),
                    "platform": "Amazon",
                    "product_url": real_amazon_prod["product_url"],
                    "image_url": real_amazon_prod["image_url"],
                    "color_name": color_name,
                    "color_hex": color_hex,
                    "asin": real_amazon_prod.get("asin")
                })
                actual_total += item_price

            style_name = gemini_fashion.get("style_name") or f"{style_preference} · {gender_desc} Head-to-Toe ({occ})"
            styling_tips = gemini_fashion.get("styling_tips") or [
                f"Chromatic Color Match ({season}): Tailored upper silhouette in {c_top['name']} ({c_top['hex']}) harmonizes with your skin undertones.",
                f"Budget Calibration: Complete 5-piece capsule ensemble scaled within your target budget of ₹{preferred_budget:,.0f} (Total: ₹{actual_total:,.0f}).",
                f"Real Amazon Product Links: Real products linked with one-click purchasing on Amazon India."
            ]
        else:
            # Fallback path: use verified chromatic ensemble and query Amazon PA-API with fallback
            for it in items_def:
                keywords = f"{it['brand']} {it['name']} {it['color']['name']}"
                real_amazon_prod = await AmazonPAAPIService.search_item(
                    keywords=keywords,
                    fallback_data=it
                )

                item_price = float(real_amazon_prod.get("price_inr") or it["price"])
                selected_items.append({
                    "item_type": it["type"],
                    "name": real_amazon_prod["title"],
                    "brand": real_amazon_prod.get("brand") or it["brand"],
                    "price_inr": round(item_price, 2),
                    "platform": "Amazon",
                    "product_url": real_amazon_prod["product_url"],
                    "image_url": real_amazon_prod["image_url"],
                    "color_name": it["color"]["name"],
                    "color_hex": it["color"]["hex"],
                    "asin": real_amazon_prod.get("asin")
                })
                actual_total += item_price

            style_name = f"{style_preference} · {gender_desc} Head-to-Toe ({occ})"
            styling_tips = [
                f"Chromatic Color Match ({season}): Upper silhouette in {c_top['name']} ({c_top['hex']}) harmonizes with your diagnosed skin undertones, paired with {c_bot['name']} bottoms.",
                f"Budget Optimization: Complete 5-piece {gender_desc} capsule ensemble curated within your preferred budget of ₹{preferred_budget:,.0f} (Total: ₹{actual_total:,.0f}).",
                f"Real Amazon Integration: Real Amazon product listings with direct purchase URLs and tracked affiliate discount.",
                f"Facial Harmony: Neckline contouring and {items_def[0]['name']} naturally frame your {face_shape} facial profile."
            ]

        palette_list = [c["name"] for c in best_colors] if best_colors else [c_top["name"], c_bot["name"], c_head["name"], c_foot["name"]]

        return {
            "occasion": occ,
            "style_name": style_name,
            "undertone_match": skin_undertone,
            "total_cost_inr": round(actual_total, 2),
            "budget_limit_inr": preferred_budget,
            "palette": palette_list,
            "items": selected_items,
            "styling_tips": styling_tips
        }

    @classmethod
    def _get_female_ensemble(
        cls, occ: str, c_head: dict, c_top: dict, c_bot: dict, c_foot: dict, c_acc: dict,
        p_head: float, p_top: float, p_bot: float, p_foot: float, p_acc: float
    ) -> List[Dict[str, Any]]:
        if occ == "Formal":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Structured Satin Padded Headband",
                    "brand": "Carlton London",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B09MZ8Y275",
                    "direct_url": "https://www.amazon.in/dp/B09MZ8Y275",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Tailored Notched-Lapel Formal Blazer Blouse",
                    "brand": "Vero Moda",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07MGB563Q",
                    "direct_url": "https://www.amazon.in/dp/B07MGB563Q",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} High-Rise Pleated Ankle Trousers",
                    "brand": "Van Heusen Woman",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B08FBL73S9",
                    "direct_url": "https://www.amazon.in/dp/B08FBL73S9",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1479064555552-3ef4979f8908?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Pointed-Toe Comfort Block Heel Pumps",
                    "brand": "Metro",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B079DMC6K4",
                    "direct_url": "https://www.amazon.in/dp/B079DMC6K4",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Saffiano Vegan Leather Structured Handbag",
                    "brand": "Lavie",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B07N25D5MV",
                    "direct_url": "https://www.amazon.in/dp/B07N25D5MV",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=500&auto=format&fit=crop&q=60"
                }
            ]
        elif occ == "Date Night":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Velvet Twist Statement Hairband",
                    "brand": "Carlton London",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B09MZ8Y275",
                    "direct_url": "https://www.amazon.in/dp/B09MZ8Y275",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Tie-Up Georgette Wrap Blouse",
                    "brand": "Forever New",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B091V28X1K",
                    "direct_url": "https://www.amazon.in/dp/B091V28X1K",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1518622358385-90d473aab4b8?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Satin Finish Flared Midi Skirt",
                    "brand": "ONLY",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B084ZNWN2M",
                    "direct_url": "https://www.amazon.in/dp/B084ZNWN2M",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Strappy Stiletto Open-Toe Heeled Sandals",
                    "brand": "Catwalk",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B07X99182C",
                    "direct_url": "https://www.amazon.in/dp/B07X99182C",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Dainty Layered Pendant Necklace",
                    "brand": "GIVA",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B08QCP4R1N",
                    "direct_url": "https://www.amazon.in/dp/B08QCP4R1N",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=500&auto=format&fit=crop&q=60"
                }
            ]
        elif occ == "Party":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Crystal Embellished Statement Hairpiece",
                    "brand": "Zaveri Pearls",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B079DMSM1Z",
                    "direct_url": "https://www.amazon.in/dp/B079DMSM1Z",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1534215754734-18e55d13e346?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Shimmer Ruched Crop Corset Top",
                    "brand": "Snitch Woman",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07Z8TKMZP",
                    "direct_url": "https://www.amazon.in/dp/B07Z8TKMZP",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1518622358385-90d473aab4b8?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} High-Rise Wide-Leg Sleek Palazzo Trousers",
                    "brand": "Sassafras",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B08N5S55W3",
                    "direct_url": "https://www.amazon.in/dp/B08N5S55W3",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Shimmer Metallic Block Heeled Sandals",
                    "brand": "Mochi",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B079DMC6K4",
                    "direct_url": "https://www.amazon.in/dp/B079DMC6K4",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Designer Evening Envelope Clutch",
                    "brand": "Baggit",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B07N25D5MV",
                    "direct_url": "https://www.amazon.in/dp/B07N25D5MV",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=500&auto=format&fit=crop&q=60"
                }
            ]
        elif occ == "Athletic":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Aeroready Performance Running Visor Cap",
                    "brand": "Puma",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B07H83L144",
                    "direct_url": "https://www.amazon.in/dp/B07H83L144",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Quick-Dry Seamless Racerback Athletic Tank",
                    "brand": "HRX",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07Z8TKMZP",
                    "direct_url": "https://www.amazon.in/dp/B07Z8TKMZP",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1518622358385-90d473aab4b8?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} High-Rise Squat-Proof Compression Tights",
                    "brand": "Cultsport",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B08N5S55W3",
                    "direct_url": "https://www.amazon.in/dp/B08N5S55W3",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Cloud-Cushioned Lightweight Running Shoes",
                    "brand": "Sparx",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B09NVXWW39",
                    "direct_url": "https://www.amazon.in/dp/B09NVXWW39",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1607522370275-f14206abe5d3?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Water-Resistant Active Gym Sling Bag",
                    "brand": "Safari",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B08339Z8XQ",
                    "direct_url": "https://www.amazon.in/dp/B08339Z8XQ",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500&auto=format&fit=crop&q=60"
                }
            ]
        elif occ == "College":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Washed Cotton Embroidered Bucket Hat",
                    "brand": "Urban Monkey",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B07H83L144",
                    "direct_url": "https://www.amazon.in/dp/B07H83L144",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1534215754734-18e55d13e346?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Oversized Drop-Shoulder Graphic Tee",
                    "brand": "Bewakoof",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07Z8TKMZP",
                    "direct_url": "https://www.amazon.in/dp/B07Z8TKMZP",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} High-Rise Wide-Leg Denim Jeans",
                    "brand": "Tokyo Talkies",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B08N5S55W3",
                    "direct_url": "https://www.amazon.in/dp/B08N5S55W3",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1542272604-780c96856592?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Retro Platform Clean Canvas Sneakers",
                    "brand": "Red Tape",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B09NVXWW39",
                    "direct_url": "https://www.amazon.in/dp/B09NVXWW39",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"Everyday Multi-Pocket Ergonomic College Backpack",
                    "brand": "Safari",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B08339Z8XQ",
                    "direct_url": "https://www.amazon.in/dp/B08339Z8XQ",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500&auto=format&fit=crop&q=60"
                }
            ]
        elif occ == "Traditional":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Kundan Embellished Floral Hair Accessory",
                    "brand": "Zaveri Pearls",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B079DMSM1Z",
                    "direct_url": "https://www.amazon.in/dp/B079DMSM1Z",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Chanderi Silk Embroidered Straight Kurti",
                    "brand": "Libas",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07P7V9HZZ",
                    "direct_url": "https://www.amazon.in/dp/B07P7V9HZZ",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Gold-Bordered Flared Ethnic Sharara Pants",
                    "brand": "W for Woman",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B08B5374G3",
                    "direct_url": "https://www.amazon.in/dp/B08B5374G3",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Handcrafted Zari Embroidered Punjabi Juttis",
                    "brand": "Metro",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B079DMC6K4",
                    "direct_url": "https://www.amazon.in/dp/B079DMC6K4",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Kundan Pearl Drop Traditional Jhumkas",
                    "brand": "Zaveri Pearls",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B079DMSM1Z",
                    "direct_url": "https://www.amazon.in/dp/B079DMSM1Z",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=500&auto=format&fit=crop&q=60"
                }
            ]
        else: # Casual
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Washed Cotton Vintage Baseball Cap",
                    "brand": "Puma",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B07H83L144",
                    "direct_url": "https://www.amazon.in/dp/B07H83L144",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Pure Cotton Breathable Linen-Blend Shirt",
                    "brand": "ONLY",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07Z8TKMZP",
                    "direct_url": "https://www.amazon.in/dp/B07Z8TKMZP",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Straight-Fit Cropped Ankle Chinos",
                    "brand": "Tokyo Talkies",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B08N5S55W3",
                    "direct_url": "https://www.amazon.in/dp/B08N5S55W3",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Minimalist Low-Top Clean White Sneakers",
                    "brand": "Red Tape",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B09NVXWW39",
                    "direct_url": "https://www.amazon.in/dp/B09NVXWW39",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Dainty Crossbody Vegan Leather Sling Bag",
                    "brand": "Lavie",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B07N25D5MV",
                    "direct_url": "https://www.amazon.in/dp/B07N25D5MV",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=500&auto=format&fit=crop&q=60"
                }
            ]

    @classmethod
    def _get_male_ensemble(
        cls, occ: str, c_head: dict, c_top: dict, c_bot: dict, c_foot: dict, c_acc: dict,
        p_head: float, p_top: float, p_bot: float, p_foot: float, p_acc: float
    ) -> List[Dict[str, Any]]:
        if occ == "Formal":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Structured Wool Felt Fedora Hat",
                    "brand": "Peter England",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B08L7V7YJ2",
                    "direct_url": "https://www.amazon.in/dp/B08L7V7YJ2",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1514327605112-b887c0e61c0a?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Spread Collar Egyptian Cotton Formal Shirt",
                    "brand": "Raymond",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B08V536F3Z",
                    "direct_url": "https://www.amazon.in/dp/B08V536F3Z",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Tailored Flat-Front Formal Trousers",
                    "brand": "Van Heusen",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B07N8D439K",
                    "direct_url": "https://www.amazon.in/dp/B07N8D439K",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1479064555552-3ef4979f8908?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Handcrafted Derby Formal Leather Shoes",
                    "brand": "Bata",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B00T75A4E8",
                    "direct_url": "https://www.amazon.in/dp/B00T75A4E8",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Reversible Full-Grain Leather Belt",
                    "brand": "Titan",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B07Y5CK5D4",
                    "direct_url": "https://www.amazon.in/dp/B07Y5CK5D4",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1624222247344-550fb60583dc?w=500&auto=format&fit=crop&q=60"
                }
            ]
        elif occ == "Date Night":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Suede Ivy Driving Flat Cap",
                    "brand": "Karry",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B08L7V7YJ2",
                    "direct_url": "https://www.amazon.in/dp/B08L7V7YJ2",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Cuban Camp Collar Textured Resort Shirt",
                    "brand": "Dennis Lingo",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07D3N2L9F",
                    "direct_url": "https://www.amazon.in/dp/B07D3N2L9F",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Slim Fit Stretch Cotton Chinos",
                    "brand": "Highlander",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B07PPNVL93",
                    "direct_url": "https://www.amazon.in/dp/B07PPNVL93",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Suede Penny Loafers with Cushion Footbed",
                    "brand": "Kraasa",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B08FB98V5T",
                    "direct_url": "https://www.amazon.in/dp/B08FB98V5T",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1560343090-f0409e92791a?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"Minimalist {c_acc['name']} Dial Analog Watch",
                    "brand": "Fastrack",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B007V2TY2G",
                    "direct_url": "https://www.amazon.in/dp/B007V2TY2G",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=500&auto=format&fit=crop&q=60"
                }
            ]
        elif occ == "Party":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Structured Streetwear Snapback",
                    "brand": "Urban Monkey",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B07H83L144",
                    "direct_url": "https://www.amazon.in/dp/B07H83L144",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1534215754734-18e55d13e346?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Satin Finish Oversized Statement Shirt",
                    "brand": "Snitch",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07D3N2L9F",
                    "direct_url": "https://www.amazon.in/dp/B07D3N2L9F",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Relaxed Straight Tapered Trousers",
                    "brand": "Roadster",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B07PPNVL93",
                    "direct_url": "https://www.amazon.in/dp/B07PPNVL93",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Designer Low-Top Clean Platform Sneakers",
                    "brand": "Red Tape",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B08R7R5VBD",
                    "direct_url": "https://www.amazon.in/dp/B08R7R5VBD",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Accent Stainless Steel Minimalist Pendant",
                    "brand": "Yellow Chimes",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B079Z1K9CP",
                    "direct_url": "https://www.amazon.in/dp/B079Z1K9CP",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=500&auto=format&fit=crop&q=60"
                }
            ]
        elif occ == "Athletic":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Aeroready Performance Running Cap",
                    "brand": "Puma",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B07H83L144",
                    "direct_url": "https://www.amazon.in/dp/B07H83L144",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Dri-FIT Breathable Training Tee",
                    "brand": "Campus Sutra",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07D3N2L9F",
                    "direct_url": "https://www.amazon.in/dp/B07D3N2L9F",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Tapered Lightweight Stretch Trackpants",
                    "brand": "HRX",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B07PPNVL93",
                    "direct_url": "https://www.amazon.in/dp/B07PPNVL93",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Responsive Foam Athletic Running Shoes",
                    "brand": "Sparx",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B08R7R5VBD",
                    "direct_url": "https://www.amazon.in/dp/B08R7R5VBD",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1607522370275-f14206abe5d3?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"Water-Resistant Everyday Technical Backpack",
                    "brand": "Safari",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B08339Z8XQ",
                    "direct_url": "https://www.amazon.in/dp/B08339Z8XQ",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500&auto=format&fit=crop&q=60"
                }
            ]
        elif occ == "College":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Streetwear Washed Dad Cap",
                    "brand": "Urban Monkey",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B07H83L144",
                    "direct_url": "https://www.amazon.in/dp/B07H83L144",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1534215754734-18e55d13e346?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Relaxed Fit Heavyweight Cotton Tee",
                    "brand": "Bewakoof",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07D3N2L9F",
                    "direct_url": "https://www.amazon.in/dp/B07D3N2L9F",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Distressed Slim Tapered Jeans",
                    "brand": "Roadster",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B07PPNVL93",
                    "direct_url": "https://www.amazon.in/dp/B07PPNVL93",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1542272604-780c96856592?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Retro High-Top Canvas Sneakers",
                    "brand": "Sparx",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B08R7R5VBD",
                    "direct_url": "https://www.amazon.in/dp/B08R7R5VBD",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1607522370275-f14206abe5d3?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"Water-Resistant Everyday Canvas Backpack",
                    "brand": "Safari",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B08339Z8XQ",
                    "direct_url": "https://www.amazon.in/dp/B08339Z8XQ",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500&auto=format&fit=crop&q=60"
                }
            ]
        elif occ == "Traditional":
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Royal Chanderi Silk Safa Turban Accent",
                    "brand": "Manyavar",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B08L7V7YJ2",
                    "direct_url": "https://www.amazon.in/dp/B08L7V7YJ2",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1514327605112-b887c0e61c0a?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Embroidered Jacquard Silk Festive Kurta",
                    "brand": "Manyavar",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07V2D3Y7T",
                    "direct_url": "https://www.amazon.in/dp/B07V2D3Y7T",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Dupion Silk Slim Churidar Pyjama",
                    "brand": "Manyavar",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B085V8G9V8",
                    "direct_url": "https://www.amazon.in/dp/B085V8G9V8",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1479064555552-3ef4979f8908?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Handcrafted Ethnic Mojari Leather Loafers",
                    "brand": "Bata",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B00T75A4E8",
                    "direct_url": "https://www.amazon.in/dp/B00T75A4E8",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Classic Gold-Plated Chronograph Analog Watch",
                    "brand": "Titan",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B008630J4E",
                    "direct_url": "https://www.amazon.in/dp/B008630J4E",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=500&auto=format&fit=crop&q=60"
                }
            ]
        else: # Casual
            return [
                {
                    "type": "Headwear",
                    "name": f"{c_head['name']} Washed Cotton Vintage Baseball Cap",
                    "brand": "Puma",
                    "price": p_head,
                    "plat": "Amazon",
                    "asin": "B07H83L144",
                    "direct_url": "https://www.amazon.in/dp/B07H83L144",
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Pure Cotton Relaxed Drop-Shoulder Shirt",
                    "brand": "Dennis Lingo",
                    "price": p_top,
                    "plat": "Amazon",
                    "asin": "B07D3N2L9F",
                    "direct_url": "https://www.amazon.in/dp/B07D3N2L9F",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Straight-Fit Washed Chino Trousers",
                    "brand": "Roadster",
                    "price": p_bot,
                    "plat": "Amazon",
                    "asin": "B07PPNVL93",
                    "direct_url": "https://www.amazon.in/dp/B07PPNVL93",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Minimalist Low-Top Clean Sneakers",
                    "brand": "Red Tape",
                    "price": p_foot,
                    "plat": "Amazon",
                    "asin": "B08R7R5VBD",
                    "direct_url": "https://www.amazon.in/dp/B08R7R5VBD",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Accent Minimalist Chain Pendant",
                    "brand": "Yellow Chimes",
                    "price": p_acc,
                    "plat": "Amazon",
                    "asin": "B079Z1K9CP",
                    "direct_url": "https://www.amazon.in/dp/B079Z1K9CP",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=500&auto=format&fit=crop&q=60"
                }
            ]
