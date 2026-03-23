"""
OANP Negotiation Graph — LangGraph StateGraph implementing the protocol.

Architecture rethink (v2): Each protocol phase is a graph node with explicit
Command-based routing. This eliminates the accept-storm bug from the v1
while-loop approach and gives us:
  - Per-round checkpointing in the bargaining critical path
  - Proper human-in-the-loop via interrupt()/Command(resume=)
  - Crash recovery and state replay
  - Clean phase transitions without nested if/elif

Key research-informed design decisions (unchanged from v1):
- Rahwan IBN: discovery phase exists specifically so agents exchange interest
  information before bargaining — this expands achievable deals.
- MIT competition: cooperation_level (warmth) is a tunable strategy parameter
  because the 180K-negotiation study proved it predicts outcomes.
- Shared/private split (OWL-DL literature): agents only see their own private
  state + shared state. The graph enforces this by passing scoped views.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Literal, Optional, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

from ..protocol.types import (
    Architecture,
    MediatorState,
    Move,
    MoveType,
    NegotiationPhase,
    NegotiationState,
    OptionPackage,
)
from .negotiator import run_negotiator, get_legal_moves
from .mediator import run_mediator
from .events import EventBus
from .scorer import LLMUtilityScorer
from .validator import MoveValidator


# ---------------------------------------------------------------------------
# Event callback type — for streaming to WebSocket / CLI
# ---------------------------------------------------------------------------

EventCallback = Optional[Callable[[str, dict], Any]]


# ---------------------------------------------------------------------------
# Graph state — wraps NegotiationState for LangGraph
# ---------------------------------------------------------------------------

class GraphState(TypedDict):
    negotiation: NegotiationState


# ---------------------------------------------------------------------------
# Package hashing — for accept consistency
# ---------------------------------------------------------------------------

def _package_hash(package: OptionPackage) -> str:
    """Deterministic hash of a package's issue values (ignoring UUID/rationale)."""
    canonical = json.dumps(package.issue_values, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Phase transition logic (unchanged from v1)
# ---------------------------------------------------------------------------

def should_transition_from_discovery(state: NegotiationState) -> bool:
    """Discovery → Generation when enough interests disclosed, arguments made, and round minimum met."""
    total_disclosed = sum(
        len(ps.disclosed_interests) for ps in state.private_states.values()
    )
    total_interests = sum(
        len(ps.interests) for ps in state.private_states.values()
    )
    disclosure_rate = total_disclosed / total_interests if total_interests > 0 else 0
    rounds = state.protocol.round
    has_arguments = any(
        m.move_type in (MoveType.ARGUE, MoveType.INVOKE_CRITERION)
        for m in state.move_history
    )

    # Hard cap: exit after 5 rounds regardless
    if rounds >= 5:
        return True

    # Normal: need 50% disclosure + 3 rounds + at least one argument
    if disclosure_rate >= 0.5 and rounds >= 3 and has_arguments:
        return True

    # Fallback: 60% disclosure even without arguments (agents may not argue)
    if disclosure_rate >= 0.6 and rounds >= 3:
        return True

    return False


def should_transition_from_generation(state: NegotiationState) -> bool:
    """Generation → Bargaining when enough proposals exist and options explored."""
    proposals = [
        m for m in state.move_history
        if m.move_type in (MoveType.PROPOSE, MoveType.MESO)
    ]
    # Need at least 3 proposals and 2 rounds in generation
    # (counting rounds since discovery ended)
    gen_moves = [m for m in state.move_history if m.phase == NegotiationPhase.GENERATION.value]
    gen_rounds = len(set(m.round for m in gen_moves)) if gen_moves else 0
    return len(proposals) >= 3 and gen_rounds >= 2


def check_bargaining_outcome(state: NegotiationState) -> str:
    """Returns 'continue', 'settlement', 'converge', or 'impasse'."""
    if not state.move_history:
        return "continue"

    # BATNA invocation → impasse
    if any(m.move_type == MoveType.INVOKE_BATNA for m in state.move_history[-3:]):
        return "impasse"

    # Settlement: all non-mediator parties have accepted the same package
    party_ids = {p.id for p in state.parties}
    if state.protocol.accepted_by >= party_ids:
        return "settlement"

    # Any accept → convergence
    if state.protocol.accepted_by:
        return "converge"

    # Round limit
    if state.protocol.max_rounds and state.protocol.total_rounds >= state.protocol.max_rounds:
        return "impasse"

    return "continue"


# ---------------------------------------------------------------------------
# Moves that immediately halt the round and trigger state transition
# ---------------------------------------------------------------------------

# ACCEPT is intentionally NOT an interrupt move. Both parties must get their
# turn in a round — otherwise Party 0 accepting interrupts the round before
# Party 1 can respond, creating an infinite accept loop.
# Only truly terminal moves (walk-away, mediation request) interrupt.
INTERRUPT_MOVES = {MoveType.INVOKE_BATNA, MoveType.REQUEST_MEDIATION}


# ---------------------------------------------------------------------------
# Core round execution helpers (shared by all phase nodes)
# ---------------------------------------------------------------------------

def _advance_round(neg: NegotiationState):
    """Increment round counters."""
    neg.protocol.round += 1
    neg.protocol.total_rounds += 1


def _enter_phase(neg: NegotiationState, phase: NegotiationPhase):
    """Transition to a new phase, reset phase-local round counter."""
    neg.protocol.phase = phase
    neg.protocol.round = 0
    neg.protocol.phase_history.append({
        "phase": phase.value,
        "total_round": neg.protocol.total_rounds,
        "total_moves": neg.protocol.total_moves,
    })


def _record_move(neg: NegotiationState, move: Move) -> None:
    """Stamp move with protocol context, update accepted_by, append to history.

    Fixes from v1:
    - Package consistency: accepts must reference the same deal
    - Stale accept clearing: if a party makes a non-accept move, remove
      their prior accept from accepted_by
    """
    proto = neg.protocol
    move.phase = proto.phase.value
    move.round = proto.total_rounds
    move.turn = proto.turn
    neg.move_history.append(move)
    proto.total_moves += 1
    proto.turn += 1

    if move.move_type == MoveType.ACCEPT and move.party_id != "mediator":
        if move.package:
            pkg_hash = _package_hash(move.package)
            if proto.accepted_package_hash is None:
                # First accept — set the reference
                proto.accepted_package_hash = pkg_hash
                proto.accepted_package_id = move.package.id
                proto.accepted_by.add(move.party_id)
            elif pkg_hash == proto.accepted_package_hash:
                # Same deal — count it
                proto.accepted_by.add(move.party_id)
            else:
                # Different deal — reset, start fresh with this accept
                proto.accepted_by.clear()
                proto.accepted_by.add(move.party_id)
                proto.accepted_package_hash = pkg_hash
                proto.accepted_package_id = move.package.id
        else:
            # Accept without package — still count it
            proto.accepted_by.add(move.party_id)

    elif move.move_type in (MoveType.COUNTER, MoveType.REJECT, MoveType.PROPOSE):
        # A new proposal/counter/reject invalidates all prior accepts
        proto.accepted_by.clear()
        proto.accepted_package_id = None
        proto.accepted_package_hash = None

    else:
        # Any other move (ARGUE, INVOKE_CRITERION, DISCLOSE_INTEREST, MESO)
        # from a party that previously accepted = stale accept, remove them
        if move.party_id in proto.accepted_by and move.party_id != "mediator":
            proto.accepted_by.discard(move.party_id)
            if not proto.accepted_by:
                proto.accepted_package_id = None
                proto.accepted_package_hash = None


def _emit_move_event(neg: NegotiationState, move: Move, party_name: str) -> dict:
    """Build a move event dict that the frontend can consume."""
    base = json.loads(move.model_dump_json())
    base["party_name"] = party_name
    return base


def _track_disclosure(neg: NegotiationState, move: Move, party_id: str) -> None:
    """Track interest disclosures, matching by description to original interests."""
    if move.move_type != MoveType.DISCLOSE_INTEREST or not move.disclosed_interest:
        return
    ps = neg.private_states.get(party_id)
    if not ps:
        return

    # Match disclosed interest to original by description similarity
    disclosed_desc = move.disclosed_interest.description.lower()
    for interest in ps.interests:
        if interest.id in ps.disclosed_interests:
            continue  # already disclosed
        if (interest.description.lower() in disclosed_desc
                or disclosed_desc in interest.description.lower()):
            interest.disclosed = True
            ps.disclosed_interests.append(interest.id)
            break
    else:
        # No match found — record the move's interest ID as a fallback
        move.disclosed_interest.disclosed = True
        ps.disclosed_interests.append(move.disclosed_interest.id)


async def _run_round(
    neg: NegotiationState,
    llm: BaseChatModel,
    emit: Callable,
    validator: Any = None,
) -> None:
    """Run one round: each party takes a turn, then mediator optionally intervenes.

    Interrupt moves (ACCEPT, INVOKE_BATNA, REQUEST_MEDIATION) immediately
    halt the round — remaining parties don't get a turn.
    """
    neg.protocol.turn = 0
    interrupted = False

    for party in neg.parties:
        if party.is_human:
            # HITL: pause for human input via LangGraph interrupt
            human_move_data = interrupt({
                "party_id": party.id,
                "party_name": party.name,
                "phase": neg.protocol.phase.value,
                "legal_moves": [m.value for m in get_legal_moves(neg.protocol.phase)],
            })
            # human_move_data is provided via Command(resume=...) from the frontend
            move = Move(
                party_id=party.id,
                move_type=MoveType(human_move_data["move_type"]),
                package=OptionPackage(**human_move_data["package"]) if human_move_data.get("package") else None,
            )
        else:
            # Run the negotiator agent
            move = await run_negotiator(neg, party.id, llm)

        # Validate the move (if validator available)
        if validator:
            result = await validator.validate(move, neg)
            if not result.valid:
                await emit("validation_error", {
                    "party_id": party.id,
                    "violations": result.violations,
                })
                if result.corrected_move:
                    move = result.corrected_move

        _record_move(neg, move)
        _track_disclosure(neg, move, party.id)

        party_name = party.name
        await emit("move", _emit_move_event(neg, move, party_name))

        # Interrupt: terminal moves halt the round immediately
        if move.move_type in INTERRUPT_MOVES:
            interrupted = True
            break

    # Mediator intervention (if not interrupted and architecture supports it)
    if (
        not interrupted
        and neg.protocol.architecture != Architecture.BILATERAL
        and neg.mediator
    ):
        mediator_move = await run_mediator(neg, llm)
        if mediator_move:
            _record_move(neg, mediator_move)
            await emit("mediator_note", _emit_move_event(neg, mediator_move, "Mediator"))


# ---------------------------------------------------------------------------
# Graph node functions
# ---------------------------------------------------------------------------

async def discovery_node(state: GraphState) -> GraphState:
    """Discovery phase: agents exchange interests. Internal loop until transition."""
    neg = state["negotiation"]
    engine = neg._engine_ref  # set by NegotiationEngine before run

    _enter_phase(neg, NegotiationPhase.DISCOVERY)
    await engine.emit("phase_change", {
        "phase": "discovery",
        "round": neg.protocol.total_rounds,
        "message": "Entering interest discovery phase",
    })

    while not should_transition_from_discovery(neg):
        _advance_round(neg)
        await _run_round(neg, engine.llm, engine.emit, engine.validator)

    return {"negotiation": neg}


async def generation_node(state: GraphState) -> GraphState:
    """Generation phase: agents propose initial packages. Internal loop."""
    neg = state["negotiation"]
    engine = neg._engine_ref

    _enter_phase(neg, NegotiationPhase.GENERATION)
    await engine.emit("phase_change", {
        "phase": "generation",
        "round": neg.protocol.total_rounds,
        "message": "Entering option generation phase — agents propose packages",
    })

    while not should_transition_from_generation(neg):
        _advance_round(neg)
        await _run_round(neg, engine.llm, engine.emit, engine.validator)

    return {"negotiation": neg}


async def bargaining_node(
    state: GraphState,
) -> Command[Literal["bargaining", "convergence", "settlement", "impasse"]]:
    """Bargaining phase: ONE round per invocation, Command-based routing.

    This is the critical path where the accept storm was happening in v1.
    By running exactly one round and routing via Command, we eliminate
    the nested while-loop that caused the oscillation.
    """
    neg = state["negotiation"]
    engine = neg._engine_ref

    # Enter phase (only on first visit or re-entry from convergence)
    if neg.protocol.phase != NegotiationPhase.BARGAINING:
        _enter_phase(neg, NegotiationPhase.BARGAINING)
        await engine.emit("phase_change", {
            "phase": "bargaining",
            "round": neg.protocol.total_rounds,
            "message": "Entering bargaining phase — proposals and counterproposals",
        })

    _advance_round(neg)
    await _run_round(neg, engine.llm, engine.emit, engine.validator)

    outcome = check_bargaining_outcome(neg)

    if outcome == "settlement":
        return Command(update={"negotiation": neg}, goto="settlement")
    elif outcome == "impasse":
        return Command(update={"negotiation": neg}, goto="impasse")
    elif outcome == "converge":
        return Command(update={"negotiation": neg}, goto="convergence")
    else:
        return Command(update={"negotiation": neg}, goto="bargaining")


async def convergence_node(
    state: GraphState,
) -> Command[Literal["bargaining", "settlement", "impasse"]]:
    """Convergence phase: ONE round. Parties are close to agreement.

    If settlement is reached, route there. Otherwise, back to bargaining.
    No more single-round-then-bounce — the Command routing makes
    the decision explicit and final.
    """
    neg = state["negotiation"]
    engine = neg._engine_ref

    if neg.protocol.phase != NegotiationPhase.CONVERGENCE:
        _enter_phase(neg, NegotiationPhase.CONVERGENCE)
        await engine.emit("phase_change", {
            "phase": "convergence",
            "round": neg.protocol.total_rounds,
            "message": "Parties are close — entering convergence",
        })

    _advance_round(neg)
    await _run_round(neg, engine.llm, engine.emit, engine.validator)

    outcome = check_bargaining_outcome(neg)

    if outcome == "settlement":
        return Command(update={"negotiation": neg}, goto="settlement")
    elif outcome == "impasse":
        return Command(update={"negotiation": neg}, goto="impasse")
    else:
        # Back to bargaining — not settled yet
        return Command(update={"negotiation": neg}, goto="bargaining")


async def settlement_node(state: GraphState) -> GraphState:
    """Record agreement and emit settlement event."""
    neg = state["negotiation"]
    engine = neg._engine_ref

    _enter_phase(neg, NegotiationPhase.SETTLEMENT)
    neg.outcome = "agreement"

    # Find the last accepted package
    for move in reversed(neg.move_history):
        if move.package:
            neg.agreement = move.package
            break

    await engine.emit("settlement", {
        "agreement": neg.agreement.model_dump() if neg.agreement else None,
        "total_rounds": neg.protocol.total_rounds,
        "total_moves": neg.protocol.total_moves,
    })

    return {"negotiation": neg}


async def impasse_node(state: GraphState) -> GraphState:
    """Record impasse and emit event."""
    neg = state["negotiation"]
    engine = neg._engine_ref

    _enter_phase(neg, NegotiationPhase.IMPASSE)
    neg.outcome = "impasse"

    await engine.emit("impasse", {
        "total_rounds": neg.protocol.total_rounds,
        "total_moves": neg.protocol.total_moves,
        "message": "No agreement reached — parties fall back to BATNAs",
    })

    return {"negotiation": neg}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_negotiation_graph(checkpointer=None):
    """Build the LangGraph StateGraph for negotiation.

    Graph structure:
        START → discovery → generation → bargaining ⇄ convergence
                                              ↓              ↓
                                         settlement      impasse → END
    """
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("discovery", discovery_node)
    graph.add_node("generation", generation_node)
    graph.add_node("bargaining", bargaining_node)
    graph.add_node("convergence", convergence_node)
    graph.add_node("settlement", settlement_node)
    graph.add_node("impasse", impasse_node)

    # Edges
    graph.add_edge(START, "discovery")
    graph.add_edge("discovery", "generation")
    graph.add_edge("generation", "bargaining")
    # bargaining and convergence use Command-based routing (no explicit edges needed)
    graph.add_edge("settlement", END)
    graph.add_edge("impasse", END)

    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# NegotiationEngine — public API (backward compatible)
# ---------------------------------------------------------------------------

class NegotiationEngine:
    """
    Runs a full negotiation simulation using LLM-powered agents.

    v2: Uses LangGraph StateGraph internally instead of manual while loops.
    Public API is unchanged — simulate.py and backend work without modification.
    """

    def __init__(
        self,
        state: NegotiationState,
        llm: BaseChatModel,
        on_event: EventCallback = None,
        event_bus: "EventBus | None" = None,
        validator: "MoveValidator | None" = None,
        scorer: "LLMUtilityScorer | None" = None,
        checkpointer=None,
    ):
        self.state = state
        self.llm = llm

        # Scorer — create if not provided
        self.scorer = scorer or LLMUtilityScorer(llm)

        # Validator — create with scorer if not provided
        self.validator = validator or MoveValidator(scorer=self.scorer)

        # EventBus — prefer bus, fall back to callback for backward compat
        if event_bus:
            self.event_bus = event_bus
        else:
            from .events import EventBus
            self.event_bus = EventBus()
            if on_event:
                self.event_bus.subscribe(on_event)

        # Checkpointer — default to InMemorySaver
        self.checkpointer = checkpointer or InMemorySaver()

        # Compile the graph
        self._graph = build_negotiation_graph(checkpointer=self.checkpointer)

    async def emit(self, event_type: str, data: dict):
        """Emit an event via the event bus."""
        await self.event_bus.emit(event_type, data)

    async def run(self) -> NegotiationState:
        """Run the full negotiation from current state to settlement or impasse."""

        if self.state.protocol.architecture != Architecture.BILATERAL:
            self.state.mediator = self.state.mediator or MediatorState()

        # --- Phase 0: Generate satisfaction anchors for each party ---
        # Anchors ground the utility scorer with concrete reference points.
        # They're generated once, stored on Interest objects, and visible in the UI.
        # All parties run in parallel for speed.
        await self.emit("phase_change", {
            "phase": "setup",
            "round": 0,
            "message": "Generating satisfaction anchors for utility scoring...",
        })

        total_interests = sum(
            len(ps.interests) if (ps := self.state.private_states.get(p.id)) else 0
            for p in self.state.parties
        )
        await self.emit("setup_progress", {
            "message": f"Generating anchors for {len(self.state.parties)} parties ({total_interests} interests)...",
            "parties": [p.id for p in self.state.parties],
            "total_interests": total_interests,
            "completed_interests": 0,
        })

        completed_count = 0

        async def _generate_for_party(party):
            nonlocal completed_count
            ps = self.state.private_states.get(party.id)
            if not (ps and ps.interests):
                return

            await self.emit("setup_progress", {
                "message": f"Generating anchors for {party.name} ({len(ps.interests)} interests)...",
                "party_id": party.id,
                "party_name": party.name,
                "interest_count": len(ps.interests),
            })

            async def on_interest_done(interest, anchors):
                nonlocal completed_count
                completed_count += 1
                await self.emit("anchor_progress", {
                    "party_id": party.id,
                    "party_name": party.name,
                    "interest_description": interest.description,
                    "interest_type": interest.interest_type.value,
                    "anchor_count": len(anchors),
                    "completed_interests": completed_count,
                    "total_interests": total_interests,
                })

            try:
                updated = await self.scorer.generate_anchors(
                    ps, self.state.issues, on_progress=on_interest_done
                )
                ps.interests = updated
                anchor_count = sum(
                    len(i.satisfaction_anchors) for i in updated
                )
                await self.emit("anchors_generated", {
                    "party_id": party.id,
                    "party_name": party.name,
                    "anchor_count": anchor_count,
                    "interests": [
                        {
                            "description": i.description,
                            "interest_type": i.interest_type.value,
                            "priority": i.priority,
                            "related_issues": i.related_issues,
                            "anchors": [
                                {"condition": a.condition, "score": a.score, "reason": a.reason}
                                for a in i.satisfaction_anchors
                            ],
                        }
                        for i in updated
                    ],
                })
            except Exception as e:
                # Non-fatal — scorer still works without anchors (pure LLM)
                await self.emit("anchors_failed", {
                    "party_id": party.id,
                    "error": str(e),
                })

        # Run ALL parties in parallel
        import asyncio as _aio
        await _aio.gather(*[_generate_for_party(p) for p in self.state.parties])

        # Attach engine reference so nodes can access llm, emit, validator
        # This is a lightweight ref — not serialized, not part of the state schema
        self.state._engine_ref = self  # type: ignore[attr-defined]

        initial_state: GraphState = {"negotiation": self.state}

        config = {"configurable": {"thread_id": self.state.id}}

        result = await self._graph.ainvoke(initial_state, config=config)

        self.state = result["negotiation"]

        # Clean up the engine ref
        if hasattr(self.state, "_engine_ref"):
            del self.state._engine_ref

        return self.state
