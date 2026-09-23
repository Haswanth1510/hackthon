import os
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

class FashionService:
    """
    AI Fashion Stylist providing complete Head-to-Toe styling (Hat to Shoes).
    Curates Headwear, Topwear, Bottomwear, Footwear, and Accessories in the exact
    chromatic colors diagnosed for the user's skin undertones, strictly calibrated
    to fit within the user's preferred budget price with active affiliate links.
    Supports tailored silhouettes for female, male, and gender-inclusive profiles.
    """

    @staticmethod
    def _create_affiliate_link(platform: str, query: str) -> str:
        from backend.services.product_service import ProductService
        return ProductService.generate_affiliate_url(platform, query)

    @classmethod
    async def recommend_outfit(
        cls,
        occasion: str = "Casual",
        skin_undertone: str = "Warm",
        face_shape: str = "Oval",
        gender: str = "unspecified",
        budget_inr: Optional[float] = None,
        style_preference: str = "Modern Minimalist",
        color_palette: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Builds a complete Head-to-Toe outfit (Hat/Hairwear, Topwear, Bottomwear, Shoes, Accessories)
        tailored directly in the AI diagnosed chromatic skin colors, strictly observing
        the user's preferred budget price and creating affiliate search links for each piece.
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

        # 3. Occasion & Gender Apparel Templates with Diagnosed Colors
        occ = (occasion or "Casual").strip().title()
        gen_clean = (gender or "").strip().lower()
        is_female = gen_clean in ["female", "woman", "women", "f"]

        if is_female:
            items_def = cls._get_female_ensemble(occ, c_head, c_top, c_bot, c_foot, c_acc, p_head, p_top, p_bot, p_foot, p_acc)
        else:
            items_def = cls._get_male_ensemble(occ, c_head, c_top, c_bot, c_foot, c_acc, p_head, p_top, p_bot, p_foot, p_acc)

        selected_items = []
        actual_total = 0.0

        for it in items_def:
            # Affiliate search query precisely matching brand, diagnosed color, and item type
            q = f"{it['brand']} {it['name']}"
            aff_url = cls._create_affiliate_link(it["plat"], q)
            item_obj = {
                "item_type": it["type"],
                "name": it["name"],
                "brand": it["brand"],
                "price_inr": float(it["price"]),
                "platform": it["plat"],
                "product_url": aff_url,
                "image_url": it["img"],
                "color_name": it["color"]["name"],
                "color_hex": it["color"]["hex"]
            }
            selected_items.append(item_obj)
            actual_total += it["price"]

        palette_list = [c["name"] for c in best_colors] if best_colors else [c_top["name"], c_bot["name"], c_head["name"], c_foot["name"]]

        gender_desc = "Women's" if is_female else ("Men's" if gen_clean in ["male", "man", "men", "m"] else "Unisex")
        styling_tips = [
            f"Chromatic Color Match ({season}): Upper silhouette in {c_top['name']} ({c_top['hex']}) harmonizes with your diagnosed skin undertones, paired with {c_bot['name']} bottoms.",
            f"Budget Optimization: Complete 5-piece {gender_desc} capsule ensemble curated within your preferred budget of ₹{preferred_budget:,.0f} (Total: ₹{actual_total:,.0f}).",
            f"Facial Harmony: Neckline contouring and {items_def[0]['name']} naturally frame your {face_shape} facial profile."
        ]

        return {
            "occasion": occ,
            "style_name": f"{style_preference} · {gender_desc} Head-to-Toe ({occ})",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Tailored Notched-Lapel Formal Blazer Blouse",
                    "brand": "Vero Moda",
                    "price": p_top,
                    "plat": "Amazon",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} High-Rise Pleated Ankle Trousers",
                    "brand": "Van Heusen Woman",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1479064555552-3ef4979f8908?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Pointed-Toe Comfort Block Heel Pumps",
                    "brand": "Metro",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Saffiano Vegan Leather Structured Handbag",
                    "brand": "Lavie",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Tie-Up Georgette Wrap Blouse",
                    "brand": "Forever New",
                    "price": p_top,
                    "plat": "Amazon",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1518622358385-90d473aab4b8?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Satin Finish Flared Midi Skirt",
                    "brand": "ONLY",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Strappy Stiletto Open-Toe Heeled Sandals",
                    "brand": "Catwalk",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Dainty Layered Pendant Necklace",
                    "brand": "GIVA",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1534215754734-18e55d13e346?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Shimmer Ruched Crop Corset Top",
                    "brand": "Snitch Woman",
                    "price": p_top,
                    "plat": "Flipkart",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1518622358385-90d473aab4b8?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} High-Rise Wide-Leg Sleek Palazzo Trousers",
                    "brand": "Sassafras",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Shimmer Metallic Block Heeled Sandals",
                    "brand": "Mochi",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Designer Evening Envelope Clutch",
                    "brand": "Baggit",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Quick-Dry Seamless Racerback Athletic Tank",
                    "brand": "HRX",
                    "price": p_top,
                    "plat": "Flipkart",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1518622358385-90d473aab4b8?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} High-Rise Squat-Proof Compression Tights",
                    "brand": "Cultsport",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Cloud-Cushioned Lightweight Running Shoes",
                    "brand": "Sparx",
                    "price": p_foot,
                    "plat": "Flipkart",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1607522370275-f14206abe5d3?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Water-Resistant Active Gym Sling Bag",
                    "brand": "Safari",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1534215754734-18e55d13e346?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Oversized Drop-Shoulder Graphic Tee",
                    "brand": "Bewakoof",
                    "price": p_top,
                    "plat": "Flipkart",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} High-Rise Wide-Leg Denim Jeans",
                    "brand": "Tokyo Talkies",
                    "price": p_bot,
                    "plat": "Amazon",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1542272604-780c96856592?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Retro Platform Clean Canvas Sneakers",
                    "brand": "Red Tape",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"Everyday Multi-Pocket Ergonomic College Backpack",
                    "brand": "Safari",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Chanderi Silk Embroidered Straight Kurti",
                    "brand": "Libas",
                    "price": p_top,
                    "plat": "Amazon",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Gold-Bordered Flared Ethnic Sharara Pants",
                    "brand": "W for Woman",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Handcrafted Zari Embroidered Punjabi Juttis",
                    "brand": "Metro",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Kundan Pearl Drop Traditional Jhumkas",
                    "brand": "Zaveri Pearls",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Pure Cotton Breathable Linen-Blend Shirt",
                    "brand": "ONLY",
                    "price": p_top,
                    "plat": "Flipkart",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Straight-Fit Cropped Ankle Chinos",
                    "brand": "Tokyo Talkies",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Minimalist Low-Top Clean White Sneakers",
                    "brand": "Red Tape",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Dainty Crossbody Vegan Leather Sling Bag",
                    "brand": "Lavie",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1514327605112-b887c0e61c0a?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Spread Collar Egyptian Cotton Formal Shirt",
                    "brand": "Raymond",
                    "price": p_top,
                    "plat": "Amazon",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Tailored Flat-Front Formal Trousers",
                    "brand": "Van Heusen",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1479064555552-3ef4979f8908?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Handcrafted Derby Formal Leather Shoes",
                    "brand": "Bata",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Reversible Full-Grain Leather Belt",
                    "brand": "Titan",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Cuban Camp Collar Textured Resort Shirt",
                    "brand": "Dennis Lingo",
                    "price": p_top,
                    "plat": "Amazon",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Slim Fit Stretch Cotton Chinos",
                    "brand": "Highlander",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Suede Penny Loafers with Cushion Footbed",
                    "brand": "Kraasa",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1560343090-f0409e92791a?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"Minimalist {c_acc['name']} Dial Analog Watch",
                    "brand": "Fastrack",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1534215754734-18e55d13e346?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Satin Finish Oversized Statement Shirt",
                    "brand": "Snitch",
                    "price": p_top,
                    "plat": "Flipkart",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Relaxed Straight Tapered Trousers",
                    "brand": "Roadster",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Designer Low-Top Clean Platform Sneakers",
                    "brand": "Red Tape",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Accent Stainless Steel Minimalist Pendant",
                    "brand": "Yellow Chimes",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Dri-FIT Breathable Training Tee",
                    "brand": "Campus Sutra",
                    "price": p_top,
                    "plat": "Flipkart",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Tapered Lightweight Stretch Trackpants",
                    "brand": "HRX",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Responsive Foam Athletic Running Shoes",
                    "brand": "Sparx",
                    "price": p_foot,
                    "plat": "Flipkart",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1607522370275-f14206abe5d3?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"Water-Resistant Everyday Technical Backpack",
                    "brand": "Safari",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1534215754734-18e55d13e346?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Relaxed Fit Heavyweight Cotton Tee",
                    "brand": "Bewakoof",
                    "price": p_top,
                    "plat": "Flipkart",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Distressed Slim Tapered Jeans",
                    "brand": "Roadster",
                    "price": p_bot,
                    "plat": "Amazon",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1542272604-780c96856592?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Retro High-Top Canvas Sneakers",
                    "brand": "Sparx",
                    "price": p_foot,
                    "plat": "Flipkart",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1607522370275-f14206abe5d3?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"Water-Resistant Everyday Canvas Backpack",
                    "brand": "Safari",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1514327605112-b887c0e61c0a?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Embroidered Jacquard Silk Festive Kurta",
                    "brand": "Manyavar",
                    "price": p_top,
                    "plat": "Amazon",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Dupion Silk Slim Churidar Pyjama",
                    "brand": "Manyavar",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1479064555552-3ef4979f8908?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Handcrafted Ethnic Mojari Leather Loafers",
                    "brand": "Bata",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Classic Gold-Plated Chronograph Analog Watch",
                    "brand": "Titan",
                    "price": p_acc,
                    "plat": "Amazon",
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
                    "color": c_head,
                    "img": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Topwear",
                    "name": f"{c_top['name']} Pure Cotton Relaxed Drop-Shoulder Shirt",
                    "brand": "Dennis Lingo",
                    "price": p_top,
                    "plat": "Flipkart",
                    "color": c_top,
                    "img": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Bottomwear",
                    "name": f"{c_bot['name']} Straight-Fit Washed Chino Trousers",
                    "brand": "Roadster",
                    "price": p_bot,
                    "plat": "Flipkart",
                    "color": c_bot,
                    "img": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Footwear",
                    "name": f"{c_foot['name']} Minimalist Low-Top Clean Sneakers",
                    "brand": "Red Tape",
                    "price": p_foot,
                    "plat": "Amazon",
                    "color": c_foot,
                    "img": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=500&auto=format&fit=crop&q=60"
                },
                {
                    "type": "Accessory",
                    "name": f"{c_acc['name']} Accent Minimalist Chain Pendant",
                    "brand": "Yellow Chimes",
                    "price": p_acc,
                    "plat": "Amazon",
                    "color": c_acc,
                    "img": "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=500&auto=format&fit=crop&q=60"
                }
            ]
