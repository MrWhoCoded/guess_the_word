from fastapi import APIRouter, Depends
from app.database import operations as db
from app.api.auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/reports/daily")
def get_daily_report(admin: dict = Depends(get_current_admin)):
    return db.get_daily_report()

@router.get("/reports/users")
def get_user_report(admin: dict = Depends(get_current_admin)):
    return db.get_user_report()
