// ========================================
// api.js — Central API communication layer
// ========================================

const API_BASE = "";  // Same origin — served by FastAPI

/**
 * Makes an authenticated or unauthenticated fetch request.
 * Automatically attaches the Bearer token if one exists in localStorage.
 * Returns the parsed JSON response.
 */
async function apiRequest(path, options = {}) {
    const token = localStorage.getItem("token");

    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers
    });

    // Parse the JSON body (even error responses have JSON from FastAPI)
    let data;
    try {
        data = await response.json();
    } catch {
        data = null;
    }

    return { ok: response.ok, status: response.status, data };
}

// ---------- Auth API ----------

async function apiRegister(username, password) {
    return apiRequest("/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, password })
    });
}

async function apiLogin(username, password) {
    return apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password })
    });
}

async function apiLogout() {
    return apiRequest("/auth/logout", {
        method: "POST"
    });
}

// ---------- Game API ----------

async function apiStartGame() {
    return apiRequest("/games", { method: "POST" });
}

async function apiSubmitGuess(gameId, guess) {
    return apiRequest(`/games/${gameId}/guesses`, {
        method: "POST",
        body: JSON.stringify({ guess })
    });
}

async function apiGetGame(gameId) {
    return apiRequest(`/games/${gameId}`, { method: "GET" });
}

async function apiGetGuesses(gameId) {
    return apiRequest(`/games/${gameId}/guesses`, { method: "GET" });
}

// ---------- Admin API ----------

async function apiGetDailyReport() {
    return apiRequest("/admin/reports/daily", { method: "GET" });
}

async function apiGetUserReport() {
    return apiRequest("/admin/reports/users", { method: "GET" });
}

