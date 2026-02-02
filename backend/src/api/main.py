from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# from services.youtube_tools import YouTubeTools
from src.api import chat
from src.agents.chat.graph import workflow
from src.core.config import settings
from src.core.database import init_db
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
import uvicorn
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINT_DB_PATH) as checkpointer:
        app.state.graph = workflow.compile(checkpointer=checkpointer)
        yield

app = FastAPI(debug=True, lifespan=lifespan)

origins = [
#    "https://explainium.vercel.app",
   "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)


if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)