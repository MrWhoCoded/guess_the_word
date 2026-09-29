# pyrefly: ignore [missing-import]
import pytest
from app.game.engine import Game

def test_game_starts_correctly():
    game = Game("APPLE")
    assert game.target == "APPLE"
    assert game.guesses == []
    assert game.max_attempts == 5
    assert not game.game_over
    assert not game.won

def test_invalid_target_length():
    with pytest.raises(ValueError, match="exactly 5 characters"):
        Game("A")
    with pytest.raises(ValueError, match="exactly 5 characters"):
        Game("ABCDEF")

def test_invalid_target_characters():
    with pytest.raises(ValueError, match="only alphabetic"):
        Game("12345")
    with pytest.raises(ValueError, match="only alphabetic"):
        Game("AB1DE")

def test_invalid_guess_length():
    game = Game("APPLE")
    with pytest.raises(ValueError, match="exactly 5 characters"):
        game.guess("APP")
    with pytest.raises(ValueError, match="exactly 5 characters"):
        game.guess("APPLES")

def test_invalid_guess_characters():
    game = Game("APPLE")
    with pytest.raises(ValueError, match="only alphabetic"):
        game.guess("AP1LE")

def test_first_guess_recorded():
    game = Game("APPLE")
    res = game.guess("GHOST")
    assert res["guess"] == "GHOST"
    assert res["attempt"] == 1
    assert game.guesses == ["GHOST"]

def test_multiple_guesses_recorded_in_order():
    game = Game("APPLE")
    game.guess("GHOST")
    game.guess("ALLEY")
    assert game.guesses == ["GHOST", "ALLEY"]

def test_winning_on_first_guess():
    game = Game("APPLE")
    res = game.guess("APPLE")
    assert res["won"] is True
    assert res["game_over"] is True
    assert game.won is True
    assert game.game_over is True

def test_winning_on_later_guess():
    game = Game("APPLE")
    game.guess("GHOST")
    res = game.guess("APPLE")
    assert res["won"] is True
    assert res["game_over"] is True

def test_losing_after_five_guesses():
    game = Game("APPLE")
    game.guess("GHOST")
    game.guess("GHOST")
    game.guess("GHOST")
    game.guess("GHOST")
    res = game.guess("GHOST")
    assert res["won"] is False
    assert res["game_over"] is True
    assert game.won is False
    assert game.game_over is True

def test_cannot_guess_after_winning():
    game = Game("APPLE")
    game.guess("APPLE")
    with pytest.raises(ValueError, match="Game is already over"):
        game.guess("GHOST")

def test_cannot_guess_after_losing():
    game = Game("APPLE")
    game.guess("GHOST")
    game.guess("GHOST")
    game.guess("GHOST")
    game.guess("GHOST")
    game.guess("GHOST")
    with pytest.raises(ValueError, match="Game is already over"):
        game.guess("GHOST")

def test_attempt_count_is_correct():
    game = Game("APPLE")
    res = game.guess("GHOST")
    assert res["attempt"] == 1
    res2 = game.guess("ALLEY")
    assert res2["attempt"] == 2

def test_case_normalization_in_game():
    game = Game("apple")
    assert game.target == "APPLE"
    res = game.guess("apple")
    assert res["guess"] == "APPLE"
    assert res["won"] is True
