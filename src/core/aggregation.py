from __future__ import annotations

import numpy as np
import pandas as pd

def calcular_peso_temporal(data_pesquisa, data_referencia, tau=7):
    """
    Calculates temporal weight for a poll using exponential decay.
    
    More recent polls receive higher weights.
    
    Args:
        data_pesquisa: Poll date (string YYYY-MM-DD or date object)
        data_referencia: Reference date (usually today)
        tau: Time constant in days (default: 7 days)
    
    Returns:
        float: Weight between 0 and 1
    
    Formula:
        peso = exp(-dias_atras / tau)
        
    Examples:
        Today: weight = 1.0
        7 days ago: weight = 0.368 (1/e)
        14 days ago: weight = 0.135 (1/e²)
    """
    from src.core.poll_quality import parse_date
    if not np.isfinite(tau) or tau <= 0:
        raise ValueError("tau must be finite and positive")
    d = parse_date(data_pesquisa)
    if d is None or d > data_referencia:
        raise ValueError(f"Invalid, missing or future poll date: {data_pesquisa!r}")
    return float(np.exp(-(data_referencia - d).days / tau))

def detectar_outliers(valores, threshold=2.5):
    """
    Detects outliers using modified z-score method (robust to outliers).
    
    Uses median absolute deviation (MAD) instead of standard deviation.
    
    Args:
        valores: Array of values
        threshold: Modified z-score threshold (default: 2.5)
    
    Returns:
        Array of boolean indicating outliers (True = outlier)
    """
    if len(valores) < 3:
        return np.zeros(len(valores), dtype=bool)
    
    mediana = np.median(valores)
    mad = np.median(np.abs(valores - mediana))
    
    if mad == 0:
        return np.zeros(len(valores), dtype=bool)
    
    # Modified z-score
    z_scores = 0.6745 * (valores - mediana) / mad
    return np.abs(z_scores) > threshold

def agregar_pesquisas_candidato(df_candidato, data_referencia):
    """
    Aggregates multiple polls for a single candidate.
    
    Uses temporal weighting and detects outliers.
    
    Args:
        df_candidato: DataFrame with polls for one candidate
        data_referencia: Reference date for temporal weighting
    
    Returns:
        tuple: (voto_agregado, rejeicao_agregada, desvio_agregado, info)
            - voto_agregado: Weighted mean of vote intention
            - rejeicao_agregada: Weighted mean of rejection
            - desvio_agregado: Combined standard deviation
            - info: Dictionary with aggregation details
    """
    if "data" not in df_candidato or df_candidato.empty:
        raise ValueError("Missing dates or empty poll input")
    for value in df_candidato["data"]:
        calcular_peso_temporal(value, data_referencia)
    n_pesquisas = len(df_candidato)
    
    # Single poll - no aggregation needed
    if n_pesquisas == 1:
        row = df_candidato.iloc[0]
        return (
            row['intencao_voto_pct'],
            row.get('rejeicao_pct', 0.0),
            row['desvio_padrao_pct'],
            {
                'n_pesquisas': 1,
                'n_validas': 1,
                'institutos': [row.get('instituto', 'Unknown')],
                'outliers': [],
                'desvio_medio': row['desvio_padrao_pct'],
                'desvio_entre': 0.0
            }
        )
    
    # Calculate temporal weights
    if 'data' in df_candidato.columns:
        pesos = df_candidato['data'].apply(
            lambda d: calcular_peso_temporal(d, data_referencia)
        ).values
    else:
        pesos = np.ones(n_pesquisas)
    
    # Normalize weights
    pesos = pesos / pesos.sum()
    
    # Detect outliers in vote intention
    votos = df_candidato['intencao_voto_pct'].values
    is_outlier = detectar_outliers(votos)
    
    # Calculate weighted mean (excluding outliers)
    mask_validos = ~is_outlier
    if mask_validos.sum() == 0:
        # All polls are outliers - keep all
        mask_validos = np.ones(n_pesquisas, dtype=bool)
    
    pesos_validos = pesos[mask_validos]
    pesos_validos = pesos_validos / pesos_validos.sum()
    
    # Weighted vote intention
    voto_agregado = np.average(
        df_candidato.loc[mask_validos, 'intencao_voto_pct'].values,
        weights=pesos_validos
    )
    
    # Weighted rejection (if available)
    # Rows with rejeicao_pct == 0 are treated as not measured, not as true zero rejection.
    # Only polls that explicitly reported a rejection value (> 0) are included.
    if 'rejeicao_pct' in df_candidato.columns:
        # Rejection is an independent measurement from vote intention.
        # Outlier exclusion applied to vote intention (mask_validos) must NOT
        # carry over here — a poll flagged as a vote outlier may still report
        # a valid rejection value. Filter only on rejeicao_pct > 0.
        mask_tem_rejeicao = df_candidato['rejeicao_pct'].values > 0
        if mask_tem_rejeicao.any():
            pesos_rej = pesos[mask_tem_rejeicao]
            pesos_rej = pesos_rej / pesos_rej.sum()
            rejeicao_agregada = float(np.average(
                df_candidato['rejeicao_pct'].values[mask_tem_rejeicao],
                weights=pesos_rej
            ))
        else:
            rejeicao_agregada = 0.0
    else:
        rejeicao_agregada = 0.0
    
    # Calculate aggregated standard deviation
    # Formula: σ_agregado = √(σ_médio² + σ_entre_institutos²)
    
    # Average within-poll standard deviation
    desvio_medio = np.average(
        df_candidato.loc[mask_validos, 'desvio_padrao_pct'].values,
        weights=pesos_validos
    )
    
    # Between-institute variance
    variancia_entre = np.average(
        (df_candidato.loc[mask_validos, 'intencao_voto_pct'].values - voto_agregado) ** 2,
        weights=pesos_validos
    )
    desvio_entre = np.sqrt(variancia_entre)
    
    # Combined standard deviation
    desvio_agregado = np.sqrt(desvio_medio**2 + desvio_entre**2)
    
    # Collect info for reporting
    institutos = df_candidato['instituto'].tolist() if 'instituto' in df_candidato.columns else ['Unknown'] * n_pesquisas
    outliers_info = [
        {'instituto': inst, 'valor': val}
        for inst, val, is_out in zip(institutos, votos, is_outlier)
        if is_out
    ]
    
    info = {
        'n_pesquisas': n_pesquisas,
        'n_validas': int(mask_validos.sum()),
        'institutos': institutos,
        'outliers': outliers_info,
        'desvio_medio': float(desvio_medio),
        'desvio_entre': float(desvio_entre)
    }

    return voto_agregado, rejeicao_agregada, desvio_agregado, info


