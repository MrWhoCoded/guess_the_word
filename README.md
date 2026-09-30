# Guess the Word

A complete, end-to-end Wordle-style word guessing game built as a learning project.

## Architecture

```
        Browser (HTML / CSS / JS)
                  │
              HTTP / JSON
                  ↓
             FastAPI API
                  │
        ┌─────────┴─────────┐
   Authentication       Game Engine
        │                    │
        └─────────┬──────────┘
                  ↓
             PostgreSQL
```

## Running the Application

1.  Install dependencies:
    ```
    pip install -r requirements.txt
    ```

2.  Configure `secrets.env` with your PostgreSQL credentials (see `secrets.env.example`).

3.  Initialize the database:
    ```
    python -m app.database.init_db
    ```

4.  Start the server:
    ```
    uvicorn app.main:app --reload
    ```

5.  Open your browser:
    ```
    http://127.0.0.1:8000/
    ```

## Stage 5: Frontend

The frontend is served by FastAPI itself from the `frontend/` directory. Because the browser loads pages from the same `http://127.0.0.1:8000` origin as the API, **no CORS configuration is needed**. The browser sees one origin for both HTML and JSON endpoints.

### Pages

| URL | Purpose |
|-----|---------|
| `/` | Landing page with links to Login / Register |
| `/register.html` | Create a new account |
| `/login.html` | Log in with existing credentials |
| `/game.html` | Play the game (requires authentication) |
| `/admin.html` | Admin reporting dashboard (requires role="admin") |

## Stage 6: Admin & Reporting

Stage 6 introduces administrative reporting endpoints and an admin frontend dashboard.

### Admin Endpoints

| Endpoint | Method | Role Required | Description |
|----------|--------|---------------|-------------|
| `/admin/reports/daily` | GET | `admin` | Aggregated daily game activity summary |
| `/admin/reports/users` | GET | `admin` | Per-user game activity summary grouped by date |

### Report Definitions

- **Daily Report (`GET /admin/reports/daily`)**:
  - `date`: Date string formatted as `YYYY-MM-DD` (grouped by `DATE(started_at)`).
  - `users`: Number of **distinct users** who started at least one game on that date (`COUNT(DISTINCT user_id)`).
  - `correct_guesses`: Total number of **games won** on that date (`COUNT(CASE WHEN won IS TRUE THEN 1 END)`).

- **User Report (`GET /admin/reports/users`)**:
  - `date`: Date string formatted as `YYYY-MM-DD`.
  - `username`: The player's username.
  - `words_tried`: Total number of **games started** by the user on that date (`COUNT(g.id)`).
  - `correct_guesses`: Total number of **games won** by the user on that date (`COUNT(CASE WHEN won IS TRUE THEN 1 END)`).

### Admin Authorization Flow

1. **Seeding**: Initial admin account is seeded automatically from `secrets.env` credentials (`ADMIN_USERNAME` / `ADMIN_PASSWORD`) with `role = "admin"` during database initialization.
2. **Server-Side Enforcement**: All `/admin/*` endpoints depend on `get_current_admin`. The backend verifies the session token and asserts `user.role == "admin"`. Non-admin players or unauthenticated requests are rejected with `403 Forbidden` or `401 Unauthorized`.
3. **Frontend Dashboard**: `/admin.html` uses `apiGetDailyReport()` and `apiGetUserReport()` to display table summaries. Frontend visibility is purely UX; the server strictly enforces all permissions.

### How a Guess Travels Through the System

```
1. User types "HOUSE" and clicks Submit
                  ↓
2. game.js calls apiSubmitGuess(gameId, "HOUSE")
                  ↓
3. api.js sends:  POST /games/42/guesses
                  Headers: Authorization: Bearer <token>
                  Body:    {"guess": "HOUSE"}
                  ↓
4. FastAPI extracts the token, looks up the session in PostgreSQL,
   finds the user, confirms they own game 42
                  ↓
5. games.py fetches the target word from PostgreSQL,
   reconstructs the Game object from saved guesses,
   calls game.guess("HOUSE")
                  ↓
6. engine.py / evaluator.py determines:
   ["GREY", "GREY", "GREEN", "ORANGE", "GREY"]
                  ↓
7. The guess and result are saved to PostgreSQL
                  ↓
8. FastAPI returns JSON:
   {"guess": "HOUSE", "result": ["GREY","GREY","GREEN","ORANGE","GREY"],
    "attempt": 1, "won": false, "game_over": false}
                  ↓
9. game.js reads the response and paints each tile:
   GREEN  → CSS class "correct" (green background)
   ORANGE → CSS class "present" (orange background)
   GREY   → CSS class "absent"  (grey background)
```

