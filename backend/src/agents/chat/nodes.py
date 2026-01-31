from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from src.agents.chat.state import RAGState
from src.common.services import chroma_client, embeddings, llm

def retrieve_context(state: RAGState, config: RunnableConfig) -> dict:
    """Retrieve relevant context from ChromaDB based on the user's latest message."""
    messages = state['messages']
    if not messages:
        return {"context": []}
        
    last_message = messages[-1]
    query = last_message.content
    
    video_id = config.get("configurable", {}).get("video_id")
    if not video_id:
        return {"context": []}

    try:
        try:
            collection = chroma_client.get_collection(name=f"video_{video_id}")
        except ValueError:
            # Collection does not exist
            return {"context": []}
        
        query_embedding = embeddings.embed_query(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5
        )
        
        docs = results.get("documents", [])
        if docs:
            retrieved_context = docs[0]
        else:
            retrieved_context = []
            
        return {"context": retrieved_context}
        
    except Exception as e:
        print(f"Error retrieving context: {e}")
        return {"context": []}

def generate_response(state: RAGState) -> dict:
    """Generate a response using the retrieved context."""
    messages = state['messages']
    context = state.get('context', [])
    
    context_str = "\n\n".join(context)
    
    system_prompt = f"""You are a helpful educational assistant. 
    Answer the user's question based on the following context derived from a video transcript.
    If the answer is not in the context, say you don't know based on the video.
    
    Context:
    {context_str}
    """
    
    # Prepend system message to history
    prompt_messages = [SystemMessage(content=system_prompt)] + messages
    
    response = llm.invoke(prompt_messages)
    
    return {"messages": [response]}
