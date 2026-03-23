"""Tests for the analyst (metrics computation)."""


from src.protocol.types import (
    BATNA,
    Interest,
    InterestType,
    Issue,
    Move,
    MoveType,
    NegotiationState,
    OptionPackage,
    Party,
    PrivatePartyState,
)
from src.agents.analyst import analyze_negotiation, compute_utility


class TestComputeUtility:
    def test_no_interests(self):
        pkg = OptionPackage(issue_values={"price": "200"})
        ps = PrivatePartyState(party_id="p1")
        assert compute_utility(pkg, ps, []) == 0.5

    def test_all_issues_addressed(self):
        pkg = OptionPackage(issue_values={"salary": "150000", "remote": "hybrid"})
        ps = PrivatePartyState(
            party_id="p1",
            interests=[
                Interest(
                    description="High salary",
                    interest_type=InterestType.DESIRE,
                    priority=0.9,
                    related_issues=["salary"],
                ),
                Interest(
                    description="Remote work",
                    interest_type=InterestType.NEED,
                    priority=0.8,
                    related_issues=["remote"],
                ),
            ],
        )
        utility = compute_utility(pkg, ps, [])
        assert 0.5 < utility <= 1.0  # both interests addressed

    def test_partial_coverage(self):
        pkg = OptionPackage(issue_values={"salary": "150000"})
        ps = PrivatePartyState(
            party_id="p1",
            interests=[
                Interest(description="Salary", interest_type=InterestType.DESIRE, priority=0.9, related_issues=["salary"]),
                Interest(description="Remote", interest_type=InterestType.NEED, priority=0.8, related_issues=["remote"]),
            ],
        )
        utility = compute_utility(pkg, ps, [])
        # Only one of two interests addressed
        assert 0.2 < utility < 0.8


class TestAnalyzeNegotiation:
    def _make_completed_state(self) -> NegotiationState:
        agreement = OptionPackage(issue_values={"salary": "155000", "remote": "hybrid"})
        return NegotiationState(
            parties=[
                Party(id="p1", name="Candidate", role="candidate"),
                Party(id="p2", name="Employer", role="employer"),
            ],
            issues=[
                Issue(id="salary", name="Salary", issue_type="monetary", range=[120000, 180000]),
                Issue(id="remote", name="Remote", options=["full_remote", "hybrid", "onsite"]),
            ],
            private_states={
                "p1": PrivatePartyState(
                    party_id="p1",
                    interests=[
                        Interest(description="High salary", interest_type=InterestType.DESIRE, priority=0.9, related_issues=["salary"]),
                    ],
                    batna=BATNA(description="Other offer", utility=0.5),
                ),
                "p2": PrivatePartyState(
                    party_id="p2",
                    interests=[
                        Interest(description="Budget", interest_type=InterestType.NEED, priority=0.9, related_issues=["salary"]),
                    ],
                    batna=BATNA(description="Keep searching", utility=0.3),
                ),
            },
            move_history=[
                Move(party_id="p1", move_type=MoveType.PROPOSE, package=agreement),
                Move(party_id="p2", move_type=MoveType.ACCEPT, package=agreement),
            ],
            agreement=agreement,
            outcome="agreement",
        )

    def test_agreement_metrics(self):
        state = self._make_completed_state()
        metrics = analyze_negotiation(state)

        assert metrics.outcome == "agreement"
        assert metrics.total_moves == 2
        assert "p1" in metrics.party_utilities
        assert "p2" in metrics.party_utilities
        assert metrics.social_welfare > 0
        assert metrics.agreement is not None

    def test_impasse_metrics(self):
        state = self._make_completed_state()
        state.agreement = None
        state.outcome = "impasse"

        metrics = analyze_negotiation(state)
        assert metrics.outcome == "impasse"
        # Utilities fall back to BATNA values
        assert metrics.party_utilities["p1"] == 0.5
        assert metrics.party_utilities["p2"] == 0.3

    def test_disclosure_rate(self):
        state = self._make_completed_state()
        # No interests disclosed
        metrics = analyze_negotiation(state)
        assert metrics.disclosure_rate == 0.0

        # Disclose one
        state.private_states["p1"].disclosed_interests = ["i1"]
        metrics = analyze_negotiation(state)
        assert metrics.disclosure_rate == 0.5  # 1 of 2

    def test_move_breakdown(self):
        state = self._make_completed_state()
        metrics = analyze_negotiation(state)
        assert metrics.move_breakdown["propose"] == 1
        assert metrics.move_breakdown["accept"] == 1
