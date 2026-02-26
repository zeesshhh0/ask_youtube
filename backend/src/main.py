from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import chat
from src.agents.chat_agent import agent
from src.core.config import settings
from src.core.database import init_db
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINT_DB_PATH) as checkpointer:
        agent.checkpointer = checkpointer
        app.state.agent = agent
        yield

app = FastAPI(debug=True, lifespan=lifespan)

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


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)