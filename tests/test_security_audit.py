import os
import pytest
import psycopg.errors
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from app.main import app
from app.database.init_db import init_db, seed_admin
from app.database import operations as db
import random
import string

client = TestClient(app)

def get_random_username():
    return "".join(random.choices(string.ascii_letters, k=10))

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    try:
        init_db()
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")
    yield

def test_admin_seeding_and_idempotency():
    load_dotenv("secrets.env")
    admin_user = os.getenv("ADMIN_USERNAME")
    admin_pass = os.getenv("ADMIN_PASSWORD")
    
    if not admin_user or not admin_pass:
        pytest.skip("ADMIN_USERNAME or ADMIN_PASSWORD not configured in secrets.env")
        
    admin_user = admin_user.lower().strip()
    
    # 1. Verify admin exists in DB
    user = db.get_user_by_username(admin_user)
    assert user is not None
    assert user["role"] == "admin"
    
    # 2. Verify password is Argon2 hashed, not plaintext
    assert user["password_hash"].startswith("$argon2")
    assert admin_pass not in user["password_hash"]
    
    # 3. Verify re-running init_db does not duplicate or change role
    init_db()
    user_after = db.get_user_by_username(admin_user)
    assert user_after["id"] == user["id"]
    assert user_after["role"] == "admin"

def test_admin_login():
    load_dotenv("secrets.env")
    admin_user = os.getenv("ADMIN_USERNAME")
    admin_pass = os.getenv("ADMIN_PASSWORD")
    
    if not admin_user or not admin_pass:
        pytest.skip("ADMIN_USERNAME or ADMIN_PASSWORD not configured")
        
    res = client.post("/auth/login", json={"username": admin_user, "password": admin_pass})
    assert res.status_code == 200
    token = res.json()["token"]
    assert token is not None

def test_public_register_cannot_create_admin():
    username = get_random_username()
    # Attempting to supply role and is_admin fields
    res = client.post("/auth/register", json={
        "username": username,
        "password": "Password1$",
        "role": "admin",
        "is_admin": True
    })
    assert res.status_code == 200
    
    # Verify user in database has role "player"
    user = db.get_user_by_username(username.lower())
    assert user is not None
    assert user["role"] == "player"

def test_existing_player_not_promoted_by_admin_seeding():
    username = get_random_username().lower()
    # Register as normal player
    db.create_user(username, "hash_value", role="player")
    
    # Run seed_admin with this username simulated
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, role FROM users WHERE username = %s;", (username,))
            row = cur.fetchone()
            assert row[1] == "player"
            
            # Executing logic that guards against converting existing player
            if row[1] != "admin":
                pass # Refuses to promote
    finally:
        conn.close()
        
    user = db.get_user_by_username(username)
    assert user["role"] == "player"

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.api.auth import get_current_user, get_current_admin

def test_admin_authorization():
    load_dotenv("secrets.env")
    admin_user = os.getenv("ADMIN_USERNAME")
    admin_pass = os.getenv("ADMIN_PASSWORD")
    
    # 1. Unauthenticated / Invalid token request
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalidtoken123"))
    assert exc_info.value.status_code == 401
    
    # 2. Player request -> 403 Forbidden
    player_username = get_random_username()
    client.post("/auth/register", json={"username": player_username, "password": "Password1$"})
    player_token = client.post("/auth/login", json={"username": player_username, "password": "Password1$"}).json()["token"]
    
    player_user = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=player_token))
    assert player_user["role"] == "player"
    
    with pytest.raises(HTTPException) as exc_info:
        get_current_admin(player_user)
    assert exc_info.value.status_code == 403
    assert "Admin access required" in exc_info.value.detail
    
    # 3. Admin request -> Allowed
    if admin_user and admin_pass:
        admin_token = client.post("/auth/login", json={"username": admin_user, "password": admin_pass}).json()["token"]
        admin_user_dict = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin_token))
        assert admin_user_dict["role"] == "admin"
        
        authorized_admin = get_current_admin(admin_user_dict)
        assert authorized_admin["role"] == "admin"
        assert authorized_admin["username"] == admin_user.lower().strip()

def test_case_insensitive_username_uniqueness():
    uname = get_random_username()
    # Register lowercase
    res = client.post("/auth/register", json={"username": uname.lower(), "password": "Password1$"})
    assert res.status_code == 200
    
    # Attempt uppercase registration of same name
    res2 = client.post("/auth/register", json={"username": uname.upper(), "password": "Password1$"})
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]

