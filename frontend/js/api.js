// API Client for Skincare & Fashion AI Backend
const API_BASE = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1")
  ? "" 
  : "";

const API = {
  getToken() {
    return localStorage.getItem("token");
  },

  setToken(token) {
    if (token) localStorage.setItem("token", token);
    else localStorage.removeItem("token");
  },

  getUser() {
    const raw = localStorage.getItem("user");
    return raw ? JSON.parse(raw) : null;
  },

  setUser(user) {
    if (user) localStorage.setItem("user", JSON.stringify(user));
    else localStorage.removeItem("user");
  },

  async request(endpoint, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 401 && !endpoint.includes("/api/auth/login")) {
          this.setToken(null);
          this.setUser(null);
        }
        throw new Error(data.detail || `Request failed: ${response.status}`);
      }
      return data;
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err);
      throw err;
    }
  },

  // Auth Endpoints
  async register(userData) {
    const res = await this.request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(userData)
    });
    this.setToken(res.access_token);
    this.setUser(res.user);
    return res;
  },

  async login(email, password) {
    const res = await this.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    this.setToken(res.access_token);
    this.setUser(res.user);
    return res;
  },

  async getMe() {
    const user = await this.request("/api/auth/me");
    this.setUser(user);
    return user;
  },

  async updateProfile(profile) {
    const user = await this.request("/api/auth/profile", {
      method: "PUT",
      body: JSON.stringify(profile)
    });
    this.setUser(user);
    return user;
  },

  async changePassword(oldPassword, newPassword) {
    return await this.request("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword
      })
    });
  },

  logout() {
    this.setToken(null);
    this.setUser(null);
    window.location.reload();
  },

  // Skin Analysis Endpoints
  async analyzeSkin(imageBase64, landmarks, budgetSkincare, budgetFashion, notes) {
    return await this.request("/api/skin/analyze", {
      method: "POST",
      body: JSON.stringify({
        image_base64: imageBase64,
        landmarks: landmarks,
        budget_skincare: budgetSkincare,
        budget_fashion: budgetFashion,
        notes: notes
      })
    });
  },

  async getScanHistory() {
    return await this.request("/api/scans/history");
  },

  async getProgressTrends() {
    return await this.request("/api/scans/progress");
  },

  // Fashion & Outfit Endpoints
  async generateOutfit(scanId, occasion, budgetInr, stylePreference) {
    return await this.request("/api/fashion/outfit", {
      method: "POST",
      body: JSON.stringify({
        scan_id: scanId,
        occasion: occasion,
        budget_inr: budgetInr,
        style_preference: stylePreference
      })
    });
  },

  // Click / Purchase tracking
  async trackClick(productName, platform, priceInr, productUrl, category) {
    return await this.request("/api/purchases/click", {
      method: "POST",
      body: JSON.stringify({
        product_name: productName,
        platform: platform,
        price_inr: priceInr,
        product_url: productUrl,
        category: category
      })
    });
  },

  async getPurchases() {
    return await this.request("/api/purchases");
  }
};
