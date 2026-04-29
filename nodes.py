import os
import json
from state import GraphState
from schemas import GradeResult, SearchQuery
from langchain_groq import ChatGroq
from tavily import TavilyClient
from tools import search_arxiv

from dotenv import load_dotenv
load_dotenv()


llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

def rewrite_query_for_arxiv(state: GraphState):
    print("---NODE: REWRITING QUERY FOR ARXIV---")
    question = state["question"]
    chat_history = state.get("chat_history", [])
    
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    
    prompt = f"""You are an expert at arXiv search syntax and conversational context.
    Given the chat history and the latest user question, rewrite the question into a 
    standalone, concise, keyword-based search query. Focus on technical terms.
    If the question uses pronouns like "it" or "they", resolve them using the chat history.
    
    Chat History:
    {history_text}
    
    Latest User Question: {question}
    
    Respond strictly with the optimized search query."""

    query_llm = llm.with_structured_output(SearchQuery)
    response = query_llm.invoke(prompt)
    new_query = response.query.strip()
    
    print(f"---UPDATED QUERY: {new_query}---")
    return {"question": new_query}


def retrieve(state: GraphState):
    question = state["question"]
    documents = search_arxiv(question)
    return {"documents": [documents]}


def grade_documents(state: GraphState):
    print("---NODE: GRADING DOCUMENTS (STRICT)---")
    question = state["question"]
    docs = state["documents"]
    
    # We increment iteration here to keep track of how many times we've graded
    iteration = state.get("iteration", 0) + 1
    
    prompt = f"""You are a strict grader evaluating if a document is RELEVANT to a query.
    
    User Query: {question}
    Document: {docs}
    
    STRICT RULES:
    1. If the document is about the general topic but DOES NOT address the specific 
       concept (e.g., '{question}'), grade it as 'no'.
    2. If you are unsure, grade it as 'no'. 
    3. We prefer a 'no' (triggering web search) over a 'yes' with bad data.
    """

    # Structured Output enforces the Phase 1 schema (GradeResult) on the LLM
    grader_llm = llm.with_structured_output(GradeResult)
    response = grader_llm.invoke(prompt)
    
    print(f"---GRADE: {response.score.upper()} (Rationale: {response.rationale})---")
    
    if response.score == "yes":
        return {"web_search": False, "iteration": iteration}
    else:
        return {"web_search": True, "iteration": iteration}


tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def web_search(state: GraphState):
    """
    Why this node?
    If the Grader said 'No' (web_search=True), this node triggers. 
    It searches the live internet to fill the knowledge gap.
    """
    print("---NODE: PERFORMING WEB SEARCH---")
    question = state["question"]
    
    # We search the web for the answer
    search_result = tavily.search(query=question, search_depth="advanced")
    
    # We extract just the content snippets from the search
    search_content = "\n".join([r["content"] for r in search_result["results"]])
    
    # We update the 'documents' in our state with this new web data
    return {"documents": [search_content]}

def generate(state: GraphState):
    """
    Why this node?
    This is the final step. It takes the validated context and 
    the question to produce the final answer.
    """
    print("---NODE: GENERATING FINAL ANSWER---")
    question = state["question"]
    documents = state["documents"]
    
    # The Prompt: We tell the LLM to be a technical expert
    prompt = f"""You are a technical research assistant. 
    Use the following retrieved context to answer the user's question.
    If you don't know the answer based on the context, say you don't know.
    
    Question: {question}
    Context: {documents}
    
    Answer:"""

    response = llm.invoke(prompt)
    
    return {"generation": response.content}