import os
from dotenv import load_dotenv
from argon2 import PasswordHasher
from app.database.connection import get_connection

def seed_admin(cur):
    load_dotenv("secrets.env")
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_username or not admin_password:
        return

    admin_username = admin_username.lower().strip()
    
    cur.execute("SELECT id, role FROM users WHERE username = %s;", (admin_username,))
    row = cur.fetchone()

    if not row:
        ph = PasswordHasher()
        password_hash = ph.hash(admin_password)
        cur.execute("""
            INSERT INTO users (username, password_hash, role)
            VALUES (%s, %s, %s);
        """, (admin_username, password_hash, "admin"))
        print(f"Admin user '{admin_username}' created successfully.")
    else:
        user_id, role = row
        if role == "admin":
            print(f"Admin user '{admin_username}' already exists.")
        else:
            print(f"User '{admin_username}' already exists with role '{role}'. Cannot convert to admin.")

def init_db():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'player',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token VARCHAR(255) PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create words table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    id SERIAL PRIMARY KEY,
                    word VARCHAR(5) NOT NULL UNIQUE
                );
            """)
            
            # Create games table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id SERIAL PRIMARY KEY,
                    word_id INTEGER NOT NULL REFERENCES words(id),
                    user_id INTEGER REFERENCES users(id),
                    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    won BOOLEAN
                );
            """)
            cur.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);")
            
            # Create guesses table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS guesses (
                    id SERIAL PRIMARY KEY,
                    game_id INTEGER NOT NULL REFERENCES games(id),
                    guess VARCHAR(5) NOT NULL,
                    guess_number INTEGER NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Insert 20 initial words
            initial_words = [
                "APPLE", "HOUSE", "TIGER", "WATER", "TRAIN",
                "GHOST", "ALLEY", "WORLD", "HELLO", "PUPPY",
                "BEACH", "CHAIR", "DANCE", "EAGLE", "FLAME",
                "GRAPE", "HEART", "IMAGE", "JUICE", "KNIFE"
            ]
            
            for word in initial_words:
                cur.execute("""
                    INSERT INTO words (word) 
                    VALUES (%s) 
                    ON CONFLICT (word) DO NOTHING;
                """, (word,))
                
            # Seed admin user
            seed_admin(cur)
                
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")

