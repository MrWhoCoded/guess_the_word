// ========================================
// login.js — Login page logic
// ========================================

document.addEventListener("DOMContentLoaded", () => {
    redirectIfLoggedIn();

    const form = document.getElementById("login-form");
    const messageEl = document.getElementById("message");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideMessage();

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;

        if (!username || !password) {
            return showMessage("Please fill in both fields", "error");
        }

        const res = await apiLogin(username, password);

        if (res.ok) {
            saveSession(res.data.token, username);
            window.location.href = "game.html";
        } else {
            const detail = res.data?.detail;
            if (Array.isArray(detail)) {
                showMessage(detail[0]?.msg || "Login failed", "error");
            } else {
                showMessage(detail || "Invalid username or password", "error");
            }
        }
    });

    function showMessage(text, type) {
        messageEl.textContent = text;
        messageEl.className = `message ${type}`;
    }

    function hideMessage() {
        messageEl.textContent = "";
        messageEl.className = "message";
    }
});
