from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from sqlmodel import select
from langchain_core.messages.ai import AIMessageChunk
from sqlmodel.ext.asyncio.session import AsyncSession
from src.agents.chat_agent import YTAgentState, YoutubeVideo
from src.core.database import get_db
from src.core.models import YTVideo, Thread, Message
from src.common.youtube_tools import YouTubeTools
from src.common.services import embeddings, llm, vector_store
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
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
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
):
    """Initialize a chat thread by ingesting a YouTube video."""
    try:
        video_url = str(request.video_url)
        video_id = YouTubeTools.get_youtube_video_id(video_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        # Check if video already exists
        result = await session.exec(select(YTVideo).where(YTVideo.video_id == video_id))
        video = result.first()

        if not video:
            video_info = YouTubeTools.get_video_data(video_url)
            transcript = await YouTubeTools.get_video_timestamps(video_url)

            if not transcript or transcript.startswith("No captions"):
                raise HTTPException(
                    status_code=404,
                    detail="No transcript available for this video",
                )

            parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
            child_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

            parent_docs = parent_splitter.create_documents([transcript])

            ids = []
            metadatas = []
            texts = []
            chapter_summaries_list = []

            for p_index, parent_doc in enumerate(parent_docs):
                chapter_prompt = (
                    f"Summarize this specific video section in 2 sentences:\n\n"
                    f"{parent_doc.page_content}"
                )
                chapter_summary_res = await llm.ainvoke(chapter_prompt)
                chapter_context = chapter_summary_res.content

                chapter_summaries_list.append(chapter_context)

                child_chunks = child_splitter.split_text(parent_doc.page_content)

                for c_index, chunk_text in enumerate(child_chunks):
                    doc_id = f"{video_id}_P{p_index}_C{c_index}"
                    ids.append(doc_id)
                    texts.append(chunk_text)
                    metadatas.append({
                        "video_id": video_id,
                        "chunk_index": c_index,
                        "parent_id": p_index,
                        "chapter_summary": chapter_context,
                    })

            combined_summaries = "\n- ".join(chapter_summaries_list)
            global_summary_prompt = (
                f"Here is an outline of a video based on its chapter summaries:\n\n"
                f"- {combined_summaries}\n\n"
                f"Task: Write a concise 5 Sentence Global Summary of the entire video based on this outline."
            )
            global_summary_res = await llm.ainvoke(global_summary_prompt)
            video_global_summary = global_summary_res.content

            docs_embeddings = embeddings.embed_documents(texts)
            vector_store.add_texts(
                ids=ids,
                texts=texts,
                embeddings=docs_embeddings,
                metadatas=metadatas,
            )

            # Insert video into DB
            video = YTVideo(
                video_id=video_id,
                url=video_url,
                title=video_info.get("title"),
                author_name=video_info.get("author_name"),
                thumbnail_url=video_info.get("thumbnail_url"),
                transcript=transcript,
                summary=video_global_summary,  # type: ignore
            )
            session.add(video)
            await session.commit()
            await session.refresh(video)

        # Create thread
        thread = Thread(video_id=video_id, title=video.title)
        session.add(thread)
        await session.commit()
        await session.refresh(thread)

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
    result = await session.exec(select(Thread))
    threads = result.all()
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
    result = await session.exec(select(Thread).where(Thread.thread_id == thread_id))
    thread = result.first()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Delete associated messages first
    messages_result = await session.exec(
        select(Message).where(Message.thread_id == thread_id)
    )
    for msg in messages_result.all():
        await session.delete(msg)

    await session.delete(thread)
    await session.commit()

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
):
    """Send a user message and stream the AI response via SSE."""

    result = await session.exec(select(Thread).where(Thread.thread_id == thread_id))
    thread = result.first()
    print(thread)
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    ytvideo_result = await session.exec(select(YTVideo).where(YTVideo.video_id == thread.video_id)) 
    ytvideo = ytvideo_result.first()

    if not ytvideo:
        raise HTTPException(status_code=404, detail="video not found")
    
    
    async def event_generator():
        agent = request.app.state.agent
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
async def get_messages(thread_id: str, request: Request):
    """Retrieve the message history for a thread."""
    agent = request.app.state.agent
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