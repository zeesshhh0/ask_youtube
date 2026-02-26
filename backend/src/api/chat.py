from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_core.messages.ai import AIMessageChunk
from sqlmodel.ext.asyncio.session import AsyncSession
from src.agents.chat_agent import YTAgentState, YoutubeVideo
from src.api.deps import get_db, get_llm, get_embeddings, get_vector_store, get_agent
from src.core.models import Message
from src.core.database import engine
from starlette.background import BackgroundTask
from src.crud import thread as crud_thread
from src.crud import video as crud_video
from src.crud import message as crud_message
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
import json
from src.services.youtube_service import ingest_youtube_video
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
            duration=video.duration,
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

    response_context = {'content': "" }

    try:
        thread = await crud_thread.get_thread_by_id(session, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        ytvideo = await crud_video.get_video_by_id(session, thread.video_id)
        if not ytvideo:
            raise HTTPException(status_code=404, detail="video not found")
        
        user_message = Message(
            thread_id=thread_id,
            content=message.content,
            sender="human",
        )
        
        await crud_message.create_message(session, user_message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    async def event_generator():
        try:
            config = {
                "configurable": {
                    "thread_id": thread_id,
                }
            }
            
            video = YoutubeVideo(
                video_id=thread.video_id,
                title=ytvideo.title,
                summary=ytvideo.summary
            )

            input_state: YTAgentState = YTAgentState(
                messages=[HumanMessage(content=message.content)],
                videos=[video]
            )

            async for event in agent.astream(
                input=input_state,
                config=config,
                stream_mode="messages"
            ):
                msg = event[0]
                
                if isinstance(msg, AIMessageChunk):
                    content = msg.content
                    response_context['content'] += content # type: ignore
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

            yield f"data: {json.dumps({'type': 'end'})}\n\n"
        except Exception as e:
            logger.error(f"Error during SSE generation: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': 'An error occurred during message generation.'})}\n\n"

    async def save_streamed_message():
        try:
            if response_context['content']:
                async with AsyncSession(engine, expire_on_commit=False) as bg_session:
                    ai_message = Message(
                        thread_id=thread_id,
                        content=response_context['content'],
                        sender="ai",
                    )
                    await crud_message.create_message(session=bg_session, message=ai_message)
        except Exception as e:
            logger.error(f"Error saving streamed message: {e}")

    try:
        return StreamingResponse(
            event_generator(), 
            media_type="text/event-stream", 
            background=BackgroundTask(save_streamed_message)
        )
    except Exception as e:
        logger.error(f"Error establishing stream: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
    session: AsyncSession = Depends(get_db)
):
    """Retrieve the message history for a thread."""
    thread = await crud_thread.get_thread_by_id(session, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages_from_db = await crud_message.get_all_message_by_thread(session, thread_id)

    messages = [
        MessageResponse(
            message_id=msg.message_id,
            role="human" if msg.sender == "human" else "ai",
            content=msg.content if isinstance(msg.content, str) else str(msg.content),
            metadata=json.loads(msg.metadata_json) if msg.metadata_json else None,
            created_at=msg.created_at,
        )
        for msg in messages_from_db
        if msg.sender in ("human", "ai")
    ]

    return ThreadMessagesResponse(thread_id=thread_id, messages=messages)