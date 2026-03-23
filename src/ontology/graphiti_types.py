"""
OANP Graphiti Prescribed Ontology — Pydantic models for the negotiation knowledge graph.

These models define the entity and edge types that Graphiti uses to structure
the negotiation knowledge graph using Graphiti prescribed types.
but purpose-built for negotiation domains.

Usage with Graphiti:
    entity_types = NEGOTIATION_ENTITY_TYPES
    edge_types = NEGOTIATION_EDGE_TYPES
    edge_type_map = NEGOTIATION_EDGE_TYPE_MAP

    await graphiti.add_episode(
        name="Negotiation Round 3",
        episode_body="Candidate proposed $155k base with accelerated vesting...",
        entity_types=entity_types,
        edge_types=edge_types,
        edge_type_map=edge_type_map,
    )
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Entity Types (Graphiti Nodes)
# ---------------------------------------------------------------------------

class NegotiationParty(BaseModel):
    """A party in the negotiation — individual, organization, or representative."""
    role: Optional[str] = Field(None, description="Role in negotiation (buyer, seller, etc.)")
    party_type: Optional[str] = Field(None, description="Type: individual, organization, agent")


class NegotiationIssue(BaseModel):
    """A negotiable dimension — something the parties are bargaining over."""
    issue_type: Optional[str] = Field(None, description="monetary, categorical, temporal")
    is_divisible: Optional[bool] = Field(None, description="Whether the issue can be split")
    current_range: Optional[str] = Field(None, description="Current negotiation range or options")


class PartyInterest(BaseModel):
    """An underlying interest — the WHY behind a party's position."""
    interest_type: Optional[str] = Field(None, description="need, desire, fear, concern")
    priority: Optional[float] = Field(None, description="Priority weight 0.0-1.0")
    is_disclosed: Optional[bool] = Field(None, description="Whether shared with other parties")


class NegotiationCriterion(BaseModel):
    """An objective criterion for evaluating fairness — market rate, precedent, etc."""
    criterion_source: Optional[str] = Field(None, description="market_data, precedent, regulation")
    reference_value: Optional[str] = Field(None, description="The reference standard")


class ProposedPackage(BaseModel):
    """A proposed deal — a bundle of values across issues."""
    proposal_round: Optional[int] = Field(None, description="Round when proposed")
    pareto_rank: Optional[float] = Field(None, description="Pareto efficiency score")
    status: Optional[str] = Field(None, description="proposed, accepted, rejected, countered")


class NegotiationArgument(BaseModel):
    """An argument made during bargaining — claim + evidence."""
    argument_type: Optional[str] = Field(None, description="justify, refute, appeal_to_criterion")
    strength: Optional[float] = Field(None, description="Estimated argument strength 0-1")


# ---------------------------------------------------------------------------
# Edge Types (Graphiti Relationships)
# ---------------------------------------------------------------------------

class HasInterest(BaseModel):
    """A party has an underlying interest."""
    disclosed_at: Optional[datetime] = Field(None, description="When the interest was disclosed")
    disclosure_round: Optional[int] = Field(None, description="Round of disclosure")


class RelatesTo(BaseModel):
    """An interest relates to a negotiable issue."""
    relationship_strength: Optional[float] = Field(None, description="How strongly related 0-1")


class Satisfies(BaseModel):
    """A proposed package satisfies an interest."""
    satisfaction_degree: Optional[float] = Field(None, description="Degree of satisfaction 0-1")


class Undermines(BaseModel):
    """A proposed package undermines an interest."""
    severity: Optional[float] = Field(None, description="How badly undermined 0-1")


class ProposedBy(BaseModel):
    """A package was proposed by a party."""
    proposed_at: Optional[datetime] = Field(None, description="When proposed")


class RespondsTo(BaseModel):
    """A move or argument responds to a previous move."""
    response_type: Optional[str] = Field(None, description="counter, accept, reject, argue")


class ConflictsWith(BaseModel):
    """Two interests are in conflict."""
    conflict_type: Optional[str] = Field(None, description="direct, resource, temporal")


class TradesOffWith(BaseModel):
    """Two issues can be traded off — concession on one for gain on another."""
    trade_off_potential: Optional[float] = Field(None, description="Estimated value 0-1")


class AppliesToIssue(BaseModel):
    """An objective criterion applies to an issue."""
    relevance: Optional[float] = Field(None, description="How relevant 0-1")


# ---------------------------------------------------------------------------
# Type Registries — pass these to Graphiti
# ---------------------------------------------------------------------------

NEGOTIATION_ENTITY_TYPES = {
    "NegotiationParty": NegotiationParty,
    "NegotiationIssue": NegotiationIssue,
    "PartyInterest": PartyInterest,
    "NegotiationCriterion": NegotiationCriterion,
    "ProposedPackage": ProposedPackage,
    "NegotiationArgument": NegotiationArgument,
}

NEGOTIATION_EDGE_TYPES = {
    "HasInterest": HasInterest,
    "RelatesTo": RelatesTo,
    "Satisfies": Satisfies,
    "Undermines": Undermines,
    "ProposedBy": ProposedBy,
    "RespondsTo": RespondsTo,
    "ConflictsWith": ConflictsWith,
    "TradesOffWith": TradesOffWith,
    "AppliesToIssue": AppliesToIssue,
}

NEGOTIATION_EDGE_TYPE_MAP = {
    ("NegotiationParty", "PartyInterest"): ["HasInterest"],
    ("PartyInterest", "NegotiationIssue"): ["RelatesTo"],
    ("ProposedPackage", "PartyInterest"): ["Satisfies", "Undermines"],
    ("ProposedPackage", "NegotiationParty"): ["ProposedBy"],
    ("NegotiationArgument", "ProposedPackage"): ["RespondsTo"],
    ("NegotiationArgument", "NegotiationArgument"): ["RespondsTo"],
    ("PartyInterest", "PartyInterest"): ["ConflictsWith"],
    ("NegotiationIssue", "NegotiationIssue"): ["TradesOffWith"],
    ("NegotiationCriterion", "NegotiationIssue"): ["AppliesToIssue"],
}
