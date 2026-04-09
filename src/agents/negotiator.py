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

    # BCI opponent model section (if data available)
    bci_section = _build_bci_section(state, party_id)
    if bci_section:
        system += "\n\n" + bci_section

    # Advanced mode: append legal compliance context
    if state.compliance and state.compliance.mode.value == "advanced":
        system += _build_compliance_context(state)

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


def _build_bci_section(state: NegotiationState, party_id: str) -> str:
    """Build BCI opponent model section for the negotiator prompt.

    Suppressed when confidence is too low or no opponent bids observed.
    """
    private = state.private_states.get(party_id)
    if not private or not private.belief_models:
        return ""

    def _weight_label(w: float) -> str:
        if w > 0.30:
            return "HIGH"
        if w > 0.15:
            return "MODERATE"
        return "LOW"

    def _util_label(u: float) -> str:
        if u > 0.8:
            return "VERY HIGH"
        if u > 0.6:
            return "HIGH"
        if u > 0.4:
            return "MODERATE"
        if u > 0.2:
            return "LOW"
        return "VERY LOW"

    sections = []
    for target_id, belief in private.belief_models.items():
        if belief.confidence < 0.2:
            continue
        if not belief.estimated_priorities:
            continue

        target_name = next(
            (p.name for p in state.parties if p.id == target_id), target_id
        )

        conf_label = "HIGH" if belief.confidence > 0.7 else "MODERATE" if belief.confidence > 0.5 else "LOW"

        lines = [
            f"## Opponent Model: {target_name} (Bayesian Estimate from Observed Bids)",
            f"Confidence: {conf_label} ({belief.confidence:.0%})",
            "",
            "Estimated priorities (what they care about most):",
        ]

        # Sort by weight descending, map issue IDs to names
        sorted_priorities = sorted(belief.estimated_priorities.items(), key=lambda x: -x[1])
        for issue_id, weight in sorted_priorities:
            issue_name = next(
                (iss.name for iss in state.issues if iss.id == issue_id or iss.name == issue_id),
                issue_id,
            )
            lines.append(f"- {issue_name}: {_weight_label(weight)} (weight {weight:.2f})")

        # Utility estimates (only when confidence is reasonable)
        if belief.confidence >= 0.5:
            # Find opponent's last bid and our last bid
            opponent_bids = [m for m in state.move_history if m.party_id == target_id and m.package]
            our_bids = [m for m in state.move_history if m.party_id == party_id and m.package]

            if opponent_bids or our_bids:
                lines.append("")
                # Use BCI engine if available via _engine_ref
                engine = getattr(state, '_engine_ref', None)
                bci_models = getattr(engine, 'bci_models', {}) if engine else {}
                bci = bci_models.get(party_id, {}).get(target_id)
                if bci:
                    if our_bids:
                        our_util = bci.estimate_utility(our_bids[-1].package.issue_values)
                        lines.append(
                            f"Estimated opponent satisfaction with YOUR last proposal: "
                            f"{our_util:.2f} ({_util_label(our_util)})"
                        )
                    if opponent_bids:
                        their_util = bci.estimate_utility(opponent_bids[-1].package.issue_values)
                        lines.append(
                            f"Estimated opponent satisfaction with THEIR last proposal: "
                            f"{their_util:.2f} ({_util_label(their_util)})"
                        )

        if belief.confidence < 0.5:
            lines.append("")
            lines.append("(Low confidence — treat as tentative hypotheses, not facts.)")

        lines.extend([
            "",
            "This data COMPLEMENTS your theory-of-mind reasoning. The opponent may have",
            "interests not captured by bid patterns (relationship concerns, undisclosed constraints).",
        ])

        # Strategy hints based on BCI
        if belief.confidence >= 0.4 and len(sorted_priorities) >= 2:
            top_issue = sorted_priorities[0][0]
            top_name = next(
                (iss.name for iss in state.issues if iss.id == top_issue or iss.name == top_issue),
                top_issue,
            )
            bottom_issue = sorted_priorities[-1][0]
            bottom_name = next(
                (iss.name for iss in state.issues if iss.id == bottom_issue or iss.name == bottom_issue),
                bottom_issue,
            )
            lines.append("")
            lines.append(
                f"TACTICAL HINT: Opponent cares most about {top_name} and least about "
                f"{bottom_name}. Consider conceding on {top_name} (high value to them) "
                f"while holding firm on issues you value most."
            )

        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _build_compliance_context(state: NegotiationState) -> str:
    """Build legal compliance context to append to negotiator system prompt (advanced mode)."""
    parts = ["\n\n## Legal Compliance Context (Advanced Mode)\n"]
    c = state.compliance

    if c.institution:
        parts.append(f"**Institutional Rules:** {c.institution.framework.value.upper()}")
        parts.append(f"**Procedure:** {c.institution.procedure}")
        if c.institution.governing_law:
            parts.append(f"**Governing Law:** {c.institution.governing_law}")
        if c.institution.seat:
            parts.append(f"**Seat:** {c.institution.seat}")

    if c.escalation:
        tier_str = " → ".join(t.value.upper() for t in c.escalation.tiers)
        parts.append(f"\n**Escalation Path:** {tier_str}")
        parts.append(f"**Current Tier:** {c.current_tier.value.upper()}")
        if c.tier_history:
            parts.append(f"**Escalation Events:** {len(c.tier_history)} tier transitions so far")

    if c.deadlines:
        limits = c.deadlines.phase_max_rounds
        if limits:
            current_phase = state.protocol.phase.value
            limit = limits.get(current_phase)
            if limit:
                remaining = max(0, limit - state.protocol.round)
                parts.append(f"\n**Phase Deadline:** {remaining} rounds remaining in {current_phase}")
        if c.deadlines.hard_deadline_rounds:
            remaining_total = max(0, c.deadlines.hard_deadline_rounds - state.protocol.total_rounds)
            parts.append(f"**Hard Deadline:** {remaining_total} rounds remaining overall")

    parts.append(
        "\n**Legal Awareness Instructions:**\n"
        "- You are operating under formal institutional arbitration rules.\n"
        "- Be aware of time pressure — deadlines will trigger automatic escalation.\n"
        "- If the negotiation escalates to arbitration, an arbitrator will impose a binding decision.\n"
        "- Reaching a negotiated settlement is almost always better than an imposed award.\n"
        "- Frame your arguments using objective criteria recognized by the institutional framework.\n"
        "- Ensure any agreement you accept could be enforceable under the New York Convention."
    )

    return "\n".join(parts)
