from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.games import router as games_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router

app = FastAPI(title="Guess the Word API")

# --- API routes ---
app.include_router(auth_router)
app.include_router(games_router)
app.include_router(admin_router)

# --- Serve frontend static files ---
# The frontend/ directory sits next to the app/ package.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Mount static assets (css, js, etc.) so they resolve correctly
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")

# Serve HTML pages at their natural URLs
@app.get("/")
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/login.html")
def serve_login():
    return FileResponse(FRONTEND_DIR / "login.html")

@app.get("/register.html")
def serve_register():
    return FileResponse(FRONTEND_DIR / "register.html")

@app.get("/game.html")
def serve_game():
    return FileResponse(FRONTEND_DIR / "game.html")

@app.get("/admin.html")
def serve_admin():
    return FileResponse(FRONTEND_DIR / "admin.html")

