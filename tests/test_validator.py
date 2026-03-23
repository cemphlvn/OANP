"""Tests for the move validator."""

import pytest

from src.protocol.types import (
    BATNA,
    Move,
    MoveType,
    NegotiationPhase,
    NegotiationState,
    OptionPackage,
    Party,
    PrivatePartyState,
    ProtocolState,
)
from src.agents.validator import MoveValidator


@pytest.fixture
def state() -> NegotiationState:
    return NegotiationState(
        parties=[
            Party(id="p1", name="Alice", role="buyer"),
            Party(id="p2", name="Bob", role="seller"),
        ],
        private_states={
            "p1": PrivatePartyState(
                party_id="p1",
                batna=BATNA(description="Walk", utility=0.5),
            ),
        },
        protocol=ProtocolState(phase=NegotiationPhase.BARGAINING),
    )


@pytest.fixture
def validator() -> MoveValidator:
    return MoveValidator()


class TestMoveValidator:
    @pytest.mark.asyncio
    async def test_valid_propose(self, state, validator):
        move = Move(
            party_id="p1",
            move_type=MoveType.PROPOSE,
            package=OptionPackage(issue_values={"price": "200"}),
        )
        result = await validator.validate(move, state)
        assert result.valid

    @pytest.mark.asyncio
    async def test_propose_without_package(self, state, validator):
        move = Move(party_id="p1", move_type=MoveType.PROPOSE)
        result = await validator.validate(move, state)
        assert not result.valid
        assert any("must include a package" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_propose_with_empty_package(self, state, validator):
        move = Move(
            party_id="p1",
            move_type=MoveType.PROPOSE,
            package=OptionPackage(issue_values={}),
        )
        result = await validator.validate(move, state)
        assert not result.valid
        assert any("no issue values" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_accept_finds_last_package(self, state, validator):
        pkg = OptionPackage(issue_values={"price": "250"})
        state.move_history = [
            Move(party_id="p2", move_type=MoveType.PROPOSE, package=pkg),
        ]
        move = Move(party_id="p1", move_type=MoveType.ACCEPT)
        await validator.validate(move, state)
        # Should auto-fill the package from history
        assert move.package is not None
        assert move.package.issue_values["price"] == "250"

    @pytest.mark.asyncio
    async def test_valid_argue(self, state, validator):
        from src.protocol.types import Argument
        move = Move(
            party_id="p1",
            move_type=MoveType.ARGUE,
            argument=Argument(claim="Market rate is higher"),
        )
        result = await validator.validate(move, state)
        assert result.valid
