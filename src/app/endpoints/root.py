from fastapi import APIRouter
from src.app.services.system.info import SystemInfoService

router = APIRouter(tags=["Root"])


@router.get("/")
async def root():
    """Главная страница API"""
    return SystemInfoService.get_info()
