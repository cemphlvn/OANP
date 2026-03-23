"""Tests for StateView — information boundary enforcement."""


from src.protocol.types import (
    Interest,
    InterestType,
    MediatorConfig,
    MediatorKnowledge,
    MediatorState,
    Move,
    MoveType,
    NegotiationState,
    OptionPackage,
    Party,
    PrivatePartyState,
)
from src.protocol.views import StateView


def _make_state() -> NegotiationState:
    """Create a test state with two parties, moves, and private reasoning."""
    state = NegotiationState(
        parties=[
            Party(id="p1", name="Alice", role="buyer"),
            Party(id="p2", name="Bob", role="seller"),
        ],
        private_states={
            "p1": PrivatePartyState(
                party_id="p1",
                interests=[
                    Interest(
                        description="Low price",
                        interest_type=InterestType.DESIRE,
                        priority=0.9,
                        disclosed=True,
                    ),
                    Interest(
                        description="Secret fallback",
                        interest_type=InterestType.FEAR,
                        priority=0.5,
                        disclosed=False,
                    ),
                ],
            ),
            "p2": PrivatePartyState(
                party_id="p2",
                interests=[
                    Interest(
                        description="High price",
                        interest_type=InterestType.DESIRE,
                        priority=0.9,
                        disclosed=False,
                    ),
                ],
            ),
        },
        move_history=[
            Move(
                party_id="p1",
                move_type=MoveType.PROPOSE,
                package=OptionPackage(issue_values={"price": "200"}),
                reasoning="I think 200 is fair because their BATNA is weak",
            ),
            Move(
                party_id="p2",
                move_type=MoveType.COUNTER,
                package=OptionPackage(issue_values={"price": "350"}),
                reasoning="Push high, they'll come up",
            ),
        ],
        mediator=MediatorState(
            config=MediatorConfig(knowledge=MediatorKnowledge.CAUCUS_ONLY)
        ),
    )
    return state


class TestForParty:
    def test_sees_own_reasoning(self):
        state = _make_state()
        view = StateView.for_party(state, "p1")
        # p1 sees their own reasoning
        assert view["move_history"][0]["reasoning"] is not None
        assert "BATNA is weak" in view["move_history"][0]["reasoning"]

    def test_cannot_see_other_reasoning(self):
        state = _make_state()
        view = StateView.for_party(state, "p1")
        # p1 cannot see p2's reasoning
        assert view["move_history"][1]["reasoning"] is None

    def test_sees_own_private_state(self):
        state = _make_state()
        view = StateView.for_party(state, "p1")
        assert view["my_state"] is not None
        assert view["my_state"]["party_id"] == "p1"

    def test_cannot_see_other_private_state(self):
        state = _make_state()
        view = StateView.for_party(state, "p1")
        # Only "my_state", no access to p2
        assert "p2" not in str(view.get("my_state", {}).get("party_id", ""))


class TestForMediator:
    def test_blind_sees_no_private_state(self):
        state = _make_state()
        state.mediator.config.knowledge = MediatorKnowledge.BLIND
        view = StateView.for_mediator(state)
        assert "private_states" not in view
        assert "disclosed_interests" not in view

    def test_caucus_sees_disclosed_only(self):
        state = _make_state()
        view = StateView.for_mediator(state)
        assert "disclosed_interests" in view
        # p1 has one disclosed interest
        p1_disclosed = view["disclosed_interests"].get("p1", [])
        assert len(p1_disclosed) == 1
        assert p1_disclosed[0]["description"] == "Low price"
        # p2 has no disclosed interests
        p2_disclosed = view["disclosed_interests"].get("p2", [])
        assert len(p2_disclosed) == 0

    def test_omniscient_sees_everything(self):
        state = _make_state()
        state.mediator.config.knowledge = MediatorKnowledge.OMNISCIENT
        view = StateView.for_mediator(state)
        assert "private_states" in view
        assert "p1" in view["private_states"]
        assert "p2" in view["private_states"]

    def test_reasoning_stripped(self):
        state = _make_state()
        view = StateView.for_mediator(state)
        for move in view["move_history"]:
            assert move["reasoning"] is None


class TestForFrontend:
    def test_strips_reasoning(self):
        state = _make_state()
        view = StateView.for_frontend(state)
        for move in view["move_history"]:
            assert "reasoning" not in move

    def test_includes_session_id(self):
        state = _make_state()
        view = StateView.for_frontend(state)
        assert view["session_id"] == state.id

    def test_includes_protocol(self):
        state = _make_state()
        view = StateView.for_frontend(state)
        assert "phase" in view["protocol"]
        assert "round" in view["protocol"]
