import os
from state import GraphState
from schemas import IntentClassification, SearchQuery, BatchGradeResult
from langchain_groq import ChatGroq
from tavily import TavilyClient
from tools import search_arxiv
import chromadb

from dotenv import load_dotenv
load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

chroma_client = chromadb.PersistentClient(path="./chroma_db")
arxiv_collection = chroma_client.get_or_create_collection(name="arxiv_research")
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


def classify_intent(state: GraphState):
    print("---NODE: CLASSIFYING INTENT---")
    question = state["question"]
    chat_history = state.get("chat_history", [])

    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history])

    prompt = f"""You are an intent classifier for a research assistant.

Chat History:
{history_text}

Latest User Message: {question}

Classify the intent:
- "synthesis": the user wants to summarize, rephrase, translate, or discuss information already present in the chat history above.
- "research": the user is asking for new facts, papers, data, or any topic not already covered in the chat history.

Be strict. Only choose "synthesis" if the answer can be fully derived from the chat history without any new retrieval."""

    intent_llm = llm.with_structured_output(IntentClassification)
    response = intent_llm.invoke(prompt)

    print(f"---INTENT: {response.intent.upper()} | {response.reasoning}---")
    return {"intent": response.intent}


def rewrite_query(state: GraphState):
    print("---NODE: REWRITING QUERY FOR ARXIV---")
    question = state["question"]
    chat_history = state.get("chat_history", [])

    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history])

    prompt = f"""You are an expert at arXiv search syntax.
Rewrite the user's question into a concise, keyword-based technical search query optimized for arXiv.
Resolve any pronouns using the chat history.

Chat History:
{history_text}

User Question: {question}

Return only the optimized search query string."""

    query_llm = llm.with_structured_output(SearchQuery)
    response = query_llm.invoke(prompt)
    new_query = response.query.strip()

    print(f"---REWRITTEN QUERY: {new_query}---")
    return {"question": new_query}


def retrieve(state: GraphState):
    print("---NODE: HYBRID RETRIEVAL (CHROMADB + ARXIV)---")
    question = state["question"]

    local_results = arxiv_collection.query(
        query_texts=[question],
        n_results=5
    )

    valid_cached_docs = []
    if local_results["distances"] and len(local_results["distances"]) > 0:
        for doc_str, dist in zip(local_results["documents"][0], local_results["distances"][0]):
            if dist < 1.3:
                valid_cached_docs.append(doc_str)

    if valid_cached_docs:
        print("---CACHE HIT: RETRIEVED FROM LOCAL CHROMADB---")
        return {"documents": valid_cached_docs}

    print("---CACHE MISS: DOWNLOADING FROM LIVE ARXIV API---")
    new_papers = search_arxiv(question)

    if not new_papers:
        return {"documents": ["No arXiv results found."]}

    paper_ids = [p["id"] for p in new_papers]
    paper_texts = [p["content"] for p in new_papers]

    try:
        arxiv_collection.upsert(documents=paper_texts, ids=paper_ids)
        print(f"---INDEXED: Saved {len(new_papers)} new papers to ChromaDB---")
    except Exception as e:
        print(f"Failed to save to cache: {e}")

    return {"documents": paper_texts}


def grade_documents(state: GraphState):
    print("---NODE: BATCH GRADING DOCUMENTS---")
    question = state["question"]
    docs = state["documents"]
    iteration = state.get("iteration", 0) + 1

    numbered = "\n\n".join([f"[{i}]: {doc}" for i, doc in enumerate(docs)])

    prompt = f"""You are a strict relevance grader for a research assistant.

User Query: {question}

Documents:
{numbered}

For each document index above, return a verdict:
- "yes" if the document directly addresses the core topic of the query.
- "no" if it is off-topic or fails to discuss the central concept.

Return one verdict per document index. Do not skip any index."""

    grader_llm = llm.with_structured_output(BatchGradeResult)
    batch = grader_llm.invoke(prompt)

    relevant_docs = [
        docs[v.doc_index]
        for v in batch.verdicts
        if v.score == "yes" and v.doc_index < len(docs)
    ]

    yes_count = len(relevant_docs)
    print(f"---GRADE: {yes_count}/{len(docs)} documents relevant---")

    if relevant_docs:
        return {"web_search": False, "retrieved_context": relevant_docs, "iteration": iteration}
    else:
        return {"web_search": True, "retrieved_context": [], "iteration": iteration}


def web_search(state: GraphState):
    print("---NODE: PERFORMING WEB SEARCH---")
    question = state["question"]

    search_result = tavily.search(query=question, search_depth="advanced")
    search_content = [r["content"] for r in search_result["results"]]

    return {"documents": search_content, "retrieved_context": search_content}


def generate(state: GraphState):
    print("---NODE: GENERATING FINAL ANSWER---")
    question = state["question"]
    chat_history = state.get("chat_history", [])
    intent = state.get("intent", "research")

    retrieved_context = state.get("retrieved_context") or []
    documents = state.get("documents", [])
    context = retrieved_context if retrieved_context else documents

    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history])
    context_text = "\n\n---\n\n".join(context) if context else "No external context retrieved."

    prompt = f"""You are a highly analytical technical research assistant.
Synthesize the context and chat history to directly answer the user's question.

Rules:
1. For synthesis queries, rely on the chat history as primary source.
2. For research queries, extract key findings, methodologies, and conclusions from the context.
3. Cite sources inline using titles and URLs where available.
4. Be direct. If you don't know, say so.

Previous Chat History:
{history_text}

Intent: {intent}

Retrieved Context:
{context_text}

Question: {question}

Response:"""

    response = llm.invoke(prompt)
    return {"generation": response.content}