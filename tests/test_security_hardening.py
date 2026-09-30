import os
import random
import string
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from app.main import app
from app.database.init_db import init_db
from app.database import operations as db
from app.services.rate_limiter import limiter

client = TestClient(app)

def get_random_username():
    return "".join(random.choices(string.ascii_letters, k=10)).lower()

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    try:
        init_db()
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")
    yield

@pytest.fixture(autouse=True)
def reset_limiter_state():
    limiter.reset()
    yield
    limiter.reset()

@pytest.fixture
def admin_headers():
    load_dotenv("secrets.env")
    admin_user = os.getenv("ADMIN_USERNAME")
    admin_pass = os.getenv("ADMIN_PASSWORD")
    if not admin_user or not admin_pass:
        pytest.skip("ADMIN_USERNAME or ADMIN_PASSWORD not configured")
    res = client.post("/auth/login", json={"username": admin_user, "password": admin_pass})
    assert res.status_code == 200
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def player_auth():
    uname = get_random_username()
    client.post("/auth/register", json={"username": uname, "password": "Password1$"})
    token = client.post("/auth/login", json={"username": uname, "password": "Password1$"}).json()["token"]
    return {"username": uname, "token": token, "headers": {"Authorization": f"Bearer {token}"}}

# ==========================================
# 1. AUTHENTICATION & SESSION TESTS
# ==========================================

def test_auth_missing_token():
    res = client.get("/games/1")
    assert res.status_code in (401, 403)

def test_auth_invalid_token():
    res = client.get("/games/1", headers={"Authorization": "Bearer non_existent_token_12345"})
    assert res.status_code == 401
    assert "Invalid or expired token" in res.json()["detail"]

def test_auth_malformed_token():
    res = client.get("/games/1", headers={"Authorization": "InvalidScheme token"})
    assert res.status_code in (401, 403)

