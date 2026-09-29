from app.game.evaluator import evaluate_guess

class Game:
    def __init__(self, target: str):
        self.target = self._validate_word(target)
        self.guesses = []
        self.max_attempts = 5
        self.game_over = False
        self.won = False
        
    def _validate_word(self, word: str) -> str:
        if not isinstance(word, str):
            raise ValueError("Word must be a string")
        if len(word) != 5:
            raise ValueError("Word must be exactly 5 characters long")
        if not word.isalpha():
            raise ValueError("Word must contain only alphabetic characters")
        return word.upper()

    def guess(self, word: str) -> dict:
        if self.game_over:
            raise ValueError("Game is already over")
            
        word = self._validate_word(word)
        
        result = evaluate_guess(self.target, word)
        
        self.guesses.append(word)
        attempt = len(self.guesses)
        
        if result == ["GREEN", "GREEN", "GREEN", "GREEN", "GREEN"]:
            self.won = True
            self.game_over = True
        elif attempt >= self.max_attempts:
            self.game_over = True
            
        return {
            "guess": word,
            "result": result,
            "attempt": attempt,
            "won": self.won,
            "game_over": self.game_over
        }
