import re
import secrets
import psycopg.errors
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import operations as db

router = APIRouter(prefix="/auth", tags=["auth"])
ph = PasswordHasher()
security = HTTPBearer()

class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str):
        if len(v) < 5 or not v.isalpha():
            raise ValueError("Username must be at least 5 alphabetic characters")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        if len(v) < 5:
            raise ValueError("Password must be at least 5 characters long")
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError("Password must contain at least one alphabetic character")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r'[$%*&]', v):
            raise ValueError("Password must contain at least one of: $, %, *, &")
        if re.search(r'[^a-zA-Z0-9$%*&]', v):
            raise ValueError("Password contains unsupported special characters")
        return v

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/register")
def register(request: RegisterRequest):
    username = request.username.lower()
    if db.get_user_by_username(username):
        raise HTTPException(status_code=400, detail="Username already exists. Please choose another username.")
    
    password_hash = ph.hash(request.password)
    try:
        db.create_user(username, password_hash, role="player")
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="Username already exists. Please choose another username.")
    return {"message": "User registered successfully"}

@router.post("/login")
def login(request: LoginRequest):
    username = request.username.lower()
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    try:
        ph.verify(user["password_hash"], request.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    token = secrets.token_hex(32)
    db.create_session(token, user["id"])
    return {"token": token}

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = db.get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

def get_current_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


