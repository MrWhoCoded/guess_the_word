// ========================================
// admin.js — Admin reports page logic
// ========================================

document.addEventListener("DOMContentLoaded", () => {
    requireAuth();

    const usernameDisplay = document.getElementById("username-display");
    const logoutBtn = document.getElementById("logout-btn");
    const messageEl = document.getElementById("message");
    const dailyBody = document.getElementById("daily-report-body");
    const userBody = document.getElementById("user-report-body");

    if (usernameDisplay) {
        usernameDisplay.textContent = getUsername() || "User";
    }

    if (logoutBtn) {
        logoutBtn.addEventListener("click", logout);
    }

    function showMessage(msg, type = "error") {
        if (!messageEl) return;
        messageEl.textContent = msg;
        messageEl.className = `message ${type}`;
    }

    async function loadReports() {
        const [dailyRes, userRes] = await Promise.all([
            apiGetDailyReport(),
            apiGetUserReport()
        ]);

        if (!dailyRes.ok || !userRes.ok) {
            const err = (dailyRes.data && dailyRes.data.detail) || (userRes.data && userRes.data.detail) || "Failed to load admin reports.";
            showMessage(err, "error");
            dailyBody.innerHTML = `<tr><td colspan="3" style="text-align:center; color:var(--accent-hover);">Access Denied: ${err}</td></tr>`;
            userBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--accent-hover);">Access Denied: ${err}</td></tr>`;
            return;
        }

        renderDailyReport(dailyRes.data);
        renderUserReport(userRes.data);
    }

    function renderDailyReport(data) {
        if (!data || data.length === 0) {
            dailyBody.innerHTML = `<tr><td colspan="3" style="text-align:center; color:var(--text-muted);">No game activity recorded yet.</td></tr>`;
            return;
        }

        dailyBody.innerHTML = data.map(row => `
            <tr>
                <td>${escapeHtml(row.date)}</td>
                <td>${row.users}</td>
                <td>${row.correct_guesses}</td>
            </tr>
        `).join("");
    }

    function renderUserReport(data) {
        if (!data || data.length === 0) {
            userBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No game activity recorded yet.</td></tr>`;
            return;
        }

        userBody.innerHTML = data.map(row => `
            <tr>
                <td>${escapeHtml(row.date)}</td>
                <td>${escapeHtml(row.username)}</td>
                <td>${row.words_tried}</td>
                <td>${row.correct_guesses}</td>
            </tr>
        `).join("");
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    loadReports();
});
