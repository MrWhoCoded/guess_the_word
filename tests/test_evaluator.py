from app.game.evaluator import evaluate_guess

def test_evaluate_exact_match():
    assert evaluate_guess("APPLE", "APPLE") == ["GREEN", "GREEN", "GREEN", "GREEN", "GREEN"]

def test_evaluate_completely_incorrect():
    assert evaluate_guess("APPLE", "GHOST") == ["GREY", "GREY", "GREY", "GREY", "GREY"]

def test_evaluate_correct_letter_wrong_position():
    assert evaluate_guess("APPLE", "PEACH") == ["ORANGE", "ORANGE", "ORANGE", "GREY", "GREY"]

def test_evaluate_mixture():
    assert evaluate_guess("APPLE", "AMPLY") == ["GREEN", "GREY", "GREEN", "GREEN", "GREY"]

def test_evaluate_repeated_letters_in_target():
    # Target: A P P L E
    # Guess:  A L L E Y
    # Pass 1: A at 0 matches (GREEN)
    # Pass 2: L at 1 gets ORANGE (matches L at 3). L at 2 gets GREY. E at 3 gets ORANGE (matches E at 4).
    assert evaluate_guess("APPLE", "ALLEY") == ["GREEN", "ORANGE", "GREY", "ORANGE", "GREY"]

def test_evaluate_repeated_letters_in_guess():
    # Guess has two L's, target has one L
    # Target: W O R L D
    # Guess:  H E L L O
    # Pass 1: L at 3 matches L at 3 (GREEN). 
    # Pass 2: L at 2 gets GREY. O at 4 gets ORANGE (matches O at 1).
    assert evaluate_guess("WORLD", "HELLO") == ["GREY", "GREY", "GREY", "GREEN", "ORANGE"]

def test_evaluate_repeated_letters_in_both():
    # Target: A P P L E
    # Guess:  P U P P Y
    # Pass 1: P at 2 matches P at 2 (GREEN).
    # Pass 2: P at 0 matches P at 1 (ORANGE). P at 3 gets GREY.
    assert evaluate_guess("APPLE", "PUPPY") == ["ORANGE", "GREY", "GREEN", "GREY", "GREY"]

def test_evaluate_duplicate_orange_limitation():
    # Target: W A T E R
    # Guess:  A A L I I
    # Pass 1: A at 1 matches A at 1 (GREEN).
    # Pass 2: A at 0 gets GREY.
    assert evaluate_guess("WATER", "AALII") == ["GREY", "GREEN", "GREY", "GREY", "GREY"]
    
def test_evaluate_case_normalization():
    assert evaluate_guess("apple", "APPLE") == ["GREEN", "GREEN", "GREEN", "GREEN", "GREEN"]
    assert evaluate_guess("APPLE", "apple") == ["GREEN", "GREEN", "GREEN", "GREEN", "GREEN"]
