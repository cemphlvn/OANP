"""
LLM-based Utility Scorer — evaluates how well a deal satisfies a party's interests.

This is the core measurement instrument for OANP. Without accurate utility scores,
metrics (Pareto efficiency, Nash product, integrative index) are meaningless.

Architecture:
1. ANCHOR GENERATION (once, at scenario setup):
   LLM reads the scenario and generates SatisfactionAnchors per interest.
   These are concrete reference points ("if salary >= $160K → 0.9 satisfaction").
   Anchors are visible in the UI and editable by users.

2. SCORING (per package evaluation):
   LLM scores each interest using the anchors as grounding context.
   Reasoning comes BEFORE scores (causal influence on calibration).
   Overall score is computed programmatically from per-interest scores + priorities.

3. BATNA COMPARISON (pairwise, not dual absolute):
   Direct "is this deal better than the BATNA?" per interest.
   Avoids fragile dual-absolute-score approach.

Research grounding:
- LLM-as-judge: Zheng et al. 2023, >80% human agreement
- Decomposed scoring: DeCE (EMNLP 2025), r=0.78 vs r=0.35 holistic
- Reasoning-before-score: Cameron Wolfe LLM-as-Judge survey
- Pairwise > dual-absolute for comparison: COLM 2025
- LLM utility elicitation: DeLLMa (ICLR 2025 Spotlight)
"""

from __future__ import annotations

import asyncio
import logging
import statistics
from dataclasses import dataclass
from typing import Callable, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, field_validator