# ═════════════════════════════════════════════════════════════════════════════
# v3 aggregator: house effects, detrended outliers, sd of the weighted mean
# ═════════════════════════════════════════════════════════════════════════════
#
# The functions above are the v2 contract and stay for compatibility. Their
# dispersion mixes three different things: the margin of error of a single
# poll, the temporal trend and the systematic difference between institutes.
# The aggregator below separates them:
#
#   x_j = trend(t_j) + house(institute_j) + noise_j
#
# * house effects are estimated from residuals against a leave-institute-out
#   local trend, shrunk toward zero and centred on the industry average (the
#   industry-wide error is not identifiable from polls and is modelled in the
#   engine as the common election error);
# * outliers are flagged on detrended, house-adjusted residuals, so a
#   candidate whose support moved over the campaign is not trimmed;
# * the reported uncertainty is the standard error of the weighted mean,
#   sqrt(sum w^2 (SE_j^2 + tau^2)) / sum w, where SE_j comes from the poll's
#   stated margin of error and tau^2 is the dispersion left beyond sampling.

from dataclasses import dataclass, field

# desvio_padrao_pct in the poll CSVs holds the published 95% margin of error.
Z_MARGEM_ERRO: float = 1.96
# Modified z-score threshold (Iglewicz & Hoaglin) on detrended residuals.
LIMIAR_OUTLIER: float = 3.5
MIN_PESQUISAS_OUTLIER: int = 5


@dataclass
class AgregacaoCandidato:
    """Aggregated estimate for one candidate (all values in pp)."""

    voto: float
    rejeicao: float
    sd_media: float
    info: dict = field(default_factory=dict)


def _dias(datas: np.ndarray, data_referencia) -> np.ndarray:
    from src.core.poll_quality import parse_date
    out = []
    for value in datas:
        d = parse_date(value)
        if d is None or d > data_referencia:
            raise ValueError(f"Invalid, missing or future poll date: {value!r}")
        out.append((data_referencia - d).days)
    return np.asarray(out, dtype=float)


