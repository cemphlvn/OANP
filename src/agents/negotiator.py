"""
Negotiator Agent — represents a single party in the negotiation.

Each negotiator has access to:
- Their own private state (interests, BATNA, strategy, belief models)
- The shared state (issues, criteria, move history, protocol phase)

The agent uses an LLM to decide the next move, guided by:
1. Harvard negotiation principles (encoded in the system prompt)
2. Current protocol phase constraints (what moves are legal)
3. Strategy parameters (aspiration level, cooperation, disclosure policy)
4. Belief models about other parties (updated from observed moves)
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from ..protocol.types import (
    Move,
    MoveType,
    NegotiationPhase,
    NegotiationState,
    OptionPackage,
    Argument,
)


NEGOTIATOR_SYSTEM_PROMPT = """You are a negotiation agent operating under the OANP protocol. \
You represent {party_name} ({party_role}) in this negotiation.

## Your Guiding Principles (Harvard Negotiation Project)

1. **Focus on interests, not positions.** Understand WHY you want things, not just WHAT you want.
2. **Generate options for mutual gain.** Look for creative packages that satisfy both sides.
3. **Insist on objective criteria.** Use market data, precedents, and fair standards.
4. **Know your BATNA.** Never accept a deal worse than your best alternative.
5. **Be warm and cooperative.** Research shows warmth produces better outcomes for everyone.
6. **Separate people from the problem.** Stay respectful and constructive.

## Theory of Mind — Model the Other Party

Before deciding your move, ACTIVELY THINK about the other party's perspective. \
You can ONLY infer their interests from what they have COMMUNICATED — their proposals, \
arguments, disclosed interests, and observable behavior. You have NO access to their \
private interests, BATNA, or strategy.

Based on what they have shown you:
- **What do they likely care about most?** Infer from their proposals and arguments.
- **What would cost you little but benefit them greatly?** These are the trade-off levers \
that create mutual value.
- **What are they afraid of?** Their rejections and counterproposals reveal concerns.
- **What is their likely BATNA?** Estimate from their behavior — are they eager or patient?

Use this model to craft proposals that maximize YOUR outcome while ALSO satisfying their \
key interests. This is not altruism — it is strategic. Packages that address both sides' \
core interests are more likely to be accepted, reach agreement faster, and avoid impasse. \
The best deal for you is often one that also works well for them.

**In your reasoning field, explicitly state your theory of mind:** what you think the other \
party wants, why, and how your move accounts for it.

## Your Interests (private — do not reveal all at once, disclose strategically)
{interests_text}

## Your BATNA (private — never reveal this)
{batna_text}

## Your Strategy
- Aspiration level: {aspiration_level} (target utility, 0-1)
- Cooperation level: {cooperation_level} (warmth, 0-1)
- Disclosure policy: {disclosure_policy}
- Current tactic: {current_tactic}

## Move Selection Priority

In DISCOVERY: Lead with DISCLOSE_INTEREST to share your interests. Use ARGUE to explain \
WHY your interests matter, citing objective criteria. Don't rush to PROPOSE until you \
understand the other party's interests.

In GENERATION: Propose packages but ALSO argue for why your proposals are fair using \
objective criteria. Use INVOKE_CRITERION to reference market data, precedents, or \
regulations that support your position.

In BARGAINING: When countering or rejecting, ALWAYS explain your reasoning with an \
ARGUE move. Don't just reject — say WHY and cite criteria. A rejection without \
reasoning is a wasted move.

IMPORTANT: You should use ARGUE or INVOKE_CRITERION at least once every 2-3 moves. \
Negotiations without arguments devolve into positional bargaining — exactly what we \
want to avoid. REJECT moves MUST include an argument explaining what is unacceptable \
and what would need to change.

IMPORTANT: For categorical issues, you MUST choose from the provided options only. \
Do not invent new option values. For monetary/temporal issues with ranges, \
stay within the defined range.

## Current Phase: {phase}
## Legal Moves This Phase: {legal_moves}

