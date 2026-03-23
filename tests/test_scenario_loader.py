"""Tests for the YAML scenario loader."""

from pathlib import Path

from src.protocol.scenario import load_scenario, load_scenario_from_dict
from src.protocol.types import (
    Architecture,
    InterestType,
    MediatorKnowledge,
    MediatorMode,
)

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


class TestLoadScenario:
    def test_load_salary_negotiation(self):
        state = load_scenario(SCENARIOS_DIR / "salary-negotiation.yaml")

        # Parties
        assert len(state.parties) == 2
        assert state.parties[0].id == "candidate"
        assert state.parties[1].id == "employer"

        # Issues
        assert len(state.issues) == 5
        issue_ids = {i.id for i in state.issues}
        assert "base_salary" in issue_ids
        assert "remote_work" in issue_ids

        # Private states
        assert "candidate" in state.private_states
        assert "employer" in state.private_states

        candidate = state.private_states["candidate"]
        assert len(candidate.interests) == 4
        assert candidate.batna is not None
        assert candidate.batna.utility == 0.65

        # Protocol
        assert state.protocol.architecture == Architecture.MEDIATED
        assert state.protocol.max_rounds == 20

        # Mediator
        assert state.mediator is not None
        assert state.mediator.config.mode == MediatorMode.FACILITATIVE
        assert state.mediator.config.knowledge == MediatorKnowledge.CAUCUS_ONLY

    def test_load_all_scenarios(self):
        """Every YAML scenario in the scenarios/ dir should load without error."""
        yaml_files = list(SCENARIOS_DIR.glob("*.yaml"))
        assert len(yaml_files) >= 3, "Expected at least 3 scenario files"

        for path in yaml_files:
            state = load_scenario(path)
            assert len(state.parties) >= 2, f"{path.name}: needs at least 2 parties"
            assert len(state.issues) >= 2, f"{path.name}: needs at least 2 issues"
            for party in state.parties:
                ps = state.private_states.get(party.id)
                assert ps is not None, f"{path.name}: missing private state for {party.id}"
                assert len(ps.interests) >= 1, f"{path.name}: {party.id} needs interests"


class TestLoadScenarioFromDict:
    def test_minimal_scenario(self):
        raw = {
            "parties": [
                {
                    "id": "buyer",
                    "name": "Buyer",
                    "role": "buyer",
                    "interests": [
                        {"description": "Low price", "type": "desire", "priority": 0.9}
                    ],
                    "batna": {"description": "Walk away", "utility": 0.3},
                },
                {
                    "id": "seller",
                    "name": "Seller",
                    "role": "seller",
                    "interests": [
                        {"description": "High price", "type": "desire", "priority": 0.9}
                    ],
                    "batna": {"description": "Sell elsewhere", "utility": 0.4},
                },
            ],
            "issues": [
                {"id": "price", "name": "Price", "type": "monetary", "range": [100, 500]},
            ],
            "architecture": "mediated",
        }

        state = load_scenario_from_dict(raw)
        assert len(state.parties) == 2
        assert state.private_states["buyer"].interests[0].interest_type == InterestType.DESIRE
        assert state.private_states["seller"].batna.utility == 0.4
        assert state.mediator is not None

    def test_bilateral_no_mediator(self):
        raw = {
            "parties": [
                {"id": "a", "name": "A", "role": "a", "interests": [{"description": "x", "priority": 0.5}]},
                {"id": "b", "name": "B", "role": "b", "interests": [{"description": "y", "priority": 0.5}]},
            ],
            "issues": [{"id": "q", "name": "Q"}],
            "architecture": "bilateral",
        }
        state = load_scenario_from_dict(raw)
        assert state.protocol.architecture == Architecture.BILATERAL
        assert state.mediator is None

    def test_criteria_and_constraints(self):
        raw = {
            "parties": [
                {"id": "a", "name": "A", "role": "a"},
                {"id": "b", "name": "B", "role": "b"},
            ],
            "issues": [{"id": "q", "name": "Q"}],
            "criteria": [
                {"name": "Market rate", "source": "market_data", "reference_value": "$100k"},
            ],
            "constraints": [
                {"description": "Must close by Q2", "source": "temporal"},
            ],
        }
        state = load_scenario_from_dict(raw)
        assert len(state.criteria) == 1
        assert state.criteria[0].reference_value == "$100k"
        assert len(state.constraints) == 1
        assert state.constraints[0].source == "temporal"
