"""
Unit tests for BCI opponent model (src/agents/bci.py).

Wave 1 gate: All pass. test_model_recovers_weights achieves Pearson > 0.90.
"""

import numpy as np
import pytest

from src.agents.bci import (
    IssueCodec,
    HypothesisSpace,
    StepwiseConcessionLikelihood,
    ConditionalUpdater,
    InverseTransformResampler,
    OpponentModel,
)
from src.protocol.types import Issue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def salary_issue():
    return Issue(id="salary", name="Base Salary", issue_type="monetary", range=[120000, 180000])


@pytest.fixture
def remote_issue():
    return Issue(
        id="remote", name="Remote Work", issue_type="categorical",
        options=["full_remote", "hybrid", "onsite"],
    )


@pytest.fixture
def date_issue():
    return Issue(
        id="start_date", name="Start Date", issue_type="temporal",
        range=["2026-04-01", "2026-06-01"],
    )


@pytest.fixture
def rent_issue():
    return Issue(id="rent", name="Rent Adjustment", issue_type="monetary", range=[-100, 400])


@pytest.fixture
def three_issues(salary_issue, remote_issue, date_issue):
    return [salary_issue, remote_issue, date_issue]


@pytest.fixture
def codec(three_issues):
    return IssueCodec(three_issues)


@pytest.fixture
def hypothesis_space(codec):
    return HypothesisSpace(codec, K_w=11, K_e=11)


# ---------------------------------------------------------------------------
# Synthetic opponent helper
# ---------------------------------------------------------------------------


class SyntheticOpponent:
    """Generates bids from a known utility function for testing."""

    def __init__(self, weights: np.ndarray, issues: list[Issue], seed: int = 42):
        self.weights = weights / weights.sum()
        self.codec = IssueCodec(issues)
        self.rng = np.random.RandomState(seed)
        self.aspiration = 0.95
        self.issues = issues

    def make_bid(self, target_utility: float) -> dict[str, str]:
        """Generate a bid that approximates target_utility."""
        # Simple strategy: for high-weight issues, bid near the high end
        # proportional to weight and target utility
        bid = {}
        for i, iid in enumerate(self.codec.issue_ids):
            # The opponent's ideal value is 1.0 (top of range)
            # They concede toward 0.0 as target_utility drops
            w = self.weights[i]
            # High-weight issues: concede less. Low-weight: concede more.
            concession = (1.0 - target_utility) * (1.0 + 0.5 * (1.0 - w))
            val = max(0.0, min(1.0, 1.0 - concession))
            # Add small noise
            val += self.rng.normal(0, 0.02)
            val = max(0.0, min(1.0, val))
            bid[iid] = self.codec.decode(iid, val)
        return bid

    def conceding_sequence(self, n_bids: int, rate: float = 0.04) -> list[dict[str, str]]:
        """Generate a conceding bid sequence."""
        bids = []
        for t in range(n_bids):
            target = max(0.1, self.aspiration - t * rate)
            bids.append(self.make_bid(target))
        return bids


# ---------------------------------------------------------------------------
# IssueCodec Tests
# ---------------------------------------------------------------------------


class TestIssueCodec:

    def test_encode_monetary_midpoint(self, codec):
        assert codec.encode("salary", "150000") == pytest.approx(0.5, abs=0.001)

    def test_encode_monetary_boundaries(self, codec):
        assert codec.encode("salary", "120000") == pytest.approx(0.0, abs=0.001)
        assert codec.encode("salary", "180000") == pytest.approx(1.0, abs=0.001)

    def test_encode_categorical(self, codec):
        assert codec.encode("remote", "full_remote") == pytest.approx(0.0, abs=0.001)
        assert codec.encode("remote", "hybrid") == pytest.approx(0.5, abs=0.001)
        assert codec.encode("remote", "onsite") == pytest.approx(1.0, abs=0.001)

    def test_clamp_out_of_range(self, codec):
        assert codec.encode("salary", "200000") == pytest.approx(1.0, abs=0.001)
        assert codec.encode("salary", "100000") == pytest.approx(0.0, abs=0.001)

    def test_negative_range(self):
        rent = Issue(id="rent", name="Rent", issue_type="monetary", range=[-100, 400])
        c = IssueCodec([rent])
        assert c.encode("rent", "0") == pytest.approx(0.2, abs=0.001)
        assert c.encode("rent", "-100") == pytest.approx(0.0, abs=0.001)
        assert c.encode("rent", "400") == pytest.approx(1.0, abs=0.001)

    def test_encode_temporal_date(self, codec):
        # 2026-04-01 to 2026-06-01 = 61 days
        # 2026-05-01 is ~30 days in ≈ 0.49
        val = codec.encode("start_date", "2026-05-01")
        assert 0.4 < val < 0.6

    def test_roundtrip_categorical(self, codec):
        for opt in ["full_remote", "hybrid", "onsite"]:
            encoded = codec.encode("remote", opt)
            decoded = codec.decode("remote", encoded)
            assert decoded == opt

    def test_roundtrip_monetary(self, codec):
        encoded = codec.encode("salary", "150000")
        decoded = codec.decode("salary", encoded)
        assert abs(int(decoded) - 150000) < 1000  # Within 1K tolerance

    def test_encode_bid(self, codec):
        bid = {"salary": "150000", "remote": "hybrid", "start_date": "2026-05-01"}
        arr = codec.encode_bid(bid)
        assert arr.shape == (3,)
        assert arr[0] == pytest.approx(0.5, abs=0.01)
        assert arr[1] == pytest.approx(0.5, abs=0.01)

    def test_encode_bid_missing_issue(self, codec):
        bid = {"salary": "150000"}  # missing remote and start_date
        arr = codec.encode_bid(bid)
        assert arr.shape == (3,)
        assert arr[0] == pytest.approx(0.5, abs=0.01)
        assert arr[1] == 0.5  # default midpoint
        assert arr[2] == 0.5  # default midpoint

    def test_unknown_option(self, codec):
        # Unknown categorical option — returns midpoint
        val = codec.encode("remote", "flex_friday")
        assert val == 0.5


