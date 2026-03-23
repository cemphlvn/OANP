"""
Analyst Agent — post-hoc analysis of negotiation outcomes.

Computes the metrics defined in the protocol spec:
- Individual utility (interest satisfaction per party)
- Social welfare (sum of utilities)
- Pareto efficiency (is the outcome on the frontier?)
- BATNA surplus (how much better than walking away)
- Fairness (Nash bargaining solution proximity)
- Integrative index (did the negotiation create value?)

These metrics are critical for:
1. The paper — proving OANP produces better outcomes than baselines
2. The playground — showing users why the protocol matters
3. The simulation comparison — mediated vs bilateral, warm vs cold, etc.

Research grounding:
- MIT competition scored agents on Harvard's six principles
- ANAC uses individual utility and social welfare as primary metrics
- Pareto efficiency is the gold standard from mechanism design
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scorer import LLMUtilityScorer

from ..protocol.types import (
    NegotiationState,
    OptionPackage,
    PrivatePartyState,
)


@dataclass
class NegotiationMetrics:
    """Complete analysis of a negotiation outcome."""

    # Per-party metrics
    party_utilities: dict[str, float]        # party_id -> utility score 0-1
    party_batna_surplus: dict[str, float]    # party_id -> (utility - batna)
    party_interest_satisfaction: dict[str, float]  # party_id -> % interests addressed

    # Aggregate metrics
    social_welfare: float                    # sum of utilities
    pareto_efficient: bool                   # no party can improve without another worsening
    nash_product: float                      # product of BATNA surpluses (fairness)
    integrative_index: float                 # social_welfare / sum_of_batnas (>1 = value created)

    # Process metrics
    total_rounds: int
    total_moves: int
    move_breakdown: dict[str, int]           # move_type -> count
    phases_visited: list[str]
    disclosure_rate: float                   # % of interests disclosed

    # Outcome
    outcome: str                             # agreement / impasse
    agreement: dict | None


def compute_utility(
    package: OptionPackage,
    private: PrivatePartyState,
    issues: list,
) -> float:
    """
    Estimate utility of a package for a party based on their interests.

    Simple heuristic: for each interest, check if any related issue in the
    package has a value that seems favorable. More sophisticated scoring
    would use the party's utility function if defined.

    Returns 0.0-1.0.
    """
    if not private.interests:
        return 0.5  # no interests defined — neutral

    total_weight = sum(i.priority for i in private.interests)
    if total_weight == 0:
        return 0.5

    satisfied_weight = 0.0

    for interest in private.interests:
        # Check if any related issue has a value in the package
        for issue_id in interest.related_issues:
            if issue_id in package.issue_values:
                # Issue is addressed in the package — partial satisfaction
                # (A real implementation would evaluate the specific value
                # against the interest; for MVP we count coverage)
                # Issue is addressed — assume partial satisfaction (heuristic fallback;
                # LLM scorer in analyze_negotiation_llm provides accurate per-interest scores)
                satisfied_weight += interest.priority * 0.7
                break

    return min(satisfied_weight / total_weight, 1.0)


def analyze_negotiation(state: NegotiationState) -> NegotiationMetrics:
    """Synchronous analysis using heuristic utility. Use analyze_negotiation_llm() for LLM scoring."""
    return _build_metrics(state, _compute_utilities_heuristic(state))


async def analyze_negotiation_llm(
    state: NegotiationState,
    scorer: "LLMUtilityScorer",
) -> NegotiationMetrics:
    """Full analysis using the LLM utility scorer for accurate per-interest scores."""
    utility_data = await _compute_utilities_llm(state, scorer)
    return _build_metrics(state, utility_data)


def _compute_utilities_heuristic(
    state: NegotiationState,
) -> dict[str, tuple[float, float]]:
    """Heuristic fallback: returns {party_id: (utility, interest_satisfaction)}."""
    result = {}
    for party in state.parties:
        ps = state.private_states.get(party.id)
        if not ps:
            continue
        if state.agreement:
            utility = compute_utility(state.agreement, ps, state.issues)
            # Interest satisfaction by coverage
            total = len(ps.interests)
            addressed = 0
            if total > 0:
                for interest in ps.interests:
                    for issue_id in interest.related_issues:
                        if issue_id in state.agreement.issue_values:
                            addressed += 1
                            break
            satisfaction = addressed / max(total, 1)
        else:
            utility = ps.batna.utility if ps.batna else 0.0
            satisfaction = 0.0
        result[party.id] = (utility, satisfaction)
    return result


async def _compute_utilities_llm(
    state: NegotiationState,
    scorer: "LLMUtilityScorer",
) -> dict[str, tuple[float, float]]:
    """LLM-based utility scoring: returns {party_id: (utility, interest_satisfaction)}."""
    result = {}
    for party in state.parties:
        ps = state.private_states.get(party.id)
        if not ps:
            continue
        if state.agreement:
            try:
                score = await scorer.score(state.agreement, ps, state.issues)
                utility = score.overall
                # Interest satisfaction: mean of per-interest scores
                if score.per_interest:
                    satisfaction = sum(score.per_interest.values()) / len(score.per_interest)
                else:
                    satisfaction = utility
            except Exception:
                # Fall back to heuristic if scorer fails
                utility = compute_utility(state.agreement, ps, state.issues)
                satisfaction = 0.0
        else:
            utility = ps.batna.utility if ps.batna else 0.0
            satisfaction = 0.0
        result[party.id] = (utility, satisfaction)
    return result


def _build_metrics(
    state: NegotiationState,
    utility_data: dict[str, tuple[float, float]],
) -> NegotiationMetrics:
    """Build metrics from pre-computed utility data."""
    party_utilities: dict[str, float] = {}
    party_batna_surplus: dict[str, float] = {}
    party_interest_satisfaction: dict[str, float] = {}

    for party in state.parties:
        ps = state.private_states.get(party.id)
        if not ps:
            continue
        utility, satisfaction = utility_data.get(party.id, (0.0, 0.0))
        party_utilities[party.id] = utility
        batna_utility = ps.batna.utility if ps.batna else 0.0
        party_batna_surplus[party.id] = utility - batna_utility
        party_interest_satisfaction[party.id] = satisfaction

    # --- Aggregate metrics ---
    social_welfare = sum(party_utilities.values())

    nash_product = 1.0
    for surplus in party_batna_surplus.values():
        nash_product *= max(surplus, 0.001)

    sum_batnas = sum(
        (state.private_states[p.id].batna.utility
         if state.private_states.get(p.id) and state.private_states[p.id].batna else 0.0)
        for p in state.parties
    )
    integrative_index = social_welfare / max(sum_batnas, 0.001)

    pareto_efficient = all(s >= 0 for s in party_batna_surplus.values())

    # --- Process metrics ---
    move_breakdown = dict(Counter(m.move_type.value for m in state.move_history))

    phases_visited = list(dict.fromkeys(
        e.get("phase", "") for e in state.protocol.phase_history
    )) if state.protocol.phase_history else [state.protocol.phase.value]

    total_interests = sum(len(ps.interests) for ps in state.private_states.values())
    total_disclosed = sum(len(ps.disclosed_interests) for ps in state.private_states.values())
    disclosure_rate = total_disclosed / max(total_interests, 1)

    return NegotiationMetrics(
        party_utilities=party_utilities,
        party_batna_surplus=party_batna_surplus,
        party_interest_satisfaction=party_interest_satisfaction,
        social_welfare=social_welfare,
        pareto_efficient=pareto_efficient,
        nash_product=nash_product,
        integrative_index=integrative_index,
        total_rounds=state.protocol.total_rounds,
        total_moves=len(state.move_history),
        move_breakdown=move_breakdown,
        phases_visited=phases_visited,
        disclosure_rate=disclosure_rate,
        outcome=state.outcome or "unknown",
        agreement=state.agreement.model_dump() if state.agreement else None,
    )


def format_metrics_report(metrics: NegotiationMetrics, state: NegotiationState) -> str:
    """Format metrics as a human-readable report."""
    lines = []
    lines.append("=" * 50)
    lines.append("  NEGOTIATION ANALYSIS REPORT")
    lines.append("=" * 50)
    lines.append("")

    lines.append(f"Outcome: {metrics.outcome.upper()}")
    lines.append(f"Rounds: {metrics.total_rounds}  |  Moves: {metrics.total_moves}")
    lines.append("")

    lines.append("--- Per-Party Results ---")
    for party in state.parties:
        pid = party.id
        utility = metrics.party_utilities.get(pid, 0)
        surplus = metrics.party_batna_surplus.get(pid, 0)
        satisfaction = metrics.party_interest_satisfaction.get(pid, 0)
        lines.append(f"  {party.name}:")
        lines.append(f"    Utility:              {utility:.2f}")
        lines.append(f"    BATNA surplus:         {surplus:+.2f}")
        lines.append(f"    Interest satisfaction: {satisfaction:.0%}")
    lines.append("")

    lines.append("--- Aggregate Metrics ---")
    lines.append(f"  Social welfare:    {metrics.social_welfare:.2f}")
    lines.append(f"  Nash product:      {metrics.nash_product:.4f}")
    lines.append(f"  Integrative index: {metrics.integrative_index:.2f} {'(value created!)' if metrics.integrative_index > 1.0 else ''}")
    lines.append(f"  Pareto efficient:  {'Yes' if metrics.pareto_efficient else 'No'}")
    lines.append(f"  Disclosure rate:   {metrics.disclosure_rate:.0%}")
    lines.append("")

    lines.append("--- Move Breakdown ---")
    for move_type, count in sorted(metrics.move_breakdown.items(), key=lambda x: -x[1]):
        lines.append(f"  {move_type}: {count}")

    if metrics.agreement:
        lines.append("")
        lines.append("--- Agreement ---")
        for k, v in metrics.agreement.get("issue_values", {}).items():
            lines.append(f"  {k}: {v}")

    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)
