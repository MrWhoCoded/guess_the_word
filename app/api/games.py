from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from app.database import operations as db
from app.game.engine import Game
from app.api.auth import get_current_user

router = APIRouter(prefix="/games", tags=["games"])

class GuessRequest(BaseModel):
    guess: str

@router.post("", status_code=status.HTTP_201_CREATED)
def start_game(user = Depends(get_current_user)):
    games_today = db.count_user_games_today(user["id"])
    if games_today >= 3:
        raise HTTPException(status_code=400, detail="Daily game limit reached")
        
    word_id, _ = db.get_random_word()
    if not word_id:
        raise HTTPException(status_code=500, detail="No words available in the database.")
    
    game_id = db.create_game(word_id, user["id"])
    return {
        "game_id": game_id,
        "attempts_used": 0,
        "max_attempts": 5,
        "game_over": False,
        "won": False
    }

@router.get("/{game_id}")
def get_game(game_id: int, user = Depends(get_current_user)):
    game_data = db.get_game(game_id)
    if not game_data or game_data[5] != user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    
    _, _, _, completed_at, won, _ = game_data
    guesses = db.get_guesses(game_id)
    
    return {
        "game_id": game_id,
        "attempts_used": len(guesses),
        "max_attempts": 5,
        "won": won if won is not None else False,
        "game_over": completed_at is not None
    }

@router.post("/{game_id}/guesses")
def submit_guess(game_id: int, request: GuessRequest, user = Depends(get_current_user)):
    game_data = db.get_game(game_id)
    if not game_data or game_data[5] != user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    
    _, word_id, _, completed_at, _, _ = game_data
    
    if completed_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game is already over")
        
    target_word = db.get_word(word_id)
    if not target_word:
        raise HTTPException(status_code=500, detail="Target word not found")
    
    # Reconstruct game state
    game = Game(target_word)
    previous_guesses = db.get_guesses(game_id)
    
    # Play previous guesses to reach current state
    for prev_guess, _, _ in previous_guesses:
        game.guess(prev_guess)
        
    # Process new guess
    try:
        res = game.guess(request.guess)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    # Save the new guess
    db.save_guess(game_id, res["guess"], res["attempt"])
    
    # If game ended, mark as completed
    if res["game_over"]:
        db.complete_game(game_id, res["won"])
        
    return {
        "game_id": game_id,
        "guess": res["guess"],
        "result": res["result"],
        "attempt": res["attempt"],
        "won": res["won"],
        "game_over": res["game_over"]
    }

@router.get("/{game_id}/guesses")
def get_game_guesses(game_id: int, user = Depends(get_current_user)):
    game_data = db.get_game(game_id)
    if not game_data or game_data[5] != user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
        
    guesses = db.get_guesses(game_id)
    return {
        "game_id": game_id,
        "guesses": [
            {"guess": g[0], "guess_number": g[1]} 
            for g in guesses
        ]
    }
