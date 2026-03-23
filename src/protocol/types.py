"""
OANP Protocol Types — the formal type system for the negotiation protocol.

These types define the shared language of OANP. They are used by agents, the mediator,
the simulation engine, and the frontend. This is the single source of truth.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NegotiationPhase(str, Enum):
    SETUP = "setup"
    ALIGNMENT = "alignment"
    DISCOVERY = "discovery"
    GENERATION = "generation"
    BARGAINING = "bargaining"
    CONVERGENCE = "convergence"
    SETTLEMENT = "settlement"
    IMPASSE = "impasse"
    ARBITRATION = "arbitration"


class MoveType(str, Enum):
    PROPOSE = "propose"
    COUNTER = "counter"
    ARGUE = "argue"
    DISCLOSE_INTEREST = "disclose_interest"
    INVOKE_CRITERION = "invoke_criterion"
    MESO = "meso"
    ACCEPT = "accept"
    REJECT = "reject"
    INVOKE_BATNA = "invoke_batna"
    REQUEST_MEDIATION = "request_mediation"


class InterestType(str, Enum):
    NEED = "need"
    DESIRE = "desire"
    FEAR = "fear"
    CONCERN = "concern"


class Architecture(str, Enum):
    BILATERAL = "bilateral"
    MEDIATED = "mediated"
    MULTI_PARTY = "multi_party"


class MediatorMode(str, Enum):
    """How the mediator operates — from pure facilitation to adjudication."""
    FACILITATIVE = "facilitative"    # Process only — reframes, generates options, never evaluates
    EVALUATIVE = "evaluative"        # Gives opinions on likely outcomes, references criteria
    ARBITRATIVE = "arbitrative"      # Decides the outcome when parties can't agree


class MediatorKnowledge(str, Enum):
    """What the mediator knows — its epistemic position."""
    BLIND = "blind"                  # Sees only shared state (move history, issues, criteria)
    CAUCUS_ONLY = "caucus_only"      # Sees what parties voluntarily disclose in private sessions
    OMNISCIENT = "omniscient"        # Sees all private state (for simulation/research only)


class MediatorIntervention(str, Enum):
    """When the mediator intervenes."""
    EVERY_ROUND = "every_round"      # After every round of party moves
    ON_REQUEST = "on_request"        # Only when a party requests mediation
    AT_IMPASSE = "at_impasse"        # Only when negotiation stalls or nears impasse


# ---------------------------------------------------------------------------
# Shared Domain Entities
# ---------------------------------------------------------------------------

class Issue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str = ""
    issue_type: str = "categorical"  # monetary, categorical, temporal
    options: list[str] = []
    range: Optional[list[float | str]] = None  # for divisible issues [min, max] or dates
    is_divisible: bool = False


class Constraint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    source: str = "practical"  # legal, regulatory, practical, temporal
    applies_to: list[str] = []  # issue IDs
    is_hard: bool = True


class ObjectiveCriterion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str = ""
    source: str = "market_data"  # market_data, precedent, regulation, expert_opinion
    applies_to: list[str] = []
    reference_value: Optional[str] = None


# ---------------------------------------------------------------------------
# Proposals and Arguments
# ---------------------------------------------------------------------------

class OptionPackage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    issue_values: dict[str, str]  # issue_id -> proposed value
    rationale: Optional[str] = None
    pareto_rank: Optional[float] = None


class Argument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    claim: str
    grounds: list[str] = []
    criterion_id: Optional[str] = None
    backing: Optional[str] = None
    targets: list[str] = []  # move IDs this argues for/against


# ---------------------------------------------------------------------------
# Moves — the atomic unit of the protocol
# ---------------------------------------------------------------------------

class Move(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    party_id: str
    move_type: MoveType
    package: Optional[OptionPackage] = None
    argument: Optional[Argument] = None
    disclosed_interest: Optional["Interest"] = None
    references: list[str] = []  # IDs of moves this responds to
    reasoning: Optional[str] = None  # Agent's private reasoning (not shown to other parties)
    phase: Optional[str] = None  # Phase when this move was made
    round: int = 0  # Round within the negotiation
    turn: int = 0  # Turn within the round


# ---------------------------------------------------------------------------
# Private State — per party
# ---------------------------------------------------------------------------

class SatisfactionAnchor(BaseModel):
    """A concrete reference point mapping a deal condition to a satisfaction score.

    Generated by LLM at scenario setup, visible in the UI, and editable by users.
    These ground the utility scorer — instead of scoring from vibes, the LLM
    interpolates between human-inspectable anchors.
    """
    condition: str  # e.g. "base_salary >= 160000 AND equity = performance_based"
    score: float  # 0.0 - 1.0
    reason: str  # why this condition maps to this score


class Interest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    interest_type: InterestType
    priority: float = 0.5  # 0.0 - 1.0
    related_issues: list[str] = []
    disclosed: bool = False
    satisfaction_anchors: list[SatisfactionAnchor] = []  # LLM-generated, user-editable


class BATNA(BaseModel):
    description: str
    utility: float
    confidence: float = 0.5
    components: dict[str, str | int | float] = {}  # issue_id -> BATNA value


class BeliefModel(BaseModel):
    target_party_id: str
    estimated_interests: list[dict] = []
    estimated_batna_utility: Optional[float] = None
    estimated_priorities: dict[str, float] = {}
    confidence: float = 0.3
    evidence: list[str] = []


class StrategyState(BaseModel):
    aspiration_level: float = 0.8
    concession_rate: float = 0.0
    cooperation_level: float = 0.7  # warmth — validated by MIT competition
    disclosure_policy: str = "gradual"  # none, gradual, reciprocal, full
    current_tactic: str = "explore"
    reservation_value: float = 0.0  # derived from BATNA


class LeverageEdge(BaseModel):
    source_party_id: str
    target_party_id: str
    leverage_type: str  # informational, positional, temporal, relational
    description: str
    strength: float = 0.5
    related_issues: list[str] = []


class PrivatePartyState(BaseModel):
    party_id: str
    interests: list[Interest] = []
    batna: Optional[BATNA] = None
    belief_models: dict[str, BeliefModel] = {}
    strategy: StrategyState = Field(default_factory=StrategyState)
    leverage: list[LeverageEdge] = []
    disclosed_interests: list[str] = []  # interest IDs shared so far


# ---------------------------------------------------------------------------
# Protocol State
# ---------------------------------------------------------------------------

class ProtocolState(BaseModel):
    phase: NegotiationPhase = NegotiationPhase.SETUP
    round: int = 0               # rounds within current phase
    total_rounds: int = 0        # rounds across all phases
    turn: int = 0                # turn within current round
    total_moves: int = 0         # all moves ever made
    max_rounds: Optional[int] = None  # max total_rounds before impasse
    deadline: Optional[datetime] = None
    architecture: Architecture = Architecture.MEDIATED
    active_party: Optional[str] = None
    phase_history: list[dict] = []
    accepted_by: set[str] = set()        # party IDs that have accepted
    accepted_package_id: Optional[str] = None  # which package they accepted
    accepted_package_hash: Optional[str] = None  # hash of accepted issue_values for consistency


# ---------------------------------------------------------------------------
# Mediator State
# ---------------------------------------------------------------------------

class MediatorConfig(BaseModel):
    """Configurable mediator architecture — the key research parameter."""
    mode: MediatorMode = MediatorMode.FACILITATIVE
    knowledge: MediatorKnowledge = MediatorKnowledge.CAUCUS_ONLY
    intervention: MediatorIntervention = MediatorIntervention.EVERY_ROUND
    evaluates_fairness: bool = False  # Does it comment on outcome balance?


class MediatorState(BaseModel):
    config: MediatorConfig = Field(default_factory=MediatorConfig)
    disclosed_interests_registry: dict[str, list[str]] = {}
    detected_overlaps: list[dict] = []
    pareto_frontier: list[OptionPackage] = []
    suggested_packages: list[OptionPackage] = []
    zopa_estimate: Optional[dict] = None
    caucus_notes: dict[str, list[str]] = {}  # party_id -> private session notes


# ---------------------------------------------------------------------------
# Party
# ---------------------------------------------------------------------------

class Party(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    role: str
    agent_model: Optional[str] = None
    is_human: bool = False


# ---------------------------------------------------------------------------
# Top-Level Negotiation State
# ---------------------------------------------------------------------------

class NegotiationState(BaseModel):
    """The single source of truth — LangGraph state object."""

    id: str = Field(default_factory=lambda: f"neg_{uuid.uuid4().hex[:12]}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Parties
    parties: list[Party] = []

    # Shared state
    issues: list[Issue] = []
    constraints: list[Constraint] = []
    criteria: list[ObjectiveCriterion] = []
    protocol: ProtocolState = Field(default_factory=ProtocolState)
    move_history: list[Move] = []

    # Private state (scoped per party)
    private_states: dict[str, PrivatePartyState] = {}

    # Mediator state
    mediator: Optional[MediatorState] = None

    # Outcome
    agreement: Optional[OptionPackage] = None
    outcome: Optional[str] = None  # "agreement", "impasse", "arbitration"
