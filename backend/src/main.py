from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import chat
from src.agents.chat_agent import agent
from src.core.config import settings
from src.core.database import init_db
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from contextlib import asynccontextmanager
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncPostgresSaver.from_conn_string(f"dbname={settings.DB_DBNAME} user={settings.DB_USER} password={settings.DB_PASSWORD} host={settings.DB_HOST} port={settings.DB_PORT}") as checkpointer:
        agent.checkpointer = checkpointer
        app.state.agent = agent
        yield

app = FastAPI(lifespan=lifespan)

origins = [
   "https://ask-youtubee.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix=settings.API_V1_STR)

@app.get('/')
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)