from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from sqlmodel import select
from langchain_core.messages.ai import AIMessageChunk
from sqlmodel.ext.asyncio.session import AsyncSession
from src.agents.chat_agent import YTAgentState, YoutubeVideo
from src.api.deps import get_db, get_llm, get_embeddings, get_vector_store, get_agent
from src.crud import thread as crud_thread
from src.crud import video as crud_video
from src.api.schemas import (
    CreateThreadRequest,
    CreateThreadResponse,
    SendMessageRequest,
    ThreadListItem,
    ThreadMessagesResponse,
    MessageResponse,
    DeleteThreadResponse,
    ErrorResponse,
)
from src.services.youtube_service import ingest_youtube_video
from uuid import uuid4
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/threads", tags=["Threads"])


# ──────────────────────────────────────────────
# POST /threads — Create a new thread (ingest video)
# ──────────────────────────────────────────────

@router.post(
    "",
    response_model=CreateThreadResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def create_thread(
    request: CreateThreadRequest,
    session: AsyncSession = Depends(get_db),
    llm = Depends(get_llm),
    embeddings = Depends(get_embeddings),
    vector_store = Depends(get_vector_store),
):
    """Initialize a chat thread by ingesting a YouTube video."""
    try:
        video_url = str(request.video_url)
        
        # Ingest logic is now in the service layer
        video = await ingest_youtube_video(video_url, session, llm, embeddings, vector_store)

        # Create thread
        thread = await crud_thread.create_thread(session, video.video_id, video.title)

        return CreateThreadResponse(
            thread_id=thread.thread_id,
            video_id=video.video_id,
            title=video.title,
            summary=video.summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating thread: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# GET /threads — List all threads
# ──────────────────────────────────────────────

@router.get("", response_model=list[ThreadListItem])
async def list_threads(session: AsyncSession = Depends(get_db)):
    """List all conversation threads."""
    threads = await crud_thread.get_all_threads(session)
    return [
        ThreadListItem(
            thread_id=t.thread_id,
            title=t.title,
            video_id=t.video_id,
            created_at=t.created_at,
        )
        for t in threads
    ]


# ──────────────────────────────────────────────
# DELETE /threads/{thread_id} — Delete a thread
# ──────────────────────────────────────────────

@router.delete(
    "/{thread_id}",
    response_model=DeleteThreadResponse,
    responses={404: {"model": ErrorResponse}},
)
async def delete_thread(
    thread_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Delete a conversation thread and its messages."""
    success = await crud_thread.delete_thread_with_messages(session, thread_id)
    if not success:
        raise HTTPException(status_code=404, detail="Thread not found")

    return DeleteThreadResponse(success=True, thread_id=thread_id)


# ──────────────────────────────────────────────
# POST /threads/{thread_id}/messages — Send a message (SSE stream)
# ──────────────────────────────────────────────

@router.post("/{thread_id}/messages")
async def send_message(
    thread_id: str,
    message: SendMessageRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    agent = Depends(get_agent),
):
    """Send a user message and stream the AI response via SSE."""

    thread = await crud_thread.get_thread_by_id(session, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    ytvideo = await crud_video.get_video_by_id(session, thread.video_id)
    if not ytvideo:
        raise HTTPException(status_code=404, detail="video not found")
    
    
    async def event_generator():
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }
        
        video = YoutubeVideo(
        video_id= thread.video_id,
        title= ytvideo.title,
        summary= ytvideo.summary
        )

        input: YTAgentState = YTAgentState(
            messages=[HumanMessage(content= message.content)],
            videos=[video]
            )

        async for event in agent.astream(
            input = input,
            config=config,
            stream_mode="messages"
        ):
            msg = event[0]
            
            if isinstance(msg, AIMessageChunk):
                content = msg.content
                if content:
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ──────────────────────────────────────────────
# GET /threads/{thread_id}/messages — Get chat history
# ──────────────────────────────────────────────

@router.get(
    "/{thread_id}/messages",
    response_model=ThreadMessagesResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_messages(
    thread_id: str, 
    request: Request,
    agent = Depends(get_agent),
):
    """Retrieve the message history for a thread."""
    config = {"configurable": {"thread_id": thread_id}}

    state = await agent.aget_state(config)
    raw_messages = state.values.get("messages", [])

    messages = [
        MessageResponse(
            message_id=i,
            role="human" if msg.type == "human" else "ai",
            content=msg.content if isinstance(msg.content, str) else str(msg.content),
            metadata=getattr(msg, "response_metadata", None),
            created_at=getattr(msg, "created_at", None) or datetime.fromisoformat("1970-01-01T00:00:00"),
        )
        for i, msg in enumerate(raw_messages)
        if msg.type in ("human", "ai")
    ]

    return ThreadMessagesResponse(thread_id=thread_id, messages=messages)