from app.database.connection import get_connection

def get_random_word():
    """Returns a tuple of (word_id, word) for a random word in the database."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, word FROM words ORDER BY RANDOM() LIMIT 1;")
            result = cur.fetchone()
            if result:
                return result[0], result[1]
            return None, None
    finally:
        conn.close()

def get_word(word_id):
    """Returns the word string for a given word_id."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT word FROM words WHERE id = %s;", (word_id,))
            result = cur.fetchone()
            if result:
                return result[0]
            return None
    finally:
        conn.close()

def create_game(word_id, user_id):
    """Creates a new game and returns the game_id."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO games (word_id, user_id) 
                VALUES (%s, %s) 
                RETURNING id;
            """, (word_id, user_id))
            game_id = cur.fetchone()[0]
        conn.commit()
        return game_id
    finally:
        conn.close()

def save_guess(game_id, guess, guess_number):
    """Saves a guess for a specific game."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO guesses (game_id, guess, guess_number) 
                VALUES (%s, %s, %s);
            """, (game_id, guess.upper(), guess_number))
        conn.commit()
    finally:
        conn.close()

def complete_game(game_id, won):
    """Marks a game as completed and updates its win status."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE games 
                SET completed_at = CURRENT_TIMESTAMP, won = %s 
                WHERE id = %s;
            """, (won, game_id))
        conn.commit()
    finally:
        conn.close()

def get_game(game_id):
    """Retrieves basic game info including user_id."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, word_id, started_at, completed_at, won, user_id 
                FROM games 
                WHERE id = %s;
            """, (game_id,))
            return cur.fetchone()
    finally:
        conn.close()

def get_guesses(game_id):
    """Retrieves all guesses for a game ordered by guess_number."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT guess, guess_number, created_at 
                FROM guesses 
                WHERE game_id = %s 
                ORDER BY guess_number ASC;
            """, (game_id,))
            return cur.fetchall()
    finally:
        conn.close()

def create_user(username, password_hash, role="player"):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, %s);
            """, (username, password_hash, role))
        conn.commit()
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s;", (username,))
            row = cur.fetchone()
            if row:
                return {"id": row[0], "username": row[1], "password_hash": row[2], "role": row[3]}
            return None
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, role FROM users WHERE id = %s;", (user_id,))
            row = cur.fetchone()
            if row:
                return {"id": row[0], "username": row[1], "role": row[2]}
            return None
    finally:
        conn.close()

def create_session(token, user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO sessions (token, user_id) VALUES (%s, %s);", (token, user_id))
        conn.commit()
    finally:
        conn.close()

def get_user_by_token(token):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.username, u.role
                FROM users u
                JOIN sessions s ON u.id = s.user_id
                WHERE s.token = %s;
            """, (token,))
            row = cur.fetchone()
            if row:
                return {"id": row[0], "username": row[1], "role": row[2]}
            return None
    finally:
        conn.close()

def count_user_games_today(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM games 
                WHERE user_id = %s AND DATE(started_at) = CURRENT_DATE;
            """, (user_id,))
            return cur.fetchone()[0]
    finally:
        conn.close()

def get_daily_report():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    TO_CHAR(started_at, 'YYYY-MM-DD') AS date,
                    COUNT(DISTINCT user_id) AS users,
                    COUNT(CASE WHEN won IS TRUE THEN 1 END) AS correct_guesses
                FROM games
                WHERE started_at IS NOT NULL
                GROUP BY DATE(started_at), TO_CHAR(started_at, 'YYYY-MM-DD')
                ORDER BY DATE(started_at) DESC;
            """)
            rows = cur.fetchall()
            return [
                {
                    "date": row[0],
                    "users": row[1],
                    "correct_guesses": row[2]
                }
                for row in rows
            ]
    finally:
        conn.close()

def get_user_report():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    TO_CHAR(g.started_at, 'YYYY-MM-DD') AS date,
                    u.username,
                    COUNT(g.id) AS words_tried,
                    COUNT(CASE WHEN g.won IS TRUE THEN 1 END) AS correct_guesses
                FROM games g
                JOIN users u ON g.user_id = u.id
                WHERE g.started_at IS NOT NULL
                GROUP BY DATE(g.started_at), TO_CHAR(g.started_at, 'YYYY-MM-DD'), u.username
                ORDER BY DATE(g.started_at) DESC, u.username ASC;
            """)
            rows = cur.fetchall()
            return [
                {
                    "date": row[0],
                    "username": row[1],
                    "words_tried": row[2],
                    "correct_guesses": row[3]
                }
                for row in rows
            ]
    finally:
        conn.close()

