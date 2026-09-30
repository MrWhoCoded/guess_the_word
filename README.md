# Guess the Word

A clean, self-contained Python game engine for a 5-letter word guessing game.

## Stage 4: Users & Authentication

This stage introduces a secure authentication system using Postgres and Argon2, allowing individual users to have separate identities, independent game histories, and a daily play limit of 3 games.

### Authentication Flow

1.  **Registration (`POST /auth/register`)**: Accepts a JSON body with `username` and `password`. The password undergoes validation (must contain a letter, number, and one of `$ % * &`). If valid, the password is mathematically hashed using the robust Argon2 algorithm (`argon2-cffi`), and the original password is discarded. Only the username and hash are stored in Postgres.
2.  **Login (`POST /auth/login`)**: Takes credentials, locates the user in the database, and uses Argon2 to verify the hash. If successful, it generates a 64-character hex `token` using `secrets.token_hex(32)` and saves it inside the `sessions` table mapped to the `user_id`.
3.  **Authenticated Game Request**: The frontend or API client attaches this token into the `Authorization: Bearer <token>` header on subsequent requests. The `get_current_user` FastAPI dependency intercepts this token, does a DB lookup in the `sessions` table, retrieves the associated `user_id`, and safely passes the User object into the route handler. 

### Why Argon2 over SHA-256?

Argon2 is a modern, memory-hard key derivation function. Unlike SHA-256 (which is fast and designed for message integrity), Argon2 is intentionally slow and requires significant memory. This makes it mathematically resistant to brute-force and GPU cracking attacks, which is essential for protecting user passwords.

### Game Ownership & Daily Limits

-   **Game Ownership**: The `games` table now contains a `user_id` foreign key. The `/games/{id}` routes use the `Depends(get_current_user)` injection. The SQL queries naturally extract the game, and Python enforces that `game_data[5] == user["id"]`. Any mismatches result in a `404 Not Found` (intentionally hiding the existence of other users' games).
-   **3-Games-per-Day Rule**: Inside `POST /games`, before grabbing a target word, we execute `SELECT COUNT(*) FROM games WHERE user_id = %s AND DATE(started_at) = CURRENT_DATE`. If the count is >= 3, FastAPI aborts the request with a 400 error.

### Running the API Server

Start the local development server:
`uvicorn app.main:app --reload`

The API will be available at `http://127.0.0.1:8000/docs`. You can use the "Authorize" button to inject your Bearer token across endpoints.

### Running Tests

Run the complete test suite (Requires local Postgres connection with credentials set in `secrets.env`):
`pytest`

*Over 40 distinct tests cover evaluator edge-cases, database sanity, API integrations, and auth strictness.*
