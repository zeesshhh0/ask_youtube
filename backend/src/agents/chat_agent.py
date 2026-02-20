from typing import Dict, List, TypedDict
from langchain.tools import tool
from langchain.agents import create_agent
from src.common.services import vector_store, llm
from langchain.tools import tool, ToolRuntime
from langchain.agents.middleware import dynamic_prompt, ModelRequest, AgentState
from langsmith import Client
from langgraph.checkpoint.memory import InMemorySaver
from langchain_classic.prompts import BaseChatPromptTemplate
from collections import defaultdict


langsmith_client = Client()
ask_youtube_agent_system_prompt : BaseChatPromptTemplate = langsmith_client.pull_prompt(
    "ask_youtube_agent_system_prompt",
) 

class YoutubeVideo(TypedDict):
    video_id: str
    title: str
    summary: str

class YTAgentState(AgentState):
    videos: List[YoutubeVideo]

@dynamic_prompt
def inject_video_summaries(request: ModelRequest) -> str:
    """
    Dynamically generates the system prompt based on the active videos
    in the current runtime context.
    """
    
    base_prompt = ask_youtube_agent_system_prompt.format()

    active_videos = request.state.get('videos', [])

    video_context_str = "\n\n# CURRENT CONTEXT\n## Active Video Summaries:\n"
    
    for id, vid in enumerate(active_videos):
        # Get summary or fallback text
        video_context_str += f"- **Video** - Video Number: {id+1}\n Video Title: {vid['title']}\n Video Summary: {vid['summary']}\n"
    
    return base_prompt + video_context_str



@tool(response_format="content_and_artifact")
def retrieve_context(query: str, runtime: ToolRuntime[YTAgentState]):
    """
    Search the video transcripts for specific details.
    """
    videos = runtime.state.get('videos', [])

    video_ids = [vid['video_id'] for vid in videos]

    retrieved_docs = vector_store.similarity_search(
        query,
        k=5,
        filter={
            "video_id": {"$in": video_ids}
        } # type: ignore
    )

    grouped_docs = defaultdict(lambda: defaultdict(list))
    for doc in retrieved_docs:
        vid = doc.metadata.get('video_id', 'Unknown Video')
        chapter = doc.metadata.get('chapter_summary', 'No chapter context')

        clean_content = doc.page_content.replace('\n', ' ').strip()
        grouped_docs[vid][chapter].append(clean_content)

    serialized_parts = []
    for vid, chapters in grouped_docs.items():
        serialized_parts.append(f"### Video ID: {vid}")
        for chapter_summary, chunks in chapters.items():
            serialized_parts.append(f"**Chapter Context:** {chapter_summary} \n Here are some transcripts with timestamps:")
            for chunk in chunks:
                serialized_parts.append(f"- {chunk}")
        serialized_parts.append("---")

    serialized = "\n".join(serialized_parts)
    
    return serialized, retrieved_docs


agent = create_agent(
    model=llm,
    tools=[retrieve_context],
    middleware=[inject_video_summaries],
    state_schema=YTAgentState,
    # debug=True
)
