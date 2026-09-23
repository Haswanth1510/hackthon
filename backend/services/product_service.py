import urllib.parse
import os
from typing import List, Dict, Any, Optional


class ProductService:
    """
    AI-Driven Product Recommendation Engine.
    Uses the AI's detected skin issues and recommended ingredients to build
    precise, live Amazon India / Flipkart search URLs with the affiliate tag.
    All product suggestions are AI-personalised — no static hardcoded picks.
    """

    # Maps AI-detected issue_type keywords → best clinical ingredient(s) to search
    ISSUE_TO_INGREDIENTS: Dict[str, List[str]] = {
        "acne":             ["Salicylic Acid", "Niacinamide", "Benzoyl Peroxide"],
        "blemish":          ["Niacinamide", "Alpha Arbutin", "Kojic Acid"],
        "pore":             ["Salicylic Acid", "Niacinamide", "Retinol"],
        "oilin":            ["Niacinamide", "Salicylic Acid"],
        "dark spot":        ["Vitamin C", "Alpha Arbutin", "Kojic Acid"],
        "hyperpigment":     ["Vitamin C", "Alpha Arbutin", "Niacinamide"],
        "dull":             ["Vitamin C", "Glycolic Acid", "Niacinamide"],
        "uneven":           ["Vitamin C", "AHA", "Niacinamide"],
        "dryness":          ["Hyaluronic Acid", "Ceramide", "Squalane"],
        "barrier":          ["Ceramide", "Panthenol", "Squalane"],
        "redness":          ["Centella Asiatica", "Ceramide", "Azelaic Acid"],
        "sensitiv":         ["Centella Asiatica", "Oat Extract", "Ceramide"],
        "wrinkle":          ["Retinol", "Peptide", "Hyaluronic Acid"],
        "fine line":        ["Retinol", "Peptide", "Vitamin C"],
        "dark circle":      ["Caffeine", "Vitamin C", "Peptide"],
        "puffiness":        ["Caffeine", "Peptide"],
        "texture":          ["AHA", "BHA", "Retinol"],
        "sun damage":       ["Vitamin C", "Niacinamide", "SPF"],
        "tan":              ["Kojic Acid", "Vitamin C", "Glycolic Acid"],
    }

    # Maps ingredient → product candidates with AI-targeted search queries
    INGREDIENT_TO_PRODUCTS: Dict[str, List[Dict[str, Any]]] = {
        "Salicylic Acid": [
            {"category": "Cleanser",      "query": "Salicylic Acid 2% face wash acne oily skin India", "platform": "Amazon",   "price_inr": 299},
            {"category": "Serum",         "query": "Salicylic Acid BHA serum acne pores India",        "platform": "Amazon",   "price_inr": 449},
        ],
        "Niacinamide": [
            {"category": "Serum",         "query": "Niacinamide 10% face serum pores oil control India","platform": "Amazon",  "price_inr": 399},
            {"category": "Moisturizer",   "query": "Niacinamide moisturizer brightening India",         "platform": "Amazon",  "price_inr": 349},
        ],
        "Vitamin C": [
            {"category": "Serum",         "query": "Vitamin C face serum brightening 15% glow India",  "platform": "Amazon",   "price_inr": 550},
            {"category": "Cleanser",      "query": "Vitamin C face wash glow radiance India",          "platform": "Flipkart", "price_inr": 249},
        ],
        "Hyaluronic Acid": [
            {"category": "Serum",         "query": "Hyaluronic Acid serum 2% hydration India",         "platform": "Amazon",   "price_inr": 499},
            {"category": "Moisturizer",   "query": "Hyaluronic Acid water gel moisturizer India",      "platform": "Amazon",   "price_inr": 480},
        ],
        "Ceramide": [
            {"category": "Moisturizer",   "query": "Ceramide moisturizer barrier repair skin India",   "platform": "Amazon",   "price_inr": 499},
            {"category": "Cleanser",      "query": "Ceramide gentle cleanser sensitive dry skin India", "platform": "Flipkart","price_inr": 365},
        ],
        "Retinol": [
            {"category": "Serum",         "query": "Retinol serum anti aging wrinkle India",           "platform": "Amazon",   "price_inr": 699},
        ],
        "Alpha Arbutin": [
            {"category": "Serum",         "query": "Alpha Arbutin 2% dark spot serum India",           "platform": "Amazon",   "price_inr": 449},
        ],
        "Kojic Acid": [
            {"category": "Serum",         "query": "Kojic Acid face serum hyperpigmentation India",    "platform": "Amazon",   "price_inr": 399},
            {"category": "Cleanser",      "query": "Kojic Acid face wash dark spots India",            "platform": "Flipkart", "price_inr": 249},
        ],
        "Centella Asiatica": [
            {"category": "Serum",         "query": "Centella Asiatica cica serum calming redness India","platform": "Amazon",  "price_inr": 499},
            {"category": "Moisturizer",   "query": "Centella cica cream soothing India",               "platform": "Amazon",   "price_inr": 399},
        ],
        "Caffeine": [
            {"category": "Eye Care",      "query": "Caffeine eye serum dark circles puffiness India",  "platform": "Amazon",   "price_inr": 499},
        ],
        "Peptide": [
            {"category": "Serum",         "query": "Peptide collagen anti aging serum India",          "platform": "Amazon",   "price_inr": 649},
            {"category": "Eye Care",      "query": "Peptide eye cream fine lines India",               "platform": "Flipkart", "price_inr": 449},
        ],
        "Glycolic Acid": [
            {"category": "Exfoliant",     "query": "Glycolic Acid toner AHA exfoliant India",          "platform": "Amazon",   "price_inr": 499},
        ],
        "AHA": [
            {"category": "Exfoliant",     "query": "AHA BHA exfoliating toner face India",             "platform": "Amazon",   "price_inr": 499},
        ],
        "Benzoyl Peroxide": [
            {"category": "Spot Treatment","query": "Benzoyl Peroxide acne spot treatment gel India",   "platform": "Amazon",   "price_inr": 299},
        ],
        "Azelaic Acid": [
            {"category": "Serum",         "query": "Azelaic Acid serum redness rosacea India",         "platform": "Amazon",   "price_inr": 549},
        ],
        "Squalane": [
            {"category": "Moisturizer",   "query": "Squalane face oil moisturizer plumping India",     "platform": "Amazon",   "price_inr": 599},
        ],
        "Panthenol": [
            {"category": "Moisturizer",   "query": "Panthenol B5 moisturizer barrier India",           "platform": "Amazon",   "price_inr": 399},
        ],
        "SPF": [
            {"category": "Sunscreen",     "query": "SPF 50 PA++++ sunscreen no white cast India",      "platform": "Amazon",   "price_inr": 399},
        ],
    }

    SUNSCREEN_FALLBACK = {
        "category": "Sunscreen",
        "query": "SPF 50 PA++++ sunscreen broad spectrum no white cast India",
        "platform": "Amazon",
        "price_inr": 399,
        "reason": (
            "Daily SPF 50+ PA++++ is clinically essential to prevent UV-induced "
            "pigmentation and protect active ingredient treatments from degradation."
        ),
    }

    @classmethod
    def generate_affiliate_url(cls, platform: str, query: str) -> str:
        """Constructs a live deep-link Amazon India / Flipkart search URL with affiliate tag."""
        amazon_tag = os.getenv("AMAZON_AFFILIATE_TAG", "stylicai21-21")
        flipkart_id = os.getenv("FLIPKART_AFFILIATE_ID", "skincarefashion")
        encoded_query = urllib.parse.quote_plus(query)
        if platform.lower() == "flipkart":
            return (
                f"https://www.flipkart.com/search?q={encoded_query}"
                f"&affid={flipkart_id}&otracker=search&marketplace=FLIPKART"
            )
        return f"https://www.amazon.in/s?k={encoded_query}&tag={amazon_tag}"

    @classmethod
    def match_products(
        cls,
        detected_issues: List[Dict[str, Any]],
        max_budget_inr: Optional[float] = None,
        skin_type: str = "Combination",
        recommended_ingredients: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        AI-Driven product matching:
        1. Uses AI's recommended_ingredients as the primary signal (highest priority).
        2. Falls back to detected issue_type → ingredient mapping.
        3. Each ingredient maps to a targeted Amazon/Flipkart live search URL.
        4. Deduplicates by category. Always includes sunscreen.
        """
        # ── Step 1: Build prioritised ingredient list ───────────────────────────
        priority_ingredients: List[str] = []

        # Primary: AI-returned recommended_ingredients
        if recommended_ingredients:
            for ing in recommended_ingredients:
                ing_clean = ing.strip()
                if ing_clean in cls.INGREDIENT_TO_PRODUCTS:
                    if ing_clean not in priority_ingredients:
                        priority_ingredients.append(ing_clean)
                else:
                    # Fuzzy match e.g. "Salicylic Acid 2%" → "Salicylic Acid"
                    for known in cls.INGREDIENT_TO_PRODUCTS:
                        if known.lower() in ing_clean.lower() or ing_clean.lower() in known.lower():
                            if known not in priority_ingredients:
                                priority_ingredients.append(known)
                            break

        # Secondary: issue-type → ingredient mapping
        issue_names = [i.get("issue_type", "").lower() for i in detected_issues]
        for issue in issue_names:
            for keyword, ings in cls.ISSUE_TO_INGREDIENTS.items():
                if keyword in issue:
                    for ing in ings:
                        if ing in cls.INGREDIENT_TO_PRODUCTS and ing not in priority_ingredients:
                            priority_ingredients.append(ing)

        # ── Step 2: Build one product per category ──────────────────────────────
        matched: List[Dict[str, Any]] = []
        categories_filled: set = set()

        for ingredient in priority_ingredients:
            if len(matched) >= 5:
                break
            for candidate in cls.INGREDIENT_TO_PRODUCTS.get(ingredient, []):
                cat = candidate["category"]
                if cat in categories_filled:
                    continue

                price = candidate["price_inr"]
                if max_budget_inr and max_budget_inr > 0:
                    if price > max_budget_inr * 1.25 and len(matched) >= 2:
                        continue

                categories_filled.add(cat)
                query = candidate["query"]
                platform = candidate["platform"]
                affiliate_url = cls.generate_affiliate_url(platform, query)

                linked_issues = [
                    iss for iss, ings in cls.ISSUE_TO_INGREDIENTS.items()
                    if ingredient in ings and any(iss in issue for issue in issue_names)
                ]
                reason = (
                    f"AI-recommended {ingredient} to target your detected "
                    f"{', '.join(linked_issues) if linked_issues else 'skin concerns'}. "
                    f"Click to shop live {platform} results with affiliate savings."
                )

                matched.append({
                    "category":         cat,
                    "title":            f"{ingredient} – AI-Matched {cat}",
                    "brand":            "AI Recommended · Live Amazon Search",
                    "price_inr":        float(price),
                    "rating":           4.5,
                    "platform":         platform,
                    "search_query":     query,
                    "product_url":      affiliate_url,
                    "target_issue":     linked_issues[0] if linked_issues else "Skin Health",
                    "target_issues":    linked_issues or ["Skin Health"],
                    "reason":           reason,
                    "image_url":        (
                        "https://images.unsplash.com/photo-1620916566398-39f1143ab7be"
                        "?w=500&auto=format&fit=crop&q=60"
                    ),
                    "ingredient_focus": ingredient,
                    "shop_note":        f"🔍 Live Amazon India search: '{ingredient}'",
                })
                break

        # ── Step 3: Always add sunscreen if not present ─────────────────────────
        if "Sunscreen" not in categories_filled:
            sun = cls.SUNSCREEN_FALLBACK
            ok_budget = (
                not max_budget_inr
                or max_budget_inr <= 0
                or sun["price_inr"] <= max_budget_inr * 1.25
            )
            if ok_budget:
                affiliate_url = cls.generate_affiliate_url(sun["platform"], sun["query"])
                matched.append({
                    "category":         "Sunscreen",
                    "title":            "SPF 50+ PA++++ Broad-Spectrum – AI Essential",
                    "brand":            "AI Recommended · Live Amazon Search",
                    "price_inr":        float(sun["price_inr"]),
                    "rating":           4.7,
                    "platform":         sun["platform"],
                    "search_query":     sun["query"],
                    "product_url":      affiliate_url,
                    "target_issue":     "UV Protection",
                    "target_issues":    ["UV Protection", "Dark Spots & Hyperpigmentation"],
                    "reason":           sun["reason"],
                    "image_url":        (
                        "https://images.unsplash.com/photo-1563178406-4cdc2923acbc"
                        "?w=500&auto=format&fit=crop&q=60"
                    ),
                    "ingredient_focus": "SPF",
                    "shop_note":        "🔍 Live Amazon India search: SPF 50 sunscreens",
                })

        return matched[:5]
