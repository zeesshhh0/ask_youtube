from typing import List, Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.core.models import Thread, Message, YTVideo

async def get_thread_by_id(session: AsyncSession, thread_id: str) -> Optional[Thread]:
    """Retrieve a single thread by its ID."""
    result = await session.exec(select(Thread).where(Thread.thread_id == thread_id))
    return result.first()

async def get_all_threads(session: AsyncSession) -> List[Thread]:
    """Retrieve all threads."""
    result = await session.exec(select(Thread))
    return list(result.all())

async def create_thread(session: AsyncSession, video_id: str, title: str) -> Thread:
    """Create a new thread."""
    thread = Thread(video_id=video_id, title=title)
    session.add(thread)
    await session.commit()
    await session.refresh(thread)
    return thread

async def delete_thread_with_messages(session: AsyncSession, thread_id: str) -> bool:
    """Delete a thread and all associated messages."""
    thread = await get_thread_by_id(session, thread_id)
    if not thread:
        return False

    # Delete associated messages first
    messages_result = await session.exec(
        select(Message).where(Message.thread_id == thread_id)
    )
    for msg in messages_result.all():
        await session.delete(msg)

    await session.delete(thread)
    await session.commit()
    return True
