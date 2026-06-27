from fastapi import APIRouter
from app.api.routes import auth, jobs, apply

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(apply.router, prefix="/public", tags=["Public Apply"])
