from langgraph.graph import StateGraph, START, END
from src.agents.chat.state import RAGState
from src.agents.chat.nodes import retrieve_context, generate_response

workflow = StateGraph(RAGState)

workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("generate_response", generate_response)

workflow.add_edge(START, "retrieve_context")
workflow.add_edge("retrieve_context", "generate_response")
workflow.add_edge("generate_response", END)

# graph = workflow.compile()
