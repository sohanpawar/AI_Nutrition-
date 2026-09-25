"""Stable Milestone 1/2 response contract.

`Claim.source` is always null in Milestone 1; Milestone 2 fills citations.
"""

from typing import Literal

from pydantic import BaseModel, Field


DeclineReason = Literal[
    "calorie_or_weight_target",
    "medical_advice",
    "out_of_scope",
]


class Claim(BaseModel):
    text: str = Field(..., min_length=1)
    source: str | None = Field(
        default=None,
        description="Always null in Milestone 1; citation string/URL in Milestone 2",
    )


class AssistantResponse(BaseModel):
    """Structured model output (and refusal) payload without transport IDs."""

    answer: str = Field(..., min_length=1)
    claims: list[Claim] = Field(default_factory=list)
    declined: bool = False
    decline_reason: DeclineReason | None = None
