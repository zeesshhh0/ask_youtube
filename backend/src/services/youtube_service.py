import logging
from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from src.core.models import YTVideo
from src.services.youtube_tools import YouTubeTools

logger = logging.getLogger(__name__)

async def ingest_youtube_video(
    video_url: str, 
    session: AsyncSession,
    llm: BaseChatModel,
    embeddings: Embeddings,
    vector_store: VectorStore
) -> YTVideo:
    """Ingests a YouTube video: fetches transcript, chunks, summarizes, embeds, and saves to DB."""
    video_id = YouTubeTools.get_youtube_video_id(video_url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # Check if video already exists
    result = await session.exec(select(YTVideo).where(YTVideo.video_id == video_id))
    video = result.first()

    if video:
        return video
    
    try:
        duration = YouTubeTools.get_video_duration(video_url)
        if duration and duration > 1200:
            raise HTTPException(
                status_code=413,
                detail=f"Video is too long ({duration}s). Maximum allowed duration is 1200 seconds (20 minutes)."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to fetch duration for {video_id}: {e}")
        duration = None

    logger.info(f"Ingesting new video: {video_id}")
    video_info = YouTubeTools.get_video_data(video_url)
    transcript = await YouTubeTools.get_video_timestamps(video_url)
    

    if not transcript or transcript.startswith("No captions"):
        raise HTTPException(
            status_code=404,
            detail="No transcript available for this video",
        )

    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=300)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

    parent_docs = (doc for doc in parent_splitter.create_documents([transcript]))

    ids = []
    metadatas = []
    texts = []
    chapter_summaries_list = []

    for p_index, parent_doc in enumerate(parent_docs):
        chapter_prompt = f"""You are summarizing a section of a YouTube video transcript for use in a retrieval-augmented search system.

        Your goal is to write a dense, information-rich summary that preserves:
        - The core topic or argument of this section
        - Any specific facts, names, tools, or steps mentioned
        - The "so what" — why this section matters in the broader video

        Rules:
        - Write exactly 2-3 sentences
        - Use plain, direct language (no filler like "In this section...")
        - Preserve technical terms exactly as spoken
        - Do NOT add information not present in the transcript

        Transcript section:
        \"\"\"
        {parent_doc.page_content}
        \"\"\"

        Summary:"""
        
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
    global_summary_prompt = f"""You are creating a global summary of a YouTube video based on its section summaries.

    This summary will be shown to users who want to quickly understand what the entire video covers before asking questions about it.

    Chapter summaries:
    {combined_summaries}

    Task: Write a 4-6 sentence global summary that:
    1. Opens with the video's central topic and purpose
    2. Covers the main themes/phases in logical order
    3. Highlights the most important takeaways or conclusions
    4. Uses language a reader unfamiliar with the topic can understand

    Do not use bullet points. Write in flowing prose. Do not reference "chapters" or "sections" explicitly.

    Global Summary:"""
    
    global_summary_res = await llm.ainvoke(global_summary_prompt)
    video_global_summary = global_summary_res.content

    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_texts = texts[i : i + batch_size]
        batch_metadatas = metadatas[i : i + batch_size]

        batch_embeddings = await embeddings.aembed_documents(batch_texts)
        await vector_store.aadd_texts(
            ids=batch_ids,
            texts=batch_texts,
            embeddings=batch_embeddings,
            metadatas=batch_metadatas,
        )

    # Insert video into DB
    video = YTVideo(
        video_id=video_id,
        url=video_url,
        title=video_info.get("title"), # type: ignore
        author_name=video_info.get("author_name"),
        thumbnail_url=video_info.get("thumbnail_url"),
        transcript=transcript,
        duration=duration,
        summary=video_global_summary,  # type: ignore
    )
    session.add(video)
    await session.commit()
    await session.refresh(video)

    return video
