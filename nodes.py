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

    search_result = tavily.search(query=question, search_depth="advanced")

    search_content = "\n".join([r["content"] for r in search_result["results"]])

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

    prompt = f"""You are a highly analytical technical research assistant. 
    Your goal is to synthesize the following retrieved context into a concentrated, noise-free summary that directly answers the user's question.
    
    CRITICAL INSTRUCTIONS:
    1. If the context contains research papers or web results, extract the main findings, methodologies, or conclusions.
    2. Provide a deep, comprehensive answer. Do not just list the titles.
    3. YOU MUST tag/cite your sources inline or at the bottom. Use the provided Titles, URLs, and publication dates.
    4. If there is irrelevant noise in the context, ignore it and focus only on the best information.
    5. If you don't know the answer based on the context, say you don't know.
    
    Question: {question}
    
    Retrieved Context: 
    {documents}
    
    Synthesized Research Response:"""

    response = llm.invoke(prompt)
    
    return {"generation": response.content}