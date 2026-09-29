# Guess the Word

A clean, self-contained Python game engine for a 5-letter word guessing game.

## Stage 1: Core Game Logic

This stage implements only the core, in-memory game logic. It correctly evaluates guesses against a target word, accounting for duplicate characters, and manages the state of the game (attempts, win/loss status).

It intentionally does not include FastAPI, databases, authentication, or a frontend. Those will be added in future stages.

## Installation

1. Create a virtual environment:
   `python -m venv venv`
2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
3. Install dependencies:
   `pip install -r requirements.txt`

## Running Tests

To run the complete test suite:

`pytest`
