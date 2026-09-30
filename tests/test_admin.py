import os
import pytest
import random
import string
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from app.main import app
from app.database.init_db import init_db
from app.database import operations as db

client = TestClient(app)

def get_random_username():
    return "".join(random.choices(string.ascii_letters, k=10)).lower()

def get_unique_test_date():
    y = random.randint(2035, 2099)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y:04d}-{m:02d}-{d:02d}"

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    try:
        init_db()
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")
    yield

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
def player_headers():
    uname = get_random_username()
    client.post("/auth/register", json={"username": uname, "password": "Password1$"})
    token = client.post("/auth/login", json={"username": uname, "password": "Password1$"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}

def create_test_game(word_id, user_id, date_str, won=None):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO games (word_id, user_id, started_at, completed_at, won)
                VALUES (%s, %s, %s::timestamptz, %s, %s)
                RETURNING id;
            """, (word_id, user_id, f"{date_str} 12:00:00+00", f"{date_str} 12:05:00+00" if won is not None else None, won))
            game_id = cur.fetchone()[0]
        conn.commit()
        return game_id
    finally:
        conn.close()

def test_admin_can_access_daily_report(admin_headers):
    res = client.get("/admin/reports/daily", headers=admin_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_admin_can_access_user_report(admin_headers):
    res = client.get("/admin/reports/users", headers=admin_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_unauthenticated_cannot_access_reports():
    res1 = client.get("/admin/reports/daily")
    assert res1.status_code in (401, 403)
    
    res2 = client.get("/admin/reports/users")
    assert res2.status_code in (401, 403)

def test_player_cannot_access_reports(player_headers):
    res1 = client.get("/admin/reports/daily", headers=player_headers)
    assert res1.status_code == 403
    assert "Admin access required" in res1.json()["detail"]
    
    res2 = client.get("/admin/reports/users", headers=player_headers)
    assert res2.status_code == 403
    assert "Admin access required" in res2.json()["detail"]

def test_daily_report_distinct_users_and_wins_count(admin_headers):
    test_date = get_unique_test_date()
    word_id, _ = db.get_random_word()
    
    u1, u2 = get_random_username(), get_random_username()
    db.create_user(u1, "hash")
    db.create_user(u2, "hash")
    u1_id = db.get_user_by_username(u1)["id"]
    u2_id = db.get_user_by_username(u2)["id"]
    
    # User 1 starts 2 games on test_date: 1 win, 1 loss
    create_test_game(word_id, u1_id, test_date, won=True)
    create_test_game(word_id, u1_id, test_date, won=False)
    
    # User 2 starts 1 game on test_date: 1 win
    create_test_game(word_id, u2_id, test_date, won=True)
    
    res = client.get("/admin/reports/daily", headers=admin_headers)
    assert res.status_code == 200
    reports = res.json()
    
    target_row = next((r for r in reports if r["date"] == test_date), None)
    assert target_row is not None
    # 2 distinct users (User 1 and User 2) despite 3 games started
    assert target_row["users"] == 2
    # 2 correct guesses (1 from User 1 + 1 from User 2)
    assert target_row["correct_guesses"] == 2

def test_user_report_words_tried_vs_guesses_and_wins_count(admin_headers):
    test_date = get_unique_test_date()
    word_id, _ = db.get_random_word()
    
    u1 = get_random_username()
    db.create_user(u1, "hash")
    u1_id = db.get_user_by_username(u1)["id"]
    
    # User 1 starts 2 games on test_date
    g1 = create_test_game(word_id, u1_id, test_date, won=True)
    create_test_game(word_id, u1_id, test_date, won=False)
    
    # Add 4 individual guess attempts to g1
    for i in range(1, 5):
        db.save_guess(g1, "APPLE", i)
        
    res = client.get("/admin/reports/users", headers=admin_headers)
    assert res.status_code == 200
    reports = res.json()
    
    user_row = next((r for r in reports if r["date"] == test_date and r["username"] == u1), None)
    assert user_row is not None
    # words_tried = 2 games started (NOT 4 guesses + games)
    assert user_row["words_tried"] == 2
    # correct_guesses = 1 (1 game won)
    assert user_row["correct_guesses"] == 1

def test_multiple_dates_grouped_separately(admin_headers):
    date1 = get_unique_test_date()
    date2 = get_unique_test_date()
    while date2 == date1:
        date2 = get_unique_test_date()
        
    word_id, _ = db.get_random_word()
    
    u1 = get_random_username()
    db.create_user(u1, "hash")
    u1_id = db.get_user_by_username(u1)["id"]
    
    create_test_game(word_id, u1_id, date1, won=True)
    create_test_game(word_id, u1_id, date2, won=False)
    
    res = client.get("/admin/reports/daily", headers=admin_headers)
    assert res.status_code == 200
    reports = res.json()
    
    row1 = next((r for r in reports if r["date"] == date1), None)
    row2 = next((r for r in reports if r["date"] == date2), None)
    assert row1 is not None
    assert row2 is not None
    assert row1["date"] != row2["date"]

def test_user_without_games_does_not_appear_in_user_report(admin_headers):
    test_date = get_unique_test_date()
    word_id, _ = db.get_random_word()
    
    u_active = get_random_username()
    u_inactive = get_random_username()
    
    db.create_user(u_active, "hash")
    db.create_user(u_inactive, "hash")
    
    u_active_id = db.get_user_by_username(u_active)["id"]
    
    create_test_game(word_id, u_active_id, test_date, won=True)
    
    res = client.get("/admin/reports/users", headers=admin_headers)
    assert res.status_code == 200
    reports = res.json()
    
    active_row = next((r for r in reports if r["date"] == test_date and r["username"] == u_active), None)
    inactive_row = next((r for r in reports if r["date"] == test_date and r["username"] == u_inactive), None)
    
    assert active_row is not None
    assert inactive_row is None

def test_empty_report_format(admin_headers):
    daily = client.get("/admin/reports/daily", headers=admin_headers).json()
    users = client.get("/admin/reports/users", headers=admin_headers).json()
    assert isinstance(daily, list)
    assert isinstance(users, list)
