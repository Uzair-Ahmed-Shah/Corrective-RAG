from langgraph.graph import StateGraph, END
from state import GraphState
from nodes import classify_intent, rewrite_query, retrieve, grade_documents, web_search, generate

workflow = StateGraph(GraphState)

workflow.add_node("classify_intent", classify_intent)
workflow.add_node("rewrite_query", rewrite_query)
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("web_search", web_search)
workflow.add_node("generate", generate)


def route_after_intent(state: GraphState):
    if state.get("intent") == "synthesis":
        return "generate"
    return "rewrite_query"


def route_after_grading(state: GraphState):
    iteration = state.get("iteration", 0)
    if state.get("web_search") and iteration < 2:
        return "web_search"
    return "generate"


workflow.set_entry_point("classify_intent")

workflow.add_conditional_edges(
    "classify_intent",
    route_after_intent,
    {
        "generate": "generate",
        "rewrite_query": "rewrite_query",
    },
)

workflow.add_edge("rewrite_query", "retrieve")
workflow.add_edge("retrieve", "grade_documents")

workflow.add_conditional_edges(
    "grade_documents",
    route_after_grading,
    {
        "web_search": "web_search",
        "generate": "generate",
    },
)

workflow.add_edge("web_search", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()