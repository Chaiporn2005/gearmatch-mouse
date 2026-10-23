from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    budget: float | None = Field(None, ge=0, le=10000)
    max_weight: float | None = Field(None, gt=0, le=1000)
    connection: Literal["wired", "bluetooth", "2.4ghz"] | None = None
    handedness: Literal["left", "right", "ambidextrous"] | None = None
    use_case: Literal["gaming", "office", "travel"] | None = None


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=2, max_length=1500)
    filters: Filters = Field(default_factory=Filters)


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str
    reason: str = Field(min_length=1, max_length=700)
    tradeoff: str = Field(min_length=1, max_length=400)
    citation_ids: list[str] = Field(min_length=1, max_length=4)


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=1000)
    recommendations: list[Recommendation] = Field(max_length=3)
    limitations: list[str] = Field(max_length=5)
    abstain: bool = False
