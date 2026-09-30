import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.init_db import init_db
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

@pytest.fixture
def auth_headers(setup_db):
    username = get_random_username()
    client.post("/auth/register", json={"username": username, "password": "Password1$"})
    token = client.post("/auth/login", json={"username": username, "password": "Password1$"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_game(auth_headers):
    response = client.post("/games", headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert "game_id" in data
    assert "target_word" not in data
    assert data["attempts_used"] == 0
    
def test_get_invalid_game(auth_headers):
    response = client.get("/games/9999999", headers=auth_headers)
    assert response.status_code == 404

def test_full_game_flow(auth_headers):
    response = client.post("/games", headers=auth_headers)
    game_id = response.json()["game_id"]
    
    guess_resp = client.post(f"/games/{game_id}/guesses", json={"guess": "APPLE"}, headers=auth_headers)
    assert guess_resp.status_code == 200
    data = guess_resp.json()
    assert "result" in data
    assert data["attempt"] == 1
    assert "target_word" not in data
    
    guesses_resp = client.get(f"/games/{game_id}/guesses", headers=auth_headers)
    assert guesses_resp.status_code == 200
    guesses_data = guesses_resp.json()
    assert len(guesses_data["guesses"]) == 1
    assert guesses_data["guesses"][0]["guess"] == "APPLE"
    assert guesses_data["guesses"][0]["guess_number"] == 1
    
    game_resp = client.get(f"/games/{game_id}", headers=auth_headers)
    assert game_resp.status_code == 200
    assert game_resp.json()["attempts_used"] == 1
    
def test_invalid_guess_rejected(auth_headers):
    response = client.post("/games", headers=auth_headers)
    game_id = response.json()["game_id"]
    
    resp = client.post(f"/games/{game_id}/guesses", json={"guess": "APP"}, headers=auth_headers)
    assert resp.status_code == 400
    
    resp = client.post(f"/games/{game_id}/guesses", json={"guess": "12345"}, headers=auth_headers)
    assert resp.status_code == 400
    
def test_game_over_rejects_guesses(auth_headers):
    response = client.post("/games", headers=auth_headers)
    game_id = response.json()["game_id"]
    
    for i in range(5):
        client.post(f"/games/{game_id}/guesses", json={"guess": "GHOST"}, headers=auth_headers)
        
    resp = client.post(f"/games/{game_id}/guesses", json={"guess": "GHOST"}, headers=auth_headers)
    assert resp.status_code == 400
    assert "over" in resp.json()["detail"].lower()
