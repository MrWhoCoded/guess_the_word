from fastapi import APIRouter, Depends
from app.database import operations as db
from app.api.auth import get_current_admin
from app.services.rate_limiter import rate_limit

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/reports/daily", dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))])
def get_daily_report(admin: dict = Depends(get_current_admin)):
    return db.get_daily_report()

@router.get("/reports/users", dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))])
def get_user_report(admin: dict = Depends(get_current_admin)):
    return db.get_user_report()

