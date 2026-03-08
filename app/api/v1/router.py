from fastapi import APIRouter

from app.api.v1 import web, images, news, suggest, videos

router = APIRouter(prefix="/v1")

router.include_router(web.router)
router.include_router(images.router)
router.include_router(news.router)
router.include_router(suggest.router)
router.include_router(videos.router)
