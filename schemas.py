from pydantic import BaseModel, Field
from typing import Literal, List


class IntentClassification(BaseModel):
    intent: Literal["research", "synthesis"] = Field(
        description="'research' if the user is asking for new information, papers, or facts. 'synthesis' if they are asking to summarize, translate, or discuss information already in the conversation."
    )
    reasoning: str = Field(
        description="One sentence explaining why this intent was chosen."
    )


class SearchQuery(BaseModel):
    query: str = Field(
        description="The highly optimized, technical keyword-based search query for arXiv."
    )


class DocumentVerdict(BaseModel):
    doc_index: int = Field(
        description="The zero-based index of the document being graded, matching the [index] prefix in the prompt."
    )
    score: Literal["yes", "no"] = Field(
        description="'yes' if this document is relevant to the query, 'no' otherwise."
    )


class BatchGradeResult(BaseModel):
    verdicts: List[DocumentVerdict] = Field(
        description="A verdict for every document provided. Must contain one entry per document index."
    )


class TopicClassification(BaseModel):
    topic_label: str = Field(
        description="A concise topic label of 4 words or fewer in title case. Must exactly match an existing label if the paper fits one, or be a new specific label if none match."
    )
    is_new_label: bool = Field(
        description="True if this is a brand new topic label, False if it matches an existing one."
    )
