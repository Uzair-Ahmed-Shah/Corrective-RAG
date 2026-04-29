import streamlit as st
import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv
from graph import app as graph_app
import auth
import library
from streamlit_cookies_controller import CookieController

load_dotenv()

st.set_page_config(
    page_title="CRAG — Research Agent",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Basic Font & Background */
html, body, [class*="css"] { 
    font-family: 'Inter', -apple-system, sans-serif; 
}

/* 
   FIX: Restore the Sidebar Toggle 
   Instead of display:none, we just hide the 'rainbow' line and 3-dot menu 
   without collapsing the header area.
*/
[data-testid="stHeader"] {
    background: transparent;
}
[data-testid="stToolbar"] {
    right: 1.5rem; /* Moves the 3-dot menu slightly so it doesn't overlap */
}
[data-testid="stDecoration"] {
    display: none; /* This is the rainbow bar; usually safe to hide */
}

/* Sidebar Styling */
[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid rgba(255,255,255,0.06);
}

/* Chat Message Styling (The 'Chat Bubbles' you wanted) */
[data-testid="stChatMessage"] { 
    padding: 1rem; 
    border-radius: 12px;
    margin-bottom: 1rem;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
}

/* Button & Input Styling */
.stButton > button {
    border-radius: 7px;
    font-weight: 500;
}

/* Custom Classes for Library Groups */
.section-label {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #475569;
    margin: 1rem 0 0.5rem 0;
}

.paper-row {
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        st.error("Supabase credentials missing in .env file.")
        st.stop()
    return create_client(url, key)


supabase = init_supabase()
controller = CookieController()


def init_session():
    defaults = {
        "token": None,
        "session_id": None,
        "messages": [],
        "retrieved_context": [],
        "current_papers": [],
        "saved_article_ids": set(),
        "library": {},
        "_needs_library_refresh": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def load_chat_history(session_id: str):
    try:
        response = (
            supabase.table("chat_messages")
            .select("role, content")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        return response.data
    except Exception:
        return []


def save_chat_message(session_id: str, role: str, content: str):
    try:
        supabase.table("chat_messages").insert(
            {"session_id": session_id, "role": role, "content": content}
        ).execute()
    except Exception as e:
        print(f"Chat save error: {e}")


def refresh_library(user_id: str):
    st.session_state.library = library.load_library(supabase, user_id)

def handle_save_article(art_id, paper, user_sub):
    existing = library.get_existing_labels(supabase, user_sub)
    topic = library.classify_topic(paper["title"], paper.get("summary", ""), existing)
    if library.save_article(supabase, user_sub, paper, topic):
        st.session_state.saved_article_ids.add(art_id)
        st.session_state._needs_library_refresh = True

def show_auth_page():
    st.markdown("<br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("🧬", unsafe_allow_html=True)
        st.markdown('<div class="auth-title">CRAG Research Agent</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-sub">AI-powered research with arXiv retrieval and intelligent web search fallbacks.</div>',
            unsafe_allow_html=True,
        )

        tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                if submitted:
                    if not email or not password:
                        st.error("Please fill in all fields.")
                    else:
                        token = auth.login(supabase, email, password)
                        if token:
                            controller.set("auth_token", token, max_age=14*24*60*60)
                            user = auth.decode_token(token)
                            st.session_state.token = token
                            st.session_state.session_id = str(user["sub"])
                            st.session_state.messages = load_chat_history(user["sub"])
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")

        with tab_signup:
            with st.form("signup_form"):
                name = st.text_input("Full Name", placeholder="Jane Smith")
                email_s = st.text_input("Email", placeholder="you@example.com", key="s_email")
                password_s = st.text_input("Password", type="password", placeholder="Min. 8 characters", key="s_pw")
                submitted_s = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                if submitted_s:
                    if not name or not email_s or not password_s:
                        st.error("Please fill in all fields.")
                    elif len(password_s) < 8:
                        st.error("Password must be at least 8 characters.")
                    else:
                        token = auth.signup(supabase, name, email_s, password_s)
                        if token:
                            controller.set("auth_token", token, max_age=14*24*60*60)
                            user = auth.decode_token(token)
                            st.session_state.token = token
                            st.session_state.session_id = str(user["sub"])
                            st.session_state.messages = []
                            st.rerun()
                        else:
                            st.error("An account with this email already exists.")


def show_sidebar(user: dict):
    with st.sidebar:
        initial = user["name"][0].upper()
        st.markdown(
            f'<div class="user-block">'
            f'<div class="avatar">{initial}</div>'
            f'<div><div class="user-name">{user["name"]}</div>'
            f'<div class="user-email">{user["email"]}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Chat", use_container_width=True):
                supabase.table("chat_messages").delete().eq("session_id", user["sub"]).execute()
                st.session_state.messages = []
                st.session_state.current_papers = []
                st.session_state.saved_article_ids = set()
                st.session_state.retrieved_context = []
                st.rerun()
        with col2:
            if st.button("Sign Out", use_container_width=True):
                controller.remove("auth_token")
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

        st.markdown('<div class="section-label">Research Library</div>', unsafe_allow_html=True)

        lib = st.session_state.library
        if not lib:
            st.markdown(
                '<div class="empty-state">Save papers from any research response to build your personal library, organised by topic.</div>',
                unsafe_allow_html=True,
            )
        else:
            for topic_label, articles in lib.items():
                with st.expander(f"{topic_label}  ·  {len(articles)}"):
                    for article in articles:
                        st.markdown(
                            f'<div class="paper-row">'
                            f'<div><a class="paper-title-link" href="{article["url"]}" target="_blank">{article["title"]}</a></div>'
                            f'<div class="paper-meta">{article.get("published_date", "")}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if st.button("Remove", key=f"del_{article['id']}"):
                            library.delete_article(supabase, user["sub"], article["article_id"])
                            st.session_state.saved_article_ids.discard(article["article_id"])
                            st.session_state._needs_library_refresh = True
                            st.rerun()


def show_chat(user: dict):
    # 1. Page Header
    st.markdown('<div class="chat-header-title">🧬 Corrective Research Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="chat-header-sub">Retrieves papers from arXiv · Falls back to web search · Saves to your library</div>', unsafe_allow_html=True)
    st.divider()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if st.session_state.get("current_papers"):
        with st.chat_message("assistant"):
            st.markdown('**📚 Extracted Sources:**')
            for paper in st.session_state.current_papers:
                art_id = paper["url"]
                is_saved = art_id in st.session_state.saved_article_ids
                
                col_text, col_btn = st.columns([6, 1])
                with col_text:
                    st.markdown(f'<div class="paper-row"><a class="paper-title-link" href="{paper["url"]}" target="_blank">{paper["title"]}</a></div>', unsafe_allow_html=True)
                with col_btn:
                    if is_saved:
                        st.button("✓ Saved", key=f"perm_v_{art_id}", disabled=True)
                    else:
                        st.button("💾 Save", key=f"perm_save_{art_id}", on_click=handle_save_article, args=(art_id, paper, user["sub"]))

    if prompt := st.chat_input("Ask a research question..."):

        st.session_state.messages.append({"role": "user", "content": prompt})
        save_chat_message(st.session_state.session_id, "user", prompt)
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.status("Thinking...", expanded=True) as status:
                inputs = {
                    "question": prompt,
                    "chat_history": st.session_state.messages[:-1],
                    "documents": [],
                    "retrieved_context": st.session_state.retrieved_context,
                    "intent": "",
                    "web_search": False,
                    "generation": "",
                    "iteration": 0,
                }
                final_response = ""

                for output in graph_app.stream(inputs):
                    for key, value in output.items():
                        if key == "classify_intent":
                            intent = value.get("intent", "")
                            if intent == "research":
                                st.session_state.current_papers = []
                                st.session_state.saved_article_ids = set()
                            icon = "🔬" if intent == "research" else "💬"
                            st.write(f"{icon} Intent: **{intent.capitalize()}**")

                        elif key == "rewrite_query":
                            st.write(f"📝 Query rewritten → `{value.get('question')}`")

                        elif key == "retrieve":
                            st.write("🔍 Searching arXiv...")

                        elif key == "grade_documents":
                            ctx = value.get("retrieved_context", [])
                            if value.get("web_search"):
                                st.write("⚠️ Papers irrelevant — falling back to web search.")
                            else:
                                st.write(f"✅ {len(ctx)} relevant paper(s) retained.")
                            if ctx:
                                st.session_state.retrieved_context = ctx
                                st.session_state.current_papers = library.parse_papers_from_context(ctx)

                        elif key == "web_search":
                            st.write("🌐 Searching the web via Tavily...")
                            ctx = value.get("retrieved_context", [])
                            if ctx:
                                st.session_state.retrieved_context = ctx
                                st.session_state.current_papers = library.parse_papers_from_context(ctx)

                        elif key == "generate":
                            st.write("✍️ Synthesising answer...")
                            final_response = value.get("generation", "")

                status.update(label="Done", state="complete", expanded=False)

            st.markdown(final_response)

            save_chat_message(st.session_state.session_id, "assistant", final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            
            st.rerun()
def main():
    init_session()

    cookie_token = controller.get("auth_token")
    if cookie_token and not st.session_state.token:
        user = auth.decode_token(cookie_token)
        if user:
            st.session_state.token = cookie_token
            st.session_state.session_id = str(user["sub"])
            st.session_state.messages = load_chat_history(user["sub"])
        else:
            controller.remove("auth_token")

    user = auth.get_current_user(st.session_state)
    if not user:
        show_auth_page()
        return

    if st.session_state._needs_library_refresh:
        refresh_library(user["sub"])
        st.session_state._needs_library_refresh = False
    elif not st.session_state.library:
        refresh_library(user["sub"])

    show_sidebar(user)
    show_chat(user)

if __name__ == "__main__":
    main()