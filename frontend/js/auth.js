// ========================================
// auth.js — Shared authentication utilities
// ========================================

/**
 * Returns the stored token, or null if not logged in.
 */
function getToken() {
    return localStorage.getItem("token");
}

/**
 * Returns the stored username, or null.
 */
function getUsername() {
    return localStorage.getItem("username");
}

/**
 * Saves the token and username after a successful login.
 */
function saveSession(token, username) {
    localStorage.setItem("token", token);
    localStorage.setItem("username", username);
}

/**
 * Clears the session server-side and client-side and redirects to login.
 */
async function logout() {
    try {
        if (typeof apiLogout === "function") {
            await apiLogout();
        }
    } catch {
        // Continue logout even if server request fails
    }
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    window.location.href = "login.html";
}

/**
 * If the user is NOT logged in, redirect them to login.html.
 * Call this at the top of protected pages like game.html.
 */
function requireAuth() {
    if (!getToken()) {
        window.location.href = "login.html";
    }
}

/**
 * If the user IS logged in, redirect them to game.html.
 * Call this on login.html and register.html to skip re-authentication.
 */
function redirectIfLoggedIn() {
    if (getToken()) {
        window.location.href = "game.html";
    }
}

// ---------- Frontend validation helpers ----------

function validateUsername(username) {
    if (username.length < 5) return "Username must be at least 5 characters";
    if (!/^[a-zA-Z]+$/.test(username)) return "Username must contain only letters";
    return null;
}

function validatePassword(password) {
    if (password.length < 5) return "Password must be at least 5 characters";
    if (!/[a-zA-Z]/.test(password)) return "Password must contain at least one letter";
    if (!/[0-9]/.test(password)) return "Password must contain at least one number";
    if (!/[$%*&]/.test(password)) return "Password must contain one of: $ % * &";
    return null;
}
