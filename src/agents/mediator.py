"""
Mediator Agent — configurable neutral facilitator.

The mediator's behavior is governed by three parameters:
  - mode: facilitative | evaluative | arbitrative
  - knowledge: blind | caucus_only | omniscient
  - intervention: every_round | on_request | at_impasse

FACILITATIVE (default, real-world mediation model):
  - Never evaluates outcomes or pushes for specific deals
  - Reframes positions as interests
  - Reality-tests proposals ("have you considered...?")
  - Generates creative options based on patterns it sees
  - Maintains process fairness (equal voice), not outcome fairness

EVALUATIVE:
  - Everything facilitative does, plus:
  - References objective criteria ("market rate for this is...")
  - Gives opinions on likely outcomes if parties don't agree

ARBITRATIVE:
  - Everything evaluative does, plus:
  - Can propose binding solutions at impasse
  - Acts as final decision-maker when negotiation fails

Knowledge levels:
  - BLIND: Only sees shared state (move history, issues, criteria)
  - CAUCUS_ONLY: Sees what parties voluntarily disclose (realistic)
  - OMNISCIENT: Sees all private state (research/simulation only)
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from ..protocol.types import (
    Argument,
    MediatorIntervention,
    MediatorKnowledge,
    MediatorMode,
    Move,
    MoveType,
    NegotiationState,
    OptionPackage,
)
from .schemas import MediatorResponse


# ---------------------------------------------------------------------------
# System prompts per mode
# ---------------------------------------------------------------------------

FACILITATIVE_PROMPT = """You are a facilitative mediator in an OANP negotiation. You are NEUTRAL — \
you do not represent any party and you do NOT decide what is fair.

## Your Role
You are a PROCESS FACILITATOR, not an outcome judge. Your job is to help parties reach \
their own agreement by:

1. **Reframing** — when a party states a position, help them and others see the underlying interest. \
("It sounds like what matters to you is flexibility, not the specific schedule.")

2. **Reality-testing** — help parties think through consequences without telling them what to do. \
("What happens if you can't reach agreement here? What are your alternatives?")

3. **Option generation** — suggest creative packages that neither party has proposed. Look for \
trade-offs where parties value things differently. ("What if we explored a package where...")

4. **Process management** — ensure both parties are being heard and the conversation is productive. \
If one party is dominating, redirect. If parties are stuck on positions, shift to interests.

## Action Selection Priority

Your PRIMARY role is to facilitate understanding, not to propose deals:

1. **FIRST CHOICE: highlight_overlap** — point out where parties' interests align. \
This is the most valuable thing you can do. ("Both of you have expressed concern about...")
2. **SECOND CHOICE: reframe** — restate a positional statement as an underlying interest. \
("When you say X, it sounds like what you really need is Y.")
3. **THIRD CHOICE: propose_criterion** — introduce an objective standard that could \
break a deadlock. ("Industry data from [source] shows...")
4. **LAST RESORT: suggest_package** — only after you have done at least 2 of the above. \
A premature package short-circuits the discovery process.

Do NOT suggest a package in the first 3 mediator interventions. Focus on helping parties \
understand each other's interests first. When you do suggest a package, it should \
synthesize insights from overlaps and criteria you've already identified.

## What You Must NOT Do
- Do NOT evaluate whether an outcome is "fair" or "balanced"
- Do NOT push for a specific deal
- Do NOT tell parties what they should accept
- Do NOT reveal what one party told you in private to the other party
- You facilitate the PROCESS — the parties own the OUTCOME

{knowledge_section}

## Current Phase: {phase}
## Issues: {issues_text}
{criteria_section}
{history_section}
"""

EVALUATIVE_ADDITION = """
## Additional Role: Evaluative
In addition to facilitation, you may:
- Reference objective criteria and standards ("Market data suggests...")
- Give your assessment of likely outcomes if no agreement is reached
- Point out when a proposal is significantly outside normal ranges
- Help parties understand the strengths and weaknesses of their positions

You still do NOT decide the outcome — you inform it.
"""

ARBITRATIVE_ADDITION = """
## Additional Role: Arbitrative
If the negotiation reaches impasse, you have authority to:
- Propose a binding resolution based on the evidence and criteria
- Make a final determination that both parties must accept
- This authority should only be exercised after facilitation and evaluation have been exhausted
"""


# ---------------------------------------------------------------------------
# Knowledge level builders
# ---------------------------------------------------------------------------

def build_knowledge_section(state: NegotiationState) -> str:
    """Build the information the mediator has access to, based on knowledge config."""
    if not state.mediator:
        return ""

    knowledge = state.mediator.config.knowledge

    if knowledge == MediatorKnowledge.BLIND:
        return """## What You Know
