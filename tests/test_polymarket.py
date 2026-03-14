"""
tests/test_polymarket.py
========================
Unit tests for src/core/polymarket.polymarket_edge().

Covered behaviors:
    - market_prob = 0: must raise ValueError (function validates input domain)
    - model_prob > market_prob: edge is positive, kelly_fraction > 0
    - model_prob < market_prob: edge is negative, kelly_fraction = 0
    - kelly_fraction is never negative under any inputs
    - unconditional (margem_1t) and conditional (margem_<candidate>) modes
    - missing margin column: raises KeyError

All tests use the df1_stub fixture from conftest.py — no simulation engine is invoked, keeping these tests fast and isolated.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.core.polymarket import polymarket_edge


# ─── TestPolymarketEdge ───────────────────────────────────────────────────────

class TestPolymarketEdge:
    """Unit tests for polymarket_edge(df1, threshold, market_prob, candidate)."""

    # -- Input validation -----------------------------------------------------

    def test_market_prob_zero_raises_value_error(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """market_prob = 0 must raise ValueError, not ZeroDivisionError.

        The Kelly formula contains (1 / market_prob); a zero value would cause a ZeroDivisionError deep inside the function if not caught explicitly.
        The function must validate the domain (0, 1] upfront and raise a descriptive ValueError instead.
        """
        with pytest.raises(ValueError, match=r"market_prob"):
            polymarket_edge(df1_stub, threshold=10.0, market_prob=0.0)

    def test_market_prob_negative_raises_value_error(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """Negative market_prob must also raise ValueError."""
        with pytest.raises(ValueError):
            polymarket_edge(df1_stub, threshold=10.0, market_prob=-0.1)

    def test_market_prob_above_one_raises_value_error(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """market_prob > 1 is outside the probability domain — must raise."""
        with pytest.raises(ValueError):
            polymarket_edge(df1_stub, threshold=10.0, market_prob=1.1)

    def test_missing_margem_1t_raises_key_error(self) -> None:
        """A df1 without 'margem_1t' must raise KeyError when candidate=None."""
        df_bad = pd.DataFrame({"vencedor": ["Lula"] * 10})
        with pytest.raises(KeyError, match="margem_1t"):
            polymarket_edge(df_bad, threshold=10.0, market_prob=0.5)

    def test_missing_candidate_column_raises_key_error(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """Requesting a candidate margin that does not exist must raise KeyError."""
        with pytest.raises(KeyError, match="margem_CandidatoInexistente"):
            polymarket_edge(
                df1_stub,
                threshold=10.0,
                market_prob=0.5,
                candidate="CandidatoInexistente",
            )

    # -- Positive edge --------------------------------------------------------

    def test_positive_edge_when_model_above_market(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """When model_prob > market_prob, edge must be positive.

        df1_stub has Lula leading with large margins in most simulations.
        Setting market_prob very low (0.10) and a low threshold (5pp) ensures model_prob >> market_prob and edge > 0.
        """
        result = polymarket_edge(df1_stub, threshold=5.0, market_prob=0.10)
        assert result["edge"] > 0, (
            f"Expected positive edge; got edge={result['edge']}, "
            f"model_prob={result['model_prob']}, market_prob={result['market_prob']}"
        )

    def test_positive_edge_implies_positive_kelly(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """Positive edge must yield a positive kelly_fraction."""
        result = polymarket_edge(df1_stub, threshold=5.0, market_prob=0.10)
        assert result["kelly_fraction"] > 0, (
            "kelly_fraction must be positive when edge > 0."
        )

    def test_edge_equals_model_minus_market(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """edge must equal model_prob - market_prob (within rounding tolerance)."""
        result = polymarket_edge(df1_stub, threshold=5.0, market_prob=0.30)
        expected_edge = round(result["model_prob"] - result["market_prob"], 4)
        assert result["edge"] == pytest.approx(expected_edge, abs=1e-4)

    # -- Negative edge --------------------------------------------------------

    def test_negative_edge_when_model_below_market(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """When model_prob < market_prob, edge must be negative.

        Using a very high threshold (99pp) ensures P(margin > 99pp) ≈ 0, while market_prob = 0.80 is far above the model estimate.
        """
        result = polymarket_edge(df1_stub, threshold=99.0, market_prob=0.80)
        assert result["edge"] < 0, (
            f"Expected negative edge; got edge={result['edge']}, "
            f"model_prob={result['model_prob']}"
        )

    def test_negative_edge_implies_zero_kelly(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """When edge <= 0, kelly_fraction must be exactly 0.0.

        Half-Kelly is only meaningful when there is a positive edge.
        A negative kelly_fraction would imply betting on the wrong side, which the function must never return.
        """
        result = polymarket_edge(df1_stub, threshold=99.0, market_prob=0.80)
        assert result["kelly_fraction"] == 0.0

    # -- kelly_fraction is never negative ------------------------------------

    def test_kelly_fraction_never_negative_parametric(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """kelly_fraction must be >= 0 across a range of market_prob values.

        Tests a grid of (threshold, market_prob) combinations to verify the invariant holds regardless of whether edge is positive or negative.
        """
        thresholds = [1.0, 5.0, 10.0, 15.0, 25.0]
        market_probs = [0.01, 0.10, 0.30, 0.50, 0.70, 0.90, 0.99]
        for threshold in thresholds:
            for mp in market_probs:
                result = polymarket_edge(df1_stub, threshold=threshold, market_prob=mp)
                assert result["kelly_fraction"] >= 0.0, (
                    f"kelly_fraction < 0 for threshold={threshold}, market_prob={mp}: "
                    f"got {result['kelly_fraction']}"
                )

    # -- Conditional mode (candidate) ----------------------------------------

    def test_conditional_mode_uses_candidate_margin_column(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """When candidate='Lula', the function must use 'margem_Lula', not 'margem_1t'.

        The conditional model_prob should differ from the unconditional one because 'margem_Lula' is signed (negative when Lula is trailing) while 'margem_1t' is always positive.
        """
        result_unconditional = polymarket_edge(
            df1_stub, threshold=5.0, market_prob=0.50
        )
        result_conditional = polymarket_edge(
            df1_stub, threshold=5.0, market_prob=0.50, candidate="Lula"
        )
        # Signed margin <= unsigned margin for any given simulation, so
        # conditional model_prob <= unconditional model_prob
        assert result_conditional["model_prob"] <= result_unconditional["model_prob"]

    def test_conditional_candidate_echo_in_result(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """The 'candidate' field in the result must echo the argument."""
        result = polymarket_edge(
            df1_stub, threshold=5.0, market_prob=0.50, candidate="Lula"
        )
        assert result["candidate"] == "Lula"

    def test_unconditional_candidate_is_none(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """When candidate is not provided, the echo must be None."""
        result = polymarket_edge(df1_stub, threshold=5.0, market_prob=0.50)
        assert result["candidate"] is None

    # -- Return contract ------------------------------------------------------

    def test_return_dict_has_all_required_keys(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """Result dict must contain all documented keys."""
        result = polymarket_edge(df1_stub, threshold=10.0, market_prob=0.50)
        required = {
            "model_prob", "market_prob", "edge",
            "kelly_fraction", "threshold_pp", "candidate", "n_sim",
        }
        assert required <= result.keys()

    def test_n_sim_echoes_dataframe_length(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """n_sim in the result must equal len(df1)."""
        result = polymarket_edge(df1_stub, threshold=10.0, market_prob=0.50)
        assert result["n_sim"] == len(df1_stub)

    def test_model_prob_is_between_zero_and_one(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """model_prob must always be in [0, 1]."""
        for threshold in [0.0, 5.0, 50.0, 99.0]:
            result = polymarket_edge(
                df1_stub, threshold=threshold, market_prob=0.50
            )
            assert 0.0 <= result["model_prob"] <= 1.0

    def test_threshold_pp_echoes_argument(
        self, df1_stub: pd.DataFrame
    ) -> None:
        """threshold_pp in the result must echo the threshold argument."""
        result = polymarket_edge(df1_stub, threshold=17.5, market_prob=0.50)
        assert result["threshold_pp"] == 17.5
