"""
OANP Compliance Engine — legal compliance checking for advanced negotiation mode.

Enforces institutional rules, deadlines, escalation policies, and due process
requirements. Generates enforceable award records and compliance checklists.

Inspired by:
- UNCITRAL Expedited Arbitration Rules 2021 (time-boxing)
- UNCITRAL ODR Technical Notes 2016/2017 (three-stage escalation)
- New York Convention Art. IV-V (award enforceability)
- Singapore Convention on Mediation Art. 4-5 (settlement enforceability)
- IBA Guidelines on Conflicts of Interest 2024 (due process)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from .types import (
    AwardRecord,
    AwardType,
    ComplianceMetadata,
    EscalationPolicy,
    EscalationTier,
    NegotiationMode,
    NegotiationState,
)


class ComplianceEngine:
    """Enforces institutional rules and tracks legal compliance."""

    def __init__(self, compliance: ComplianceMetadata):
        self.compliance = compliance
        self.profile: Optional[dict] = None

        # Load institution profile if available
        if compliance.institution and compliance.institution.framework.value != "none":
            try:
                from .institutions import load_profile
                self.profile = load_profile(compliance.institution.framework.value)
            except FileNotFoundError:
                pass

    @property
    def is_advanced(self) -> bool:
        return self.compliance.mode == NegotiationMode.ADVANCED

    # -----------------------------------------------------------------------
    # Deadline enforcement
    # -----------------------------------------------------------------------

    def check_phase_deadline(self, state: NegotiationState) -> Optional[str]:
        """Check if the current phase has exceeded its round limit.

        Returns a reason string if deadline exceeded, None otherwise.
        """
        if not self.compliance.deadlines:
            return None

        phase = state.protocol.phase.value
        limits = self.compliance.deadlines.phase_max_rounds
        phase_round = state.protocol.round

        if phase in limits and phase_round >= limits[phase]:
            return f"Phase '{phase}' exceeded round limit ({phase_round}/{limits[phase]})"

        return None

    def check_hard_deadline(self, state: NegotiationState) -> Optional[str]:
        """Check if the global round limit has been reached.

        Returns a reason string if deadline exceeded, None otherwise.
        """
        if not self.compliance.deadlines:
            return None

        hard_limit = self.compliance.deadlines.hard_deadline_rounds
        if hard_limit and state.protocol.total_rounds >= hard_limit:
            return f"Hard deadline reached ({state.protocol.total_rounds}/{hard_limit} rounds)"

        return None

    def check_stagnation(self, state: NegotiationState) -> bool:
        """Detect convergence stagnation over the configured window.

        Returns True if negotiation appears stagnant (no convergence improvement).
        Checks if the last N rounds contain only REJECT/COUNTER moves with no progress.
        """
        if not self.compliance.deadlines:
            return False

        window = self.compliance.deadlines.stagnation_window
        if len(state.move_history) < window * 2:  # Need enough moves to judge
            return False

        # Check recent moves for stagnation signals
        recent = state.move_history[-(window * len(state.parties)):]
        stagnation_types = {"reject", "counter"}
        stagnation_count = sum(
            1 for m in recent if m.move_type.value in stagnation_types
        )

        # If >80% of recent moves are reject/counter, it's stagnating
        return stagnation_count / len(recent) > 0.8 if recent else False

    # -----------------------------------------------------------------------
    # Escalation
    # -----------------------------------------------------------------------

    def should_escalate(self, state: NegotiationState) -> Optional[EscalationTier]:
        """Determine if escalation to the next tier should occur.

        Returns the next tier if escalation conditions are met, None otherwise.
        """
        escalation = self.compliance.escalation
        if not escalation or not escalation.auto_escalate:
            return None

        current_tier = self.compliance.current_tier
        tiers = escalation.tiers
        current_idx = tiers.index(current_tier) if current_tier in tiers else 0

        # Already at the last tier
        if current_idx >= len(tiers) - 1:
            return None

        # Check tier-specific deadline
        tier_round_limit = self._get_tier_round_limit(current_tier)
        tier_rounds = self._rounds_in_current_tier(state)

        deadline_exceeded = tier_round_limit and tier_rounds >= tier_round_limit
        stagnation = self.check_stagnation(state)

        if deadline_exceeded or stagnation:
            return tiers[current_idx + 1]

        return None

    def execute_escalation(self, state: NegotiationState, next_tier: EscalationTier) -> None:
        """Record the escalation in compliance metadata."""
        self.compliance.tier_history.append({
            "from_tier": self.compliance.current_tier.value,
            "to_tier": next_tier.value,
            "at_round": state.protocol.total_rounds,
            "reason": "deadline_or_stagnation",
        })
        self.compliance.current_tier = next_tier

        # Log due process event
        self._log_due_process(state, "escalation", detail=f"Escalated to {next_tier.value}")

    def _get_tier_round_limit(self, tier: EscalationTier) -> Optional[int]:
        escalation = self.compliance.escalation
        if not escalation:
            return None
        limits = {
            EscalationTier.NEGOTIATION: escalation.negotiation_deadline_rounds,
            EscalationTier.MEDIATION: escalation.mediation_deadline_rounds,
            EscalationTier.ARBITRATION: escalation.arbitration_deadline_rounds,
        }
        return limits.get(tier)

    def _rounds_in_current_tier(self, state: NegotiationState) -> int:
        """Count rounds since entering the current tier."""
        tier_history = self.compliance.tier_history
        if not tier_history:
            return state.protocol.total_rounds

        last_entry = tier_history[-1]
        return state.protocol.total_rounds - last_entry.get("at_round", 0)

    # -----------------------------------------------------------------------
    # Due process tracking
    # -----------------------------------------------------------------------

    def validate_due_process(self, state: NegotiationState) -> list[str]:
        """Check for due process violations. Returns list of violation descriptions."""
        violations = []

        if not state.parties:
            return violations

        # Equal treatment: each party should have roughly equal move counts
        party_moves = {}
        for m in state.move_history:
            party_moves[m.party_id] = party_moves.get(m.party_id, 0) + 1

        if len(party_moves) >= 2:
            counts = list(party_moves.values())
            max_count = max(counts)
            min_count = min(counts)
            if max_count > 0 and (max_count - min_count) / max_count > 0.4:
                violations.append(
                    f"Unequal participation: move counts {party_moves} "
                    f"(max disparity {max_count - min_count})"
                )

        # Right to be heard: check if any party has been silent for too many rounds
        if self.compliance.deadlines:
            timeout = self.compliance.deadlines.non_participation_timeout_rounds
            if timeout and len(state.move_history) > timeout * len(state.parties):
                recent = state.move_history[-(timeout * len(state.parties)):]
                active_parties = {m.party_id for m in recent}
                all_parties = {p.id for p in state.parties}
                silent = all_parties - active_parties
                if silent:
                    violations.append(
                        f"Non-participation detected: parties {silent} "
                        f"silent for {timeout}+ rounds"
                    )

        return violations

    def log_move_due_process(self, state: NegotiationState, party_id: str, move_type: str) -> None:
        """Log a due process event for a move."""
        self._log_due_process(
            state, "move",
            party_id=party_id,
            detail=f"{party_id} made {move_type} move"
        )

    def _log_due_process(
        self, state: NegotiationState,
        event: str, party_id: Optional[str] = None, detail: str = ""
    ) -> None:
        self.compliance.due_process_log.append({
            "event": event,
            "party_id": party_id,
            "round": state.protocol.total_rounds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        })

    # -----------------------------------------------------------------------
    # Award generation
    # -----------------------------------------------------------------------

    def generate_award(
        self,
        state: NegotiationState,
        award_type: AwardType = AwardType.CONSENT_AWARD,
        reasons: str = "",
    ) -> AwardRecord:
        """Generate a compliant award record from the negotiation outcome.

        Satisfies:
        - New York Convention Art. IV (writing, signatures, date, seat, reasons)
        - UNCITRAL Model Law Art. 31 (form requirements)
        - Singapore Convention Art. 4 (mediation evidence, if applicable)
        """
        # Extract terms from agreement
        terms = {}
        if state.agreement and state.agreement.issue_values:
            terms = state.agreement.issue_values

        # Build party records
        party_records = []
        for party in state.parties:
            party_records.append({
                "party_id": party.id,
                "name": party.name,
                "role": party.role,
                "authorized_by": "agent_delegation",
            })

        # Electronic signatures (all accepting parties)
        signatures = []
        for pid in state.protocol.accepted_by:
            signatures.append({
                "party_id": pid,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": "oanp_protocol_accept",
            })

        # Seat and governing law from institution config
        seat = None
        governing_law = None
        institution_name = None
        compliance_framework = None
        if self.compliance.institution:
            seat = self.compliance.institution.seat
            governing_law = self.compliance.institution.governing_law
            institution_name = self.compliance.institution.framework.value
            compliance_framework = institution_name

        # Mediator attestation (Singapore Convention Art 4)
        mediator_attestation = None
        if state.mediator and self.compliance.current_tier in (
            EscalationTier.MEDIATION, EscalationTier.NEGOTIATION
        ):
            mediator_attestation = {
                "mediator_type": "ai_agent",
                "mediator_mode": state.mediator.config.mode.value,
                "mediation_commenced": state.created_at.isoformat(),
                "mediation_concluded": datetime.now(timezone.utc).isoformat(),
                "process_description": (
                    "AI-mediated negotiation under OANP protocol using "
                    f"{state.mediator.config.mode.value} mediation mode"
                ),
                "institution": institution_name,
            }

        # Integrity hashes
        terms_hash = hashlib.sha256(
            json.dumps(terms, sort_keys=True).encode()
        ).hexdigest()

        moves_data = [
            {"id": m.id, "party": m.party_id, "type": m.move_type.value, "round": m.round}
            for m in state.move_history
        ]
        audit_hash = hashlib.sha256(
            json.dumps(moves_data, sort_keys=True).encode()
        ).hexdigest()

        return AwardRecord(
            award_type=award_type,
            seat=seat,
            governing_law=governing_law,
            institution=institution_name,
            parties=party_records,
            terms=terms,
            reasons=reasons or self._generate_reasons(state),
            compliance_framework=compliance_framework,
            electronic_signatures=signatures,
            mediator_attestation=mediator_attestation,
            integrity_hash=terms_hash,
            audit_trail_hash=audit_hash,
        )

    def _generate_reasons(self, state: NegotiationState) -> str:
        """Generate basic reasoning for the award based on negotiation history."""
        parts = []
        parts.append(f"Negotiation conducted under OANP protocol v0.1.")
        parts.append(f"Total rounds: {state.protocol.total_rounds}.")
        parts.append(f"Total moves: {state.protocol.total_moves}.")
        parts.append(f"Phases visited: {[h.get('phase', '') for h in state.protocol.phase_history]}.")

        if state.mediator:
            parts.append(f"Mediation mode: {state.mediator.config.mode.value}.")

        if self.compliance.institution:
            parts.append(
                f"Institutional rules: {self.compliance.institution.framework.value} "
                f"({self.compliance.institution.procedure} procedure)."
            )

        if self.compliance.tier_history:
            parts.append(f"Escalation history: {len(self.compliance.tier_history)} tier transitions.")

        due_process_violations = self.validate_due_process(state)
        if not due_process_violations:
            parts.append("No due process violations detected.")
        else:
            parts.append(f"Due process notes: {'; '.join(due_process_violations)}")

        return " ".join(parts)

    # -----------------------------------------------------------------------
    # Checklists
    # -----------------------------------------------------------------------

    def get_pre_negotiation_checklist(self) -> list[dict[str, Any]]:
        """Pre-negotiation compliance checklist."""
        items = [
            {"item": "Parties identified and authorized", "category": "parties", "required": True},
            {"item": "Issues defined with options/ranges", "category": "issues", "required": True},
            {"item": "BATNAs established for all parties", "category": "batna", "required": True},
            {"item": "Interests documented per party", "category": "interests", "required": True},
        ]

        if self.is_advanced:
            items.extend([
                {"item": "Institutional rules selected", "category": "institution", "required": True},
                {"item": "Governing law specified", "category": "jurisdiction", "required": True},
                {"item": "Seat of arbitration designated", "category": "jurisdiction", "required": True},
                {"item": "Procedural language agreed", "category": "jurisdiction", "required": False},
                {"item": "Escalation policy configured", "category": "escalation", "required": True},
                {"item": "Deadline limits set", "category": "deadlines", "required": True},
                {"item": "Document standard selected (IBA/Prague)", "category": "documents", "required": False},
            ])

        return items

    def get_during_negotiation_checklist(self, state: NegotiationState) -> list[dict[str, Any]]:
        """During-negotiation compliance checklist with current status."""
        items = [
            {
                "item": "Equal participation maintained",
                "status": len(self.validate_due_process(state)) == 0,
                "category": "due_process",
            },
            {
                "item": "Phase deadline compliance",
                "status": self.check_phase_deadline(state) is None,
                "category": "deadlines",
            },
            {
                "item": "Global deadline compliance",
                "status": self.check_hard_deadline(state) is None,
                "category": "deadlines",
            },
        ]

        if self.is_advanced and self.compliance.escalation:
            items.append({
                "item": f"Current tier: {self.compliance.current_tier.value}",
                "status": True,
                "category": "escalation",
            })

        return items

    def get_award_checklist(self) -> list[dict[str, Any]]:
        """Award/settlement compliance checklist (NYC Art IV, Model Law Art 31)."""
        items = [
            {"item": "Award in writing", "article": "NYC Art. IV(1)(a) / ML Art. 31(1)", "required": True},
            {"item": "Signed by arbitrator(s) / parties", "article": "ML Art. 31(1)", "required": True},
            {"item": "Reasons stated", "article": "ML Art. 31(2)", "required": True},
            {"item": "Date stated", "article": "ML Art. 31(3)", "required": True},
            {"item": "Seat of arbitration stated", "article": "ML Art. 31(3)", "required": True},
            {"item": "Copy delivered to each party", "article": "ML Art. 31(4)", "required": True},
            {"item": "Integrity hash generated", "article": "Best practice", "required": True},
            {"item": "Audit trail preserved", "article": "Best practice", "required": True},
        ]

        # Singapore Convention items (if mediation was used)
        if self.compliance.current_tier == EscalationTier.MEDIATION or (
            self.compliance.tier_history and
            any(t.get("to_tier") == "mediation" for t in self.compliance.tier_history)
        ):
            items.extend([
                {"item": "Settlement agreement signed by parties", "article": "SC Art. 4(1)(a)", "required": True},
                {"item": "Evidence of mediation provided", "article": "SC Art. 4(1)(b)", "required": True},
                {"item": "Mediator attestation included", "article": "SC Art. 4(1)(b)(ii)", "required": True},
            ])

        return items
