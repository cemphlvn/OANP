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
    Constraint,
    Interest,
    InterestType,
    Issue,
    MediatorConfig,
    MediatorIntervention,
    MediatorKnowledge,
    MediatorMode,
    MediatorState,
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

    return NegotiationState(
        parties=parties,
        issues=issues,
        constraints=constraints,
        criteria=criteria,
        protocol=protocol,
        private_states=private_states,
        mediator=mediator,
    )