You can only see:
- The issues being negotiated and their options/ranges
- The move history (all proposals, counterproposals, arguments made publicly)
- Any objective criteria defined for this negotiation
You do NOT see any party's private interests, BATNA, or strategy."""

    elif knowledge == MediatorKnowledge.CAUCUS_ONLY:
        # Build from disclosed interests
        disclosed_lines = []
        for party in state.parties:
            ps = state.private_states.get(party.id)
            if not ps:
                continue
            disclosed = [i for i in ps.interests if i.disclosed]
            if disclosed:
                disclosed_lines.append(f"\n{party.name} has shared with you:")
                for interest in disclosed:
                    disclosed_lines.append(
                        f"  - [{interest.interest_type.value}] {interest.description} "
                        f"(priority: {interest.priority})"
                    )

        # Add any caucus notes
        caucus_notes = []
        for party_id, notes in state.mediator.caucus_notes.items():
            party_name = next((p.name for p in state.parties if p.id == party_id), party_id)
            if notes:
                caucus_notes.append(f"\nPrivate session notes with {party_name}:")
                for note in notes[-3:]:  # last 3 notes
                    caucus_notes.append(f"  - {note}")

        return f"""## What You Know (from private sessions / caucuses)
You see the shared move history and issues.
Additionally, parties have voluntarily disclosed the following to you in confidence:
{"".join(disclosed_lines) if disclosed_lines else "(No interests disclosed yet)"}
{"".join(caucus_notes) if caucus_notes else ""}

IMPORTANT: Do not reveal Party A's private disclosures to Party B, or vice versa. \
Use this information to find bridging solutions without breaching confidence."""

    elif knowledge == MediatorKnowledge.OMNISCIENT:
        # Full visibility — for research only
        lines = []
        for party in state.parties:
            ps = state.private_states.get(party.id)
            if not ps:
                continue
            lines.append(f"\n{party.name} (FULL PRIVATE STATE — research mode):")
            for interest in ps.interests:
                lines.append(
                    f"  Interest: [{interest.interest_type.value}] {interest.description} "
                    f"(priority: {interest.priority})"
                )
            if ps.batna:
                lines.append(f"  BATNA: {ps.batna.description} (utility: {ps.batna.utility})")
            lines.append(f"  Strategy: aspiration={ps.strategy.aspiration_level}, "
                        f"cooperation={ps.strategy.cooperation_level}")

        return f"""## What You Know (OMNISCIENT MODE — research/simulation only)
WARNING: In real mediation you would never have this information.
This mode exists for research — studying how information affects outcomes.
{"".join(lines)}"""

    return ""


# ---------------------------------------------------------------------------
# Main mediator function
# ---------------------------------------------------------------------------

