"""
tests/test_aggregation.py
=========================
Unit tests for src/core/aggregation.py.

Covers:
    - calcular_peso_temporal(): temporal weighting via exponential decay
    - detectar_outliers(): modified z-score outlier detection

All tests are pure (no disk I/O, no network). The reference date is always
injected explicitly — never read from date.today() — so tests remain
deterministic regardless of when the CI runs.

Import contract:
    These tests target src/core/aggregation, which is the v3 home for the
    functions currently in simulation_v2.py. The Core Architect must migrate
    calcular_peso_temporal() and detectar_outliers() there before this test
    module can be collected.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pytest

from src.core.aggregation import calcular_peso_temporal, detectar_outliers


# ─── calcular_peso_temporal ───────────────────────────────────────────────────

class TestCalcularPesoTemporal:
    """Tests for calcular_peso_temporal(data_pesquisa, data_referencia, tau=7).

    Formula: peso = exp(-max(0, days_ago) / tau)

    Edge cases that must be handled without raising:
        - None  → treated as most recent (peso = 1.0)
        - float (NaN read from CSV) → treated as most recent (peso = 1.0)
        - string in YYYY-MM-DD format → parsed before calculation
        - future date → days_ago clamped to 0, peso = 1.0
    """

    REF = date(2026, 3, 7)  # frozen reference date; never use date.today()

    # -- Happy path -----------------------------------------------------------

    def test_today_returns_one(self) -> None:
        """Poll dated on the reference date itself must have weight exactly 1.0.

        exp(-0/7) = exp(0) = 1.0.
        """
        peso = calcular_peso_temporal(self.REF, self.REF)
        assert peso == pytest.approx(1.0)

    def test_seven_days_ago_returns_one_over_e(self) -> None:
        """Poll dated 7 days before reference must have weight 1/e.

        exp(-7/7) = exp(-1) ≈ 0.36787944.
        This is the canonical decay constant: tau = 7 days means a week-old
        poll retains ~37% of the weight of a same-day poll.
        """
        data_pesquisa = self.REF - timedelta(days=7)
        peso = calcular_peso_temporal(data_pesquisa, self.REF)
        assert peso == pytest.approx(1 / math.e, rel=1e-6)

    def test_fourteen_days_ago_returns_one_over_e_squared(self) -> None:
        """Poll dated 14 days before reference must have weight 1/e².

        exp(-14/7) = exp(-2) ≈ 0.13533528.
        Validates that the decay compounds correctly across multiple tau periods.
        """
        data_pesquisa = self.REF - timedelta(days=14)
        peso = calcular_peso_temporal(data_pesquisa, self.REF)
        assert peso == pytest.approx(math.exp(-2), rel=1e-6)

    def test_weight_is_between_zero_and_one_for_past_dates(self) -> None:
        """Weight must stay in (0, 1] for any past date."""
        for days_ago in [1, 7, 30, 90, 180, 365]:
            data_pesquisa = self.REF - timedelta(days=days_ago)
            peso = calcular_peso_temporal(data_pesquisa, self.REF)
            assert 0 < peso <= 1.0, (
                f"Expected weight in (0, 1] for {days_ago} days ago, got {peso}"
            )

    def test_weight_is_monotonically_decreasing_with_age(self) -> None:
        """Older polls must receive strictly lower weight than newer ones."""
        weights = [
            calcular_peso_temporal(self.REF - timedelta(days=d), self.REF)
            for d in [0, 7, 14, 30]
        ]
        assert weights == sorted(weights, reverse=True), (
            "Weights must decrease as polls get older."
        )

    def test_string_date_yyyy_mm_dd(self) -> None:
        """String in YYYY-MM-DD format must be parsed and produce the same
        result as the equivalent date object."""
        data_str = "2026-02-28"  # 7 days before REF
        data_obj = date(2026, 2, 28)
        peso_str = calcular_peso_temporal(data_str, self.REF)
        peso_obj = calcular_peso_temporal(data_obj, self.REF)
        assert peso_str == pytest.approx(peso_obj)

    def test_custom_tau_changes_decay_rate(self) -> None:
        """Setting tau=14 must halve the decay rate relative to tau=7."""
        data_pesquisa = self.REF - timedelta(days=7)
        peso_tau7  = calcular_peso_temporal(data_pesquisa, self.REF, tau=7)
        peso_tau14 = calcular_peso_temporal(data_pesquisa, self.REF, tau=14)
        # With tau=14 and 7 days ago: exp(-7/14) = exp(-0.5) ≈ 0.6065
        # With tau=7 and 7 days ago:  exp(-7/7)  = exp(-1)   ≈ 0.3679
        assert peso_tau14 > peso_tau7
        assert peso_tau14 == pytest.approx(math.exp(-0.5), rel=1e-6)

    # -- Edge cases: inputs that must NOT raise --------------------------------

    def test_none_returns_one(self) -> None:
        """None input (poll with no recorded date) must return 1.0.

        Semantics: missing date → treat poll as maximally recent so it is
        not penalized relative to dated polls.
        """
        peso = calcular_peso_temporal(None, self.REF)
        assert peso == pytest.approx(1.0)

    def test_float_nan_returns_one(self) -> None:
        """float('nan') input (NaN read from CSV as float) must return 1.0.

        Pandas reads empty cells in a string column as float NaN. This must
        not propagate as NaN into the weight array.
        """
        peso = calcular_peso_temporal(float("nan"), self.REF)
        assert peso == pytest.approx(1.0)

    def test_future_date_returns_one(self) -> None:
        """A poll dated in the future must return 1.0, not a value > 1.

        dias_atras is clamped to max(0, ...) before the exponent, so future
        dates are treated identically to same-day polls.
        """
        data_futura = self.REF + timedelta(days=30)
        peso = calcular_peso_temporal(data_futura, self.REF)
        assert peso == pytest.approx(1.0)

    def test_one_day_future_returns_one(self) -> None:
        """A poll dated one day ahead must also return 1.0 (boundary check)."""
        data_amanha = self.REF + timedelta(days=1)
        peso = calcular_peso_temporal(data_amanha, self.REF)
        assert peso == pytest.approx(1.0)

    def test_return_type_is_float(self) -> None:
        """Return value must always be a plain Python float, never np.floating."""
        data_pesquisa = self.REF - timedelta(days=7)
        peso = calcular_peso_temporal(data_pesquisa, self.REF)
        # np.exp returns np.float64; callers may rely on float-compatible type
        assert isinstance(peso, float | np.floating)


# ─── detectar_outliers ────────────────────────────────────────────────────────

class TestDetectarOutliers:
    """Tests for detectar_outliers(valores, threshold=2.5).

    Method: modified z-score using Median Absolute Deviation (MAD).
        z_i = 0.6745 * (x_i - median) / MAD
        Outlier if |z_i| > threshold.

    Fallback rules (must not raise):
        - len(valores) < 3: return all-False (insufficient data for MAD)
        - MAD == 0 (all values equal): return all-False (no deviation to measure)
    """

    # -- Insufficient data (len < 3) ------------------------------------------

    def test_single_element_no_outliers(self) -> None:
        """A single-element array cannot contain an outlier by definition."""
        result = detectar_outliers(np.array([38.0]))
        assert result.dtype == bool
        assert result.shape == (1,)
        assert not result.any()

    def test_two_elements_no_outliers(self) -> None:
        """Two-element array: MAD computation is unreliable; return all False."""
        result = detectar_outliers(np.array([38.0, 30.0]))
        assert result.shape == (2,)
        assert not result.any()

    # -- MAD == 0 (all values identical) --------------------------------------

    def test_all_equal_no_outliers(self) -> None:
        """When all values are identical, MAD = 0 and no outlier can be declared."""
        result = detectar_outliers(np.array([38.0, 38.0, 38.0, 38.0, 38.0]))
        assert not result.any()

    def test_all_equal_three_elements(self) -> None:
        """Minimum three-element case with identical values must also return all False."""
        result = detectar_outliers(np.array([10.0, 10.0, 10.0]))
        assert not result.any()

    # -- Normal distributions (no outlier expected) ---------------------------

    def test_tight_cluster_no_outliers(self) -> None:
        """Polls clustered within 2pp of each other must not trigger any outlier."""
        valores = np.array([37.0, 38.0, 37.5, 38.5, 37.2])
        result = detectar_outliers(valores)
        assert not result.any()

    def test_moderate_spread_no_outliers(self) -> None:
        """Values with moderate spread (within ~2 standard deviations) should
        not be flagged when none is extreme relative to the MAD."""
        valores = np.array([30.0, 32.0, 34.0, 36.0, 38.0])
        result = detectar_outliers(valores)
        assert not result.any()

    # -- Clear outlier --------------------------------------------------------

    def test_one_clear_outlier_detected(self) -> None:
        """One value far above a tight cluster must be flagged as an outlier.

        Scenario: Lula polls at 37–38% in three institutes; a fourth reading
        at 62% is a clear data anomaly (modified z-score >> 2.5).
        """
        valores = np.array([38.0, 37.0, 37.5, 62.0])
        result = detectar_outliers(valores)
        assert result.dtype == bool
        assert result[3], "Index 3 (62.0) must be detected as an outlier."
        assert result.sum() == 1, "Exactly one outlier must be flagged."

    def test_outlier_index_matches_anomalous_value(self) -> None:
        """The flagged index must correspond to the most extreme value."""
        valores = np.array([30.0, 31.0, 32.0, 30.5, 65.0])
        result = detectar_outliers(valores)
        outlier_indices = np.where(result)[0]
        assert 4 in outlier_indices, (
            f"Expected index 4 (value=65.0) to be flagged; got {outlier_indices}."
        )

    def test_low_outlier_also_detected(self) -> None:
        """An anomalously low value must be flagged, not only high ones.

        Modified z-score is symmetric around the median.
        """
        valores = np.array([38.0, 37.0, 38.5, 5.0])
        result = detectar_outliers(valores)
        assert result[3], "Index 3 (5.0) must be detected as a low outlier."

    def test_non_outliers_not_flagged(self) -> None:
        """Values within normal range must remain False when an outlier is present."""
        valores = np.array([38.0, 37.0, 37.5, 62.0])
        result = detectar_outliers(valores)
        assert not result[0]
        assert not result[1]
        assert not result[2]

    # -- Return type contract -------------------------------------------------

    def test_returns_boolean_array(self) -> None:
        """Return value must be a NumPy boolean array of the same length as input."""
        valores = np.array([38.0, 37.0, 62.0, 37.5, 38.2])
        result = detectar_outliers(valores)
        assert isinstance(result, np.ndarray)
        assert result.dtype == bool
        assert len(result) == len(valores)

    def test_custom_threshold_stricter(self) -> None:
        """A lower threshold must flag more values as outliers than the default."""
        # With a tight cluster plus one mildly-high value
        valores = np.array([38.0, 37.0, 37.5, 45.0])
        result_default  = detectar_outliers(valores, threshold=2.5)
        result_stricter = detectar_outliers(valores, threshold=1.0)
        # Stricter threshold must flag at least as many as the default
        assert result_stricter.sum() >= result_default.sum()

    def test_custom_threshold_lenient(self) -> None:
        """A very high threshold must flag nothing even for a clear outlier."""
        valores = np.array([38.0, 37.0, 37.5, 62.0])
        result = detectar_outliers(valores, threshold=100.0)
        assert not result.any()