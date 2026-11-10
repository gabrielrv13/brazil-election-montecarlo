"""
Proper scoring rules and calibration diagnostics for probabilistic forecasts.

Pure functions (NumPy only). Conventions:

* probabilities are on the 0-1 scale;
* lower is better for Brier, log score (as negative log-likelihood), CRPS and
  interval score;
* a PIT value is the predictive CDF evaluated at the outcome; for a calibrated
  forecast PIT values are Uniform(0, 1) across events.

References: Gneiting & Raftery (2007), "Strictly proper scoring rules,
prediction, and estimation", JASA 102(477).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

_EPS = 1e-12


def brier_multiclasse(probabilidades: Mapping[str, float], ocorrido: str) -> float:
    """Multiclass Brier score ``sum_c (p_c - y_c)^2`` in ``[0, 2]``.

    Classes missing from ``probabilidades`` count as probability 0. The
    pre-v3 backtest used ``(p_winner - 1)^2``, which ignores the mass placed
    on wrong classes.
    """
    classes = set(probabilidades) | {ocorrido}
    return float(sum(
        (probabilidades.get(c, 0.0) - (1.0 if c == ocorrido else 0.0)) ** 2
        for c in classes
    ))


def brier_binario(p: float, ocorreu: bool) -> float:
    """Brier score of a binary event, ``(p - y)^2``."""
    return float((p - (1.0 if ocorreu else 0.0)) ** 2)


def log_score(p_ocorrido: float, eps: float = 1e-4) -> float:
    """Negative log-likelihood of the realised outcome.

    ``p`` is clipped to ``[eps, 1 - eps]`` so a Monte Carlo estimate of 0
    (an event never seen in the draws) gives a large but finite penalty.
    """
    return float(-np.log(np.clip(p_ocorrido, eps, 1.0 - eps)))


def crps_amostral(amostras: Sequence[float] | np.ndarray, y: float) -> float:
    """Sample CRPS, ``E|X - y| - 0.5 E|X - X'|`` (same unit as ``y``).

    Uses the sorted-sample identity for ``E|X - X'|`` so the cost is
    O(n log n) instead of O(n^2).
    """
    x = np.sort(np.asarray(amostras, dtype=float))
    n = x.size
    if n == 0:
        raise ValueError("CRPS needs at least one sample")
    termo1 = np.mean(np.abs(x - y))
    i = np.arange(1, n + 1)
    # E|X - X'| = 2/n^2 * sum_i (2i - n - 1) x_(i)
    termo2 = 2.0 * np.sum((2 * i - n - 1) * x) / n**2
    return float(termo1 - 0.5 * termo2)


def pit(amostras: Sequence[float] | np.ndarray, y: float) -> float:
    """Probability integral transform with mid-ranks for ties."""
    x = np.asarray(amostras, dtype=float)
    return float((np.mean(x < y) + np.mean(x <= y)) / 2.0)


def cobertura(
    amostras: Sequence[float] | np.ndarray,
    y: float,
    niveis: Sequence[float] = (0.5, 0.8, 0.9),
) -> dict[float, bool]:
    """Whether ``y`` falls in each central interval of the samples."""
    x = np.asarray(amostras, dtype=float)
    out = {}
    for nivel in niveis:
        lo, hi = np.quantile(x, [(1 - nivel) / 2, (1 + nivel) / 2])
        out[float(nivel)] = bool(lo <= y <= hi)
    return out


def interval_score(lo: float, hi: float, y: float, alpha: float) -> float:
    """Interval score of a central ``(1 - alpha)`` interval (lower is better).

    ``(hi - lo) + 2/alpha * (lo - y)_+ + 2/alpha * (y - hi)_+``.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if hi < lo:
        raise ValueError("Interval upper bound below lower bound")
    return float((hi - lo) + 2 / alpha * max(lo - y, 0.0) + 2 / alpha * max(y - hi, 0.0))
