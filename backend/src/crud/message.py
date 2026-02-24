from typing import Literal

from src.core.models import YTVideo, Thread, Message
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

async def create_message(session: AsyncSession, message:Message) -> Message:
  session.add(message)
  await session.commit()
  await session.refresh(message)
  return message

async def get_all_message_by_thread(session: AsyncSession, thread_id: str) -> list[Message]:
  result = await session.exec(select(Message).where(Message.thread_id == thread_id))
  return list(result.all())