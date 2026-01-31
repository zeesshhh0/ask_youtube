from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.core.database import get_db
from src.core.models import YTVideo, Thread
from src.common.youtube_tools import YouTubeTools
from src.common.services import chroma_client, embeddings, llm
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from uuid import uuid4
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

class InitRequest(BaseModel):
    youtube_url: str
    generate_questions: bool = False

class MessageRequest(BaseModel):
    content: str
    video_id: str 

@router.post("/init")
async def init_chat(request: InitRequest, session: AsyncSession = Depends(get_db)):
    try:
        video_id = YouTubeTools.get_youtube_video_id(request.youtube_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        # Check if video exists
        result = await session.exec(select(YTVideo).where(YTVideo.video_id == video_id))
        video = result.first()

        if not video:
            # Video processing logic
            video_info = YouTubeTools.get_video_data(request.youtube_url)
            transcript = await YouTubeTools.get_video_captions(request.youtube_url)
            
            if not transcript or transcript.startswith("No captions"):
                    raise HTTPException(status_code=404, detail="No transcript available for this video")

            # Generate Summary
            summary_prompt = f"Summarize the following transcript in 5 bullet points:\n\n{transcript}"
            summary_response = await llm.ainvoke(summary_prompt)
            summary = summary_response.content

            # Store in ChromaDB
            collection = chroma_client.get_or_create_collection(name=f"video_{video_id}")
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunks = text_splitter.split_text(transcript)
            documents = [Document(page_content=chunk, metadata={"video_id": video_id, "chunk_index": i}) for i, chunk in enumerate(chunks)]
            
            if documents:
                ids = [f"{video_id}_chunk_{i}" for i in range(len(documents))]
                texts = [doc.page_content for doc in documents]
                metadatas = [doc.metadata for doc in documents]
                
                print("Generating embeddings...")
                docs_embeddings = embeddings.embed_documents(texts)
                
                collection.add(
                    ids=ids,
                    documents=texts,
                    embeddings=docs_embeddings, # type: ignore
                    metadatas=metadatas # type: ignore
                )

            # Insert into DB
            video = YTVideo(
                video_id=video_id,
                url=request.youtube_url, 
                title=video_info.get('title'), 
                author_name=video_info.get('author_name'), 
                thumbnail_url=video_info.get('thumbnail_url'), 
                transcript=transcript, 
                summary=summary # type: ignore
            )
            session.add(video)
            await session.commit()
            await session.refresh(video)

        # Create Thread
        thread = Thread(
            video_id=video_id,
            title=video.title
        )
        session.add(thread)
        await session.commit()
        await session.refresh(thread)

        return {
            "thread_id": thread.thread_id,
            "video_id": video.video_id,
            "title": video.title,
            "summary": video.summary
        }

    except Exception as e:
        logger.error(f"Error initializing chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{thread_id}/message")
async def chat_message(thread_id: str, message: MessageRequest, request: Request):
    async def event_generator():
        graph = request.app.state.graph
        config = {"configurable": {"thread_id": thread_id, "video_id": message.video_id}}
        
        async for event in graph.astream_events(
            {'messages': [HumanMessage(content=message.content)]},
            config=config,
            version="v2"
        ):
            kind = event["event"]
            
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            
            elif kind == "on_chain_end" and event["name"] == "retrieve_context":
                pass

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{thread_id}/messages")
async def get_messages(thread_id: str, request: Request):
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    return state.values.get("messages", [])