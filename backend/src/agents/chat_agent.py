from dataclasses import dataclass
from typing import List
from langchain.tools import tool
from langchain.agents import create_agent
from src.common.services import vector_store, llm
from langchain.tools import tool, ToolRuntime

@dataclass
class ContextSchema:
    video_ids: List[str]

@tool(response_format="content_and_artifact")
def retrieve_context(query: str, runtime: ToolRuntime[ContextSchema]):
    """Retrieve information to help answer a query."""

    video_ids = runtime.context.video_ids

    retrieved_docs = vector_store.similarity_search(
        query,
        k=5,
        filter={
            "video_id": {"$in": video_ids}
        } # type: ignore
    )

    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


tools = [retrieve_context]

agent = create_agent(llm, tools)