def test_logout_invalidates_session(player_auth):
    headers = player_auth["headers"]
    
    # 1. Verify token works before logout
    res = client.post("/games", headers=headers)
    assert res.status_code == 201
    
    # 2. Call logout
    logout_res = client.post("/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert "Logged out successfully" in logout_res.json()["message"]
    
    # 3. Attempting to use the same token now fails
    res_after = client.post("/games", headers=headers)
    assert res_after.status_code == 401
    assert "Invalid or expired token" in res_after.json()["detail"]

def test_logout_with_invalid_token():
    res = client.post("/auth/logout", headers={"Authorization": "Bearer invalidtoken999"})
    assert res.status_code == 401

# ==========================================
# 2. AUTHORIZATION TESTS
# ==========================================

def test_player_denied_admin_endpoint(player_auth):
    res = client.get("/admin/reports/daily", headers=player_auth["headers"])
    assert res.status_code == 403
    assert "Admin access required" in res.json()["detail"]

def test_admin_allowed_admin_endpoint(admin_headers):
    res = client.get("/admin/reports/daily", headers=admin_headers)
    assert res.status_code == 200

def test_game_ownership_isolation():
    u1, u2 = get_random_username(), get_random_username()
    client.post("/auth/register", json={"username": u1, "password": "Password1$"})
    client.post("/auth/register", json={"username": u2, "password": "Password1$"})
    
    t1 = client.post("/auth/login", json={"username": u1, "password": "Password1$"}).json()["token"]
    t2 = client.post("/auth/login", json={"username": u2, "password": "Password1$"}).json()["token"]
    
    g1 = client.post("/games", headers={"Authorization": f"Bearer {t1}"}).json()["game_id"]
    
    # u2 cannot read u1's game
    assert client.get(f"/games/{g1}", headers={"Authorization": f"Bearer {t2}"}).status_code == 404
    # u2 cannot submit guesses to u1's game
    assert client.post(f"/games/{g1}/guesses", json={"guess": "APPLE"}, headers={"Authorization": f"Bearer {t2}"}).status_code == 404
    # u2 cannot read u1's guesses
    assert client.get(f"/games/{g1}/guesses", headers={"Authorization": f"Bearer {t2}"}).status_code == 404

def test_user_id_spoofing_prevented(player_auth):
    # Pass arbitrary user_id in body
    res = client.post("/games", json={"user_id": 99999}, headers=player_auth["headers"])
    assert res.status_code == 201
    game_id = res.json()["game_id"]
    
    # Verify owner in DB is the authenticated user, not 99999
    game_data = db.get_game(game_id)
    auth_user = db.get_user_by_username(player_auth["username"])
    assert game_data[5] == auth_user["id"]

# ==========================================
# 3. RATE LIMITING TESTS
# ==========================================

def test_rate_limiter_allows_normal_requests():
    for _ in range(5):
        uname = get_random_username()
        res = client.post("/auth/register", json={"username": uname, "password": "Password1$"})
        assert res.status_code == 200

def test_rate_limiter_blocks_excessive_requests():
    # Attempting more than 20 logins rapidly triggers 429
    uname = get_random_username()
    client.post("/auth/register", json={"username": uname, "password": "Password1$"})
    
    for _ in range(20):
        client.post("/auth/login", json={"username": uname, "password": "Password1$"})
        
    # 21st request should be rate limited
    res = client.post("/auth/login", json={"username": uname, "password": "Password1$"})
    assert res.status_code == 429
    assert "Too many requests" in res.json()["detail"]
    assert "Retry-After" in res.headers

def test_rate_limiter_reset():
    uname = get_random_username()
    client.post("/auth/register", json={"username": uname, "password": "Password1$"})
    
    # Exhaust rate limit
    for _ in range(20):
        client.post("/auth/login", json={"username": uname, "password": "Password1$"})
    assert client.post("/auth/login", json={"username": uname, "password": "Password1$"}).status_code == 429
    
    # Reset limiter
    limiter.reset()
    
    # Request should now succeed
    res = client.post("/auth/login", json={"username": uname, "password": "Password1$"})
    assert res.status_code == 200

# ==========================================
# 4. INPUT VALIDATION TESTS
# ==========================================

def test_input_validation_malformed_game_id(player_auth):
    res = client.get("/games/invalid_id", headers=player_auth["headers"])
    assert res.status_code == 422

def test_input_validation_invalid_guesses(player_auth):
    game_id = client.post("/games", headers=player_auth["headers"]).json()["game_id"]
    headers = player_auth["headers"]
    
    # Too short
    assert client.post(f"/games/{game_id}/guesses", json={"guess": "APP"}, headers=headers).status_code == 400
    # Too long
    assert client.post(f"/games/{game_id}/guesses", json={"guess": "APPLES"}, headers=headers).status_code == 400
    # Non alpha
    assert client.post(f"/games/{game_id}/guesses", json={"guess": "12345"}, headers=headers).status_code == 400

# ==========================================
# 5. INFORMATION LEAKAGE & PRIVACY TESTS
# ==========================================

def test_target_word_not_leaked(player_auth):
    headers = player_auth["headers"]
    
    create_res = client.post("/games", headers=headers).json()
    assert "target_word" not in create_res
    game_id = create_res["game_id"]
    
    get_res = client.get(f"/games/{game_id}", headers=headers).json()
    assert "target_word" not in get_res
    
    guess_res = client.post(f"/games/{game_id}/guesses", json={"guess": "APPLE"}, headers=headers).json()
    assert "target_word" not in guess_res

def test_password_hash_never_returned():
    uname = get_random_username()
    reg_res = client.post("/auth/register", json={"username": uname, "password": "Password1$"}).json()
    assert "password_hash" not in reg_res
    assert "password" not in reg_res
    
    login_res = client.post("/auth/login", json={"username": uname, "password": "Password1$"}).json()
    assert "password_hash" not in login_res
    assert "password" not in login_res

# ==========================================
# 6. STATIC FILE SECURITY TESTS
# ==========================================

def test_secrets_env_not_accessible_via_http():
    res = client.get("/secrets.env")
    assert res.status_code == 404

def test_dot_env_not_accessible_via_http():
    res = client.get("/.env")
    assert res.status_code == 404

def test_source_code_not_accessible_via_http():
    res = client.get("/app/main.py")
    assert res.status_code == 404

# ==========================================
# 7. SECURITY HEADERS TESTS
# ==========================================

def test_security_headers_present():
    res = client.get("/")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
