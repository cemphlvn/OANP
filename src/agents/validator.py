"""
Move Validator — structural safety layer between LLM output and state recording.

Validates every move before it enters the negotiation state:
1. Phase legality — is this move type legal in the current phase?
2. Package completeness — do proposals have packages?
3. BATNA safety — never accept a deal worse than the alternative
4. Accept requires a package to accept

If a move is invalid, the validator can correct it (e.g., convert an illegal
ACCEPT to a COUNTER) or reject it entirely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..protocol.types import (
    Move,
    MoveType,
    NegotiationState,
)
from .negotiator import get_legal_moves


@dataclass
class ValidationResult:
    valid: bool
    violations: list[str] = field(default_factory=list)
    corrected_move: Optional[Move] = None


class MoveValidator:
    """Validates moves before they enter the negotiation state."""

    def __init__(self, scorer=None):
        """
        Args:
            scorer: Optional LLMUtilityScorer for BATNA comparison.
                    If None, BATNA check is skipped (graceful degradation).
        """
        self.scorer = scorer

    async def validate(self, move: Move, state: NegotiationState) -> ValidationResult:
        violations = []

        # 1. Phase legality
        legal = get_legal_moves(state.protocol.phase)
        if legal and move.move_type not in legal:
            violations.append(
                f"{move.move_type.value} is not legal in {state.protocol.phase.value} phase. "
                f"Legal moves: {[m.value for m in legal]}"
            )

        # 2. Package completeness
        if move.move_type in (MoveType.PROPOSE, MoveType.COUNTER, MoveType.MESO):
            if not move.package:
                violations.append(f"{move.move_type.value} move must include a package")
            elif not move.package.issue_values:
                violations.append(f"{move.move_type.value} package has no issue values")

        # 3. Accept must reference a package
        if move.move_type == MoveType.ACCEPT and not move.package:
            # Find the last proposed package to accept
            for prev in reversed(state.move_history):
                if prev.package:
                    move.package = prev.package
                    break

        # 4. BATNA safety (only if scorer available)
        if move.move_type == MoveType.ACCEPT and move.package and self.scorer:
            ps = state.private_states.get(move.party_id)
            if ps and ps.batna:
                try:
                    batna_result = await self.scorer.compare_to_batna(
                        move.package, ps, state.issues
                    )
                    if not batna_result.deal_is_better:
                        violations.append(
                            "Accepting a deal worse than BATNA — converting to REJECT"
                        )
                        # Auto-correct: convert unsafe ACCEPT to REJECT
                        corrected = Move(
                            party_id=move.party_id,
                            move_type=MoveType.REJECT,
                            package=move.package,
                            reasoning="Rejected by validator: deal is worse than BATNA",
                        )
                        return ValidationResult(
                            valid=False,
                            violations=violations,
                            corrected_move=corrected,
                        )
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Scorer failed during BATNA check for %s — skipping", move.party_id
                    )

        if violations:
            return ValidationResult(valid=False, violations=violations)

        return ValidationResult(valid=True)
