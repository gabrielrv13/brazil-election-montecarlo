"""
Polymarket edge calculation for brazil-election-montecarlo.

Pure functions: no I/O, no global state, no side effects.
All inputs arrive as parameters; all outputs are returned as dicts.
"""

from __future__ import annotations

import pandas as pd


def polymarket_edge(
    df1: pd.DataFrame,
    threshold: float,
    market_prob: float,
    candidate: str | None = None,
) -> dict:
    """
    Compute the edge between the model and a Polymarket margin market.

    If ``candidate`` is provided, the probability is conditioned on that
    candidate leading — i.e. ``P(margem_<candidate> > threshold)``, which
    is positive only in simulations where that candidate finishes first.
    Otherwise the unsigned ``margem_1t`` column is used (absolute gap
    between 1st and 2nd place), regardless of who leads.

    Parameters
    ----------
    df1:
        First-round simulation results DataFrame, as returned by
        ``src.core.simulation.simular_primeiro_turno()``.
        Must contain ``"margem_1t"`` (unconditional) or
        ``"margem_<candidate>"`` (conditional) columns.
    threshold:
        Margin threshold in percentage points (e.g. ``15.0`` for the
        Lula >15pp market).
    market_prob:
        Polymarket implied probability as a decimal in [0, 1]
        (e.g. ``0.55`` for a market priced at 55 cents).
    candidate:
        Optional candidate name to condition on (e.g. ``"Lula"``).
        When supplied, only simulations where that candidate is leading
        contribute to ``model_prob``.

    Returns
    -------
    dict
        Keys:

        * ``model_prob``     – ``P(margin > threshold)`` from the model, in [0, 1].
        * ``market_prob``    – Echo of the ``market_prob`` argument.
        * ``edge``           – ``model_prob − market_prob`` (positive = model
          favours YES; actionable when >= 0.12 in the primary entry window).
        * ``kelly_fraction`` – Half-Kelly stake as a fraction of bankroll;
          0.0 when ``edge <= 0``.
        * ``threshold_pp``   – Echo of ``threshold``.
        * ``candidate``      – Echo of ``candidate`` (or ``None``).
        * ``n_sim``          – Number of simulations used.

    Raises
    ------
    KeyError
        If the required margin column is missing from ``df1``.
    ValueError
        If ``market_prob`` is not in (0, 1].

    Notes
    -----
    Half-Kelly formula::

        b = (1 / market_prob) - 1
        full_kelly = (b * model_prob - (1 - model_prob)) / b
        kelly_fraction = max(0, full_kelly) / 2

    The Lula overall-winner edge is generally not actionable because
    Polymarket prices political and legal risk outside the model's scope.
    The 5–10pp margin market is the most reliable signal.
    """
    if not (0.0 < market_prob <= 1.0):
        raise ValueError(
            f"market_prob must be in (0, 1], got {market_prob}"
        )

    if candidate is not None:
        col = f"margem_{candidate}"
        if col not in df1.columns:
            raise KeyError(
                f"Column '{col}' not found in df1. "
                f"Check that simular_primeiro_turno() was called with this candidate "
                f"or verify the spelling: {list(df1.columns)}"
            )
        series = df1[col]  # signed: positive only when candidate is leading
    else:
        if "margem_1t" not in df1.columns:
            raise KeyError(
                "Column 'margem_1t' not found in df1. "
                "Ensure simular_primeiro_turno() populated the margin columns."
            )
        series = df1["margem_1t"]

    model_prob = float((series > threshold).mean())
    edge = model_prob - market_prob

    if edge > 0 and market_prob < 1.0:
        b = (1.0 / market_prob) - 1.0
        full_kelly = (b * model_prob - (1.0 - model_prob)) / b
        kelly_fraction = max(0.0, full_kelly / 2.0)
    else:
        kelly_fraction = 0.0

    return {
        "model_prob":      round(model_prob, 4),
        "market_prob":     round(market_prob, 4),
        "edge":            round(edge, 4),
        "kelly_fraction":  round(kelly_fraction, 4),
        "threshold_pp":    threshold,
        "candidate":       candidate,
        "n_sim":           len(df1),
    }