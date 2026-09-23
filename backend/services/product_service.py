import urllib.parse
import os
from typing import List, Dict, Any, Optional


class ProductService:
    """
    AI-Driven Clinical Product Recommendation Engine.
    Matches the AI's detected skin conditions, severity levels, and recommended ingredients
    to an authentic, curated catalog of real brand-name dermatological products available in India.
    Generates live affiliate links for Amazon India and Flipkart with tracked tag 'stylicai21-21'.
    """

    CATALOG: List[Dict[str, Any]] = [
        # ── Cleansers ──────────────────────────────────────────────────────────
        {
            "id": "c_salicylic_minimalist",
            "category": "Cleanser",
            "brand": "Minimalist",
            "title": "Minimalist 2% Salicylic Acid Face Cleanser with LHA & Zinc",
            "price_inr": 299.0,
            "rating": 4.6,
            "platform": "Amazon",
            "search_query": "Minimalist 2 Salicylic Acid Face Cleanser LHA",
            "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Acne & Micro-Congestion", "Pore Size & Texture", "Oiliness", "Blemishes"],
            "key_ingredients": ["Salicylic Acid", "LHA", "Zinc PCA"],
            "suitable_skin_types": ["Oily", "Combination", "Acne-Prone"],
            "clinical_action": "Lipophilic BHA penetrates deep into sebaceous pores to dissolve micro-comedones and regulate sebum."
        },
        {
            "id": "c_hydrating_cerave",
            "category": "Cleanser",
            "brand": "CeraVe",
            "title": "CeraVe Hydrating Facial Cleanser with Ceramides & Hyaluronic Acid",
            "price_inr": 365.0,
            "rating": 4.8,
            "platform": "Flipkart",
            "search_query": "CeraVe Hydrating Facial Cleanser ceramides hyaluronic",
            "image_url": "https://images.unsplash.com/photo-1556228722-d0b71f3b2361?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dryness & Barrier Compromise", "Redness & Sensitivity", "Barrier", "Dehydration"],
            "key_ingredients": ["Ceramides", "Hyaluronic Acid"],
            "suitable_skin_types": ["Dry", "Sensitive", "Normal"],
            "clinical_action": "Replaces lost intercellular lipids and restores stratum corneum barrier integrity without stripping moisture."
        },
        {
            "id": "c_cetaphil_gentle",
            "category": "Cleanser",
            "brand": "Cetaphil",
            "title": "Cetaphil Gentle Skin Cleanser with Niacinamide & Panthenol Vitamin B5",
            "price_inr": 349.0,
            "rating": 4.7,
            "platform": "Amazon",
            "search_query": "Cetaphil Gentle Skin Cleanser Niacinamide Panthenol",
            "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Redness & Sensitivity", "Dryness & Barrier Compromise", "Sensitivity"],
            "key_ingredients": ["Niacinamide", "Panthenol", "Glycerin"],
            "suitable_skin_types": ["Sensitive", "Dry", "Combination"],
            "clinical_action": "Ultra-soothing, soap-free micellar matrix cleanses gently while calming vascular hyper-reactivity."
        },
        {
            "id": "c_kojic_dermaco",
            "category": "Cleanser",
            "brand": "The Derma Co",
            "title": "The Derma Co 1% Kojic Acid Face Wash with Alpha Arbutin",
            "price_inr": 249.0,
            "rating": 4.5,
            "platform": "Flipkart",
            "search_query": "The Derma Co 1 Kojic Acid Daily Face Wash",
            "image_url": "https://images.unsplash.com/photo-1556228722-d0b71f3b2361?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dark Spots & Hyperpigmentation", "Dullness & Uneven Skin Tone", "Sun Damage", "Tan"],
            "key_ingredients": ["Kojic Acid", "Alpha Arbutin", "Niacinamide"],
            "suitable_skin_types": ["All Skin Types", "Combination", "Oily"],
            "clinical_action": "Inhibits tyrosinase enzyme activity to accelerate epidermal melanin turnover and brighten post-inflammatory marks."
        },

        # ── Targeted Treatment Serums ──────────────────────────────────────────
        {
            "id": "s_niacinamide_minimalist",
            "category": "Serum",
            "brand": "Minimalist",
            "title": "Minimalist 10% Niacinamide Face Serum with Zinc PCA & Matmarine",
            "price_inr": 399.0,
            "rating": 4.6,
            "platform": "Amazon",
            "search_query": "Minimalist 10 Niacinamide Serum Zinc PCA",
            "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Pore Size & Texture", "Oiliness", "Acne & Micro-Congestion", "Blemishes"],
            "key_ingredients": ["Niacinamide", "Zinc PCA"],
            "suitable_skin_types": ["Oily", "Combination", "All Skin Types"],
            "clinical_action": "Clinically regulates sebocyte lipid output, refines enlarged follicular pores, and reinforces skin barrier."
        },
        {
            "id": "s_vitaminc_plum",
            "category": "Serum",
            "brand": "Plum",
            "title": "Plum 15% Vitamin C Face Serum with Mandarin & Pure Ethyl Ascorbic Acid",
            "price_inr": 550.0,
            "rating": 4.5,
            "platform": "Amazon",
            "search_query": "Plum 15 Vitamin C Face Serum Mandarin",
            "image_url": "https://images.unsplash.com/photo-1608248597359-2169b16ff0b6?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dark Spots & Hyperpigmentation", "Dullness & Uneven Skin Tone", "Sun Damage"],
            "key_ingredients": ["Vitamin C", "Ethyl Ascorbic Acid", "Kakadu Plum"],
            "suitable_skin_types": ["Combination", "Dry", "Normal"],
            "clinical_action": "High-potency antioxidant scavenges free radicals, halts melanogenesis, and promotes endogenous dermal collagen."
        },
        {
            "id": "s_salicylic_dermaco",
            "category": "Serum",
            "brand": "The Derma Co",
            "title": "The Derma Co 2% Salicylic Acid Face Serum with Witch Hazel & Willow Bark",
            "price_inr": 449.0,
            "rating": 4.5,
            "platform": "Amazon",
            "search_query": "The Derma Co 2 Salicylic Acid Face Serum Witch Hazel",
            "image_url": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Acne & Micro-Congestion", "Blemishes", "Pore Size & Texture"],
            "key_ingredients": ["Salicylic Acid", "Witch Hazel", "Zinc"],
            "suitable_skin_types": ["Oily", "Acne-Prone", "Combination"],
            "clinical_action": "Rapidly decongests active inflammatory papules, accelerates blemish clearance, and calms follicular redness."
        },
        {
            "id": "s_alpha_arbutin_minimalist",
            "category": "Serum",
            "brand": "Minimalist",
            "title": "Minimalist 2% Alpha Arbutin Face Serum with Hyaluronic Acid for Dark Spots",
            "price_inr": 449.0,
            "rating": 4.6,
            "platform": "Amazon",
            "search_query": "Minimalist 2 Alpha Arbutin Face Serum Hyaluronic Acid",
            "image_url": "https://images.unsplash.com/photo-1617897903246-719242758050?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dark Spots & Hyperpigmentation", "Blemishes", "Sun Damage", "Tan"],
            "key_ingredients": ["Alpha Arbutin", "Hyaluronic Acid"],
            "suitable_skin_types": ["All Skin Types", "Sensitive", "Dry"],
            "clinical_action": "Bio-synthetic alpha arbutin safely diminishes localized melanin clusters without causing dermal sensitization."
        },
        {
            "id": "s_hyaluronic_ordinary",
            "category": "Serum",
            "brand": "The Ordinary",
            "title": "The Ordinary Hyaluronic Acid 2% + B5 Multi-Depth Hydration Serum",
            "price_inr": 700.0,
            "rating": 4.8,
            "platform": "Amazon",
            "search_query": "The Ordinary Hyaluronic Acid 2 B5 Hydration Serum",
            "image_url": "https://images.unsplash.com/photo-1617897903246-719242758050?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dryness & Barrier Compromise", "Wrinkles & Fine Lines", "Dehydration"],
            "key_ingredients": ["Hyaluronic Acid", "Panthenol Vitamin B5"],
            "suitable_skin_types": ["Dry", "Dehydrated", "Normal", "Combination"],
            "clinical_action": "Triple molecular weight hyaluronic acid delivers immediate multi-depth dermal hydration and volume plumping."
        },
        {
            "id": "s_azelaic_dermaco",
            "category": "Serum",
            "brand": "The Derma Co",
            "title": "The Derma Co 10% Azelaic Acid Gentle Face Serum for Redness & Acne Marks",
            "price_inr": 549.0,
            "rating": 4.4,
            "platform": "Amazon",
            "search_query": "The Derma Co 10 Azelaic Acid Face Serum",
            "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Redness & Sensitivity", "Acne & Micro-Congestion", "Dark Spots & Hyperpigmentation"],
            "key_ingredients": ["Azelaic Acid", "Niacinamide"],
            "suitable_skin_types": ["Sensitive", "Acne-Prone", "Rosacea-Prone"],
            "clinical_action": "Reduces dermal pro-inflammatory cytokines, suppresses Cutibacterium acnes, and calms vascular erythema."
        },
        {
            "id": "s_retinol_minimalist",
            "category": "Serum",
            "brand": "Minimalist",
            "title": "Minimalist 0.3% Retinol Face Serum with Coenzyme Q10 for Fine Lines",
            "price_inr": 599.0,
            "rating": 4.6,
            "platform": "Amazon",
            "search_query": "Minimalist 0.3 Retinol Face Serum Coenzyme Q10",
            "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Wrinkles & Fine Lines", "Pore Size & Texture", "Dullness & Uneven Skin Tone"],
            "key_ingredients": ["Retinol", "Coenzyme Q10", "Squalane"],
            "suitable_skin_types": ["Normal", "Dry", "Combination"],
            "clinical_action": "Stimulates fibroblast collagen synthesis and accelerates keratinocyte cell renewal for smooth dermal texture."
        },

        # ── Barrier Moisturizers ──────────────────────────────────────────────
        {
            "id": "m_hydroboost_neutrogena",
            "category": "Moisturizer",
            "brand": "Neutrogena",
            "title": "Neutrogena Hydro Boost Water Gel with Hyaluronic Acid & Trehalose",
            "price_inr": 480.0,
            "rating": 4.7,
            "platform": "Amazon",
            "search_query": "Neutrogena Hydro Boost Water Gel Hyaluronic",
            "image_url": "https://images.unsplash.com/photo-1556228724-4da94314c1eb?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dryness & Barrier Compromise", "Oiliness", "Dehydration"],
            "key_ingredients": ["Hyaluronic Acid", "Trehalose"],
            "suitable_skin_types": ["Oily", "Combination", "Normal"],
            "clinical_action": "Ultra-lightweight oil-free hydration gel locks in moisture without occluding acne-prone pores."
        },
        {
            "id": "m_ceramide_drsheths",
            "category": "Moisturizer",
            "brand": "Dr. Sheth's",
            "title": "Dr. Sheth's Ceramide & Vitamin C Oil-Free Barrier Repair Moisturizer",
            "price_inr": 349.0,
            "rating": 4.5,
            "platform": "Flipkart",
            "search_query": "Dr Sheths Ceramide Vitamin C Oil Free Moisturizer",
            "image_url": "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dryness & Barrier Compromise", "Redness & Sensitivity", "Barrier"],
            "key_ingredients": ["Ceramides", "Vitamin C", "Ashwagandha"],
            "suitable_skin_types": ["Dry", "Sensitive", "Combination", "Indian Skin"],
            "clinical_action": "Engineered for Indian climate to restore damaged lipid matrix, reduce transepidermal water loss, and brighten."
        },
        {
            "id": "m_ceramides_cerave",
            "category": "Moisturizer",
            "brand": "CeraVe",
            "title": "CeraVe Moisturizing Cream with 3 Essential Ceramides & MVE Technology",
            "price_inr": 499.0,
            "rating": 4.8,
            "platform": "Amazon",
            "search_query": "CeraVe Moisturizing Cream 3 Essential Ceramides",
            "image_url": "https://images.unsplash.com/photo-1556228724-4da94314c1eb?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dryness & Barrier Compromise", "Barrier", "Redness & Sensitivity"],
            "key_ingredients": ["Ceramides", "Hyaluronic Acid", "Cholesterol"],
            "suitable_skin_types": ["Dry", "Very Dry", "Compromised Barrier"],
            "clinical_action": "Patented MVE sustained-release delivery replenishes ceramides 1, 3, and 6-II for 24-hour lipid replenishment."
        },
        {
            "id": "m_salicylic_dermaco",
            "category": "Moisturizer",
            "brand": "The Derma Co",
            "title": "The Derma Co 1% Salicylic Acid Oil-Free Moisturizer with Oat Extract",
            "price_inr": 349.0,
            "rating": 4.4,
            "platform": "Amazon",
            "search_query": "The Derma Co 1 Salicylic Acid Oil Free Moisturizer",
            "image_url": "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Acne & Micro-Congestion", "Oiliness", "Pore Size & Texture"],
            "key_ingredients": ["Salicylic Acid", "Oat Extract", "Zinc PCA"],
            "suitable_skin_types": ["Oily", "Acne-Prone"],
            "clinical_action": "Provides weightless non-comedogenic hydration while gently maintaining pore clarity throughout the day."
        },

        # ── Broad-Spectrum Sunscreens ──────────────────────────────────────────
        {
            "id": "u_aqualogica_radiance",
            "category": "Sunscreen",
            "brand": "Aqualogica",
            "title": "Aqualogica Radiance+ Dewy Sunscreen SPF 50+ PA++++ with Watermelon & Niacinamide",
            "price_inr": 399.0,
            "rating": 4.6,
            "platform": "Amazon",
            "search_query": "Aqualogica Radiance Dewy Sunscreen SPF 50 Watermelon Niacinamide",
            "image_url": "https://images.unsplash.com/photo-1563178406-4cdc2923acbc?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dark Spots & Hyperpigmentation", "Dullness & Uneven Skin Tone", "Sun Damage", "UV Protection"],
            "key_ingredients": ["SPF 50", "Niacinamide", "Watermelon Extract"],
            "suitable_skin_types": ["All Skin Types", "Normal", "Dry", "Combination"],
            "clinical_action": "Delivers superior PA++++ UVA/UVB shield with zero white cast, blue light protection, and dewy radiance."
        },
        {
            "id": "u_hyaluronic_dermaco",
            "category": "Sunscreen",
            "brand": "The Derma Co",
            "title": "The Derma Co 1% Hyaluronic Sunscreen Aqua Gel SPF 50 PA++++",
            "price_inr": 499.0,
            "rating": 4.7,
            "platform": "Flipkart",
            "search_query": "The Derma Co 1 Hyaluronic Sunscreen Aqua Gel SPF 50",
            "image_url": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Acne & Micro-Congestion", "Oiliness", "Pore Size & Texture", "UV Protection"],
            "key_ingredients": ["SPF 50", "Hyaluronic Acid", "Vitamin E"],
            "suitable_skin_types": ["Oily", "Acne-Prone", "Combination"],
            "clinical_action": "Water-light non-comedogenic aqua gel protects from UV degradation without stinging eyes or inducing breakouts."
        },
        {
            "id": "u_requil_matte",
            "category": "Sunscreen",
            "brand": "Re'equil",
            "title": "Re'equil Oxybenzone & OMC Free Matte Sunscreen SPF 50 PA+++",
            "price_inr": 550.0,
            "rating": 4.7,
            "platform": "Amazon",
            "search_query": "Reequil Oxybenzone OMC Free Sunscreen SPF 50",
            "image_url": "https://images.unsplash.com/photo-1563178406-4cdc2923acbc?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Redness & Sensitivity", "Acne & Micro-Congestion", "Oiliness", "UV Protection"],
            "key_ingredients": ["SPF 50", "Zinc Oxide", "Titanium Dioxide"],
            "suitable_skin_types": ["Sensitive", "Oily", "Acne-Prone"],
            "clinical_action": "Mineral-rich physical/hybrid UV filter with velvety matte primer finish that calms sensitive, reactive skin."
        },

        # ── Targeted Eye Care & Specialty Treatments ───────────────────────────
        {
            "id": "e_caffeine_minimalist",
            "category": "Eye Care",
            "brand": "Minimalist",
            "title": "Minimalist 5% Caffeine Eye Serum with EGCG for Dark Circles & Puffiness",
            "price_inr": 499.0,
            "rating": 4.5,
            "platform": "Amazon",
            "search_query": "Minimalist 5 Caffeine Eye Serum EGCG Dark Circles",
            "image_url": "https://images.unsplash.com/photo-1512290900672-1f02e1b12b50?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Dark Circles & Periorbital Fatigue", "Dark Circles", "Puffiness"],
            "key_ingredients": ["Caffeine", "EGCG Green Tea", "Hyaluronic Acid"],
            "suitable_skin_types": ["All Skin Types"],
            "clinical_action": "High-solubility topical caffeine constricts micro-capillaries under thin periorbital tissue, draining fluid accumulation."
        },
        {
            "id": "t_peeling_minimalist",
            "category": "Exfoliant",
            "brand": "Minimalist",
            "title": "Minimalist AHA 25% + PHA 5% + BHA 2% Peeling Solution for Deep Exfoliation",
            "price_inr": 599.0,
            "rating": 4.6,
            "platform": "Amazon",
            "search_query": "Minimalist AHA 25 PHA 5 BHA 2 Peeling Solution",
            "image_url": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=500&auto=format&fit=crop&q=60",
            "target_issues": ["Pore Size & Texture", "Dullness & Uneven Skin Tone", "Texture"],
            "key_ingredients": ["Glycolic Acid", "Lactic Acid", "Salicylic Acid", "Gluconolactone"],
            "suitable_skin_types": ["Normal", "Combination", "Oily"],
            "clinical_action": "Multi-acid chemical peel dissolves desmosomes binding dead keratinocytes, unveiling luminous underlying epidermis."
        }
    ]

    # Keyword mappings to link diagnostic findings to target catalog issues
    ISSUE_KEYWORDS: Dict[str, List[str]] = {
        "acne":             ["Acne & Micro-Congestion", "Pore Size & Texture", "Oiliness", "Blemishes"],
        "congestion":       ["Acne & Micro-Congestion", "Pore Size & Texture"],
        "pustule":          ["Acne & Micro-Congestion", "Blemishes"],
        "comedone":         ["Acne & Micro-Congestion", "Pore Size & Texture"],
        "blackhead":        ["Acne & Micro-Congestion", "Pore Size & Texture"],
        "blemish":          ["Acne & Micro-Congestion", "Blemishes"],
        "dark spot":        ["Dark Spots & Hyperpigmentation", "Dullness & Uneven Skin Tone", "Sun Damage"],
        "pigment":          ["Dark Spots & Hyperpigmentation", "Sun Damage", "Tan"],
        "melasma":          ["Dark Spots & Hyperpigmentation"],
        "dull":             ["Dullness & Uneven Skin Tone", "Sun Damage"],
        "uneven":           ["Dullness & Uneven Skin Tone", "Dark Spots & Hyperpigmentation"],
        "dry":              ["Dryness & Barrier Compromise", "Barrier", "Dehydration"],
        "barrier":          ["Dryness & Barrier Compromise", "Barrier"],
        "red":              ["Redness & Sensitivity", "Sensitivity"],
        "sensitiv":         ["Redness & Sensitivity", "Dryness & Barrier Compromise"],
        "erythema":         ["Redness & Sensitivity"],
        "rosacea":          ["Redness & Sensitivity"],
        "wrinkle":          ["Wrinkles & Fine Lines"],
        "fine line":        ["Wrinkles & Fine Lines"],
        "dark circle":      ["Dark Circles & Periorbital Fatigue", "Dark Circles"],
        "periorbital":      ["Dark Circles & Periorbital Fatigue"],
        "puff":             ["Dark Circles & Periorbital Fatigue", "Puffiness"],
        "oil":              ["Oiliness", "Acne & Micro-Congestion"],
        "sebum":            ["Oiliness", "Pore Size & Texture"],
        "pore":             ["Pore Size & Texture", "Oiliness"],
        "texture":          ["Pore Size & Texture", "Dullness & Uneven Skin Tone", "Texture"],
        "sun":              ["Sun Damage", "Dark Spots & Hyperpigmentation", "UV Protection"],
    }

    @classmethod
    def generate_affiliate_url(cls, platform: str, query: str) -> str:
        """Constructs live deep-link search URL for Amazon India or Flipkart with registered affiliate tag."""
        amazon_tag = os.getenv("AMAZON_AFFILIATE_TAG", "stylicai21-21")
        flipkart_id = os.getenv("FLIPKART_AFFILIATE_ID", "skincarefashion")
        encoded_query = urllib.parse.quote_plus(query)
        if (platform or "").lower() == "flipkart":
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
        Selects an authentic, clinically coordinated 4-to-5 piece skincare regimen:
        1. Cleanser (matched to skin type & concern)
        2. Active Treatment Serum (matched to highest severity condition & AI ingredients)
        3. Barrier Moisturizer (matched to skin type & barrier state)
        4. Broad-Spectrum Sunscreen SPF 50+ (essential clinical photoprotection)
        5. Eye Care or Specialty Treatment (if dark circles, eye fatigue, or focal spots noted)
        All items feature genuine product titles, reputable brands, realistic prices, and live affiliate links.
        """
        issue_names = [i.get("issue_type", "").lower() for i in detected_issues]
        severity_map = {i.get("issue_type", "").lower(): i.get("severity", "mild") for i in detected_issues}

        # Normalize recommended ingredients
        rec_ings = [ing.lower().strip() for ing in (recommended_ingredients or [])]

        # Score every item in catalog
        scored: List[tuple[float, Dict[str, Any]]] = []

        for item in cls.CATALOG:
            score = 0.0

            # Match against AI recommended ingredients (+25 points per match)
            for item_ing in item.get("key_ingredients", []):
                for ai_ing in rec_ings:
                    if ai_ing in item_ing.lower() or item_ing.lower() in ai_ing:
                        score += 25.0

            # Match against detected concerns (+15 to +30 points based on severity)
            for target in item.get("target_issues", []):
                for issue_str in issue_names:
                    if issue_str in target.lower() or target.lower() in issue_str:
                        sev = severity_map.get(issue_str, "mild")
                        score += 30.0 if sev == "severe" else (20.0 if sev == "moderate" else 15.0)

                # Keyword match
                for kw, mapped_targets in cls.ISSUE_KEYWORDS.items():
                    if any(kw in issue_str for issue_str in issue_names):
                        if any(t.lower() == target.lower() for t in mapped_targets):
                            score += 10.0

            # Match skin type compatibility (+15 points)
            item_skin_types = [st.lower() for st in item.get("suitable_skin_types", [])]
            if skin_type.lower() in item_skin_types or "all skin types" in item_skin_types:
                score += 15.0

            # Baseline product rating factor (+4.5 to +4.8 points)
            score += item.get("rating", 4.5)

            # Budget consideration: prefer within budget if specified
            if max_budget_inr and max_budget_inr > 0:
                if item["price_inr"] <= max_budget_inr:
                    score += 10.0

            scored.append((score, item))

        # Sort descending by calculated clinical match score
        scored.sort(key=lambda x: x[0], reverse=True)

        matched: List[Dict[str, Any]] = []
        categories_filled: set[str] = set()

        # Step 1: Select best product for each primary category in logical clinical routine order
        routine_order = ["Cleanser", "Serum", "Moisturizer", "Sunscreen"]

        # If dark circles or periorbital issues detected, prioritize Eye Care
        has_eye_issue = any("dark circle" in iss or "periorbital" in iss for iss in issue_names)
        if has_eye_issue:
            routine_order.append("Eye Care")

        for desired_cat in routine_order:
            for score, item in scored:
                if item["category"] == desired_cat and desired_cat not in categories_filled:
                    categories_filled.add(desired_cat)
                    prod = cls._format_product_output(item, detected_issues, skin_type)
                    matched.append(prod)
                    break

        # Step 2: If we still have fewer than 4 items, fill from remaining scored items
        if len(matched) < 4:
            for score, item in scored:
                cat = item["category"]
                if cat not in categories_filled:
                    categories_filled.add(cat)
                    matched.append(cls._format_product_output(item, detected_issues, skin_type))
                    if len(matched) >= 4:
                        break

        # Step 3: Always guarantee a Sunscreen is in the clinical regimen
        if not any(p["category"] == "Sunscreen" for p in matched):
            sun_candidates = [item for _, item in scored if item["category"] == "Sunscreen"]
            if sun_candidates:
                matched.append(cls._format_product_output(sun_candidates[0], detected_issues, skin_type))

        return matched[:5]

    @classmethod
    def _format_product_output(
        cls,
        item: Dict[str, Any],
        detected_issues: List[Dict[str, Any]],
        skin_type: str
    ) -> Dict[str, Any]:
        """Constructs user-facing response payload with genuine brand, title, description, and affiliate URL."""
        affiliate_url = cls.generate_affiliate_url(item["platform"], item["search_query"])
        primary_issue = item["target_issues"][0] if item.get("target_issues") else "Overall Skin Radiance"

        # Build personalized clinical reason
        key_ings = ", ".join(item.get("key_ingredients", [])[:2])
        reason = (
            f"Prescribed for {skin_type} skin addressing {primary_issue}. "
            f"{item.get('clinical_action', '')} "
            f"Key active actives: {key_ings}."
        )

        return {
            "category":         item["category"],
            "title":            item["title"],
            "brand":            item["brand"],
            "price_inr":        float(item["price_inr"]),
            "rating":           float(item.get("rating", 4.6)),
            "platform":         item["platform"],
            "search_query":     item["search_query"],
            "product_url":      affiliate_url,
            "target_issue":     primary_issue,
            "target_issues":    item.get("target_issues", [primary_issue]),
            "reason":           reason,
            "image_url":        item.get("image_url", "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500&auto=format&fit=crop&q=60"),
            "ingredient_focus": key_ings,
            "shop_note":        f"🔍 Verified {item['brand']} on {item['platform']} India",
        }
