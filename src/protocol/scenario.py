"""
Scenario loader — parses YAML scenario files into NegotiationState.

This is the quickstart entry point:
  oanp simulate --scenario salary-negotiation
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .types import (
    BATNA,
    Architecture,
    ComplianceFramework,
    ComplianceMetadata,
    Constraint,
    DeadlineConfig,
    DocumentStandard,
    EscalationPolicy,
    EscalationTier,
    InstitutionConfig,
    Interest,
    InterestType,
    Issue,
    MediatorConfig,
    MediatorIntervention,
    MediatorKnowledge,
    MediatorMode,
    MediatorState,
    NegotiationMode,
    NegotiationState,
    ObjectiveCriterion,
    Party,
    PrivatePartyState,
    ProtocolState,
    StrategyState,
)


def load_scenario(path: str | Path) -> NegotiationState:
    """Load a YAML scenario file and return a fully initialized NegotiationState."""
    with open(path) as f:
        raw: dict[str, Any] = yaml.safe_load(f)
    return load_scenario_from_dict(raw)


def load_scenario_from_dict(raw: dict[str, Any]) -> NegotiationState:
    """Build a NegotiationState from a scenario dict (YAML-parsed or generated)."""

    # Build parties and private states
    parties: list[Party] = []
    private_states: dict[str, PrivatePartyState] = {}

    for p in raw.get("parties", []):
        party = Party(
            id=p["id"],
            name=p["name"],
            role=p["role"],
            agent_model=p.get("agent_model"),
            is_human=p.get("is_human", False),
        )
        parties.append(party)

        # Build interests
        interests = []
        for i in p.get("interests", []):
            interests.append(
                Interest(
                    description=i["description"],
                    interest_type=InterestType(i.get("type", "desire")),
                    priority=i.get("priority", 0.5),
                    related_issues=i.get("related_issues", []),
                )
            )

        # Build BATNA
        batna = None
        if "batna" in p:
            b = p["batna"]
            batna = BATNA(
                description=b["description"],
                utility=b["utility"],
                confidence=b.get("confidence", 0.5),
                components=b.get("components", {}),
            )

        private_states[party.id] = PrivatePartyState(
            party_id=party.id,
            interests=interests,
            batna=batna,
            strategy=StrategyState(
                disclosure_policy=raw.get("protocol", {}).get("disclosure_policy", "gradual")
            ),
        )

    # Build issues
    issues = []
    for iss in raw.get("issues", []):
        issues.append(
            Issue(
                id=iss["id"],
                name=iss["name"],
                description=iss.get("description", ""),
                issue_type=iss.get("type", "categorical"),
                options=iss.get("options", []),
                range=iss.get("range"),
                is_divisible=iss.get("divisible", False),
            )
        )

    # Build criteria
    criteria = []
    for c in raw.get("criteria", []):
        criteria.append(
            ObjectiveCriterion(
                name=c["name"],
                source=c.get("source", "market_data"),
                applies_to=c.get("applies_to", []),
                reference_value=c.get("reference_value"),
            )
        )

    # Build constraints
    constraints = []
    for con in raw.get("constraints", []):
        constraints.append(
            Constraint(
                description=con["description"],
                source=con.get("source", "practical"),
                applies_to=con.get("applies_to", []),
                is_hard=con.get("is_hard", True),
            )
        )

    # Protocol config
    proto_raw = raw.get("protocol", {})
    architecture = Architecture(proto_raw.get("architecture", raw.get("architecture", "mediated")))

    protocol = ProtocolState(
        architecture=architecture,
        max_rounds=proto_raw.get("max_rounds"),
    )

    # Mediator config and state
    mediator = None
    if architecture != Architecture.BILATERAL:
        med_raw = raw.get("mediator", {})
        mediator_config = MediatorConfig(
            mode=MediatorMode(med_raw.get("mode", "facilitative")),
            knowledge=MediatorKnowledge(med_raw.get("knowledge", "caucus_only")),
            intervention=MediatorIntervention(med_raw.get("intervention", "every_round")),
            evaluates_fairness=med_raw.get("evaluates_fairness", False),
        )
        mediator = MediatorState(config=mediator_config)

    # Legal compliance (advanced mode) — all optional, backward compatible
    compliance = None
    mode_str = raw.get("mode", "streamlined")
    if mode_str == "advanced" or "institution" in raw or "escalation" in raw:
        mode = NegotiationMode(mode_str) if mode_str in ("streamlined", "advanced") else NegotiationMode.ADVANCED

        # Institution config
        institution = None
        inst_raw = raw.get("institution", {})
        if inst_raw:
            institution = InstitutionConfig(
                framework=ComplianceFramework(inst_raw.get("framework", "none")),
                procedure=inst_raw.get("procedure", "standard"),
                claim_amount_usd=inst_raw.get("claim_amount_usd"),
                governing_law=inst_raw.get("governing_law"),
                seat=inst_raw.get("seat"),
                language=inst_raw.get("language", "en"),
                document_standard=DocumentStandard(inst_raw.get("document_standard", "none")),
            )

        # Escalation policy
        escalation = None
        esc_raw = raw.get("escalation", {})
        if esc_raw:
            escalation = EscalationPolicy(
                tiers=[EscalationTier(t) for t in esc_raw.get("tiers", ["negotiation"])],
                negotiation_deadline_rounds=esc_raw.get("negotiation_deadline_rounds", 10),
                mediation_deadline_rounds=esc_raw.get("mediation_deadline_rounds", 6),
                arbitration_deadline_rounds=esc_raw.get("arbitration_deadline_rounds", 4),
                stagnation_threshold=esc_raw.get("stagnation_threshold", 0.02),
                auto_escalate=esc_raw.get("auto_escalate", True),
                cooling_off_rounds=esc_raw.get("cooling_off_rounds", 1),
            )

        # Deadline config
        deadlines = None
        dl_raw = raw.get("deadlines", {})
        if dl_raw:
            deadlines = DeadlineConfig(
                phase_max_rounds=dl_raw.get("phase_max_rounds", {}),
                hard_deadline_rounds=dl_raw.get("hard_deadline_rounds"),
                stagnation_window=dl_raw.get("stagnation_window", 3),
                stagnation_threshold=dl_raw.get("stagnation_threshold", 0.02),
                non_participation_timeout_rounds=dl_raw.get("non_participation_timeout_rounds", 2),
            )

        # Auto-populate from institution profile if available
        if institution and institution.framework != ComplianceFramework.NONE:
            try:
                from .institutions import get_oanp_defaults
                defaults = get_oanp_defaults(
                    institution.framework.value,
                    procedure=institution.procedure,
                    claim_amount_usd=institution.claim_amount_usd,
                )
                # Fill in deadline config from profile if not explicitly set
                if not deadlines:
                    deadlines = DeadlineConfig(
                        phase_max_rounds=defaults.get("phase_round_limits", {}),
                        hard_deadline_rounds=defaults.get("hard_deadline_rounds"),
                        stagnation_window=defaults.get("stagnation_window", 3),
                        stagnation_threshold=defaults.get("stagnation_threshold", 0.02),
                    )
                # Fill in escalation from profile if not explicitly set
                if not escalation and defaults.get("escalation_tiers"):
                    tier_list = [EscalationTier(t["tier"]) for t in defaults["escalation_tiers"]]
                    escalation = EscalationPolicy(tiers=tier_list)
                # Update protocol with phase round limits
                if deadlines and deadlines.phase_max_rounds:
                    protocol.phase_round_limits = deadlines.phase_max_rounds
            except (FileNotFoundError, Exception):
                pass  # Profile not found — use explicit config only

        compliance = ComplianceMetadata(
            mode=mode,
            institution=institution,
            escalation=escalation,
            deadlines=deadlines,
        )

    return NegotiationState(
        parties=parties,
        issues=issues,
        constraints=constraints,
        criteria=criteria,
        protocol=protocol,
        private_states=private_states,
        mediator=mediator,
        compliance=compliance,
    )
