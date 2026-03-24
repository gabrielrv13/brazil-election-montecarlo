"""
Unit tests for src/core/simulation.py — v3.0
"""
import math
import numpy as np
import pytest
from datetime import date

from src.core.simulation import (
    aplicar_teto_rejeicao,
    distribuir_indecisos,
    _calcular_desvio_ajustado,
)


class TestCalcularDesvioAjustado:
    def test_past_election_returns_base(self):
        base = 2.0
        result = _calcular_desvio_ajustado(base, date(2025, 1, 1), date(2025, 6, 1))
        assert result == base

    def test_30_days_out_returns_base(self):
        base = 2.0
        election = date(2026, 10, 4)
        ref = date(2026, 9, 4)  # exactly 30 days before
        result = _calcular_desvio_ajustado(base, election, ref)
        assert abs(result - base) < 0.01

    def test_240_days_out_increases_desvio(self):
        base = 2.0
        election = date(2026, 10, 4)
        ref = date(2026, 2, 6)  # ~240 days before
        result = _calcular_desvio_ajustado(base, election, ref)
        assert result > base


class TestAplicarTetoRejeicao:
    def test_no_clipping_when_under_ceiling(self):
        votos = np.array([[40.0, 35.0], [38.0, 33.0]])
        rejeicao = np.array([42.0, 48.0])  # ceilings: 58, 52
        candidatos = ["Lula", "Flávio"]
        result, info = aplicar_teto_rejeicao(votos, rejeicao, candidatos)
        np.testing.assert_array_equal(result, votos)
        assert info == {}

    def test_clips_above_ceiling(self):
        votos = np.array([[60.0, 40.0]])  # Lula above ceiling of 58
        rejeicao = np.array([42.0, 48.0])
        candidatos = ["Lula", "Flávio"]
        result, info = aplicar_teto_rejeicao(votos, rejeicao, candidatos)
        assert result[0, 0] == 58.0
        assert result[0, 1] == 40.0
        assert "Lula" in info

    def test_zero_rejection_no_ceiling(self):
        votos = np.array([[80.0, 20.0]])
        rejeicao = np.array([0.0, 0.0])
        candidatos = ["A", "B"]
        result, info = aplicar_teto_rejeicao(votos, rejeicao, candidatos)
        np.testing.assert_array_equal(result, votos)
        assert info == {}


class TestDistribuirIndecisos:
    def test_zero_indecisos_no_change(self):
        base = np.array([35.0, 29.0, 21.0, 15.0])
        rejeicao = np.array([42.0, 48.0, 0.0, 0.0])
        candidatos = ["Lula", "Flávio", "Outros", "Brancos/Nulos"]
        result, info = distribuir_indecisos(base, 0.0, rejeicao, candidatos)
        np.testing.assert_array_equal(result, base)
        assert info == {}

    def test_redistributed_sum_conserved(self):
        base = np.array([35.0, 29.0, 21.0, 15.0])
        rejeicao = np.array([42.0, 48.0, 0.0, 0.0])
        candidatos = ["Lula", "Flávio", "Outros", "Brancos/Nulos"]
        indecisos = 12.0
        result, info = distribuir_indecisos(base, indecisos, rejeicao, candidatos)
        assert abs(result.sum() - (base.sum() + indecisos)) < 0.01

    def test_higher_rejection_absorbs_less(self):
        base = np.array([35.0, 29.0])
        rejeicao = np.array([30.0, 60.0])  # Flávio higher rejection
        candidatos = ["Lula", "Flávio"]
        result, info = distribuir_indecisos(base, 10.0, rejeicao, candidatos)
        gain_lula = result[0] - base[0]
        gain_flavio = result[1] - base[1]
        assert gain_lula > gain_flavio