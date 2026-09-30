// ========================================
// game.js — Game page logic
// ========================================

document.addEventListener("DOMContentLoaded", () => {
    requireAuth();

    // --- DOM references ---
    const usernameDisplay = document.getElementById("username-display");
    const logoutBtn = document.getElementById("logout-btn");
    const startBtn = document.getElementById("start-btn");
    const guessInput = document.getElementById("guess-input");
    const submitBtn = document.getElementById("submit-btn");
    const statusEl = document.getElementById("game-status");
    const messageEl = document.getElementById("message");

    // --- State ---
    let currentGameId = null;
    let currentRow = 0;
    let gameOver = false;

    // --- Init ---
    usernameDisplay.textContent = getUsername() || "Player";
    const adminLink = document.getElementById("admin-link");
    if (adminLink && getUsername() === "admin") {
        adminLink.style.display = "inline-block";
    }
    logoutBtn.addEventListener("click", logout);

    // --- Build the 5×5 board ---
    const board = document.getElementById("board");
    for (let r = 0; r < 5; r++) {
        const row = document.createElement("div");
        row.className = "board-row";
        row.id = `row-${r}`;
        for (let c = 0; c < 5; c++) {
            const tile = document.createElement("div");
            tile.className = "tile";
            tile.id = `tile-${r}-${c}`;
            row.appendChild(tile);
        }
        board.appendChild(row);
    }

    // --- Start Game ---
    startBtn.addEventListener("click", async () => {
        hideMessage();
        const res = await apiStartGame();

        if (res.ok) {
            currentGameId = res.data.game_id;
            currentRow = 0;
            gameOver = false;
            clearBoard();
            enableGuessing();
            statusEl.textContent = `Game #${currentGameId} — Guess 1 of 5`;
            startBtn.disabled = true;
        } else {
            showMessage(res.data?.detail || "Could not start game", "error");
        }
    });

    // --- Submit Guess ---
    submitBtn.addEventListener("click", submitGuess);
    guessInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") submitGuess();
    });

    async function submitGuess() {
        hideMessage();
        if (!currentGameId || gameOver) return;

        const guess = guessInput.value.trim().toUpperCase();
        if (guess.length !== 5) {
            return showMessage("Guess must be exactly 5 letters", "error");
        }
        if (!/^[A-Z]+$/.test(guess)) {
            return showMessage("Guess must contain only letters", "error");
        }

        submitBtn.disabled = true;
        const res = await apiSubmitGuess(currentGameId, guess);
        submitBtn.disabled = false;

        if (!res.ok) {
            return showMessage(res.data?.detail || "Invalid guess", "error");
        }

        // Paint the current row with the backend's evaluation
        const { result, attempt, won, game_over } = res.data;
        paintRow(currentRow, guess, result);
        currentRow = attempt;
        guessInput.value = "";

        if (game_over) {
            gameOver = true;
            disableGuessing();
            if (won) {
                statusEl.textContent = "Congratulations! 🎉";
                showMessage("You guessed the word!", "success");
            } else {
                statusEl.textContent = "Better luck next time!";
                showMessage("You've used all 5 guesses.", "info");
            }
            startBtn.disabled = false;
        } else {
            statusEl.textContent = `Game #${currentGameId} — Guess ${attempt + 1} of 5`;
        }
    }

    // --- Board helpers ---

    function paintRow(rowIndex, guess, result) {
        // Map backend color names to CSS class names
        const colorMap = { "GREEN": "correct", "ORANGE": "present", "GREY": "absent" };

        for (let c = 0; c < 5; c++) {
            const tile = document.getElementById(`tile-${rowIndex}-${c}`);
            tile.textContent = guess[c];
            tile.className = `tile ${colorMap[result[c]]}`;
        }
    }

    function clearBoard() {
        for (let r = 0; r < 5; r++) {
            for (let c = 0; c < 5; c++) {
                const tile = document.getElementById(`tile-${r}-${c}`);
                tile.textContent = "";
                tile.className = "tile";
            }
        }
    }

    function enableGuessing() {
        guessInput.disabled = false;
        submitBtn.disabled = false;
        guessInput.focus();
    }

    function disableGuessing() {
        guessInput.disabled = true;
        submitBtn.disabled = true;
    }

    // --- Message helpers ---

    function showMessage(text, type) {
        messageEl.textContent = text;
        messageEl.className = `message ${type}`;
    }

    function hideMessage() {
        messageEl.textContent = "";
        messageEl.className = "message";
    }
});
