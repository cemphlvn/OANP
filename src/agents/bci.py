"""
BCI — Bayesian opponent model Considering parametric Interrelation.

Estimates an opponent's hidden utility function from observed bids using
Bayesian inference with parametric interrelation (Chang & Fujita, 2026).

Architecture:
  NumPy layer (runtime)          Pydantic layer (serialized)
  ┌─────────────────┐            ┌──────────────────┐
  │ OpponentModel    │ .to_belief │ BeliefModel      │
  │  log-alpha arrays│ ─────────►│  estimated_priors │
  │  hypothesis grids│            │  confidence       │
  └─────────────────┘            └──────────────────┘

The NumPy layer lives on NegotiationEngine (not serialized).
BeliefModel (existing Pydantic type) is what gets persisted and streamed.

Reference: Chang & Fujita (2026), Auton Agent Multi-Agent Syst 40:8
  - Eq. 9: Conditional probability update rule
  - Eq. 10: Stepwise concession likelihood
  - Algorithm 1: Inverse transform resampling
  - Algorithm 2: Full model update procedure
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import numpy as np

from ..protocol.types import BeliefModel, Issue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Numerically stable log-space helpers
# ---------------------------------------------------------------------------


def _logsumexp(a: np.ndarray) -> float:
    """Log-sum-exp without scipy dependency at runtime."""
    a_max = np.max(a)
    if not np.isfinite(a_max):
        return -np.inf
    return a_max + np.log(np.sum(np.exp(a - a_max)))


def _log_normalize(log_weights: np.ndarray) -> np.ndarray:
    """Normalize log-weights so they sum to 1 in linear space."""
    lse = _logsumexp(log_weights)
    if not np.isfinite(lse):
        # Degenerate — reset to uniform
        return np.full_like(log_weights, -np.log(len(log_weights)))
    return log_weights - lse


# ---------------------------------------------------------------------------
# IssueCodec — bidirectional string ↔ [0,1] mapping
# ---------------------------------------------------------------------------


class _SingleCodec:
    """Codec for one issue."""

    def __init__(self, issue: Issue):
        self.issue = issue
        self.issue_type = issue.issue_type

        if self.issue_type == "categorical":
            self.options = list(issue.options)
            self.n_options = len(self.options)
            if self.n_options < 2:
                self.n_options = max(self.n_options, 1)
        else:
            # monetary or temporal
            self.options = []
            self.n_options = 11  # K=11 bins for continuous
            self._parse_range(issue)

    def _parse_range(self, issue: Issue):
        """Parse range for monetary/temporal issues."""
        r = issue.range or [0, 1]
        try:
            self.lo = float(r[0])
            self.hi = float(r[1])
        except (ValueError, TypeError):
            # Likely date strings — convert to ordinal
            try:
                d0 = datetime.fromisoformat(str(r[0]))
                d1 = datetime.fromisoformat(str(r[1]))
                self.lo = float(d0.toordinal())
                self.hi = float(d1.toordinal())
                self.issue_type = "_temporal_ordinal"
            except (ValueError, TypeError):
                self.lo, self.hi = 0.0, 1.0

        if self.hi <= self.lo:
            # Zero-width range — degenerate
            self.hi = self.lo + 1e-9

    def encode(self, value: str) -> float:
        if self.issue_type == "categorical":
            if value in self.options:
                idx = self.options.index(value)
                return idx / max(self.n_options - 1, 1)
            # Unknown option — return midpoint
            return 0.5

        # monetary or temporal
        try:
            v = float(value)
        except (ValueError, TypeError):
            try:
                v = float(datetime.fromisoformat(str(value)).toordinal())
            except (ValueError, TypeError):
                return 0.5
        # Normalize and clamp
        z = (v - self.lo) / (self.hi - self.lo)
        return max(0.0, min(1.0, z))

    def decode(self, normalized: float) -> str:
        normalized = max(0.0, min(1.0, normalized))
        if self.issue_type == "categorical":
            idx = round(normalized * max(self.n_options - 1, 1))
            idx = max(0, min(self.n_options - 1, idx))
            return self.options[idx] if self.options else ""

        raw = self.lo + normalized * (self.hi - self.lo)
        if self.issue_type == "_temporal_ordinal":
            try:
                return datetime.fromordinal(round(raw)).isoformat()[:10]
            except (ValueError, OverflowError):
                return str(round(raw))
        # monetary — return integer string for large ranges, 2-decimal otherwise
        if self.hi - self.lo > 100:
            return str(round(raw))
        return f"{raw:.2f}"

    def nearest_option_index(self, normalized: float) -> int:
        """Map a normalized value to the nearest discrete option index."""
        if self.issue_type == "categorical":
            idx = round(normalized * max(self.n_options - 1, 1))
            return max(0, min(self.n_options - 1, idx))
        # Continuous: map to K=11 bin
        idx = round(normalized * (self.n_options - 1))
        return max(0, min(self.n_options - 1, idx))


class IssueCodec:
    """Bidirectional mapping: OANP string values ↔ normalized [0,1] floats."""

    def __init__(self, issues: list[Issue]):
        self.issue_ids: list[str] = []
        self._index: dict[str, int] = {}
        self._codecs: dict[str, _SingleCodec] = {}

        for i, iss in enumerate(issues):
            iid = iss.id or iss.name
            self.issue_ids.append(iid)
            self._index[iid] = i
            self._codecs[iid] = _SingleCodec(iss)

    @property
    def n_issues(self) -> int:
        return len(self.issue_ids)

    def encode(self, issue_id: str, value: str) -> float:
        c = self._codecs.get(issue_id)
        if c is None:
            return 0.5
        return c.encode(value)

    def decode(self, issue_id: str, normalized: float) -> str:
        c = self._codecs.get(issue_id)
        if c is None:
            return ""
        return c.decode(normalized)

    def encode_bid(self, bid: dict[str, str]) -> np.ndarray:
        """Encode a full bid dict into a normalized array (n_issues,)."""
        arr = np.full(self.n_issues, 0.5)  # default midpoint for missing issues
        for iid, val in bid.items():
            if iid in self._index:
                arr[self._index[iid]] = self.encode(iid, val)
            else:
                # Try matching by name — bids sometimes use issue name instead of id
                for codec_id, codec in self._codecs.items():
                    if codec.issue.name == iid:
                        arr[self._index[codec_id]] = codec.encode(val)
                        break
        return arr

    def get_option_count(self, issue_id: str) -> int:
        c = self._codecs.get(issue_id)
        return c.n_options if c else 1

    def nearest_option_index(self, issue_id: str, normalized: float) -> int:
        c = self._codecs.get(issue_id)
        return c.nearest_option_index(normalized) if c else 0

    def get_option_labels(self, issue_id: str) -> list[str]:
        """Return human-readable labels for each option/bin."""
        c = self._codecs.get(issue_id)
        if not c:
            return []
        if c.issue_type == "categorical":
            return list(c.options)
        # Continuous: generate bin labels
        return [c.decode(k / (c.n_options - 1)) for k in range(c.n_options)]


# ---------------------------------------------------------------------------
# HypothesisSpace — discrete hypothesis grid for all parameters
# ---------------------------------------------------------------------------


class HypothesisSpace:
    """Discrete hypothesis grid for opponent utility parameters.

    All weights stored in log-space to prevent underflow.
    """

    def __init__(self, codec: IssueCodec, K_w: int = 11, K_e: int = 11):
        self.codec = codec
        self.K_w = K_w
        self.K_e = K_e
        self.n_issues = codec.n_issues

        # Weight hypotheses: grid of candidate values for each w_i
        self.w_grid = np.linspace(0, 1, K_w)  # (K_w,)

        # Log-alpha for weight parameters: (n_issues, K_w)
        self.w_log_alpha = np.zeros((self.n_issues, K_w)) - np.log(K_w)

        # Evaluation hypotheses per issue: grid + log-alpha
        self.e_grid = np.linspace(0, 1, K_e)  # (K_e,) shared grid
        # Per issue, per option: (n_opts, K_e) log-alpha
        self.e_log_alpha: dict[str, np.ndarray] = {}
        for iid in codec.issue_ids:
            n_opts = codec.get_option_count(iid)
            self.e_log_alpha[iid] = np.zeros((n_opts, K_e)) - np.log(K_e)

    def estimated_weights(self) -> np.ndarray:
        """Posterior mean of issue weights, normalized to sum=1. Shape (n_issues,)."""
        raw = np.empty(self.n_issues)
        for i in range(self.n_issues):
            # E[w_i] = sum_k exp(log_alpha_k) * w_grid_k
            alpha_linear = np.exp(_log_normalize(self.w_log_alpha[i]))
            raw[i] = np.dot(alpha_linear, self.w_grid)
        total = raw.sum()
        if total > 0:
            return raw / total
        return np.full(self.n_issues, 1.0 / self.n_issues)

    def estimated_evals(self, issue_id: str) -> np.ndarray:
        """Posterior mean of evaluation values for each option. Shape (n_opts,)."""
        la = self.e_log_alpha.get(issue_id)
        if la is None:
            return np.array([0.5])
        result = np.empty(la.shape[0])
        for j in range(la.shape[0]):
            alpha_linear = np.exp(_log_normalize(la[j]))
            result[j] = np.dot(alpha_linear, self.e_grid)
        # Normalize so max=1, min=0
        r_min, r_max = result.min(), result.max()
        if r_max > r_min:
            result = (result - r_min) / (r_max - r_min)
        return result


# ---------------------------------------------------------------------------
# StepwiseConcessionLikelihood — P(b_t | theta) via Gaussian on concession
# ---------------------------------------------------------------------------


class StepwiseConcessionLikelihood:
    """Likelihood function assuming opponents concede gradually (Eq. 10).

    The likelihood is higher when the estimated concession (drop in opponent
    utility) follows a small, gradual pattern.
    """

    def __init__(self, sigma: float = 0.1, gamma: float = 0.1):
        self.sigma = sigma
        self.gamma = gamma
        self._log_floor = np.log(1e-300)

    def _compute_utility(
        self,
        bid: np.ndarray,
        weights: np.ndarray,
        evals: list[np.ndarray],
        codec: IssueCodec,
    ) -> float:
        """U(b) = sum_i w_i * e^i(b[i])."""
        u = 0.0
        for i, iid in enumerate(codec.issue_ids):
            j = codec.nearest_option_index(iid, bid[i])
            e = evals[i]
            ev = e[j] if j < len(e) else 0.5
            u += weights[i] * ev
        return u

    def _concession_delta(
        self,
        bid_t: np.ndarray,
        bid_prev: np.ndarray,
        weights: np.ndarray,
        evals: list[np.ndarray],
        codec: IssueCodec,
    ) -> float:
        """Compute concession: U(b_{t-1}) - U(b_t). Positive = opponent conceded."""
        u_t = self._compute_utility(bid_t, weights, evals, codec)
        u_prev = self._compute_utility(bid_prev, weights, evals, codec)
        return u_prev - u_t

    def _log_likelihood_from_delta(self, delta: float) -> float:
        """Gaussian log-likelihood on concession delta (Eq. 10).

        Positive delta = opponent conceded (their utility decreased).
        Negative delta = opponent improved (their utility increased, also informative).
        """
        if abs(delta) < self.gamma:
            # Very small change — not informative enough
            return 0.0
        # Gaussian centered at 0: larger magnitude = less likely = more discriminative
        return max(-delta**2 / (2 * self.sigma**2), self._log_floor)

    def weight_log_likelihoods(
        self,
        issue_idx: int,
        bid_t: np.ndarray,
        bid_prev: Optional[np.ndarray],
        w_grid: np.ndarray,
        w_current: np.ndarray,
        evals: list[np.ndarray],
        codec: IssueCodec,
    ) -> np.ndarray:
        """Log-likelihood for each weight hypothesis k of issue issue_idx."""
        K = len(w_grid)
        if bid_prev is None:
            return np.zeros(K)  # uniform — no information from first bid

        ll = np.empty(K)
        for k in range(K):
            w_test = w_current.copy()
            w_test[issue_idx] = w_grid[k]
            w_sum = w_test.sum()
            if w_sum > 0:
                w_test /= w_sum
            delta = self._concession_delta(bid_t, bid_prev, w_test, evals, codec)
            ll[k] = self._log_likelihood_from_delta(delta)
        return ll

    def eval_log_likelihoods(
        self,
        issue_id: str,
        option_idx: int,
        bid_t: np.ndarray,
        bid_prev: Optional[np.ndarray],
        e_grid: np.ndarray,
        e_current: np.ndarray,
        weights: np.ndarray,
        all_evals: list[np.ndarray],
        codec: IssueCodec,
        issue_pos: int,
    ) -> np.ndarray:
        """Log-likelihood for each eval hypothesis k of option option_idx in issue."""
        K = len(e_grid)
        if bid_prev is None:
            return np.zeros(K)

        ll = np.empty(K)
        for k in range(K):
            # Substitute hypothesis value for this option's evaluation
            evals_copy = [e.copy() for e in all_evals]
            evals_copy[issue_pos] = evals_copy[issue_pos].copy()
            if option_idx < len(evals_copy[issue_pos]):
                evals_copy[issue_pos][option_idx] = e_grid[k]
            delta = self._concession_delta(bid_t, bid_prev, weights, evals_copy, codec)
            ll[k] = self._log_likelihood_from_delta(delta)
        return ll


# ---------------------------------------------------------------------------
# ConditionalUpdater — iterative Bayesian update (Algorithm 2)
# ---------------------------------------------------------------------------


class ConditionalUpdater:
    """Iterative conditional Bayesian update (Eq. 9, Algorithm 2).

    Each parameter's posterior is conditioned on current estimates of all
    other parameters, iterated until convergence.
    """

    def __init__(self, convergence_threshold: float = 0.01, max_iterations: int = 20):
        self.convergence_threshold = convergence_threshold
        self.max_iterations = max_iterations

    def update(
        self,
        hs: HypothesisSpace,
        bid_t: np.ndarray,
        bid_prev: Optional[np.ndarray],
        likelihood: StepwiseConcessionLikelihood,
        codec: IssueCodec,
    ) -> int:
        """Run the iterative conditional update. Returns iterations to converge."""
        for iteration in range(1, self.max_iterations + 1):
            old_weights = hs.estimated_weights().copy()
            old_evals = {iid: hs.estimated_evals(iid).copy() for iid in codec.issue_ids}

            # Current evaluation estimates for likelihood computation
            current_evals = [hs.estimated_evals(iid) for iid in codec.issue_ids]

            # --- Phase 1: Update weight distributions ---
            for i in range(hs.n_issues):
                ll = likelihood.weight_log_likelihoods(
                    issue_idx=i,
                    bid_t=bid_t,
                    bid_prev=bid_prev,
                    w_grid=hs.w_grid,
                    w_current=hs.estimated_weights(),
                    evals=current_evals,
                    codec=codec,
                )
                hs.w_log_alpha[i] = _log_normalize(hs.w_log_alpha[i] + ll)

            # --- Phase 2: Update evaluation distributions ---
            current_weights = hs.estimated_weights()
            current_evals = [hs.estimated_evals(iid) for iid in codec.issue_ids]

            for pos, iid in enumerate(codec.issue_ids):
                n_opts = codec.get_option_count(iid)
                for j in range(n_opts):
                    ll = likelihood.eval_log_likelihoods(
                        issue_id=iid,
                        option_idx=j,
                        bid_t=bid_t,
                        bid_prev=bid_prev,
                        e_grid=hs.e_grid,
                        e_current=hs.estimated_evals(iid),
                        weights=current_weights,
                        all_evals=current_evals,
                        codec=codec,
                        issue_pos=pos,
                    )
                    hs.e_log_alpha[iid][j] = _log_normalize(hs.e_log_alpha[iid][j] + ll)

            # --- Convergence check ---
            new_weights = hs.estimated_weights()
            delta_w = np.max(np.abs(new_weights - old_weights))

            delta_e = 0.0
            for iid in codec.issue_ids:
                new_e = hs.estimated_evals(iid)
                old_e = old_evals[iid]
                if len(new_e) == len(old_e):
                    delta_e = max(delta_e, np.max(np.abs(new_e - old_e)))

            if max(delta_w, delta_e) < self.convergence_threshold:
                return iteration

        return self.max_iterations


# ---------------------------------------------------------------------------
# InverseTransformResampler — regenerate hypotheses (Algorithm 1)
# ---------------------------------------------------------------------------


class InverseTransformResampler:
    """Resample hypotheses via inverse transform when ESS drops (Algorithm 1)."""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def _ess(self, log_alpha: np.ndarray) -> float:
        """Effective sample size from log-weights."""
        log_norm = _log_normalize(log_alpha)
        return float(np.exp(-_logsumexp(2 * log_norm)))

    def _resample_1d(self, log_alpha: np.ndarray) -> np.ndarray:
        """Resample a single parameter's hypothesis distribution."""
        K = len(log_alpha)
        ess = self._ess(log_alpha)
        if ess / K >= self.threshold:
            return log_alpha  # No resampling needed

        # Build CDF from normalized weights
        weights = np.exp(_log_normalize(log_alpha))
        cdf = np.cumsum(weights)
        cdf[-1] = 1.0  # Ensure exact 1.0

        # Systematic resampling: evenly spaced samples
        u = np.linspace(0.5 / K, 1.0 - 0.5 / K, K)
        indices = np.searchsorted(cdf, u)
        indices = np.clip(indices, 0, K - 1)

        # New uniform weights on resampled hypotheses
        new_log_alpha = np.full(K, -np.log(K))
        # Count how many times each hypothesis is selected
        for idx in indices:
            new_log_alpha[idx] = np.logaddexp(new_log_alpha[idx], -np.log(K))
        return _log_normalize(new_log_alpha)

    def maybe_resample(self, hs: HypothesisSpace) -> bool:
        """Check and resample all parameter distributions if needed."""
        resampled = False

        # Weight parameters
        for i in range(hs.n_issues):
            new = self._resample_1d(hs.w_log_alpha[i])
            if not np.array_equal(new, hs.w_log_alpha[i]):
                hs.w_log_alpha[i] = new
                resampled = True

        # Evaluation parameters
        for iid in hs.codec.issue_ids:
            la = hs.e_log_alpha[iid]
            for j in range(la.shape[0]):
                new = self._resample_1d(la[j])
                if not np.array_equal(new, la[j]):
                    la[j] = new
                    resampled = True

        return resampled