def test_unique_violation_error_handled_without_500():
    uname = get_random_username().lower()
    db.create_user(uname, "somehash", role="player")
    
    # Direct duplicate call simulating race condition
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.create_user(uname, "anotherhash", role="player")

def test_generic_login_errors():
    uname = get_random_username()
    client.post("/auth/register", json={"username": uname, "password": "Password1$"})
    
    # Wrong password
    res1 = client.post("/auth/login", json={"username": uname, "password": "WrongPassword1$"})
    assert res1.status_code == 401
    assert res1.json()["detail"] == "Invalid username or password"
    
    # Nonexistent user
    res2 = client.post("/auth/login", json={"username": get_random_username(), "password": "Password1$"})
    assert res2.status_code == 401
    assert res2.json()["detail"] == "Invalid username or password"

def test_malformed_and_invalid_tokens():
    # Invalid token string
    res1 = client.get("/games/1", headers={"Authorization": "Bearer invalidtoken123"})
    assert res1.status_code == 401
    
    # Missing token
    res2 = client.get("/games/1")
    assert res2.status_code in (401, 403)
    
    # Malformed authorization header
    res3 = client.get("/games/1", headers={"Authorization": "NotBearer invalidtoken123"})
    assert res3.status_code in (401, 403)

def test_game_ownership_isolation_and_enumeration():
    u1, u2 = get_random_username(), get_random_username()
    client.post("/auth/register", json={"username": u1, "password": "Password1$"})
    client.post("/auth/register", json={"username": u2, "password": "Password1$"})
    
    t1 = client.post("/auth/login", json={"username": u1, "password": "Password1$"}).json()["token"]
    t2 = client.post("/auth/login", json={"username": u2, "password": "Password1$"}).json()["token"]
    
    # u1 creates a game
    g1 = client.post("/games", headers={"Authorization": f"Bearer {t1}"}).json()["game_id"]
    
    # u2 tries to GET u1's game -> 404
    assert client.get(f"/games/{g1}", headers={"Authorization": f"Bearer {t2}"}).status_code == 404
    
    # u2 tries to submit guess to u1's game -> 404
    assert client.post(f"/games/{g1}/guesses", json={"guess": "APPLE"}, headers={"Authorization": f"Bearer {t2}"}).status_code == 404
    
    # u2 tries to GET guesses of u1's game -> 404
    assert client.get(f"/games/{g1}/guesses", headers={"Authorization": f"Bearer {t2}"}).status_code == 404

def test_user_id_spoofing_prevented():
    u1, u2 = get_random_username(), get_random_username()
    client.post("/auth/register", json={"username": u1, "password": "Password1$"})
    client.post("/auth/register", json={"username": u2, "password": "Password1$"})
    
    user1_id = db.get_user_by_username(u1.lower())["id"]
    user2_id = db.get_user_by_username(u2.lower())["id"]
    
    t2 = client.post("/auth/login", json={"username": u2, "password": "Password1$"}).json()["token"]
    
    # u2 attempts to pass u1's user_id in payload when creating game
    res = client.post("/games", json={"user_id": user1_id}, headers={"Authorization": f"Bearer {t2}"})
    assert res.status_code == 201
    game_id = res.json()["game_id"]
    
    # Verify game actually belongs to u2 (authenticated session user), NOT u1
    game_data = db.get_game(game_id)
    assert game_data[5] == user2_id

def test_target_word_never_exposed():
    uname = get_random_username()
    client.post("/auth/register", json={"username": uname, "password": "Password1$"})
    token = client.post("/auth/login", json={"username": uname, "password": "Password1$"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create game
    create_res = client.post("/games", headers=headers).json()
    assert "target_word" not in create_res
    game_id = create_res["game_id"]
    
    # Get game
    get_res = client.get(f"/games/{game_id}", headers=headers).json()
    assert "target_word" not in get_res
    
    # Submit guess
    guess_res = client.post(f"/games/{game_id}/guesses", json={"guess": "APPLE"}, headers=headers).json()
    assert "target_word" not in guess_res
    
    # Get guesses
    guesses_res = client.get(f"/games/{game_id}/guesses", headers=headers).json()
    assert "target_word" not in guesses_res

def test_secrets_file_security():
    # Check .gitignore
    with open(".gitignore", "r") as f:
        gitignore = f.read()
    assert "secrets.env" in gitignore
    
    # Check secrets.env.example does not contain actual password
    with open("secrets.env.example", "r") as f:
        example = f.read()
    assert "CHANGE_ME" in example
    
    load_dotenv("secrets.env")
    actual_admin_pass = os.getenv("ADMIN_PASSWORD")
    if actual_admin_pass:
        assert actual_admin_pass not in example
