from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.core.database import get_db
from src.core.models import YTVideo, Thread
from src.common.youtube_tools import YouTubeTools
from src.common.services import chroma_client, embeddings, llm, vector_store
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_classic.chains.combine_documents.map_reduce import  MapReduceDocumentsChain
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

@router.post("/threads")
async def init_threads(request: InitRequest, session: AsyncSession = Depends(get_db)):
    try:
        video_id = YouTubeTools.get_youtube_video_id(request.youtube_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        # Check if video exists
        result = await session.exec(select(YTVideo).where(YTVideo.video_id == video_id))
        video = result.first()

        if not video:
            video_info = YouTubeTools.get_video_data(request.youtube_url)
            transcript = await YouTubeTools.get_video_timestamps(request.youtube_url)
            
            if not transcript or transcript.startswith("No captions"):
                    raise HTTPException(status_code=404, detail="No transcript available for this video")

            parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
            child_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)

            parent_docs = parent_splitter.create_documents([transcript])

            ids = []
            metadatas = []
            texts = []
            chapter_summaries_list = []

            for p_index, parent_doc in enumerate(parent_docs):
                
                chapter_prompt = f"Summarize this specific video section in 2 sentences:\n\n{parent_doc.page_content}"
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

                global_summary_prompt = f"""
                Here is an outline of a video based on its chapter summaries:

                - {combined_summaries}

                Task: Write a concise 5 Sentence Global Summary of the entire video based on this outline.
                """

                global_summary_res = await llm.ainvoke(global_summary_prompt)
                video_global_summary = global_summary_res.content
                
                docs_embeddings = embeddings.embed_documents(texts)

                vector_store.add_texts(
                    ids=ids,
                    texts=texts,
                    embeddings=docs_embeddings,
                    metadatas=metadatas
                )

            # Insert into DB
            video = YTVideo(
                video_id=video_id,
                url=request.youtube_url, 
                title=video_info.get('title'), 
                author_name=video_info.get('author_name'), 
                thumbnail_url=video_info.get('thumbnail_url'), 
                transcript=transcript, 
                summary=video_global_summary # type: ignore
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


@router.get("/threads")
async def get_threads(session: AsyncSession = Depends(get_db)):
    result = await session.exec(select(Thread))
    return result.all()


@router.get("/{thread_id}/history")
async def get_messages(thread_id: str, request: Request):
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    return state.values.get("messages", [])