# ---------------------------------------------------------------------------
# OpponentModel — top-level orchestrator
# ---------------------------------------------------------------------------


class OpponentModel:
    """Bayesian opponent model using conditional inference (BCI).

    One instance per (observer, target) party pair.
    """

    def __init__(
        self,
        issues: list[Issue],
        opponent_id: str,
        K_w: int = 11,
        K_e: int = 11,
        sigma: float = 0.05,
        gamma: float = 0.01,
        convergence_threshold: float = 0.01,
        max_iterations: int = 20,
        resample_threshold: float = 0.5,
    ):
        self.opponent_id = opponent_id
        self.codec = IssueCodec(issues)
        self.hs = HypothesisSpace(self.codec, K_w=K_w, K_e=K_e)
        # Lower sigma/gamma than paper defaults — OANP agents make small
        # concession steps, so we need finer discrimination
        self.likelihood = StepwiseConcessionLikelihood(sigma=sigma, gamma=gamma)
        self.updater = ConditionalUpdater(convergence_threshold, max_iterations)
        self.resampler = InverseTransformResampler(resample_threshold)

        self._bid_history: list[np.ndarray] = []
        self._raw_bids: list[dict[str, str]] = []
        self._update_count: int = 0
        self._concession_baseline: Optional[np.ndarray] = None

    def update(self, bid: dict[str, str]) -> None:
        """Observe an opponent bid and update the posterior.

        Safe to call repeatedly. Wraps all computation in error handling.
        """
        try:
            self._do_update(bid)
        except Exception:
            logger.warning("BCI update failed for opponent %s", self.opponent_id, exc_info=True)

    def _do_update(self, bid: dict[str, str]) -> None:
        bid_encoded = self.codec.encode_bid(bid)

        # --- First-bid heuristic: seed evals and weights from revealed preferences ---
        # The opponent's first bid breaks the uniform symmetry. They propose
        # values they prefer → bias eval priors toward those values.
        if self._update_count == 0:
            self._seed_from_first_bid(bid_encoded)

        # Determine previous bid for concession computation
        bid_prev = self._concession_baseline

        # Non-monotonic detection: if opponent's estimated utility increased
        # significantly, they may have retracted a concession. Reset baseline.
        # Note: small increases are normal noise and should be tolerated.
        if bid_prev is not None:
            weights = self.hs.estimated_weights()
            evals = [self.hs.estimated_evals(iid) for iid in self.codec.issue_ids]
            u_cur = self.likelihood._compute_utility(bid_encoded, weights, evals, self.codec)
            u_prev = self.likelihood._compute_utility(bid_prev, weights, evals, self.codec)
            if u_cur > u_prev + 0.05:
                # Opponent retracted concession — reset baseline
                bid_prev = None

        # Store
        self._bid_history.append(bid_encoded)
        self._raw_bids.append(bid)
        self._update_count += 1

        # Run conditional Bayesian update
        self.updater.update(self.hs, bid_encoded, bid_prev, self.likelihood, self.codec)

        # Resample if particle degeneracy detected
        self.resampler.maybe_resample(self.hs)

        # Update concession baseline
        self._concession_baseline = bid_encoded

        # NaN safety check
        if not np.all(np.isfinite(self.hs.w_log_alpha)):
            logger.warning("NaN detected in weight log-alpha, resetting to uniform")
            self.hs.w_log_alpha[:] = -np.log(self.hs.K_w)

    def _seed_from_first_bid(self, bid_encoded: np.ndarray) -> None:
        """Seed hypothesis priors from the first observed bid.

        The opponent's opening bid reveals preferences:
        - Issues where they bid far from center → likely high weight
        - The specific option they chose → likely high evaluation
        This breaks the uniform symmetry that prevents learning.
        """
        # 1. Seed weight priors: mild extremity-based bias.
        # Issues where opponent bid far from center get slight weight boost.
        # Very mild — the conditional updater does the real differentiation.
        for i, iid in enumerate(self.codec.issue_ids):
            c = self.codec._codecs[iid]
            if c.issue_type == "categorical":
                ext = 0.2  # mild default for categoricals
            else:
                ext = abs(bid_encoded[i] - 0.5) * 2
            if ext > 0.1:
                bias = 1.0 + ext * 2.0
                boosted = self.hs.w_log_alpha[i] + np.log(
                    np.where(self.hs.w_grid > 0.3, bias, 1.0 / max(bias, 0.01))
                )
                self.hs.w_log_alpha[i] = _log_normalize(boosted)

        # 2. Seed eval priors: the chosen option gets higher evaluation
        for i, iid in enumerate(self.codec.issue_ids):
            j = self.codec.nearest_option_index(iid, bid_encoded[i])
            n_opts = self.codec.get_option_count(iid)
            la = self.hs.e_log_alpha[iid]
            for opt_idx in range(n_opts):
                if opt_idx == j:
                    # Chosen option: bias toward high evaluation (0.7-1.0)
                    boost = np.where(self.hs.e_grid > 0.5, 2.0, 0.5)
                else:
                    # Unchosen options: slight bias toward lower evaluation
                    dist = abs(opt_idx - j) / max(n_opts - 1, 1)
                    boost = np.where(self.hs.e_grid < 0.5, 1.0 + dist, 1.0 / (1.0 + dist))
                la[opt_idx] = _log_normalize(la[opt_idx] + np.log(boost))

    def estimate_utility(self, bid: dict[str, str]) -> float:
        """Predict opponent's utility for any bid."""
        bid_encoded = self.codec.encode_bid(bid)
        weights = self.hs.estimated_weights()
        evals = [self.hs.estimated_evals(iid) for iid in self.codec.issue_ids]
        return self.likelihood._compute_utility(bid_encoded, weights, evals, self.codec)

    def get_estimated_weights(self) -> dict[str, float]:
        """Return estimated issue weights as {issue_id: weight}."""
        weights = self.hs.estimated_weights()
        return {iid: float(weights[i]) for i, iid in enumerate(self.codec.issue_ids)}

    def get_estimated_evaluations(self) -> dict[str, dict[str, float]]:
        """Return estimated option evaluations as {issue_id: {option: score}}."""
        result = {}
        for iid in self.codec.issue_ids:
            evals = self.hs.estimated_evals(iid)
            labels = self.codec.get_option_labels(iid)
            result[iid] = {
                labels[j]: float(evals[j]) for j in range(min(len(labels), len(evals)))
            }
        return result

    def get_confidence(self) -> float:
        """Confidence based on observation count and posterior concentration.

        Returns 0.0-0.85 (capped — never claim certainty).
        """
        if self._update_count == 0:
            return 0.0

        # Factor 1: observation count (saturates at 10 bids)
        obs_factor = min(1.0, self._update_count / 10.0)

        # Factor 2: posterior concentration (low ESS ratio = concentrated = confident)
        ess_ratios = []
        for i in range(self.hs.n_issues):
            log_norm = _log_normalize(self.hs.w_log_alpha[i])
            ess = float(np.exp(-_logsumexp(2 * log_norm)))
            ess_ratios.append(ess / self.hs.K_w)

        avg_concentration = 1.0 - np.mean(ess_ratios)
        confidence = obs_factor * max(0.0, avg_concentration)

        return min(0.85, confidence)

    def to_belief_model(self) -> BeliefModel:
        """Convert internal state to the existing Pydantic BeliefModel type."""
        weights = self.get_estimated_weights()
        confidence = self.get_confidence()

        # Estimate BATNA utility as min utility of opponent's own bids (discounted)
        estimated_batna = None
        if len(self._raw_bids) >= 2:
            utilities = [self.estimate_utility(b) for b in self._raw_bids]
            estimated_batna = min(utilities) * 0.85

        # Infer interests from high-weight issues
        estimated_interests = []
        evals = self.get_estimated_evaluations()
        for iid, w in sorted(weights.items(), key=lambda x: -x[1]):
            if w > 0.15:
                issue_evals = evals.get(iid, {})
                top_option = max(issue_evals, key=issue_evals.get, default="unknown") if issue_evals else "unknown"
                estimated_interests.append({
                    "issue_id": iid,
                    "description": f"Values {iid} highly, prefers {top_option}",
                    "estimated_weight": w,
                    "top_option": top_option,
                })

        # Evidence: move indices used
        evidence = [f"bid_{i}" for i in range(len(self._raw_bids))]

        return BeliefModel(
            target_party_id=self.opponent_id,
            estimated_interests=estimated_interests,
            estimated_batna_utility=estimated_batna,
            estimated_priorities=weights,
            confidence=confidence,
            evidence=evidence[-20:],  # cap at 20
        )

    def rebuild_from_bids(self, bids: list[dict[str, str]]) -> None:
        """Replay a sequence of bids to reconstruct state (for session resume)."""
        for bid in bids:
            self._do_update(bid)
