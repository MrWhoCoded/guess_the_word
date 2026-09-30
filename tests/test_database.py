import pytest
from app.database.init_db import init_db
from app.database.connection import get_connection
from app.database.operations import (
    get_random_word, create_game, save_guess, 
    complete_game, get_game, get_guesses
)
from app.game.engine import Game

@pytest.fixture(scope="session")
def db_setup():
    # Initialize the database before running tests
    try:
        init_db()
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}. Ensure PostgreSQL is running and secrets.env is configured.")
        
    yield
    # Keeping it simple as requested, no teardown to avoid complex test DB management

@pytest.fixture
def connection(db_setup):
    conn = get_connection()
    yield conn
    conn.close()

@pytest.fixture
def test_user_id(db_setup):
    from app.database.operations import create_user, get_user_by_username
    import random
    import string
    username = "".join(random.choices(string.ascii_letters, k=10))
    create_user(username, "hash")
    user = get_user_by_username(username)
    return user["id"]

def test_database_connection(connection):
    assert connection is not None
    assert not connection.closed

def test_tables_exist(connection):
    with connection.cursor() as cur:
        for table in ["words", "games", "guesses"]:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            assert cur.fetchone()[0] is True

def test_initial_words_exist(connection):
    with connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM words;")
        count = cur.fetchone()[0]
        assert count >= 20

def test_words_uppercase_and_length(connection):
    with connection.cursor() as cur:
        cur.execute("SELECT word FROM words;")
        words = cur.fetchall()
        for row in words:
            word = row[0]
            assert word.isupper()
            assert len(word) == 5
            assert word.isalpha()

def test_random_word_returns_valid(db_setup):
    word_id, word = get_random_word()
    assert word_id is not None
    assert word is not None
    assert len(word) == 5

def test_game_creation_and_persistence(test_user_id):
    word_id, word = get_random_word()
    game_id = create_game(word_id, test_user_id)
    assert game_id is not None
    
    # Verify in DB
    game = get_game(game_id)
    assert game is not None
    assert game[1] == word_id # word_id
    assert game[3] is None # completed_at
    assert game[4] is None # won

def test_game_integration_flow(test_user_id):
    # 1. Retrieve a random word
    word_id, target = get_random_word()
    
    # 2. Create a row in games
    game_id = create_game(word_id, test_user_id)
    
    # 3. Create the in-memory Game object
    game = Game(target)
    
    # 4. Player submits valid guess
    guess_word = "GHOST"
    # Ensure it's not the target to avoid winning immediately
    if target == "GHOST":
        guess_word = "APPLE"
        
    res = game.guess(guess_word)
    
    # 5. Save the valid guess in PostgreSQL
    save_guess(game_id, guess_word, res["attempt"])
    
    # 6. Verify guess is saved
    db_guesses = get_guesses(game_id)
    assert len(db_guesses) == 1
    assert db_guesses[0][0] == guess_word
    assert db_guesses[0][1] == 1 # guess_number
    
    # 7. Complete the game
    complete_game(game_id, res["won"])
    
    # 8. Verify game completion
    completed_game = get_game(game_id)
    assert completed_game[3] is not None # completed_at
    assert completed_game[4] == res["won"]
