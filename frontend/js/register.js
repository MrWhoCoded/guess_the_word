// ========================================
// register.js — Registration page logic
// ========================================

document.addEventListener("DOMContentLoaded", () => {
    redirectIfLoggedIn();

    const form = document.getElementById("register-form");
    const messageEl = document.getElementById("message");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideMessage();

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;
        const confirmPassword = document.getElementById("confirm-password").value;

        // Frontend validation (for quick feedback only — backend is authoritative)
        const usernameErr = validateUsername(username);
        if (usernameErr) return showMessage(usernameErr, "error");

        const passwordErr = validatePassword(password);
        if (passwordErr) return showMessage(passwordErr, "error");

        if (password !== confirmPassword) {
            return showMessage("Passwords do not match", "error");
        }

        // Call the API
        const res = await apiRegister(username, password);

        if (res.ok) {
            showMessage("Account created! Redirecting to login...", "success");
            setTimeout(() => {
                window.location.href = "login.html";
            }, 1500);
        } else {
            const detail = res.data?.detail;
            // FastAPI validation errors come as an array
            if (Array.isArray(detail)) {
                showMessage(detail[0]?.msg || "Registration failed", "error");
            } else {
                showMessage(detail || "Registration failed", "error");
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