def _tendencia_local(
    idade: np.ndarray, valores: np.ndarray, grupos: np.ndarray, tau: float,
    excluir_mesmo_grupo: bool,
) -> np.ndarray:
    """Leave-one-out exponential-kernel trend at each poll date.

    With ``excluir_mesmo_grupo`` the polls of the same institute are left out
    too, so the trend does not absorb that institute's own house effect.
    Returns NaN where no other poll is available.
    """
    dist = np.abs(idade[:, None] - idade[None, :])
    kernel = np.exp(-dist / tau)
    np.fill_diagonal(kernel, 0.0)
    if excluir_mesmo_grupo:
        kernel = np.where(grupos[:, None] == grupos[None, :], 0.0, kernel)
    soma = kernel.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(soma > 0, kernel @ valores / np.where(soma > 0, soma, 1.0), np.nan)


def estimar_efeitos_instituto(
    df: pd.DataFrame,
    data_referencia,
    tau_tendencia: float = 7.0,
    tau_casa: float = 60.0,
    encolhimento: float = 3.0,
    iteracoes: int = 25,
    tolerancia: float = 1e-4,
) -> dict[tuple[str, str], float]:
    """Estimate the house effect (pp) of each institute for each candidate.

    For each candidate, residuals are taken against a local trend built only
    from *other* institutes. An institute's raw effect is the
    ``exp(-age/tau_casa)``-weighted mean of its residuals, shrunk by
    ``n_eff / (n_eff + encolhimento)`` and finally centred so the weighted
    average effect across institutes is zero. Passes repeat on house-adjusted
    trends until the effects move less than ``tolerancia`` (a single pass
    overshoots because the first trend still carries the other houses'
    effects).

    Args:
        df: Poll rows with ``candidato``, ``instituto``, ``data`` and
            ``intencao_voto_pct``.
        data_referencia: as-of date; later polls raise ``ValueError``.
        tau_tendencia: Kernel time constant for the local trend (days).
        tau_casa: Time constant for weighting an institute's residuals.
        encolhimento: Pseudo-count of the shrinkage toward zero.
        iteracoes: Maximum refinement passes.
        tolerancia: Convergence threshold (pp) on the largest change.

    Returns:
        ``{(instituto, candidato): efeito_pp}``. Empty when fewer than two
        institutes are present (no effect is identifiable).
    """
    if "instituto" not in df.columns or df["instituto"].nunique() < 2:
        return {}
    efeitos: dict[tuple[str, str], float] = {}
    for cand, g in df.groupby("candidato", sort=False):
        idade = _dias(g["data"].to_numpy(), data_referencia)
        x = g["intencao_voto_pct"].to_numpy(dtype=float)
        inst = g["instituto"].astype(str).to_numpy()
        v = np.exp(-idade / tau_casa)
        h = np.zeros(len(g))
        for _ in range(max(1, iteracoes)):
            trend = _tendencia_local(idade, x - h, inst, tau_tendencia, True)
            # Compare each poll with the other institutes' (adjusted) trend.
            resid = x - trend
            brutos, massa = {}, {}
            for nome in np.unique(inst):
                m = (inst == nome) & np.isfinite(resid)
                if not m.any():
                    continue
                vm = v[m]
                raw = float(np.average(resid[m], weights=vm))
                n_eff = vm.sum() ** 2 / (vm**2).sum()
                brutos[nome] = raw * n_eff / (n_eff + encolhimento)
                massa[nome] = float(vm.sum())
            if not brutos:
                break
            centro = np.average(list(brutos.values()), weights=list(massa.values()))
            ef = {k: val - centro for k, val in brutos.items()}
            novo = np.array([ef.get(nome, 0.0) for nome in inst])
            convergiu = np.max(np.abs(novo - h)) < tolerancia
            h = novo
            if convergiu:
                break
        for nome in np.unique(inst):
            efeitos[(nome, cand)] = float(h[inst == nome][0])
    return efeitos


