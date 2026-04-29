import streamlit as st
import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv
from graph import app as graph_app
import auth
import library

load_dotenv()

st.set_page_config(
    page_title="CRAG Research Agent",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .auth-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 3rem 1rem;
    }
    .auth-card {
        background: rgba(17, 25, 40, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 2.5rem 2rem;
        width: 100%;
        max-width: 420px;
        backdrop-filter: blur(12px);
    }
    .auth-logo {
        font-size: 2.8rem;
        text-align: center;
        margin-bottom: 0.25rem;
    }
    .auth-title {
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 0.3rem;
    }
    .auth-subtitle {
        text-align: center;
        font-size: 0.85rem;
        color: #94a3b8;
        margin-bottom: 2rem;
    }
    .user-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 0;
        margin-bottom: 1rem;
    }
    .avatar {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 1rem;
        flex-shrink: 0;
    }
    .paper-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 10px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.6rem;
        transition: border-color 0.2s;
    }
    .paper-card:hover {
        border-color: rgba(99, 102, 241, 0.35);
    }
    .paper-title {
        font-weight: 600;
        font-size: 0.88rem;
        color: #e2e8f0;
        margin-bottom: 0.3rem;
        line-height: 1.4;
    }
    .paper-meta {
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 0.4rem;
    }
    .paper-summary {
        font-size: 0.8rem;
        color: #94a3b8;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .topic-badge {
        display: inline-block;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.35);
        color: #a5b4fc;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.72rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    .section-header {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #475569;
        margin: 1.25rem 0 0.5rem 0;
    }
    .save-success {
        font-size: 0.75rem;
        color: #34d399;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def init_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        st.error("Supabase credentials missing in .env file.")
        st.stop()
    return create_client(url, key)


supabase = init_supabase()


def init_session():
    defaults = {
        "token": None,
        "session_id": None,
        "messages": [],
        "retrieved_context": [],
        "current_papers": [],
        "saved_article_ids": set(),
        "library": {},
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


def show_auth_page():
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown('<div class="auth-logo">🧬</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">CRAG Research Agent</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-subtitle">AI-powered research with arXiv retrieval and intelligent fallbacks</div>',
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
                            st.session_state.token = token
                            user = auth.decode_token(token)
                            st.session_state.session_id = str(user["sub"])
                            st.session_state.messages = load_chat_history(user["sub"])
                            refresh_library(user["sub"])
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")

        with tab_signup:
            with st.form("signup_form"):
                name = st.text_input("Full Name", placeholder="Jane Smith")
                email_s = st.text_input("Email", placeholder="you@example.com", key="signup_email")
                password_s = st.text_input("Password", type="password", placeholder="Min. 8 characters", key="signup_pw")
                submitted_s = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                if submitted_s:
                    if not name or not email_s or not password_s:
                        st.error("Please fill in all fields.")
                    elif len(password_s) < 8:
                        st.error("Password must be at least 8 characters.")
                    else:
                        token = auth.signup(supabase, name, email_s, password_s)
                        if token:
                            st.session_state.token = token
                            user = auth.decode_token(token)
                            st.session_state.session_id = str(user["sub"])
                            st.session_state.messages = []
                            st.session_state.library = {}
                            st.rerun()
                        else:
                            st.error("An account with this email already exists.")


def show_sidebar(user: dict):
    with st.sidebar:
        initial = user["name"][0].upper()
        st.markdown(
            f'<div class="user-header">'
            f'<div class="avatar">{initial}</div>'
            f'<div><div style="font-weight:600;font-size:0.9rem;color:#e2e8f0">{user["name"]}</div>'
            f'<div style="font-size:0.75rem;color:#64748b">{user["email"]}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.button("Sign Out", use_container_width=True):
            for key in ["token", "session_id", "messages", "retrieved_context",
                        "current_papers", "saved_article_ids", "library"]:
                st.session_state[key] = [] if isinstance(st.session_state.get(key), list) else (
                    set() if isinstance(st.session_state.get(key), set) else
                    ({} if isinstance(st.session_state.get(key), dict) else None)
                )
            st.rerun()

        if st.session_state.current_papers:
            st.markdown('<div class="section-header">📌 Current Research</div>', unsafe_allow_html=True)
            for paper in st.session_state.current_papers:
                art_id = paper["url"]
                is_saved = art_id in st.session_state.saved_article_ids
                with st.container():
                    st.markdown(
                        f'<div class="paper-card">'
                        f'<div class="paper-title"><a href="{paper["url"]}" target="_blank" style="color:#e2e8f0;text-decoration:none;">{paper["title"]}</a></div>'
                        f'<div class="paper-meta">{paper.get("published_date", "")}</div>'
                        f'<div class="paper-summary">{paper.get("summary", "")[:200]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if is_saved:
                        st.markdown('<span class="save-success">✓ Saved</span>', unsafe_allow_html=True)
                    else:
                        if st.button("💾 Save", key=f"save_{art_id}", use_container_width=True):
                            with st.spinner("Classifying topic..."):
                                existing_labels = library.get_existing_labels(supabase, user["sub"])
                                topic = library.classify_topic(
                                    paper["title"], paper.get("summary", ""), existing_labels
                                )
                                success = library.save_article(supabase, user["sub"], paper, topic)
                                if success:
                                    st.session_state.saved_article_ids.add(art_id)
                                    refresh_library(user["sub"])
                                    st.rerun()

        st.markdown('<div class="section-header">📚 Research Library</div>', unsafe_allow_html=True)

        lib = st.session_state.library
        if not lib:
            st.markdown(
                '<div style="font-size:0.8rem;color:#475569;padding:0.5rem 0;">Save papers from your research to build your library.</div>',
                unsafe_allow_html=True,
            )
        else:
            for topic_label, articles in lib.items():
                with st.expander(f"{topic_label} ({len(articles)})"):
                    for article in articles:
                        st.markdown(
                            f'<div class="topic-badge">{topic_label}</div>'
                            f'<div class="paper-title"><a href="{article["url"]}" target="_blank" style="color:#e2e8f0;text-decoration:none;">{article["title"]}</a></div>'
                            f'<div class="paper-meta">{article.get("published_date", "")}</div>',
                            unsafe_allow_html=True,
                        )
                        if st.button("🗑️", key=f"del_{article['article_id']}_{article['id']}"):
                            library.delete_article(supabase, user["sub"], article["article_id"])
                            st.session_state.saved_article_ids.discard(article["article_id"])
                            refresh_library(user["sub"])
                            st.rerun()
                        st.markdown("---")


def show_chat(user: dict):
    st.markdown("### 🧬 Corrective Research Agent")
    st.markdown(
        "<span style='color:#64748b;font-size:0.88rem'>Searches **arXiv** for papers. If they aren't relevant, autonomously switches to **Web Search**. Supports $\\LaTeX$ in responses.</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

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
                            icon = "🔬" if intent == "research" else "💬"
                            st.write(f"{icon} Intent detected: **{intent.capitalize()}**")
                        elif key == "rewrite_query":
                            st.write(f"📝 Rewritten query: `{value.get('question')}`")
                        elif key == "retrieve":
                            st.write("🔍 Searching arXiv for relevant papers...")
                        elif key == "grade_documents":
                            ctx = value.get("retrieved_context", [])
                            if value.get("web_search"):
                                st.write("⚠️ No relevant papers found. Triggering web search fallback.")
                            else:
                                st.write(f"✅ {len(ctx)} relevant paper(s) graded and retained.")
                            if ctx:
                                st.session_state.retrieved_context = ctx
                                st.session_state.current_papers = library.parse_papers_from_context(ctx)
                                st.session_state.saved_article_ids = set()
                        elif key == "web_search":
                            st.write("🌐 Executing web search via Tavily...")
                            web_ctx = value.get("retrieved_context", [])
                            if web_ctx:
                                st.session_state.retrieved_context = web_ctx
                                st.session_state.current_papers = library.parse_papers_from_context(web_ctx)
                                st.session_state.saved_article_ids = set()
                        elif key == "generate":
                            st.write("✍️ Synthesizing final answer...")
                            final_response = value.get("generation", "")

                status.update(label="Research Complete!", state="complete", expanded=False)

            st.markdown(final_response)

            if st.session_state.current_papers:
                st.markdown("---")
                st.markdown(
                    "<div style='font-size:0.8rem;font-weight:600;color:#64748b;margin-bottom:0.5rem;'>📌 FOUND RESOURCES</div>",
                    unsafe_allow_html=True,
                )
                for paper in st.session_state.current_papers:
                    art_id = paper["url"]
                    is_saved = art_id in st.session_state.saved_article_ids
                    col_text, col_btn = st.columns([5, 1])
                    with col_text:
                        st.markdown(
                            f'<div style="font-size:0.82rem;font-weight:600;color:#e2e8f0;">'
                            f'<a href="{paper["url"]}" target="_blank" style="color:#a5b4fc;text-decoration:none;">{paper["title"]}</a>'
                            f'</div>'
                            f'<div style="font-size:0.75rem;color:#64748b;">{paper.get("published_date", "")}</div>',
                            unsafe_allow_html=True,
                        )
                    with col_btn:
                        if is_saved:
                            st.button("✓ Saved", key=f"inline_done_{art_id}", disabled=True)
                        else:
                            if st.button("💾 Save", key=f"inline_save_{art_id}"):
                                with st.spinner("Classifying topic..."):
                                    existing_labels = library.get_existing_labels(supabase, user["sub"])
                                    topic = library.classify_topic(
                                        paper["title"], paper.get("summary", ""), existing_labels
                                    )
                                    if library.save_article(supabase, user["sub"], paper, topic):
                                        st.session_state.saved_article_ids.add(art_id)
                                        refresh_library(user["sub"])
                                        st.rerun()

        save_chat_message(st.session_state.session_id, "assistant", final_response)
        st.session_state.messages.append({"role": "assistant", "content": final_response})


def main():
    init_session()

    user = auth.get_current_user(st.session_state)

    if not user:
        show_auth_page()
        return

    if not st.session_state.library:
        refresh_library(user["sub"])

    show_sidebar(user)
    show_chat(user)


main()