async def run_mediator(
    state: NegotiationState,
    llm: BaseChatModel,
) -> Move | None:
    """Run the mediator agent. Returns a Move or None if no intervention needed."""
    if not state.mediator:
        return None

    config = state.mediator.config

    # Check intervention timing
    if config.intervention == MediatorIntervention.ON_REQUEST:
        # Only intervene if a party requested mediation
        recent = state.move_history[-3:] if state.move_history else []
        if not any(m.move_type == MoveType.REQUEST_MEDIATION for m in recent):
            return None

    elif config.intervention == MediatorIntervention.AT_IMPASSE:
        # Only intervene if negotiation seems stuck
        if len(state.move_history) < 4:
            return None
        recent_types = [m.move_type for m in state.move_history[-4:]]
        stuck = all(t in (MoveType.REJECT, MoveType.COUNTER) for t in recent_types)
        if not stuck:
            return None

    # Build prompt
    issues_text = "\n".join(
        f"- {iss.name} ({iss.issue_type}): "
        + (f"range {iss.range}" if iss.range else f"options: {', '.join(iss.options)}")
        for iss in state.issues
    )

    criteria_section = ""
    if state.criteria and config.mode in (MediatorMode.EVALUATIVE, MediatorMode.ARBITRATIVE):
        criteria_section = "\n## Objective Criteria (you may reference these)\n" + "\n".join(
            f"- {c.name}: {c.reference_value}" for c in state.criteria
        )
    elif state.criteria:
        criteria_section = "\n## Objective Criteria (available if parties invoke them)\n" + "\n".join(
            f"- {c.name}: {c.reference_value}" for c in state.criteria
        )

    history_lines = []
    for move in state.move_history[-15:]:
        p_name = next((p.name for p in state.parties if p.id == move.party_id), move.party_id)
        line = f"{p_name}: {move.move_type.value}"
        if move.package:
            line += f" — {move.package.issue_values}"
        if move.argument:
            line += f" — \"{move.argument.claim}\""
        history_lines.append(line)

    history_section = "\n## Move History\n" + (
        "\n".join(history_lines) if history_lines else "(No moves yet)"
    )

    knowledge_section = build_knowledge_section(state)

    # Build system prompt based on mode
    system = FACILITATIVE_PROMPT.format(
        knowledge_section=knowledge_section,
        phase=state.protocol.phase.value,
        issues_text=issues_text,
        criteria_section=criteria_section,
        history_section=history_section,
    )

    if config.mode == MediatorMode.EVALUATIVE:
        system += EVALUATIVE_ADDITION
    elif config.mode == MediatorMode.ARBITRATIVE:
        system += EVALUATIVE_ADDITION + ARBITRATIVE_ADDITION

    # Advanced mode: append legal compliance context for mediator
    if state.compliance and state.compliance.mode.value == "advanced":
        system += _build_mediator_compliance_context(state)

    messages = [
        SystemMessage(content=system),
        HumanMessage(
            content="Review the current negotiation state. "
            "Decide whether to intervene and how. "
            "If the conversation is productive, you may choose 'no_intervention'."
        ),
    ]

    structured_llm = llm.with_structured_output(MediatorResponse)
    response: MediatorResponse = await structured_llm.ainvoke(messages)

    if response.action == "no_intervention":
        return None

    if response.action == "suggest_package" and response.package:
        return Move(
            party_id="mediator",
            move_type=MoveType.PROPOSE,
            package=OptionPackage(
                issue_values=response.package.issue_values,
                rationale=response.package.rationale or response.analysis,
            ),
        )

    # Non-package interventions → ARGUE move (reframe, highlight overlap, etc.)
    if response.action in ("highlight_overlap", "reframe", "propose_criterion"):
        grounds = [g for g in [response.overlap_detected, response.trade_off_opportunity] if g]

        return Move(
            party_id="mediator",
            move_type=MoveType.ARGUE,
            argument=Argument(
                claim=response.analysis,
                grounds=grounds,
            ),
        )

    return None


def _build_mediator_compliance_context(state) -> str:
    """Build legal compliance context for the mediator (advanced mode)."""
    parts = ["\n\n## Legal Compliance Context\n"]
    c = state.compliance

    if c.institution:
        parts.append(f"**Institutional Rules:** {c.institution.framework.value.upper()}")
        parts.append(f"**Procedure:** {c.institution.procedure}")

    parts.append(f"**Current Tier:** {c.current_tier.value.upper()}")

    if c.deadlines:
        if c.deadlines.hard_deadline_rounds:
            remaining = max(0, c.deadlines.hard_deadline_rounds - state.protocol.total_rounds)
            parts.append(f"**Hard Deadline:** {remaining} rounds remaining")

    if c.current_tier.value == "mediation":
        parts.append(
            "\n**Mediation Compliance (Singapore Convention):**\n"
            "- Any settlement you help produce should be clear, comprehensible, and enforceable.\n"
            "- Record the basis for settlement terms — the audit trail serves as mediation evidence.\n"
            "- If settlement is reached, recommend recording it as a consent award for enforceability.\n"
            "- Maintain impartiality — disclose any concerns about process integrity."
        )

    if c.current_tier.value == "arbitration":
        parts.append(
            "\n**Arbitration Mode:**\n"
            "- You are now acting as an ARBITRATOR with binding authority.\n"
            "- Your decision will be rendered as a formal AWARD.\n"
            "- Base your decision on: (1) objective criteria, (2) parties' disclosed interests, "
            "(3) fairness and equity, (4) applicable institutional rules.\n"
            "- The award must include clear reasoning to satisfy New York Convention requirements.\n"
            "- Aim for a balanced resolution that accounts for both parties' legitimate interests."
        )

    return "\n".join(parts)
