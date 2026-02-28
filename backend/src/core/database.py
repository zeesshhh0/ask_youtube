from sqlmodel import SQLModel 
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from src.core.config import settings

engine = create_async_engine(settings.DB_URL, echo=True, poolclass=NullPool)

async def init_db():
    async with engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) 
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_db():    
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
