from pydantic import BaseModel, Field
from typing import Literal

class GradeResult(BaseModel):
    """Schema for evaluating the relevance of retrieved documents."""
    score: Literal["yes", "no"] = Field(
        description="'yes' if the document is relevant to the general topic AND specific concept, 'no' otherwise."
    )
    rationale: str = Field(
        description="A short explanation of why the document was graded 'yes' or 'no'."
    )

class SearchQuery(BaseModel):
    """Schema for optimizing search queries."""
    query: str = Field(
        description="The highly optimized, technical keyword-based search query for arXiv or Tavily."
    )
