"""Version 2 first-round event contract, independent of the sampling model.

Exact ties use equal analytical credits among tied candidates (no RNG calls).
This is a model convention, not an implementation of legal age tie-breaks.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EVENTS_VERSION = 2


def eventos_primeiro_turno(votes: np.ndarray) -> dict[str, np.ndarray]:
    """Derive event indicators/credits from final valid-vote percentages.

    Direct win is strictly > 50%; exactly 50% requires a runoff. Qualification
    is unconditional: two places only on draws without a direct winner.
    Equal ties share the remaining ranked slots, preserving sum(credits)=slots.
    """
    votes = np.asarray(votes, dtype=float)
    if (votes.ndim != 2 or votes.shape[0] == 0 or votes.shape[1] < 2
            or not np.isfinite(votes).all() or (votes < 0).any()
            or not np.allclose(votes.sum(axis=1), 100., rtol=0, atol=1e-8)):
        raise ValueError('Events require nonempty, finite valid-vote shares summing to 100')
    maxima = votes.max(axis=1, keepdims=True)
    leader = votes == maxima
    leadership = leader / leader.sum(axis=1, keepdims=True)
    direct = votes > 50.0
    runoff = ~direct.any(axis=1)
    boundary = np.sort(votes, axis=1)[:, -2, None]
    above = votes > boundary
    tied = votes == boundary
    slots = 2 - above.sum(axis=1, keepdims=True)
    qualification = (above + tied * slots / tied.sum(axis=1, keepdims=True)) * runoff[:, None]
    return dict(lideranca=leadership, vitoria_1t=direct,
                classificacao_2t=qualification, segundo_turno=runoff)


def resumir_eventos(df: pd.DataFrame, candidates: list[str] | None = None) -> dict:
    """Summarize events from explicit valid-vote columns; never use raw shares."""
    candidates = candidates or [c[:-4] for c in df.columns if c.endswith('_val')]
    if not candidates:
        return {}
    events = eventos_primeiro_turno(df[[f'{c}_val' for c in candidates]].to_numpy())
    result = {f'p_{name}': dict(zip(candidates, map(float, events[name].mean(axis=0))))
              for name in ('lideranca', 'vitoria_1t', 'classificacao_2t')}
    result['p2t'] = float(events['segundo_turno'].mean())
    result['event_contract_version'] = EVENTS_VERSION
    return result


def adicionar_eventos(df: pd.DataFrame, candidates: list[str]) -> None:
    """Add explicit versioned per-draw events without changing vote draws."""
    events = eventos_primeiro_turno(df[[f'{c}_val' for c in candidates]].to_numpy())
    df['tem_2turno'] = events['segundo_turno']
    df['vencedor_1t'] = pd.array([
        candidates[int(np.argmax(v))] if v.any() else None
        for v in events['vitoria_1t']], dtype=object)
    for key in ('lideranca', 'vitoria_1t', 'classificacao_2t'):
        for i, candidate in enumerate(candidates):
            df[f'evento_{key}_{candidate}'] = events[key][:, i]
    df['event_contract_version'] = EVENTS_VERSION


def probabilidades_vitoria_2t(df: pd.DataFrame, candidates: list[str]) -> dict[str, float]:
    """P(win | runoff occurs), including qualification; exact final ties split 1/2.

    The caller must supply actual runoff rows, never hypothetical direct-win
    draws. The denominator is ALL retained runoff rows, including those in
    which a particular candidate is not a finalist (zero victory credit).
    The explicit occurrence flag, when present, is applied defensively.
    """
    if "tem_2turno" in df:
        df = df.loc[df["tem_2turno"]]
    if df.empty:
        return {}
    if {"finalista_a", "finalista_b", "voto_a", "voto_b"} <= set(df):
        a, b = df["voto_a"].to_numpy(), df["voto_b"].to_numpy()
        wins_a = (a > b).astype(float) + (a == b) * .5
        return {c: float(((df["finalista_a"] == c) * wins_a
                          + (df["finalista_b"] == c) * (1-wins_a)).mean())
                for c in candidates}
    if all(f"{c}_win" in df for c in candidates):
        credits = df[[f"{c}_win" for c in candidates]].to_numpy(dtype=float)
        # pandas.mean skips NaN and would silently change the denominator to
        # candidate-specific observed/qualified rows. Require explicit zeros.
        if (not np.isfinite(credits).all() or (credits < 0).any()
                or (credits > 1).any()
                or not np.allclose(credits.sum(axis=1), 1., rtol=0, atol=1e-8)):
            raise ValueError("Runoff win credits must be finite, in [0, 1], sum to 1 per row; "
                             "non-finalists require explicit zero credits")
        return dict(zip(candidates, map(float, credits.mean(axis=0))))
    raise ValueError("Conditional runoff victory requires explicit finalist/vote or win-credit columns")