from ..protocol.types import (
    Interest,
    Issue,
    OptionPackage,
    PrivatePartyState,
    SatisfactionAnchor,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response schemas for structured output
# ---------------------------------------------------------------------------

class InterestScore(BaseModel):
    """Score for a single interest. Reasoning fields come BEFORE the score —
    LLMs generate left-to-right, so reasoning causally influences the number."""
    interest_description: str = Field(description="Which interest this scores")
    what_the_deal_offers: str = Field(
        description="What specifically does the proposed deal offer for this interest?"
    )
    comparison_to_anchors: str = Field(
        description="How does the deal compare to the satisfaction anchors for this interest? "
        "Reference specific anchor conditions and scores."
    )
    satisfaction: float = Field(
        description="Score 0.0-1.0 based on the above analysis"
    )

    @field_validator("satisfaction")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class ScorerResponse(BaseModel):
    """LLM's evaluation of how well a deal satisfies a party's interests."""
    per_interest_scores: list[InterestScore] = Field(
        description="Score for each interest, with reasoning before scores"
    )


class InterestComparison(BaseModel):
    """Pairwise comparison of deal vs BATNA for one interest."""
    interest: str
    deal_assessment: str = Field(description="How the proposed deal serves this interest")
    batna_assessment: str = Field(description="How the BATNA serves this interest")
    winner: str = Field(description="'deal', 'batna', or 'tie'")
    magnitude: str = Field(description="'slight', 'moderate', or 'significant'")


class BATNAComparisonResponse(BaseModel):
    """Pairwise comparison — avoids fragile dual-absolute-score approach."""
    per_interest_comparison: list[InterestComparison] = Field(
        description="For each interest, which option better serves it"
    )
    overall_reasoning: str = Field(
        description="Synthesize the per-interest comparisons into an overall assessment"
    )
    deal_is_better: bool = Field(
        description="True if the deal is at least as good as the BATNA overall"
    )
    confidence: float = Field(
        description="How confident in this comparison? 0.5=coin flip, 1.0=certain"
    )

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


# -- Anchor generation schema (per-interest, not all-at-once) --

class AnchorPoint(BaseModel):
    condition: str = Field(
        description="A concrete, verifiable condition referencing issue values. "
        "E.g. 'base_salary >= 160000 AND equity = performance_based'"
    )
    score: float = Field(
        description="Satisfaction score (0.0-1.0) if this condition is met"
    )
    reason: str = Field(description="Why this condition maps to this score")

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class SingleInterestAnchors(BaseModel):
    """Anchors for a single interest — small, focused output."""
    anchors: list[AnchorPoint] = Field(
        description="4-6 satisfaction anchors spanning the full 0.0-1.0 range"
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

ANCHOR_GENERATION_PROMPT = """You are designing a utility function for a negotiation party.

Given a party's interests and the available issues with their ranges/options, generate
concrete SATISFACTION ANCHORS for each interest. These anchors define "what does a good,
mediocre, and bad deal look like for this interest?"

For each interest, produce 4-6 anchors spanning the full 0.0-1.0 range:
- At least one anchor near 0.0 (terrible outcome for this interest)
- At least one anchor near 0.3-0.4 (poor but not catastrophic)
- At least one anchor near 0.6-0.7 (acceptable, fair middle ground)
- At least one anchor near 0.9-1.0 (excellent outcome)

RULES:
- Conditions MUST reference specific issue values from the available issues.
- Use concrete comparisons: ">= 150000", "= full_remote", "before 2026-05-01"
- For interests that span multiple issues, combine conditions with AND/OR.
- Scores must reflect the PARTY'S perspective, not an objective view.
- Consider the issue ranges — a salary of $150K means different things in a
  $120K-$180K range vs a $100K-$300K range.
- Consider interactions between issues (e.g., lower salary + equity can still
  score high on "financial security" if equity is substantial)."""

SCORER_SYSTEM_PROMPT = """You are an objective evaluator assessing how well a proposed deal \
satisfies a party's interests in a negotiation.

You are NOT a participant. You are a neutral judge.

Score each interest on a 0.0-1.0 scale using the provided SATISFACTION ANCHORS as your \
reference points. The anchors define what good, mediocre, and bad outcomes look like for \
each interest — interpolate between them based on the actual deal terms.

Scale:
- 0.0 = completely ignores or contradicts this interest
- 0.2 = token gesture, falls far short of what the party needs
- 0.4 = partially addresses with significant gaps
- 0.6 = reasonably addresses, acceptable middle ground
- 0.8 = strongly serves this interest, close to ideal with minor compromises
- 1.0 = perfectly satisfies, couldn't realistically ask for more

CALIBRATION RULES:
- Compare proposed values to the FULL RANGE of what's possible, not just what was asked.
- A score of 0.5 means genuinely neutral — not a default for uncertainty.
- If all your scores cluster 0.5-0.7, you're not differentiating enough.
- Reference the satisfaction anchors explicitly in your reasoning.
- Consider cross-issue interactions: a package is more than the sum of its parts."""

BATNA_COMPARISON_PROMPT = """You are comparing two options for a negotiation party.
Your ONLY job is to determine which option better serves this party's interests.

Option A: The proposed deal
Option B: The party's BATNA (best alternative to negotiated agreement)

For each interest, determine which option serves it better and by how much.
Then make an overall determination.

IMPORTANT:
- Focus on concrete outcomes, not abstract preferences.
- Compare specific values, terms, and consequences.
- The BATNA often has uncertainty (e.g., "go to trial — 60% chance of winning").
  Factor in that uncertainty — a certain moderate outcome may beat a risky good one.
- Reference the satisfaction anchors to ground your comparison."""


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class UtilityScore:
    """Result of scoring a package against a party's interests."""
    overall: float
    per_interest: dict[str, float]  # interest description -> score
    reasoning: str
    confidence: Optional[float] = None  # set when using multi-sample mode

    @property
    def per_interest_summary(self) -> str:
        return "\n".join(f"  {k}: {v:.2f}" for k, v in self.per_interest.items())


@dataclass
class BATNAResult:
    """Result of comparing a deal against a BATNA."""
    deal_is_better: bool
    confidence: float
    per_interest: dict[str, str]  # interest -> "deal" | "batna" | "tie"
    reasoning: str


# ---------------------------------------------------------------------------
# Priority weights for programmatic aggregation
# ---------------------------------------------------------------------------

# Interest.priority is a 0-1 float. We use it directly as the weight.
# This is more reliable than asking the LLM to aggregate.


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

class LLMUtilityScorer:
    """Scores how well a deal satisfies a party's interests using LLM judgment.

    Two-phase architecture:
    1. generate_anchors() — run once at setup, produces SatisfactionAnchors per interest
    2. score() / compare_to_batna() — run per evaluation, uses anchors as grounding
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm.with_config({"temperature": 0})

    # -- Phase 1: Anchor generation ------------------------------------------

    async def generate_anchors(
        self,
        party_state: PrivatePartyState,
        issues: list[Issue],
        on_progress: "Callable[[Interest, list[SatisfactionAnchor]], None] | None" = None,
    ) -> list[Interest]:
        """Generate satisfaction anchors for each interest in parallel.

        Each interest gets its own focused LLM call — small output, never hits
        token limits, and parallelizes across interests for speed.

        Args:
            on_progress: Optional async callback(interest, anchors) called as
                each interest completes. Enables streaming progress to UI.

        Returns updated interests with anchors populated.
        These are visible in the UI and editable by users.
        """
        issues_text = "\n".join(
            f"- {iss.name} (id: {iss.id}, type: {iss.issue_type})"
            + (f" range: {iss.range}" if iss.range else f" options: {', '.join(iss.options)}")
            for iss in issues
        )

        batna_text = ""
        if party_state.batna:
            batna_text = (
                f"\nParty's BATNA: {party_state.batna.description}\n"
                + "\n".join(
                    f"- {k}: {v}" for k, v in party_state.batna.components.items()
                )
            )

        structured_llm = self.llm.with_structured_output(SingleInterestAnchors)

        async def _gen_one(interest: Interest) -> Interest:
            response: SingleInterestAnchors = await structured_llm.ainvoke([
                SystemMessage(content=ANCHOR_GENERATION_PROMPT),
                HumanMessage(content=f"""## Interest to Anchor
[{interest.interest_type.value.upper()}] {interest.description}
Priority: {interest.priority}
Related issues: {', '.join(interest.related_issues)}

## Available Issues and Ranges
{issues_text}
{batna_text}

Generate 4-6 satisfaction anchors for this ONE interest."""),
            ])
            anchors = [
                SatisfactionAnchor(
                    condition=a.condition,
                    score=a.score,
                    reason=a.reason,
                )
                for a in response.anchors
            ]
            updated = interest.model_copy(update={"satisfaction_anchors": anchors})
            if on_progress:
                result = on_progress(updated, anchors)
                if asyncio.iscoroutine(result):
                    await result
            return updated

        # Fire all interest anchor generations in parallel
        tasks = [_gen_one(interest) for interest in party_state.interests]
        return await asyncio.gather(*tasks)

    # -- Phase 2: Scoring ---------------------------------------------------

    async def score(
        self,
        package: OptionPackage,
        party_state: PrivatePartyState,
        issues: list[Issue],
    ) -> UtilityScore:
        """Score a package against a party's interests. Returns 0.0-1.0.

        Uses satisfaction anchors as grounding if available. Falls back to
        pure LLM judgment if no anchors exist (still works, just less grounded).
        """
        interests_text = self._format_interests_with_anchors(party_state.interests)

        issues_text = "\n".join(
            f"- {iss.name} (id: {iss.id}, type: {iss.issue_type})"
            + (f" range: {iss.range}" if iss.range else f" options: {', '.join(iss.options)}")
            for iss in issues
        )

        package_text = "\n".join(
            f"- {k}: {v}" for k, v in package.issue_values.items()
        )

        structured_llm = self.llm.with_structured_output(ScorerResponse)

        response: ScorerResponse = await structured_llm.ainvoke([
            SystemMessage(content=SCORER_SYSTEM_PROMPT),
            HumanMessage(content=f"""## Party's Interests and Satisfaction Anchors
{interests_text}

## Available Issues and Ranges
{issues_text}

## Proposed Deal
{package_text}

Score each interest. Reference the satisfaction anchors in your reasoning."""),
        ])

        per_interest = {
            s.interest_description: s.satisfaction
            for s in response.per_interest_scores
        }

        overall = self._compute_overall(per_interest, party_state.interests)

        # Build reasoning from per-interest analysis
        reasoning_parts = []
        for s in response.per_interest_scores:
            reasoning_parts.append(
                f"[{s.interest_description}] ({s.satisfaction:.2f}): "
                f"{s.comparison_to_anchors}"
            )

        return UtilityScore(
            overall=overall,
            per_interest=per_interest,
            reasoning="\n".join(reasoning_parts),
        )

    async def score_with_confidence(
        self,
        package: OptionPackage,
        party_state: PrivatePartyState,
        issues: list[Issue],
        n_samples: int = 3,
    ) -> UtilityScore:
        """Multi-sample scoring for high-stakes decisions.

        Runs n_samples parallel calls at T=0.3, aggregates via mean,
        and reports confidence based on variance.
        """
        scorer_llm = self.llm.with_config({"temperature": 0.3})

        # Create a temporary scorer instance to avoid mutating self.llm (thread-safety)
        temp_scorer = LLMUtilityScorer.__new__(LLMUtilityScorer)
        temp_scorer.llm = scorer_llm

        tasks = [
            temp_scorer.score(package, party_state, issues)
            for _ in range(n_samples)
        ]
        results: list[UtilityScore] = await asyncio.gather(*tasks)

        # Aggregate per-interest scores via mean
        all_keys = set()
        for r in results:
            all_keys.update(r.per_interest.keys())

        per_interest = {}
        for key in all_keys:
            scores = [r.per_interest[key] for r in results if key in r.per_interest]
            per_interest[key] = statistics.mean(scores) if scores else 0.5

        overall = self._compute_overall(per_interest, party_state.interests)

        # Confidence from variance — low variance = high confidence
        overall_scores = [r.overall for r in results]
        variance = statistics.variance(overall_scores) if len(overall_scores) > 1 else 0
        confidence = max(0.0, 1.0 - (variance * 10))  # var of 0.1 → confidence 0.0

        if variance > 0.04:
            logger.warning(
                "High variance in multi-sample scores: %s (var=%.3f)",
                overall_scores, variance,
            )

        # Use reasoning from the sample closest to the mean
        closest = min(results, key=lambda r: abs(r.overall - overall))

        return UtilityScore(
            overall=overall,
            per_interest=per_interest,
            reasoning=closest.reasoning,
            confidence=confidence,
        )

    # -- BATNA comparison ---------------------------------------------------

    async def compare_to_batna(
        self,
        package: OptionPackage,
        party_state: PrivatePartyState,
        issues: list[Issue],
    ) -> BATNAResult:
        """Pairwise comparison: is the deal better than the BATNA?

        Uses direct per-interest comparison instead of fragile dual absolute scores.
        """
        if not party_state.batna:
            return BATNAResult(
                deal_is_better=True,
                confidence=1.0,
                per_interest={},
                reasoning="No BATNA defined — any deal is acceptable.",
            )

        interests_text = self._format_interests_with_anchors(party_state.interests)

        package_text = "\n".join(
            f"- {k}: {v}" for k, v in package.issue_values.items()
        )

        batna_text = (
            f"{party_state.batna.description}\n"
            + "\n".join(
                f"- {k}: {v}" for k, v in party_state.batna.components.items()
            )
        )

        structured_llm = self.llm.with_structured_output(BATNAComparisonResponse)

        response: BATNAComparisonResponse = await structured_llm.ainvoke([
            SystemMessage(content=BATNA_COMPARISON_PROMPT),
            HumanMessage(content=f"""## Party's Interests and Satisfaction Anchors
{interests_text}

## Option A: Proposed Deal
{package_text}

## Option B: BATNA
{batna_text}

Compare per interest, then give an overall determination."""),
        ])

        per_interest = {
            c.interest: c.winner
            for c in response.per_interest_comparison
        }

        return BATNAResult(
            deal_is_better=response.deal_is_better,
            confidence=response.confidence,
            per_interest=per_interest,
            reasoning=response.overall_reasoning,
        )

    # -- Internal helpers ---------------------------------------------------

    def _format_interests_with_anchors(self, interests: list[Interest]) -> str:
        """Format interests with their satisfaction anchors for prompts."""
        parts = []
        for i in interests:
            lines = [
                f"### [{i.interest_type.value.upper()}] {i.description}",
                f"Priority: {i.priority}",
                f"Related issues: {', '.join(i.related_issues)}",
            ]
            if i.satisfaction_anchors:
                lines.append("Satisfaction anchors:")
                for a in sorted(i.satisfaction_anchors, key=lambda x: x.score):
                    lines.append(f"  - {a.score:.1f} | {a.condition} — {a.reason}")
            else:
                lines.append("(No anchors — score based on issue ranges and deal terms)")
            parts.append("\n".join(lines))
        return "\n\n".join(parts)

    @staticmethod
    def _compute_overall(
        per_interest: dict[str, float],
        interests: list[Interest],
    ) -> float:
        """Weighted average using interest priorities. Deterministic, auditable."""
        total_weight = 0.0
        weighted_sum = 0.0

        for interest in interests:
            score = per_interest.get(interest.description, 0.5)
            weight = interest.priority  # 0.0 - 1.0 float, used directly
            weighted_sum += score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.5
