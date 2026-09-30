from fastapi import FastAPI
from app.api.games import router as games_router
from app.api.auth import router as auth_router

app = FastAPI(title="Guess the Word API")

app.include_router(auth_router)
app.include_router(games_router)
