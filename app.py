import streamlit as st
import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv
from graph import app

load_dotenv()
@st.cache_resource
def init_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        st.error("Supabase credentials missing in .env file.")
        st.stop()
    return create_client(url, key)

if os.environ.get("SUPABASE_URL"):
    supabase = init_supabase()
else:
    supabase = None

def load_chat_history(session_id: str):
    if not supabase: return []
    try:
        response = supabase.table("chat_messages").select("role, content").eq("session_id", session_id).order("created_at").execute()
        return response.data
    except Exception as e:
        st.error(f"Failed to load history: {e}")
        return []

def save_chat_message(session_id: str, role: str, content: str):
    if not supabase: return
    try:
        supabase.table("chat_messages").insert({
            "session_id": session_id,
            "role": role,
            "content": content
        }).execute()
    except Exception as e:
        st.error(f"Failed to save message: {e}")

st.set_page_config(page_title="CRAG Research Agent", page_icon="🧬")

st.title("🧬 Corrective Research Agent (CRAG)")
st.markdown("I search **arXiv** for papers. If they aren't relevant, I'll autonomously switch to **Web Search** to find your answer.")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history(st.session_state.session_id)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a technical question..."):
    save_chat_message(st.session_state.session_id, "user", prompt)
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Agent is thinking...", expanded=True) as status:
            inputs = {
                "question": prompt, 
                "chat_history": st.session_state.messages[:-1], # Exclude the current prompt
                "documents": [], 
                "web_search": False, 
                "generation": "",
                "iteration": 0
            }
            final_response = ""
            
            for output in app.stream(inputs):
                for key, value in output.items():
                    if key == "rewrite_query":
                        st.write("📝 Refining query for arXiv syntax...")
                        st.write(f"> **Rewritten Query:** `{value.get('question')}`")
                    elif key == "retrieve":
                        st.write("🔍 Searching arXiv for relevant papers...")
                    elif key == "grade_documents":
                        st.write("⚖️ Grading document relevance...")
                        if value.get("web_search"):
                            st.write("⚠️ Papers irrelevant. Triggering Web Search fallback.")
                        else:
                            st.write("✅ High-quality papers found.")
                    elif key == "web_search":
                        st.write("🌐 Executing autonomous web search via Tavily...")
                    elif key == "generate":
                        st.write("✍️ Synthesizing final answer...")
                        final_response = value.get("generation")
            
            status.update(label="Research Complete!", state="complete", expanded=False)
        
        st.markdown(final_response)
        
        save_chat_message(st.session_state.session_id, "assistant", final_response)
        st.session_state.messages.append({"role": "assistant", "content": final_response})