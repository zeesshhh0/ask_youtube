from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from src.core.config import settings
from src.core.models import YTVideo, Thread, Message  # Import models to register them

DB_URL = f"sqlite+aiosqlite:///{settings.APP_DB_PATH}"

engine = create_async_engine(DB_URL, echo=True)

async def init_db():
    async with engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # Optional: if we want to reset
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_db():    
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
