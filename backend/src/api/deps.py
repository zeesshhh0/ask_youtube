from typing import AsyncGenerator
from fastapi import Request
from langchain_pinecone import PineconeVectorStore
from sqlmodel.ext.asyncio.session import AsyncSession
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from src.core.config import settings
from src.core.database import engine
from pinecone import Pinecone
import os

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting a database session."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

def get_llm():
    """Dependency for getting the Language Model."""
    return ChatGoogleGenerativeAI(
      model=settings.FASTEST_LLM_MODEL,
    )

def get_embeddings():
    """Dependency for getting the Embeddings Model."""
    return GoogleGenerativeAIEmbeddings(
      model=settings.EMBEDDING_MODEL,
    )

def get_vector_store():
    """Dependency for getting the Vector Store."""

    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    index = pc.Index(settings.PINECONE_INDEX_NAME)

    return PineconeVectorStore(index=index, embedding=get_embeddings())

    # chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)

    # return Chroma(
    #   client=chroma_client,
    #   collection_name=settings.CHROMA_COLLECTION_NAME,
    #   embedding_function=get_embeddings()
    # )


def get_agent(request: Request):
    """Dependency for getting the LangGraph agent tied to the app."""
    return request.app.state.agent
