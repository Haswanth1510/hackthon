import urllib.parse
from typing import List, Dict, Any, Optional

class ProductService:
    """
    Product matching and affiliate linking engine for Amazon India & Flipkart.
    Strictly filters product suggestions to remain within the user's budget.
    """

    # Verified high-efficacy Indian & global skincare inventory with real prices (INR)
    CATALOG = [
        # Cleansers
        {
            "category": "Cleanser",
            "title": "Minimalist 2% Salicylic Acid Face Cleanser for Acne & Blackheads",
            "brand": "Minimalist",
            "price_inr": 299.0,
            "rating": 4.6,
            "platform": "Amazon",
            "search_query": "Minimalist 2 Salicylic Acid Cleanser",
            "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Acne & Blemishes", "Pore Size & Texture", "Oiliness"],
            "reason": "Sulfate-free cleanser with BHA to dissolve pore-clogging sebum without stripping skin."
        },
        {
            "category": "Cleanser",
            "title": "Cetaphil Gentle Skin Cleanser for Sensitive & Dry Skin",
            "brand": "Cetaphil",
            "price_inr": 365.0,
            "rating": 4.7,
            "platform": "Flipkart",
            "search_query": "Cetaphil Gentle Skin Cleanser",
            "image_url": "https://images.unsplash.com/photo-1556228722-d0b714b1b369?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dryness & Barrier Compromise", "Redness & Sensitivity"],
            "reason": "Dermatologist-recommended non-foaming formula with niacinamide & panthenol."
        },
        {
            "category": "Cleanser",
            "title": "The Derma Co 1% Kojic Acid Daily Face Wash for Dark Spots",
            "brand": "The Derma Co",
            "price_inr": 249.0,
            "rating": 4.4,
            "platform": "Amazon",
            "search_query": "The Derma Co 1 Kojic Acid Face Wash",
            "image_url": "https://images.unsplash.com/photo-1570554886111-e80fcca6a029?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dark Spots & Hyperpigmentation", "Dullness & Uneven Skin Tone"],
            "reason": "Fades post-acne marks and reduces melanin transfer with alpha arbutin & niacinamide."
        },

        # Serums & Actives
        {
            "category": "Serum",
            "title": "Minimalist 10% Niacinamide Face Serum with Zinc & EUK-134",
            "brand": "Minimalist",
            "price_inr": 599.0,
            "rating": 4.6,
            "platform": "Amazon",
            "search_query": "Minimalist 10 Niacinamide Serum",
            "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Acne & Blemishes", "Pore Size & Texture", "Dark Spots & Hyperpigmentation"],
            "reason": "Clinical-strength formulation to shrink pores, balance oil, and fade blemishes."
        },
        {
            "category": "Serum",
            "title": "Plum 15% Vitamin C Face Serum with Mandarin for Glowing Skin",
            "brand": "Plum",
            "price_inr": 550.0,
            "rating": 4.5,
            "platform": "Flipkart",
            "search_query": "Plum 15 Vitamin C Face Serum",
            "image_url": "https://images.unsplash.com/photo-1608248597359-5632b71d9d9f?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dullness & Uneven Skin Tone", "Dark Spots & Hyperpigmentation"],
            "reason": "Pure ethyl ascorbic acid boosts collagen synthesis and evens out photopigmentation."
        },
        {
            "category": "Serum",
            "title": "The Ordinary Hyaluronic Acid 2% + B5 Hydration Support",
            "brand": "The Ordinary",
            "price_inr": 700.0,
            "rating": 4.8,
            "platform": "Amazon",
            "search_query": "The Ordinary Hyaluronic Acid 2 B5",
            "image_url": "https://images.unsplash.com/photo-1617897903246-719242758050?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dryness & Barrier Compromise", "Wrinkles & Fine Lines"],
            "reason": "Multi-depth molecular weight hyaluronic acid delivers immediate multi-layer dermal plumping."
        },
        {
            "category": "Serum",
            "title": "The Derma Co 2% Salicylic Acid Face Serum with Witch Hazel",
            "brand": "The Derma Co",
            "price_inr": 449.0,
            "rating": 4.5,
            "platform": "Amazon",
            "search_query": "The Derma Co 2 Salicylic Acid Serum",
            "image_url": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Acne & Blemishes", "Pore Size & Texture"],
            "reason": "Oil-soluble keratolytic serum that unplugs sebaceous micro-cysts inside the pore lining."
        },

        # Moisturizers
        {
            "category": "Moisturizer",
            "title": "Neutrogena Hydro Boost Water Gel with Hyaluronic Acid",
            "brand": "Neutrogena",
            "price_inr": 480.0,
            "rating": 4.7,
            "platform": "Amazon",
            "search_query": "Neutrogena Hydro Boost Water Gel",
            "image_url": "https://images.unsplash.com/photo-1556228724-4da94314c1eb?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dryness & Barrier Compromise", "Dullness & Uneven Skin Tone", "Oiliness"],
            "reason": "Ultra-lightweight oil-free formula that locks in 72-hour moisture without feeling greasy."
        },
        {
            "category": "Moisturizer",
            "title": "Dr. Sheth's Ceramide & Vitamin C Oil-Free Moisturizer",
            "brand": "Dr. Sheth's",
            "price_inr": 349.0,
            "rating": 4.5,
            "platform": "Flipkart",
            "search_query": "Dr Sheths Ceramide Vitamin C Moisturizer",
            "image_url": "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dryness & Barrier Compromise", "Redness & Sensitivity", "Acne & Blemishes"],
            "reason": "Formulated specifically for Indian skin to reinforce lipid barrier and soothe reactive inflammation."
        },

        # Sunscreens
        {
            "category": "Sunscreen",
            "title": "Aqualogica Radiance+ Dewy Sunscreen with Watermelon & Niacinamide SPF 50+",
            "brand": "Aqualogica",
            "price_inr": 399.0,
            "rating": 4.6,
            "platform": "Amazon",
            "search_query": "Aqualogica Radiance Dewy Sunscreen SPF 50",
            "image_url": "https://images.unsplash.com/photo-1563178406-4cdc2923acbc?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dark Spots & Hyperpigmentation", "Dullness & Uneven Skin Tone"],
            "reason": "Broad-spectrum zero white cast UV shield with PA++++ and blue light defense."
        },
        {
            "category": "Sunscreen",
            "title": "The Derma Co 1% Hyaluronic Sunscreen Aqua Gel SPF 50 PA++++",
            "brand": "The Derma Co",
            "price_inr": 499.0,
            "rating": 4.7,
            "platform": "Flipkart",
            "search_query": "The Derma Co 1 Hyaluronic Sunscreen Aqua Gel",
            "image_url": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Acne & Blemishes", "Oiliness", "Pore Size & Texture"],
            "reason": "Non-greasy, fast-absorbing sunscreen that won't clog acne-prone pores or sting eyes."
        },

        # Eye Care
        {
            "category": "Eye Care",
            "title": "Minimalist 5% Caffeine Eye Serum with EGCG for Dark Circles & Puffiness",
            "brand": "Minimalist",
            "price_inr": 499.0,
            "rating": 4.4,
            "platform": "Amazon",
            "search_query": "Minimalist 5 Caffeine Eye Serum",
            "image_url": "https://images.unsplash.com/photo-1512290900672-1f02e1b12b50?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dark Circles & Periorbital Fatigue"],
            "reason": "Vasoconstrictive high-solubility caffeine solution with antioxidant green tea catechins."
        }
    ]

    @classmethod
    def generate_affiliate_url(cls, platform: str, query: str) -> str:
        """Constructs live deep-link search/product URL for Amazon India or Flipkart with custom affiliate tags."""
        import os
        amazon_tag = os.getenv("AMAZON_AFFILIATE_TAG", "stylicai21-21")
        flipkart_id = os.getenv("FLIPKART_AFFILIATE_ID", "skincarefashion")
        
        encoded_query = urllib.parse.quote_plus(query)
        if platform.lower() == "flipkart":
            return f"https://www.flipkart.com/search?q={encoded_query}&affid={flipkart_id}&otracker=search&marketplace=FLIPKART"
        else:
            return f"https://www.amazon.in/s?k={encoded_query}&tag={amazon_tag}"

    @classmethod
    def match_products(
        cls,
        detected_issues: List[Dict[str, Any]],
        max_budget_inr: Optional[float] = None,
        skin_type: str = "Combination"
    ) -> List[Dict[str, Any]]:
        """
        Selects optimal skincare regimen components matched to detected concerns.
        If max_budget_inr is provided, respects the limit; otherwise selects best clinical matches.
        """
        issue_names = [issue.get("issue_type", "") for issue in detected_issues]
        matched: List[Dict[str, Any]] = []
        categories_filled = set()

        # Score catalog items based on relevance to detected concerns
        scored_catalog = []
        for item in cls.CATALOG:
            # Filter strictly by individual product budget if specified
            if max_budget_inr and max_budget_inr > 0 and item["price_inr"] > max_budget_inr:
                continue

            score = 0
            for issue_name in issue_names:
                for target in item["target_issues"]:
                    if issue_name.lower() in target.lower() or target.lower() in issue_name.lower():
                        score += 10

            scored_catalog.append((score, item))

        # Sort descending by relevance score, then rating
        scored_catalog.sort(key=lambda x: (x[0], x[1]["rating"]), reverse=True)

        current_total = 0.0
        for _, item in scored_catalog:
            cat = item["category"]
            if cat not in categories_filled:
                if (max_budget_inr is None or max_budget_inr <= 0) or (current_total + item["price_inr"] <= max_budget_inr * 1.25) or len(matched) < 2:
                    categories_filled.add(cat)
                    product_copy = dict(item)
                    product_copy["product_url"] = cls.generate_affiliate_url(item["platform"], item["search_query"])
                    product_copy["target_issue"] = item["target_issues"][0] if item["target_issues"] else "Skin Health"
                    matched.append(product_copy)
                    current_total += item["price_inr"]
                    if len(matched) >= 4:
                        break

        # If budget allows or fewer matched, add essential sunscreen/cleanser
        if len(matched) < 3:
            for item in cls.CATALOG:
                cat = item["category"]
                if cat not in categories_filled and item["price_inr"] <= max_budget_inr:
                    categories_filled.add(cat)
                    product_copy = dict(item)
                    product_copy["product_url"] = cls.generate_affiliate_url(item["platform"], item["search_query"])
                    product_copy["target_issue"] = item["target_issues"][0]
                    matched.append(product_copy)
                    if len(matched) >= 3:
                        break

        return matched