def agregar_pesquisas(
    df: pd.DataFrame,
    data_referencia,
    tau: float = 7.0,
    efeitos_instituto: bool = True,
    limiar_outlier: float = LIMIAR_OUTLIER,
) -> dict[str, AgregacaoCandidato]:
    """Aggregate every candidate of one poll scenario (v3 contract).

    Args:
        df: Validated poll rows (``candidato``, ``intencao_voto_pct``,
            ``desvio_padrao_pct``, ``data``; optional ``instituto``,
            ``rejeicao_pct``).
        data_referencia: as-of date; dates after it raise ``ValueError``.
        tau: Time constant (days) of the exponential recency weight.
        efeitos_instituto: Subtract shrunk house effects before averaging.
        limiar_outlier: Modified z threshold on detrended residuals; applied
            only with at least ``MIN_PESQUISAS_OUTLIER`` polls.

    Returns:
        ``{candidato: AgregacaoCandidato}`` in input order.
    """
    if df.empty or "data" not in df.columns:
        raise ValueError("Missing dates or empty poll input")
    if not np.isfinite(tau) or tau <= 0:
        raise ValueError("tau must be finite and positive")
    efeitos = estimar_efeitos_instituto(df, data_referencia, tau) if efeitos_instituto else {}
    if "instituto" in df.columns:
        inst_col = df["instituto"].astype(str)
    else:
        inst_col = pd.Series(["Unknown"] * len(df), index=df.index)

    out: dict[str, AgregacaoCandidato] = {}
    for cand in df["candidato"].unique():
        g = df[df["candidato"] == cand]
        inst = inst_col.loc[g.index].to_numpy()
        idade = _dias(g["data"].to_numpy(), data_referencia)
        bruto = g["intencao_voto_pct"].to_numpy(dtype=float)
        casa = np.array([efeitos.get((i, cand), 0.0) for i in inst])
        y = np.maximum(bruto - casa, 0.0)  # a share cannot go below zero
        se = g["desvio_padrao_pct"].to_numpy(dtype=float) / Z_MARGEM_ERRO
        w = np.exp(-idade / tau)

        trend = _tendencia_local(idade, y, inst, tau, False)
        resid = np.where(np.isfinite(trend), y - trend, 0.0)
        outlier = np.zeros(len(g), dtype=bool)
        if len(g) >= MIN_PESQUISAS_OUTLIER:
            med = np.median(resid)
            mad = np.median(np.abs(resid - med))
            if mad > 0:
                outlier = np.abs(0.6745 * (resid - med) / mad) > limiar_outlier
        ok = ~outlier if (~outlier).any() else np.ones(len(g), dtype=bool)

        wn = w[ok] / w[ok].sum()
        voto = float(wn @ y[ok])
        # Dispersion beyond sampling error, from detrended residuals.
        excesso = float(wn @ resid[ok] ** 2 - wn @ se[ok] ** 2) if len(g) > 1 else 0.0
        tau2 = max(0.0, excesso)
        sd_media = float(np.sqrt(wn**2 @ (se[ok] ** 2 + tau2)))

        rej = 0.0
        if "rejeicao_pct" in g.columns:
            r = g["rejeicao_pct"].to_numpy(dtype=float)
            m = r > 0  # zero means "not measured"
            if m.any():
                rej = float(np.average(r[m], weights=w[m]))

        out[cand] = AgregacaoCandidato(
            voto=voto, rejeicao=rej, sd_media=sd_media,
            info={
                "n_pesquisas": int(len(g)),
                "n_validas": int(ok.sum()),
                "n_efetivo": float(1.0 / (wn**2).sum()),
                "sd_extra": float(np.sqrt(tau2)),
                "media_bruta": float(w[ok] @ bruto[ok] / w[ok].sum()),
                "efeitos_instituto": {
                    i: float(e) for i, e in zip(inst, casa) if e != 0.0
                },
                "outliers": [
                    {"instituto": i, "valor": float(v)}
                    for i, v, o in zip(inst, bruto, outlier) if o
                ],
            },
        )
    return out


def sd_referencia_50(
    agregados: dict[str, AgregacaoCandidato], piso_share: float = 10.0
) -> float:
    """Convert per-candidate sd of the mean into the engine's 50%-share sd.

    The engine scales a 50%-reference sd by ``sqrt(4p(1-p))``; each
    candidate's sd is converted back to that reference and averaged over
    candidates with at least ``piso_share`` pp (the contenders that decide
    the outcome), or over all candidates when none qualifies.
    """
    total = sum(a.voto for a in agregados.values())
    itens = []
    for a in agregados.values():
        p = min(max(a.voto / total, 1e-3), 1 - 1e-3) if total > 0 else 0.5
        itens.append((a.voto, a.sd_media / np.sqrt(4 * p * (1 - p))))
    escolhidos = [s for v, s in itens if v >= piso_share] or [s for _, s in itens]
    return float(np.mean(escolhidos))