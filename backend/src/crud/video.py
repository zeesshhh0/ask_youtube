from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.core.models import YTVideo

async def get_video_by_id(session: AsyncSession, video_id: str) -> Optional[YTVideo]:
    """Retrieve a video by its ID."""
    result = await session.exec(select(YTVideo).where(YTVideo.video_id == video_id))
    return result.first()

async def get_video_by_url(session: AsyncSession, url: str) -> Optional[YTVideo]:
    """Retrieve a video by its URL."""
    result = await session.exec(select(YTVideo).where(YTVideo.url == url))
    return result.first()
