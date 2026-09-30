import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.init_db import init_db
from app.database import operations as db
import random
import string

def get_random_username():
    return "".join(random.choices(string.ascii_letters, k=10))

client = TestClient(app)

@pytest.fixture(scope="session")
def setup_db():
    try:
        init_db()
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")
    yield

def test_register_valid(setup_db):
    username = get_random_username()
    res = client.post("/auth/register", json={"username": username, "password": "Password1$"})
    assert res.status_code == 200
    assert "successfully" in res.json()["message"]

def test_register_invalid_username(setup_db):
    # Too short
    res = client.post("/auth/register", json={"username": "usr", "password": "Password1$"})
    assert res.status_code == 422
    
    # Non-alpha
    res = client.post("/auth/register", json={"username": "user123", "password": "Password1$"})
    assert res.status_code == 422

def test_register_duplicate(setup_db):
    username = get_random_username()
    client.post("/auth/register", json={"username": username, "password": "Password1$"})
    res = client.post("/auth/register", json={"username": username, "password": "Password1$"})
    assert res.status_code == 400

def test_password_validation(setup_db):
    username = get_random_username()
    
    # Too short
    assert client.post("/auth/register", json={"username": username, "password": "1$a"}).status_code == 422
    # No alpha
    assert client.post("/auth/register", json={"username": username, "password": "123456$"}).status_code == 422
    # No number
    assert client.post("/auth/register", json={"username": username, "password": "Password$"}).status_code == 422
    # No special
    assert client.post("/auth/register", json={"username": username, "password": "Password1"}).status_code == 422
    # Unsupported special
    assert client.post("/auth/register", json={"username": username, "password": "Password1!"}).status_code == 422

def test_login_success(setup_db):
    username = get_random_username()
    client.post("/auth/register", json={"username": username, "password": "Password1$"})
    
    res = client.post("/auth/login", json={"username": username, "password": "Password1$"})
    assert res.status_code == 200
    assert "token" in res.json()

def test_login_invalid(setup_db):
    username = get_random_username()
    client.post("/auth/register", json={"username": username, "password": "Password1$"})
    
    # Wrong password
    res = client.post("/auth/login", json={"username": username, "password": "WrongPassword1$"})
    assert res.status_code == 401
    
    # Nonexistent user
    res = client.post("/auth/login", json={"username": "nonexistentuser", "password": "Password1$"})
    assert res.status_code == 401

def test_auth_protection_and_daily_limit(setup_db):
    username = get_random_username()
    client.post("/auth/register", json={"username": username, "password": "Password1$"})
    token = client.post("/auth/login", json={"username": username, "password": "Password1$"}).json()["token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Play 3 games
    for _ in range(3):
        res = client.post("/games", headers=headers)
        assert res.status_code == 201
        
    # 4th game should fail
    res = client.post("/games", headers=headers)
    assert res.status_code == 400
    assert "limit" in res.json()["detail"].lower()
    
    # Unauthenticated
    res = client.post("/games")
    assert res.status_code in (401, 403)

def test_game_ownership(setup_db):
    u1 = get_random_username()
    u2 = get_random_username()
    client.post("/auth/register", json={"username": u1, "password": "Password1$"})
    client.post("/auth/register", json={"username": u2, "password": "Password1$"})
    
    t1 = client.post("/auth/login", json={"username": u1, "password": "Password1$"}).json()["token"]
    t2 = client.post("/auth/login", json={"username": u2, "password": "Password1$"}).json()["token"]
    
    game_id = client.post("/games", headers={"Authorization": f"Bearer {t1}"}).json()["game_id"]
    
    # u2 tries to access u1's game
    res = client.get(f"/games/{game_id}", headers={"Authorization": f"Bearer {t2}"})
    assert res.status_code == 404
