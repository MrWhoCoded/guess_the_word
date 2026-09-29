def evaluate_guess(target: str, guess: str) -> list[str]:
    """
    Evaluates a 5-letter guess against a 5-letter target word.
    Returns a list of 5 strings: 'GREEN', 'ORANGE', or 'GREY'.
    """
    target = target.upper()
    guess = guess.upper()
    
    result = ["GREY"] * 5
    target_letters_left = []
    
    # Pass 1: Find exact matches (GREEN)
    for i in range(5):
        if guess[i] == target[i]:
            result[i] = "GREEN"
            target_letters_left.append(None) # Consumed
        else:
            target_letters_left.append(target[i])
            
    # Pass 2: Find letter matches in wrong positions (ORANGE)
    for i in range(5):
        if result[i] != "GREEN":
            if guess[i] in target_letters_left:
                result[i] = "ORANGE"
                # Consume this letter so it can't be matched again
                idx = target_letters_left.index(guess[i])
                target_letters_left[idx] = None
                
    return result
