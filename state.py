from typing import List, Dict, TypedDict

class GraphState(TypedDict):
    """The state dictionary for our CRAG Agent."""
    question: str
    chat_history: List[Dict[str, str]]  
    documents: List[str]
    web_search: bool
    generation: str
    iteration: int 
    