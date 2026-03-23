"""
OANP Agent Response Schemas — Pydantic models for structured LLM output.

These schemas are passed to llm.with_structured_output() to guarantee
type-safe responses from the LLM. No more JSON parsing or string coercion.

This is the core fix: instead of asking the LLM to return JSON and hoping
it matches, we use tool calling / json_schema to enforce the schema at the
API level. Both Anthropic and OpenAI support this.
"""

from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class NegotiatorPackage(BaseModel):
    """A proposed deal — values for each issue under negotiation."""
    issue_values: dict[str, str] = Field(
        description="Mapping of issue ID/name to proposed value. "
        "Use the issue IDs from the scenario (e.g., 'base_salary': '155000')."
    )
    rationale: Optional[str] = Field(
        None,
        description="Brief explanation of why this package is fair or beneficial."
    )


class NegotiatorArgument(BaseModel):
    """An argument supporting or opposing a proposal."""
    claim: str = Field(description="The main claim being argued.")
    grounds: list[str] = Field(
        default_factory=list,
        description="Evidence or reasoning supporting the claim. Each item is a plain string."
    )
    criterion_id: Optional[str] = Field(
        None,
        description="ID of the objective criterion being invoked, if any."
    )


class NegotiatorInterestDisclosure(BaseModel):
    """An interest being disclosed to the other party."""
    description: str = Field(description="What the interest is about.")
    interest_type: str = Field(
        description="One of: need, desire, fear, concern."
    )
    priority: float = Field(
        description="How important this interest is, from 0.0 (low) to 1.0 (critical)."
    )
    related_issues: list[str] = Field(
        default_factory=list,
        description="Issue IDs this interest relates to."
    )


class NegotiatorResponse(BaseModel):
    """Complete response from a negotiator agent for one turn."""

    @model_validator(mode="before")
    @classmethod
    def parse_stringified_fields(cls, data):
        """Haiku sometimes returns nested objects as JSON strings. Parse them."""
        if isinstance(data, dict):
            for field in ("package", "argument", "disclosed_interest"):
                val = data.get(field)
                if isinstance(val, str):
                    try:
                        data[field] = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        data[field] = None
        return data

    move_type: str = Field(
        description="The type of move to make. Must be one of the legal moves for the current phase: "
        "propose, counter, argue, disclose_interest, invoke_criterion, meso, accept, reject, invoke_batna."
    )
    package: Optional[NegotiatorPackage] = Field(
        None,
        description="Required for propose, counter, and meso moves. The deal being proposed."
    )
    argument: Optional[NegotiatorArgument] = Field(
        None,
        description="Required for argue and invoke_criterion moves. The argument being made."
    )
    disclosed_interest: Optional[NegotiatorInterestDisclosure] = Field(
        None,
        description="Required for disclose_interest moves. The interest being revealed."
    )
    references: list[str] = Field(
        default_factory=list,
        description="IDs of previous moves this is responding to."
    )
    reasoning: str = Field(
        default="",
        description="Your internal reasoning about why you chose this move. Not shown to other parties."
    )


class MediatorPackage(BaseModel):
    """A package suggested by the mediator."""
    issue_values: dict[str, str] = Field(
        description="Mapping of issue ID/name to proposed value."
    )
    rationale: str = Field(
        default="",
        description="Explanation of why this package balances all parties' interests."
    )


class MediatorResponse(BaseModel):
    """Complete response from the mediator agent."""

    @model_validator(mode="before")
    @classmethod
    def parse_stringified_fields(cls, data):
        if isinstance(data, dict):
            for field in ("package",):
                val = data.get(field)
                if isinstance(val, str):
                    try:
                        data[field] = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        data[field] = None
        return data

    action: str = Field(
        description="What the mediator is doing. One of: "
        "suggest_package, highlight_overlap, reframe, propose_criterion, no_intervention."
    )
    package: Optional[MediatorPackage] = Field(
        None,
        description="A suggested deal package. Required when action is suggest_package."
    )
    analysis: str = Field(
        default="",
        description="The mediator's analysis of the current negotiation state."
    )
    overlap_detected: Optional[str] = Field(
        None,
        description="Description of any interest overlaps detected between parties."
    )
    trade_off_opportunity: Optional[str] = Field(
        None,
        description="Description of any trade-off opportunities identified."
    )
