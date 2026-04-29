from typing import List, Dict, TypedDict, Optional


class GraphState(TypedDict):
    question: str
    chat_history: List[Dict[str, str]]
    documents: List[str]
    retrieved_context: List[str]
    intent: str
    web_search: bool
    generation: str
    iteration: int
