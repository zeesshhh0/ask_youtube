from langgraph.graph import MessagesState


class RAGState(MessagesState):
    """State for the RAG chat workflow.
    
    Inherits from MessagesState which provides the 'messages' key.
    Adds 'context' to store retrieved documents.
    """
    context: list[str]
