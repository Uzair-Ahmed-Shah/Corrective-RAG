import os
import re
from typing import Dict, List
from langchain_groq import ChatGroq
from schemas import TopicClassification
from supabase import Client
from dotenv import load_dotenv

load_dotenv()

topic_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)


def parse_papers_from_context(context: List[str]) -> List[dict]:
    papers = []
    for doc in context:
        paper = {}
        for line in doc.strip().split("\n"):
            if line.startswith("Title: "):
                paper["title"] = line[7:].strip()
            elif line.startswith("Published: "):
                paper["published_date"] = line[11:].strip()
            elif line.startswith("URL: "):
                paper["url"] = line[5:].strip()
            elif line.startswith("Summary: "):
                paper["summary"] = line[9:].strip()
        if "title" in paper and "url" in paper:
            papers.append(paper)
    return papers


def get_existing_labels(supabase: Client, user_id: str) -> List[str]:
    response = (
        supabase.table("saved_resources")
        .select("topic_label")
        .eq("user_id", user_id)
        .execute()
    )
    return list({row["topic_label"] for row in response.data})


def classify_topic(title: str, summary: str, existing_labels: List[str]) -> str:
    labels_text = ", ".join(existing_labels) if existing_labels else "None yet"
    prompt = f"""You are a research librarian organizing academic papers into topic workspaces.

Existing topic labels for this user: {labels_text}

New paper to classify:
Title: {title}
Summary: {summary[:600]}

Rules:
1. If the paper fits well under an existing label, return that EXACT label string.
2. If no existing label fits, create a new one: 4 words or fewer, title case, specific.
3. Never create a label that is a rephrasing of an existing one."""

    classifier = topic_llm.with_structured_output(TopicClassification)
    result = classifier.invoke(prompt)
    return result.topic_label


def save_article(supabase: Client, user_id: str, article: dict, topic_label: str) -> bool:
    try:
        supabase.table("saved_resources").upsert(
            {
                "user_id": user_id,
                "article_id": article["url"],
                "topic_label": topic_label,
                "title": article["title"],
                "url": article["url"],
                "summary": article.get("summary", ""),
                "published_date": article.get("published_date", ""),
            },
            on_conflict="user_id,article_id",
        ).execute()
        return True
    except Exception as e:
        print(f"Save error: {e}")
        return False


def load_library(supabase: Client, user_id: str) -> Dict[str, List[dict]]:
    response = (
        supabase.table("saved_resources")
        .select("*")
        .eq("user_id", user_id)
        .order("saved_at", desc=True)
        .execute()
    )
    grouped: Dict[str, List[dict]] = {}
    for row in response.data:
        label = row["topic_label"]
        grouped.setdefault(label, []).append(row)
    return grouped


def delete_article(supabase: Client, user_id: str, article_id: str):
    supabase.table("saved_resources").delete().eq("user_id", user_id).eq(
        "article_id", article_id
    ).execute()
