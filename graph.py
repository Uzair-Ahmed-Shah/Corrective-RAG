from langgraph.graph import StateGraph, END
from state import GraphState
from nodes import retrieve, grade_documents, web_search, generate, rewrite_query_for_arxiv

workflow = StateGraph(GraphState)


workflow.add_node("rewrite_query", rewrite_query_for_arxiv)
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("web_search", web_search)
workflow.add_node("generate", generate)

workflow.set_entry_point("rewrite_query")
workflow.add_edge("rewrite_query", "retrieve")
workflow.add_edge("retrieve", "grade_documents")

def decide_to_generate(state):
    iteration = state.get("iteration", 0)
    
    if state.get("web_search") and iteration < 2:
        return "web_search"
    else:
        return "generate"


workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "web_search": "web_search",
        "generate": "generate"
    }
)


workflow.add_edge("web_search", "generate")


workflow.add_edge("generate", END)

app = workflow.compile()