**The frontend never knows the target word.** It never evaluates a guess. It only displays what the backend tells it.

### Authentication Token Flow

1.  **Login**: `login.js` sends `POST /auth/login`. On success, the server returns `{"token": "abc123..."}`.
2.  **Storage**: `login.js` calls `saveSession(token, username)` which stores both in `localStorage`.
3.  **Subsequent requests**: `api.js`'s `apiRequest()` function reads `localStorage.getItem("token")` and attaches it as `Authorization: Bearer <token>` on every API call.
4.  **Server verification**: FastAPI's `get_current_user` dependency extracts the token, queries the `sessions` table in PostgreSQL, joins to `users`, and returns the authenticated user object.
5.  **Logout**: Clicking Logout calls `logout()` in `auth.js`, which removes the token from `localStorage` and redirects to `login.html`.

> **Note**: Using `localStorage` for token storage is simple and appropriate for this learning project. In a production application, `httpOnly` cookies would be more resistant to XSS attacks.

### Password Security

```
Plaintext password  →  Argon2 hash  →  PostgreSQL
```

The original password is **never stored**. Argon2 is a memory-hard key derivation function that is intentionally slow, making brute-force attacks impractical compared to fast hashes like SHA-256.

### Game Ownership

Each game row in PostgreSQL has a `user_id` foreign key. When any `/games/{id}` endpoint is called, the server checks that `game.user_id == authenticated_user.id`. If they don't match, the server returns `404 Not Found` (intentionally hiding the existence of other users' games).

### Daily Limit: 3 Games per User per Day

When `POST /games` is called, the server runs:
```sql
SELECT COUNT(*) FROM games WHERE user_id = %s AND DATE(started_at) = CURRENT_DATE;
```
If the count is >= 3, the server returns `400 Bad Request` with "Daily game limit reached". The frontend simply displays this message. The count is never tracked in JavaScript.

## Running Tests

```
pytest
```

All 65 tests cover the evaluator, game engine, database operations, API endpoints, authentication, authorization, ownership, daily limits, security audit requirements, and admin reporting.

## Project Structure

```
guess-the-word/
│
├── app/
│   ├── main.py                  ← FastAPI app + static file serving
│   ├── api/
│   │   ├── admin.py             ← GET /admin/reports/daily, GET /admin/reports/users
│   │   ├── auth.py              ← POST /auth/register, POST /auth/login
│   │   └── games.py             ← POST /games, POST /games/{id}/guesses, ...
│   ├── game/
│   │   ├── engine.py            ← Game class (state, attempts, win/loss)
│   │   └── evaluator.py         ← evaluate_guess() (GREEN/ORANGE/GREY)
│   └── database/
│       ├── connection.py        ← PostgreSQL connection via psycopg
│       ├── init_db.py           ← Schema creation, initial words, admin seeding
│       └── operations.py        ← All SQL operations (users, games, guesses, reports)
│
├── frontend/
│   ├── index.html               ← Landing page
│   ├── login.html               ← Login form
│   ├── register.html            ← Registration form
│   ├── game.html                ← Game board
│   ├── admin.html               ← Admin report tables (Daily & User)
│   ├── css/
│   │   └── style.css            ← Dark theme, tile colors, responsive layout, report tables
│   └── js/
│       ├── admin.js             ← Admin dashboard fetching and table rendering
│       ├── api.js               ← Central fetch helper (auto-attaches token)
│       ├── auth.js              ← Token storage, validation helpers, logout
│       ├── login.js             ← Login form handler
│       ├── register.js          ← Registration form handler
│       └── game.js              ← Board rendering, guess submission
│
├── tests/
│   ├── test_evaluator.py        ← 9 tests
│   ├── test_game.py             ← 13 tests
│   ├── test_database.py         ← 7 tests
│   ├── test_auth.py             ← 8 tests
│   ├── test_api.py              ← 6 tests
│   ├── test_security_audit.py   ← 13 tests
│   └── test_admin.py            ← 9 tests
│
├── secrets.env                  ← PostgreSQL & Admin credentials (git-ignored)
├── secrets.env.example
├── requirements.txt
├── README.md
└── .gitignore
```
