"""
tests/test_simulation.py
Unit tests for src/core/simulation.simular_primeiro_turno().

Covered behaviors:
    - n_sim rows in output DataFrame
    - vote shares sum to 100% per simulation (within numerical tolerance)
    - alpha <= 0 floor: must not raise — function must apply a minimum floor and continue rather than propagate a ValueError to the caller

Note on the alpha <= 0 test
----------------------------
The current implementation raises ValueError when any votos_efetivos <= 0.
The planning spec (v3.0 Technical Planning, Dev 4 task 5) explicitly requires that this case be HANDLED WITHOUT RAISING — a floor must be applied instead, delegating the guard to the loader layer. These tests therefore serve as a specification: they will fail against the current implementation and pass once the floor is added to simular_primeiro_turno().
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.core.config import PollData, SimulationConfig
from src.core.simulation import (
    _calcular_desvio_ajustado,
    aplicar_teto_rejeicao,
    distribuir_indecisos,
    simular_primeiro_turno,
)


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _make_config(n_sim: int = 500, seed: int = 42) -> SimulationConfig:
    """Minimal SimulationConfig for unit tests.

    n_sim=500 keeps tests fast; seed=42 makes results deterministic.
    election_date set to 2026-10-04 (real election).
    """
    return SimulationConfig(
        csv_path=Path("tests/fixtures/pesquisas_minimal.csv"),
        n_sim=n_sim,
        seed=seed,
        use_bayesian=False,
        election_date=date(2026, 10, 4),
    )


def _make_poll_data(
    candidatos: list[str] | None = None,
    votos: list[float] | None = None,
    rejeicao: list[float] | None = None,
    desvio_base: float = 2.0,
    indecisos: float = 0.0,
) -> PollData:
    """Build a PollData with sensible defaults.

    Defaults: Lula 38%, Bolsonaro 30%, Outros 12%
    (does not need to sum to 100 — Dirichlet normalises automatically).
    """
    if candidatos is None:
        candidatos = ["Lula", "Bolsonaro", "Outros"]
    if votos is None:
        votos = [38.0, 30.0, 12.0]
    if rejeicao is None:
        rejeicao = [42.0, 48.0, 20.0]

    return PollData(
        candidatos=candidatos,
        votos_media=np.array(votos, dtype=float),
        rejeicao=np.array(rejeicao, dtype=float),
        desvio_base=desvio_base,
        indecisos=indecisos,
    )


# ─── TestSimularPrimeiroTurno ─────────────────────────────────────────────────

class TestSimularPrimeiroTurno:
    """Unit tests for simular_primeiro_turno(config, poll_data)."""

    # -- Output shape ---------------------------------------------------------

    def test_df_has_n_sim_rows(self) -> None:
        """Result DataFrame must have exactly config.n_sim rows.

        Each row is one independent Monte Carlo draw of the first round.
        """
        config = _make_config(n_sim=500)
        poll_data = _make_poll_data()
        result = simular_primeiro_turno(config, poll_data)
        assert len(result.df) == 500

    def test_n_sim_respected_across_values(self) -> None:
        """Row count must match n_sim for multiple distinct values."""
        poll_data = _make_poll_data()
        for n in [100, 250, 1_000]:
            config = _make_config(n_sim=n)
            result = simular_primeiro_turno(config, poll_data)
            assert len(result.df) == n, (
                f"Expected {n} rows for n_sim={n}, got {len(result.df)}"
            )

    def test_validos_final_shape(self) -> None:
        """validos_final must have shape (n_sim, n_valid_candidates).

        Valid candidates exclude 'Brancos' and 'Nulos' entries.
        """
        config = _make_config(n_sim=500)
        poll_data = _make_poll_data()
        result = simular_primeiro_turno(config, poll_data)
        n_validos = len(result.candidatos_validos)
        assert result.validos_final.shape == (500, n_validos)

    # -- Vote share sum -------------------------------------------------------

    def test_valid_vote_shares_sum_to_100_per_simulation(self) -> None:
        """Valid vote shares must sum to 100% in every simulation row.

        After the rejection ceiling and re-normalisation, each simulation
        must represent a complete probability distribution over valid
        candidates. Tolerance is 1e-6 to allow for floating-point rounding.
        """
        config = _make_config(n_sim=500)
        poll_data = _make_poll_data()
        result = simular_primeiro_turno(config, poll_data)
        row_sums = result.validos_final.sum(axis=1)
        np.testing.assert_allclose(
            row_sums,
            100.0,
            atol=1e-6,
            err_msg=(
                "Valid vote shares must sum to 100.0 in every simulation. "
                f"Min: {row_sums.min():.8f}, Max: {row_sums.max():.8f}"
            ),
        )

    def test_val_columns_sum_to_100_in_dataframe(self) -> None:
        """Columns ending in '_val' in result.df must also sum to 100 per row.

        This verifies that the DataFrame view is consistent with validos_final.
        """
        config = _make_config(n_sim=500)
        poll_data = _make_poll_data()
        result = simular_primeiro_turno(config, poll_data)
        val_cols = [c for c in result.df.columns if c.endswith("_val")]
        assert len(val_cols) >= 2, "Expected at least 2 '_val' columns in df."
        row_sums = result.df[val_cols].sum(axis=1)
        np.testing.assert_allclose(row_sums.values, 100.0, atol=1e-6)

    # -- Determinism ----------------------------------------------------------

    def test_same_seed_produces_identical_results(self) -> None:
        """Two runs with the same seed must produce byte-identical DataFrames."""
        config_a = _make_config(seed=99)
        config_b = _make_config(seed=99)
        poll_data = _make_poll_data()
        result_a = simular_primeiro_turno(config_a, poll_data)
        result_b = simular_primeiro_turno(config_b, poll_data)
        pd.testing.assert_frame_equal(result_a.df, result_b.df)


    def test_different_seeds_produce_different_results(self) -> None:
        """Different seeds should produce different simulated vote shares."""
        config_a = _make_config(seed=1)
        config_b = _make_config(seed=2)
        poll_data = _make_poll_data()

        result_a = simular_primeiro_turno(config_a, poll_data)
        result_b = simular_primeiro_turno(config_b, poll_data)

        # Compare simulated vote shares, not only the winner labels.
        colunas_votos = [
            c for c in result_a.df.columns
            if c.endswith("_val")
        ]

        assert colunas_votos, "Expected candidate vote-share columns."

        assert not result_a.df[colunas_votos].equals(
            result_b.df[colunas_votos]
        ), "Different seeds should produce different simulated vote shares."

    # -- Result structure -----------------------------------------------------

    def test_result_contains_required_df_columns(self) -> None:
        """result.df must contain the expected structural columns."""
        config = _make_config()
        poll_data = _make_poll_data()
        result = simular_primeiro_turno(config, poll_data)
        required = {"vencedor", "tem_2turno", "margem_1t", "lider_1t"}
        missing = required - set(result.df.columns)
        assert not missing, f"Missing columns in result.df: {missing}"

    def test_result_contains_signed_margin_columns(self) -> None:
        """A 'margem_<candidate>' column must exist for each valid candidate."""
        config = _make_config()
        poll_data = _make_poll_data()
        result = simular_primeiro_turno(config, poll_data)
        for cand in result.candidatos_validos:
            assert f"margem_{cand}" in result.df.columns, (
                f"Missing signed margin column for candidate '{cand}'."
            )

    def test_margem_1t_is_always_non_negative(self) -> None:
        """Unsigned first-round margin must be >= 0 in every simulation."""
        config = _make_config(n_sim=500)
        poll_data = _make_poll_data()
        result = simular_primeiro_turno(config, poll_data)
        assert (result.df["margem_1t"] >= 0).all(), (
            "margem_1t must be non-negative in all simulations."
        )

    def test_vencedor_is_always_a_valid_candidate(self) -> None:
        """Every 'vencedor' entry must be one of the valid candidate names."""
        config = _make_config(n_sim=500)
        poll_data = _make_poll_data()
        result = simular_primeiro_turno(config, poll_data)
        invalid = set(result.df["vencedor"]) - set(result.candidatos_validos)
        assert not invalid, f"Unexpected winners: {invalid}"

    def test_info_lim_1t_is_dict(self) -> None:
        """info_lim_1t must be a dict (may be empty if no ceiling was applied)."""
        config = _make_config()
        poll_data = _make_poll_data()
        result = simular_primeiro_turno(config, poll_data)
        assert isinstance(result.info_lim_1t, dict)

    # -- alpha <= 0 floor (specification test) --------------------------------

    def test_alpha_floor_does_not_raise(self) -> None:
        """When a candidate has votos_media = 0, the function must NOT raise.

        The loader (src/io/loader.py) is responsible for rejecting zero-vote
        candidates at load time. However, simular_primeiro_turno() must also
        be robust: if a zero or near-zero value somehow reaches the simulation
        (e.g. after undecided redistribution edge cases), it must apply a
        minimum floor to the alpha parameter instead of propagating ValueError.

        Expected floor behaviour: replace any alpha <= 0 with a small positive
        constant (e.g. 1e-6) before the Dirichlet draw so the simulation
        degrades gracefully rather than crashing.

        CONTRACT: This test is the specification. If it currently fails with
        ValueError, that signals the floor has not yet been implemented in
        simular_primeiro_turno(). Add the floor before the Dirichlet draw:

            alphas = np.maximum(alphas, 1e-6)
        """
        config = _make_config(n_sim=200)
        # Bolsonaro at 0.0 → alpha would be 0 before floor
        poll_data = _make_poll_data(votos=[38.0, 0.0, 12.0])

        # Must not raise — must return a valid FirstRoundResult
        result = simular_primeiro_turno(config, poll_data)
        assert len(result.df) == 200

    def test_near_zero_alpha_produces_valid_shares(self) -> None:
        """A candidate with votos_media = 0.001 must produce valid (non-NaN) shares."""
        config = _make_config(n_sim=200)
        poll_data = _make_poll_data(votos=[38.0, 0.001, 12.0])
        result = simular_primeiro_turno(config, poll_data)
        row_sums = result.validos_final.sum(axis=1)
        np.testing.assert_allclose(row_sums, 100.0, atol=1e-4)


class TestCalcularDesvioAjustado:
    """Tests for election-date-based uncertainty adjustment."""

    def test_returns_base_when_reference_is_election_day(self) -> None:
        election_date = date(2026, 10, 4)

        result = _calcular_desvio_ajustado(
            2.0, election_date, election_date
        )

        assert result == 2.0

    def test_returns_base_when_reference_is_after_election(self) -> None:
        result = _calcular_desvio_ajustado(
            2.0, date(2026, 10, 4), date(2026, 10, 5)
        )

        assert result == 2.0

    def test_increases_uncertainty_when_election_is_distant(self) -> None:
        result = _calcular_desvio_ajustado(
            2.0, date(2026, 10, 4), date(2026, 6, 6)
        )

        assert result == pytest.approx(4.0)


class TestAplicarTetoRejeicao:
    """Tests for rejection-based vote ceilings."""

    def test_limits_votes_above_ceiling(self) -> None:
        votos = np.array([[60.0, 30.0], [40.0, 50.0]])
        rejeicao = np.array([50.0, 20.0])
        candidatos = ["Candidato A", "Candidato B"]

        limitados, info = aplicar_teto_rejeicao(
            votos, rejeicao, candidatos
        )

        np.testing.assert_allclose(
            limitados, [[50.0, 30.0], [40.0, 50.0]]
        )
        assert info["Candidato A"]["n_simulacoes_limitadas"] == 1
        assert info["Candidato A"]["pct_simulacoes_limitadas"] == 50.0
        assert info["Candidato A"]["teto"] == 50.0
        assert info["Candidato A"]["rejeicao"] == 50.0
        assert "Candidato B" not in info

    def test_excludes_blank_null_and_zero_rejection_from_diagnostics(
        self,
    ) -> None:
        votos = np.array([[90.0, 90.0, 90.0]])
        rejeicao = np.array([10.0, 10.0, 0.0])
        candidatos = ["Brancos", "Nulos", "Candidato A"]

        limitados, info = aplicar_teto_rejeicao(
            votos, rejeicao, candidatos
        )

        np.testing.assert_allclose(limitados, [[90.0, 90.0, 90.0]])
        assert info == {}


class TestDistribuirIndecisos:
    """Tests for undecided-vote redistribution."""

    def test_zero_undecided_returns_copy_and_empty_info(self) -> None:
        votos = np.array([40.0, 30.0, 10.0])
        resultado, info = distribuir_indecisos(
            votos,
            0.0,
            np.array([20.0, 30.0, 0.0]),
            ["Candidato A", "Candidato B", "Outros"],
        )

        np.testing.assert_array_equal(resultado, votos)
        assert resultado is not votos
        assert info == {}


    def test_redistributes_undecided_votes_and_reports_diagnostics(
        self,
    ) -> None:
        votos = np.array([40.0, 30.0, 0.0, 0.0])
        candidatos = ["Candidato A", "Candidato B", "Brancos", "Nulos"]

        resultado, info = distribuir_indecisos(
            votos,
            10.0,
            np.array([20.0, 30.0, 0.0, 0.0]),
            candidatos,
            blank_fraction=0.2,
        )

        assert resultado[0] > votos[0]
        assert resultado[1] > votos[1]
        assert resultado[2] == pytest.approx(1.0)
        assert resultado[3] == pytest.approx(1.0)
        assert resultado.sum() == pytest.approx(votos.sum() + 10.0)

        assert info["indecisos_total"] == 10.0
        assert info["indecisos_redistribuiveis"] == pytest.approx(8.0)
        assert info["indecisos_para_brancos"] == pytest.approx(2.0)
        assert info["blank_fraction"] == 0.2
        assert "ganho_por_candidato" in info

    def test_zero_weights_fall_back_to_equal_distribution(self) -> None:
        votos = np.array([0.0, 0.0])
        resultado, info = distribuir_indecisos(
            votos,
            10.0,
            np.array([100.0, 100.0]),
            ["Candidato A", "Candidato B"],
            blank_fraction=0.0,
        )

        np.testing.assert_allclose(resultado, [5.0, 5.0])
        assert info["indecisos_total"] == 10.0

    def test_no_distributable_candidates_returns_unchanged_votes(
        self,
    ) -> None:
        votos = np.array([20.0, 10.0])
        resultado, info = distribuir_indecisos(
            votos,
            10.0,
            np.array([0.0, 0.0]),
            ["Brancos", "Nulos"],
        )

        np.testing.assert_array_equal(resultado, votos)
        assert info == {}

class TestSimulacaoCasosLimite:
    """Tests for undecided votes and invalid vote-share inputs."""

    def test_simulation_with_undecided_voters(self) -> None:
        config = _make_config(n_sim=100)
        poll_data = _make_poll_data(indecisos=10.0)

        result = simular_primeiro_turno(config, poll_data)

        assert len(result.df) == 100
        assert isinstance(result.info_indecisos, dict)
        assert result.info_indecisos["indecisos_total"] == 10.0
        assert np.isfinite(result.df.select_dtypes(include=[np.number])).all().all()

    @pytest.mark.parametrize(
        "invalid_vote",
        [float("nan"), float("inf"), -1.0],
        ids=["nan", "infinity", "negative"],
    )
    def test_invalid_vote_shares_raise_value_error(
        self, invalid_vote: float
    ) -> None:
        config = _make_config(n_sim=10)
        poll_data = _make_poll_data(
            votos=[invalid_vote, 30.0, 12.0],
        )

        with pytest.raises(
            ValueError,
            match="Invalid vote shares before first-round simulation",
        ):
            simular_primeiro_turno(config, poll_data)