# ---------------------------------------------------------------------------
# HypothesisSpace Tests
# ---------------------------------------------------------------------------


class TestHypothesisSpace:

    def test_uniform_prior_weights(self, hypothesis_space):
        w = hypothesis_space.estimated_weights()
        assert w.shape == (3,)
        # Uniform prior → all weights approximately equal
        np.testing.assert_allclose(w, [1 / 3, 1 / 3, 1 / 3], atol=0.05)

    def test_weights_sum_to_one(self, hypothesis_space):
        w = hypothesis_space.estimated_weights()
        assert w.sum() == pytest.approx(1.0, abs=1e-6)

    def test_evals_uniform_prior(self, hypothesis_space):
        evals = hypothesis_space.estimated_evals("remote")
        assert evals.shape == (3,)  # 3 options
        # Uniform prior → normalized to [0, 1] range
        assert evals.min() >= -0.01
        assert evals.max() <= 1.01


# ---------------------------------------------------------------------------
# Likelihood Tests
# ---------------------------------------------------------------------------


class TestStepwiseConcessionLikelihood:

    def test_first_bid_uniform(self, codec):
        lf = StepwiseConcessionLikelihood()
        w_grid = np.linspace(0, 1, 11)
        w_current = np.array([0.33, 0.33, 0.34])
        evals = [np.linspace(0, 1, 11), np.array([0.3, 0.5, 0.7]), np.linspace(0, 1, 11)]
        bid = np.array([0.5, 0.5, 0.5])

        ll = lf.weight_log_likelihoods(0, bid, None, w_grid, w_current, evals, codec)
        # All zeros (uniform)
        np.testing.assert_array_equal(ll, np.zeros(11))

    def test_concession_positive_likelihood(self, codec):
        lf = StepwiseConcessionLikelihood()
        w_grid = np.linspace(0, 1, 11)
        w_current = np.array([0.5, 0.3, 0.2])
        evals = [np.linspace(0, 1, 11), np.array([0.2, 0.5, 0.8]), np.linspace(0, 1, 11)]

        bid_prev = np.array([0.8, 0.7, 0.6])
        bid_t = np.array([0.7, 0.6, 0.5])  # concession

        ll = lf.weight_log_likelihoods(0, bid_t, bid_prev, w_grid, w_current, evals, codec)
        # Should be finite, not all zeros
        assert np.all(np.isfinite(ll))

    def test_no_concession_flat(self, codec):
        lf = StepwiseConcessionLikelihood()
        w_grid = np.linspace(0, 1, 11)
        w_current = np.array([0.33, 0.33, 0.34])
        evals = [np.linspace(0, 1, 11), np.array([0.3, 0.5, 0.7]), np.linspace(0, 1, 11)]

        bid = np.array([0.5, 0.5, 0.5])
        # Same bid twice → delta ≈ 0 → flat likelihood
        ll = lf.weight_log_likelihoods(0, bid, bid.copy(), w_grid, w_current, evals, codec)
        # All should be near 0 (log(1))
        assert np.all(ll >= -0.1)


# ---------------------------------------------------------------------------
# ConditionalUpdater Tests
# ---------------------------------------------------------------------------


class TestConditionalUpdater:

    def test_converges_within_max_iterations(self, hypothesis_space, codec):
        updater = ConditionalUpdater(convergence_threshold=0.01, max_iterations=20)
        lf = StepwiseConcessionLikelihood()

        bid_prev = np.array([0.8, 0.7, 0.6])
        bid_t = np.array([0.7, 0.6, 0.5])

        iters = updater.update(hypothesis_space, bid_t, bid_prev, lf, codec)
        assert 1 <= iters <= 20

    def test_update_does_not_produce_nan(self, hypothesis_space, codec):
        updater = ConditionalUpdater()
        lf = StepwiseConcessionLikelihood()

        bid_prev = np.array([0.9, 0.8, 0.7])
        bid_t = np.array([0.85, 0.75, 0.65])

        updater.update(hypothesis_space, bid_t, bid_prev, lf, codec)
        assert np.all(np.isfinite(hypothesis_space.w_log_alpha))