## Instructions
Given the negotiation state and move history, decide your next move. In your reasoning, \
FIRST state your theory of mind about the other party, THEN your strategic calculation, \
THEN your chosen move and why.
"""


def get_legal_moves(phase: NegotiationPhase) -> list[MoveType]:
    """Return which move types are legal in the current phase."""
    phase_moves = {
        NegotiationPhase.DISCOVERY: [
            MoveType.DISCLOSE_INTEREST,
            MoveType.ARGUE,
            MoveType.INVOKE_CRITERION,
            MoveType.PROPOSE,
        ],
        NegotiationPhase.GENERATION: [
            MoveType.PROPOSE,
            MoveType.MESO,
            MoveType.DISCLOSE_INTEREST,
            MoveType.ARGUE,
            MoveType.INVOKE_CRITERION,
        ],
        NegotiationPhase.BARGAINING: [
            MoveType.PROPOSE,
            MoveType.COUNTER,
            MoveType.ARGUE,
            MoveType.INVOKE_CRITERION,
            MoveType.ACCEPT,
            MoveType.REJECT,
            MoveType.INVOKE_BATNA,
            MoveType.MESO,
        ],
        NegotiationPhase.CONVERGENCE: [
            MoveType.PROPOSE,
            MoveType.COUNTER,
            MoveType.ARGUE,
            MoveType.INVOKE_CRITERION,
            MoveType.ACCEPT,
            MoveType.REJECT,
        ],
        NegotiationPhase.IMPASSE: [
            MoveType.REQUEST_MEDIATION,
            MoveType.INVOKE_BATNA,
        ],
    }
    return phase_moves.get(phase, [])


def build_negotiator_prompt(
    state: NegotiationState,
    party_id: str,
) -> list[Any]:
    """Build the LLM messages for a negotiator agent.

    Uses StateView to enforce information boundaries — the agent only sees
    its own private state and shared public state. Never sees other parties'
    interests, BATNAs, or strategies.
    """
    from ..protocol.views import StateView
    scoped = StateView.for_party(state, party_id)

    party = next(p for p in state.parties if p.id == party_id)
    private = state.private_states[party_id]

    interests_text = "\n".join(
        f"- [{i.interest_type.value.upper()}] {i.description} (priority: {i.priority}, "
        f"issues: {', '.join(i.related_issues)})"
        for i in private.interests
    )

    batna_text = (
        f"{private.batna.description} (utility: {private.batna.utility})"
        if private.batna
        else "No BATNA defined — avoid impasse."
    )

    legal_moves = get_legal_moves(state.protocol.phase)

    system = NEGOTIATOR_SYSTEM_PROMPT.format(
        party_name=party.name,
        party_role=party.role,
        interests_text=interests_text,
        batna_text=batna_text,
        aspiration_level=private.strategy.aspiration_level,
        cooperation_level=private.strategy.cooperation_level,
        disclosure_policy=private.strategy.disclosure_policy,
        current_tactic=private.strategy.current_tactic,
        phase=state.protocol.phase.value,
        legal_moves=", ".join(m.value for m in legal_moves),
    )

    # Build move history from scoped view (other parties' reasoning stripped)
    scoped_moves = scoped.get("move_history", [])[-20:]
    history_lines = []
    for m in scoped_moves:
        p_name = next((p.name for p in state.parties if p.id == m.get("party_id")), m.get("party_id", "?"))
        mt = m.get("move_type", "?")
        line = f"[Round {m.get('round', '?')}] {p_name}: {mt}"
        pkg = m.get("package")
        if pkg:
            line += f" — {pkg.get('issue_values', {})}"
            if pkg.get("rationale"):
                line += f" ({pkg['rationale'][:100]})"
        arg = m.get("argument")
        if arg and arg.get("claim"):
            line += f" — \"{arg['claim'][:100]}\""
        # Include disclosed interests so agent can build theory of mind
        di = m.get("disclosed_interest")
        if di:
            line += f" — disclosed [{di.get('interest_type','')}]: {di.get('description','')}"
        history_lines.append(line)

    issues_text = "\n".join(
        f"- {iss.name} ({iss.issue_type}): "
        + (f"range {iss.range}" if iss.range else f"options: {', '.join(iss.options)}")
        for iss in state.issues
    )

    criteria_text = "\n".join(
        f"- {c.name}: {c.reference_value} (source: {c.source})"
        for c in state.criteria
    )

    # Other parties — name and role only (everything else must be inferred from moves)
    other_parties = [p for p in state.parties if p.id != party_id]
    other_text = "\n".join(f"- {p.name} ({p.role})" for p in other_parties)

    user_msg = f"""## Other Parties (infer their interests ONLY from their moves and disclosures)
{other_text}

## Issues on the Table
{issues_text}

## Objective Criteria
{criteria_text}

## Move History
{chr(10).join(history_lines) if history_lines else "(No moves yet — you are opening.)"}

## Your Turn
First think about what the other party likely wants and fears based on their moves. \
Then decide your move. Use theory of mind to find creative value-creating options."""

    return [
        SystemMessage(content=system),
        HumanMessage(content=user_msg),
    ]


async def run_negotiator(
    state: NegotiationState,
    party_id: str,
    llm: BaseChatModel,
) -> Move:
    """Run one turn of a negotiator agent. Returns a typed Move via structured output."""
    from .schemas import NegotiatorResponse

    messages = build_negotiator_prompt(state, party_id)

    # Use structured output — LLM is forced to return a valid NegotiatorResponse
    structured_llm = llm.with_structured_output(NegotiatorResponse)
    response: NegotiatorResponse = await structured_llm.ainvoke(messages)

    move_type = MoveType(response.move_type)

    package = None
    if response.package:
        package = OptionPackage(
            issue_values=response.package.issue_values,
            rationale=response.package.rationale,
        )

    argument = None
    if response.argument:
        argument = Argument(
            claim=response.argument.claim,
            grounds=response.argument.grounds,
            criterion_id=response.argument.criterion_id,
        )

    disclosed_interest = None
    if response.disclosed_interest:
        from ..protocol.types import Interest, InterestType
        disclosed_interest = Interest(
            description=response.disclosed_interest.description,
            interest_type=InterestType(response.disclosed_interest.interest_type),
            priority=response.disclosed_interest.priority,
            related_issues=response.disclosed_interest.related_issues,
            disclosed=True,
        )

    return Move(
        party_id=party_id,
        move_type=move_type,
        package=package,
        argument=argument,
        disclosed_interest=disclosed_interest,
        references=response.references,
        reasoning=response.reasoning or None,
    )
