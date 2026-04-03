"""
StateView — enforces information boundaries structurally.

Instead of relying on prompts to tell agents "you can't see this,"
StateView produces filtered views of NegotiationState that make
information leakage structurally impossible.
"""

from __future__ import annotations

from .types import (
    MediatorKnowledge,
    NegotiationState,
)


class StateView:
    """Produces scoped views of NegotiationState for different actors."""

    @staticmethod
    def for_party(state: NegotiationState, party_id: str) -> dict:
        """What a party agent can see: shared state + own private state only."""
        ps = state.private_states.get(party_id)
        return {
            "parties": [{"id": p.id, "name": p.name, "role": p.role} for p in state.parties],
            "issues": [i.model_dump() for i in state.issues],
            "criteria": [c.model_dump() for c in state.criteria],
            "constraints": [c.model_dump() for c in state.constraints],
            "protocol": {
                "phase": state.protocol.phase.value,
                "round": state.protocol.round,
                "total_rounds": state.protocol.total_rounds,
            },
            # Move history is public but strip other parties' reasoning
            "move_history": [
                {
                    **m.model_dump(mode="json"),
                    "reasoning": m.reasoning if m.party_id == party_id else None,
                }
                for m in state.move_history
            ],
            # Only own private state
            "my_state": ps.model_dump() if ps else None,
        }

    @staticmethod
    def for_mediator(state: NegotiationState) -> dict:
        """What the mediator can see — depends on knowledge level config."""
        if not state.mediator:
            return StateView.for_frontend(state)

        knowledge = state.mediator.config.knowledge
        base = {
            "parties": [{"id": p.id, "name": p.name, "role": p.role} for p in state.parties],
            "issues": [i.model_dump() for i in state.issues],
            "criteria": [c.model_dump() for c in state.criteria],
            "protocol": {
                "phase": state.protocol.phase.value,
                "round": state.protocol.round,
                "total_rounds": state.protocol.total_rounds,
            },
            "move_history": [
                {**m.model_dump(mode="json"), "reasoning": None}
                for m in state.move_history
            ],
        }

        if knowledge == MediatorKnowledge.BLIND:
            # Only shared state — no private info at all
            pass

        elif knowledge == MediatorKnowledge.CAUCUS_ONLY:
            # Only disclosed interests
            disclosed = {}
            for party in state.parties:
                ps = state.private_states.get(party.id)
                if ps:
                    disclosed[party.id] = [
                        i.model_dump() for i in ps.interests if i.disclosed
                    ]
            base["disclosed_interests"] = disclosed
            base["caucus_notes"] = state.mediator.caucus_notes

        elif knowledge == MediatorKnowledge.OMNISCIENT:
            # Everything — for research only
            base["private_states"] = {
                pid: ps.model_dump() for pid, ps in state.private_states.items()
            }

        return base

    @staticmethod
    def for_frontend(state: NegotiationState, viewer_party_id: str | None = None) -> dict:
        """What the UI displays. Strips all private reasoning."""
        moves = []
        for m in state.move_history:
            d = m.model_dump(mode="json")
            d.pop("reasoning", None)
            moves.append(d)

        result = {
            "session_id": state.id,
            "parties": [{"id": p.id, "name": p.name, "role": p.role} for p in state.parties],
            "issues": [i.model_dump() for i in state.issues],
            "criteria": [c.model_dump() for c in state.criteria],
            "protocol": {
                "phase": state.protocol.phase.value,
                "round": state.protocol.round,
                "total_rounds": state.protocol.total_rounds,
                "total_moves": state.protocol.total_moves,
                "phase_round_limits": state.protocol.phase_round_limits,
                "escalation_tier": state.protocol.escalation_tier,
            },
            "move_history": moves,
            "outcome": state.outcome,
            "agreement": state.agreement.model_dump() if state.agreement else None,
        }

        # Compliance metadata (advanced mode)
        if state.compliance:
            c = state.compliance
            result["compliance"] = {
                "mode": c.mode.value,
                "current_tier": c.current_tier.value,
                "tier_history": c.tier_history,
                "due_process_log": c.due_process_log,
                "institution": c.institution.model_dump(mode="json") if c.institution else None,
                "escalation": c.escalation.model_dump(mode="json") if c.escalation else None,
                "deadlines": c.deadlines.model_dump(mode="json") if c.deadlines else None,
            }
        else:
            result["compliance"] = None

        # Award record (generated at settlement/arbitration)
        result["award"] = state.award.model_dump(mode="json") if state.award else None

        return result