# ---------------------------------------------------------------------------
# Resampler Tests
# ---------------------------------------------------------------------------


class TestInverseTransformResampler:

    def test_no_resample_uniform(self, hypothesis_space):
        resampler = InverseTransformResampler(threshold=0.5)
        # Fresh hypothesis space has uniform weights → ESS = K → no resample
        resampled = resampler.maybe_resample(hypothesis_space)
        assert not resampled

    def test_resample_collapsed(self, hypothesis_space):
        resampler = InverseTransformResampler(threshold=0.5)
        # Collapse all weight to one hypothesis
        hypothesis_space.w_log_alpha[0, :] = -100.0
        hypothesis_space.w_log_alpha[0, 5] = 0.0  # All weight on hypothesis 5
        resampled = resampler.maybe_resample(hypothesis_space)
        assert resampled


# ---------------------------------------------------------------------------
# OpponentModel End-to-End Tests
# ---------------------------------------------------------------------------


class TestOpponentModel:

    def test_zero_bids_confidence(self, three_issues):
        model = OpponentModel(three_issues, "opp")
        assert model.get_confidence() == 0.0
        belief = model.to_belief_model()
        assert belief.confidence == 0.0

    def test_single_bid_no_crash(self, three_issues):
        model = OpponentModel(three_issues, "opp")
        model.update({"salary": "160000", "remote": "hybrid", "start_date": "2026-05-01"})
        assert model.get_confidence() >= 0.0
        assert model._update_count == 1

    def test_confidence_grows(self, three_issues):
        np.random.seed(42)
        opponent = SyntheticOpponent(np.array([0.7, 0.2, 0.1]), three_issues)
        bids = opponent.conceding_sequence(10)

        model = OpponentModel(three_issues, "opp")
        confidences = []
        for bid in bids:
            model.update(bid)
            confidences.append(model.get_confidence())

        # Confidence should generally increase
        assert confidences[-1] > confidences[0]
        # Should be capped
        assert confidences[-1] <= 0.85

    def test_estimate_utility_in_range(self, three_issues):
        model = OpponentModel(three_issues, "opp")
        model.update({"salary": "160000", "remote": "hybrid", "start_date": "2026-05-01"})
        u = model.estimate_utility({"salary": "150000", "remote": "onsite", "start_date": "2026-04-15"})
        assert 0.0 <= u <= 1.0

    def test_model_recovers_weights(self, three_issues):
        """Core validation: BCI recovers true opponent weights. Gate: Pearson > 0.90."""
        np.random.seed(42)
        true_weights = np.array([0.7, 0.2, 0.1])
        opponent = SyntheticOpponent(true_weights, three_issues, seed=42)
        bids = opponent.conceding_sequence(20, rate=0.03)

        model = OpponentModel(three_issues, "opp")
        for bid in bids:
            model.update(bid)

        estimated = model.hs.estimated_weights()
        # Pearson correlation
        corr = np.corrcoef(estimated, true_weights / true_weights.sum())[0, 1]
        assert corr > 0.90, f"Pearson {corr:.3f} below 0.90 threshold"

    def test_log_space_no_underflow(self, three_issues):
        """50 updates should not produce NaN or Inf."""
        np.random.seed(42)
        opponent = SyntheticOpponent(np.array([0.5, 0.3, 0.2]), three_issues, seed=42)
        bids = opponent.conceding_sequence(50, rate=0.015)

        model = OpponentModel(three_issues, "opp")
        for bid in bids:
            model.update(bid)

        assert np.all(np.isfinite(model.hs.w_log_alpha))
        assert model.get_confidence() > 0

    def test_to_belief_model(self, three_issues):
        np.random.seed(42)
        opponent = SyntheticOpponent(np.array([0.6, 0.25, 0.15]), three_issues, seed=42)
        bids = opponent.conceding_sequence(10)

        model = OpponentModel(three_issues, "opp")
        for bid in bids:
            model.update(bid)

        belief = model.to_belief_model()
        assert belief.target_party_id == "opp"
        assert len(belief.estimated_priorities) == 3
        assert sum(belief.estimated_priorities.values()) == pytest.approx(1.0, abs=0.01)
        assert belief.confidence > 0.0
        assert len(belief.evidence) > 0

    def test_rebuild_from_bids(self, three_issues):
        np.random.seed(42)
        opponent = SyntheticOpponent(np.array([0.6, 0.25, 0.15]), three_issues, seed=42)
        bids = opponent.conceding_sequence(10)

        # Build incrementally
        model1 = OpponentModel(three_issues, "opp")
        for bid in bids:
            model1.update(bid)

        # Rebuild from scratch
        model2 = OpponentModel(three_issues, "opp")
        model2.rebuild_from_bids(bids)

        # Should produce same estimates
        w1 = model1.hs.estimated_weights()
        w2 = model2.hs.estimated_weights()
        np.testing.assert_allclose(w1, w2, atol=0.01)
