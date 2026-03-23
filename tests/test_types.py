"""Tests for the OANP protocol type system."""

from datetime import datetime

from src.protocol.types import (
    Architecture,
    BATNA,
    Interest,
    InterestType,
    Issue,
    MediatorConfig,
    MediatorIntervention,
    MediatorKnowledge,
    MediatorMode,
    Move,
    MoveType,
    NegotiationPhase,
    NegotiationState,
    OptionPackage,
    Party,
    PrivatePartyState,
    ProtocolState,
    SatisfactionAnchor,
)


class TestEnums:
    def test_negotiation_phases(self):
        assert NegotiationPhase.SETUP.value == "setup"
        assert NegotiationPhase.SETTLEMENT.value == "settlement"
        assert len(NegotiationPhase) == 9

    def test_move_types(self):
        assert MoveType.PROPOSE.value == "propose"
        assert MoveType.ACCEPT.value == "accept"
        assert len(MoveType) == 10

    def test_interest_types(self):
        assert set(t.value for t in InterestType) == {"need", "desire", "fear", "concern"}

    def test_mediator_modes(self):
        assert MediatorMode("facilitative") == MediatorMode.FACILITATIVE
        assert MediatorMode("evaluative") == MediatorMode.EVALUATIVE
        assert MediatorMode("arbitrative") == MediatorMode.ARBITRATIVE


class TestIssue:
    def test_categorical_issue(self):
        issue = Issue(name="Remote Work", options=["full_remote", "hybrid", "onsite"])
        assert issue.name == "Remote Work"
        assert issue.issue_type == "categorical"
        assert not issue.is_divisible
        assert len(issue.id) == 8

    def test_monetary_issue(self):
        issue = Issue(name="Salary", issue_type="monetary", range=[100000, 200000], is_divisible=True)
        assert issue.range == [100000, 200000]
        assert issue.is_divisible


class TestMove:
    def test_move_defaults(self):
        move = Move(party_id="p1", move_type=MoveType.ARGUE)
        assert move.party_id == "p1"
        assert move.move_type == MoveType.ARGUE
        assert move.package is None
        assert move.round == 0
        assert isinstance(move.timestamp, datetime)
        assert move.timestamp.tzinfo is not None  # timezone-aware

    def test_move_with_package(self):
        pkg = OptionPackage(issue_values={"salary": "150000", "remote": "hybrid"})
        move = Move(party_id="p1", move_type=MoveType.PROPOSE, package=pkg)
        assert move.package.issue_values["salary"] == "150000"

    def test_move_with_argument(self):
        from src.protocol.types import Argument
        arg = Argument(claim="Market rate is higher", grounds=["Levels.fyi data"])
        move = Move(party_id="p1", move_type=MoveType.ARGUE, argument=arg)
        assert move.argument.claim == "Market rate is higher"


class TestPrivatePartyState:
    def test_interests_and_batna(self):
        state = PrivatePartyState(
            party_id="candidate",
            interests=[
                Interest(description="High salary", interest_type=InterestType.DESIRE, priority=0.9),
                Interest(description="Remote work", interest_type=InterestType.NEED, priority=0.8),
            ],
            batna=BATNA(description="Other offer", utility=0.6),
        )
        assert len(state.interests) == 2
        assert state.batna.utility == 0.6
        assert state.strategy.cooperation_level == 0.7  # default

    def test_satisfaction_anchors(self):
        anchor = SatisfactionAnchor(
            condition="base_salary >= 160000",
            score=0.9,
            reason="Near top of range",
        )
        interest = Interest(
            description="High compensation",
            interest_type=InterestType.DESIRE,
            satisfaction_anchors=[anchor],
        )
        assert interest.satisfaction_anchors[0].score == 0.9


class TestNegotiationState:
    def test_empty_state(self):
        state = NegotiationState()
        assert state.id.startswith("neg_")
        assert state.protocol.phase == NegotiationPhase.SETUP
        assert state.parties == []
        assert state.move_history == []
        assert state.agreement is None
        assert state.created_at.tzinfo is not None

    def test_state_with_parties(self):
        state = NegotiationState(
            parties=[
                Party(id="p1", name="Alice", role="buyer"),
                Party(id="p2", name="Bob", role="seller"),
            ],
            issues=[
                Issue(id="price", name="Price", issue_type="monetary", range=[100, 500]),
            ],
        )
        assert len(state.parties) == 2
        assert state.parties[0].name == "Alice"
        assert state.issues[0].range == [100, 500]


class TestMediatorConfig:
    def test_defaults(self):
        config = MediatorConfig()
        assert config.mode == MediatorMode.FACILITATIVE
        assert config.knowledge == MediatorKnowledge.CAUCUS_ONLY
        assert config.intervention == MediatorIntervention.EVERY_ROUND
        assert config.evaluates_fairness is False

    def test_custom_config(self):
        config = MediatorConfig(
            mode=MediatorMode.EVALUATIVE,
            knowledge=MediatorKnowledge.OMNISCIENT,
            intervention=MediatorIntervention.AT_IMPASSE,
        )
        assert config.mode == MediatorMode.EVALUATIVE
        assert config.knowledge == MediatorKnowledge.OMNISCIENT


class TestProtocolState:
    def test_defaults(self):
        proto = ProtocolState()
        assert proto.phase == NegotiationPhase.SETUP
        assert proto.round == 0
        assert proto.architecture == Architecture.MEDIATED
        assert proto.accepted_by == set()

    def test_accepted_tracking(self):
        proto = ProtocolState()
        proto.accepted_by.add("p1")
        proto.accepted_by.add("p2")
        assert len(proto.accepted_by) == 2
